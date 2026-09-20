# AI Provider Gateway 与 Agent Runtime 设计文档

- **状态**: Draft（待用户审阅）
- **日期**: 2026-09-20
- **范围**: 平台第一期子项目——AI 接入层 + Agent 执行引擎
- **不在此范围内**: 产品管理模块、项目管理模块、多租户隔离、RAG、Slack/飞书通知、UI 完整实现

## 1. 背景与目标

搭建一个面向 1–20 人小团队的 Agent 平台，第一期目标是把基础设施打牢：

1. **统一 AI 接入层**：把自建推理服务（vLLM / Ollama / SGLang，OpenAI 兼容协议）和商用 API（OpenAI / DeepSeek / 通义 / 智谱 等）抽象成同一个调用接口，支持路由、故障转移、token 计费。
2. **Agent 执行引擎**：基于 YAML 定义 agent，支持工具调用型 agent（ReAct 循环）和定时触发型工作流，为后续 PM/PjM 业务模块（任务管理、PRD 检索、状态报告）提供可复用运行时。

**非目标（明确排除）**：不替代 LangChain 生态的全部能力，不追求零代码 agent 编排，不实现向量检索/知识库。

## 2. 关键假设

| 维度 | 假设 |
|---|---|
| 自建服务形态 | OpenAI 兼容推理端点（vLLM/Ollama/SGLang），对外 `/v1/chat/completions`，配 `base_url`+`key` |
| 商用 API | 优先支持 OpenAI 兼容厂商（OpenAI/DeepSeek/Qwen/GLM/one-api 网关），Anthropic/Gemini 留接口、v1 不实现 |
| Agent 语义 | 工具调用型（ReAct）+ 定时/触发型工作流，不是纯聊天机器人 |
| 部署模型 | 1–20 人小团队共享一个实例，账号 + 简单角色（owner/member），不做租户隔离 |
| 技术栈 | Python 3.11+ / FastAPI / SQLAlchemy + SQLite（v1，预留 PG） / Redis（队列/调度） / APScheduler |
| 流式 | SSE 透传，UI 层 v1 不实现（仅提供 API） |

## 3. 模块边界（按"可独立理解 + 可独立测试"切分）

```
┌─────────────────────────────────────────────────────────────┐
│  FastAPI App  (app/api/)                                    │
│  - auth / providers / agents / sessions / usage             │
└──────────────┬──────────────────────────────────────────────┘
               │ 依赖
       ┌───────┴────────┬──────────────────────┐
       ▼                ▼                      ▼
┌─────────────┐ ┌──────────────────┐ ┌────────────────────┐
│ Provider    │ │ Agent Runtime    │ │ Tools Registry     │
│ Gateway     │ │ - loader         │ │ - 注册装饰器       │
│ - adapters  │ │ - ReAct loop     │ │ - schema 构造      │
│ - router    │ │ - history        │ │ - 调用分发          │
│ - accounting│ │ - scheduler      │ │                    │
└──────┬──────┘ └────────┬─────────┘ └─────────┬──────────┘
       │ 依赖（运行时)     │ 依赖(运行时)         │ 叶子节点
       │                  │                      │ 后续 PM/PjM 模块在此注册工具
   ┌───▼───┐         ┌────▼────┐           ┌───▼────┐
   │SQLite│         │ Redis    │           │ (无)   │
   │      │         │ scheduler│           │        │
   └──────┘         └──────────┘           └────────┘
```

**依赖方向严格单向**：API → {Provider, Agent, Tools} → 基础设施。Tools 是叶子节点，不依赖其他业务模块；Provider 不依赖 Agent（Agent 调用 Provider）；Agent 依赖 Provider 和 Tools。这样后续加 PM/PjM 模块时只往 Tools 里加新工具，不动其他层。

## 4. Provider Gateway 详细设计

### 4.1 抽象接口

```python
# app/providers/base.py
from typing import Protocol, AsyncIterator

class LLMClient(Protocol):
    provider_id: str
    provider_type: str  # "openai_compat" | "anthropic" | "gemini"

    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolSchema] | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        stream: bool = False,
    ) -> CompletionResponse | AsyncIterator[Chunk]: ...

@dataclass
class Message:
    role: str           # system | user | assistant | tool
    content: str | None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None
    name: str | None = None  # tool name when role == "tool"

@dataclass
class CompletionResponse:
    content: str | None
    tool_calls: list[ToolCall]
    usage: TokenUsage
    finish_reason: str
    raw: dict  # 原始响应，用于调试

@dataclass
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
```

### 4.2 Adapter 实现

| Adapter | 文件 | 行数预估 | 覆盖厂商 |
|---|---|---|---|
| `OpenAICompatAdapter` | `adapters/openai_compat.py` | ~80 | vLLM / Ollama / SGLang / OpenAI / DeepSeek / Qwen / GLM / one-api |
| `AnthropicAdapter` | `adapters/anthropic.py` | ~120（接口预留，v1 不实现） | Anthropic |
| `GeminiAdapter` | `adapters/gemini.py` | ~120（接口预留，v1 不实现） | Google Gemini |

每个 adapter 实现：
1. 把统一 `Message` 格式转成厂商请求体
2. 把厂商响应转回统一 `CompletionResponse`
3. 从响应中抽取 token usage（不同厂商字段名不同）
4. 工具调用格式转换（OpenAI `tools` vs Anthropic `tool_use` content block）

### 4.3 路由策略

```python
# app/providers/router.py
class Router:
    strategies = {
        "cost_first":       lambda providers, model: sorted_by_cost(providers, model),
        "self_hosted_first": lambda providers, model: self_hosted_then_commercial(providers, model),
        "priority":         lambda providers, model: sorted_by_priority(providers, model),
    }

    async def complete(self, req: CompletionRequest) -> CompletionResponse:
        ordered = self.strategies[self.strategy](self.providers, req.model)
        last_err = None
        for provider in ordered:
            try:
                resp = await provider.chat(...)
                self.accounting.record(provider, req, resp)  # 计费落库
                return resp
            except (ProviderUnavailable, ProviderTimeout, RateLimited) as e:
                last_err = e
                continue
        raise AllProvidersFailed(last_err)
```

策略可全局配置，也可在 agent 定义里覆盖。`failover` 是无条件的：任何 5xx / 超时 / 限流都跳到下一个 provider。

### 4.4 Token 计费

数据抽取来源：
- OpenAI/compat: `response.usage.{prompt_tokens, completion_tokens, total_tokens}`
- Anthropic: `response.usage.{input_tokens, output_tokens}`
- Gemini: `response.usageMetadata.{promptTokenCount, candidatesTokenCount, totalTokenCount}`

成本计算：`provider.models_json[model].cost_per_1k_in/out × tokens / 1000` → 写入 `token_usage` 表（见 §5）。计费发生在 Router 层（不在 adapter 内），保证所有 provider 调用都被记账，包括 failover 重试。

## 5. 数据模型（SQLite v1，SQLAlchemy ORM）

```sql
-- 用户与权限
users(id PK, email UNIQUE, password_hash, role, created_at)
-- role: "owner" | "member"，owner 才能管理 provider/agent 配置

-- Provider 配置
providers(id PK, name UNIQUE, type, base_url, api_key_enc, models_json,
          priority, strategy, enabled, created_at, updated_at)
-- type:        "openai_compat" | "anthropic" | "gemini"
-- models_json: [{"model": "Qwen2.5-72B-Instruct",
--               "cost_per_1k_in_cents": 0, "cost_per_1k_out_cents": 0},
--              {"model": "deepseek-chat",
--               "cost_per_1k_in_cents": 0.1, "cost_per_1k_out_cents": 0.3}]
-- priority:    int，数字越小优先级越高
-- strategy:    "cost_first" | "self_hosted_first" | "priority"（覆盖全局）

-- Agent 定义
agents(id PK, name UNIQUE, system_prompt, tools_json, default_provider_id FK,
       default_model, temperature, max_history, retry_strategy_json,
       schedule_cron, schedule_input, enabled, created_by FK, created_at)
-- tools_json:        ["create_task", "query_prd", ...]
-- retry_strategy_json: {"max_iterations": 8}
-- schedule_cron:     "0 9 * * 1" 或 NULL
-- schedule_input:    "生成上周产品周报" 或 NULL

-- 会话与消息
sessions(id PK, agent_id FK, user_id FK, title, created_at, updated_at)
messages(id PK, session_id FK, role, content_json, tool_calls_json,
         tool_call_id, token_count, created_at)
-- content_json:  {"text": "..."} 或 {"tool_result": "..."}
-- tool_calls_json: [{"id": "...", "name": "...", "args": {...}}]
-- 按 session_id + created_at 排序即得对话历史

-- Token 计费
token_usage(id PK, provider_id FK, user_id FK, agent_id FK, session_id FK,
            model, prompt_tokens, completion_tokens, total_tokens,
            cost_cents, latency_ms, status, created_at)
-- status: "success" | "failed"
-- 一条 provider 调用一行记录，failover 会产生多条（失败的标 failed）

-- 审计
audit_log(id PK, user_id FK, action, target_type, target_id, detail_json, created_at)
```

**为什么不用 PG**：v1 团队规模 ≤20 人，单实例 SQLite + WAL 模式足够；所有 SQL 都走 ORM，后续切 PG 只改 connection string + 少量方言。

## 6. Agent Runtime 详细设计

### 6.1 Agent YAML 格式

```yaml
# agents/pm-assistant.yaml
name: pm-assistant
system_prompt: |
  你是产品管理助手。用户会询问产品规划、PRD 撰写、特性优先级等问题。
  当需要操作任务、查询路线图时，调用对应工具。回答简洁、可执行。
tools:
  - create_task
  - query_prd
  - list_roadmap
default_provider: vllm-local       # provider.name
default_model: Qwen2.5-72B-Instruct
temperature: 0.3
max_history: 20                     # 进入上下文的历史消息数
retry:
  max_iterations: 8                 # ReAct 最大轮次（工具错误在轮次内自然回灌重试）
schedule:                           # 可选；省略则纯交互型
  cron: "0 9 * * 1"                 # 周一 09:00
  input: "基于上周 sessions 生成产品周报"
```

启动时 `loader.py` 扫描 `agents/*.yaml`，upsert 到 `agents` 表（按 `name` 唯一）。后续通过 API 创建/修改 agent 也写入同一张表。

### 6.2 ReAct 循环（核心 ~200 行）

```python
# app/agents/runtime.py
async def run(self, agent, user_msg, session_id) -> AsyncIterator[Event]:
    history = await self.history.load(session_id, limit=agent.max_history)
    messages = [Message("system", agent.system_prompt)] + history + [Message("user", user_msg)]
    tools = self.tools.schemas_for(agent.tools)

    for iteration in range(agent.retry.max_iterations):
        resp = await self.router.complete(CompletionRequest(
            messages=messages, tools=tools, model=agent.default_model,
            temperature=agent.temperature,
        ))
        # 流式回包：把 assistant content chunk 透传给前端
        if resp.content:
            yield Event("content_delta", resp.content)

        if not resp.tool_calls:
            # 终止：保存 assistant 消息，结束
            await self.history.save_assistant(session_id, resp.content, tool_calls=None)
            yield Event("done", {"finish_reason": resp.finish_reason})
            return

        # 有工具调用：保存 assistant 消息（含 tool_calls），逐个执行工具
        await self.history.save_assistant(session_id, resp.content, resp.tool_calls)
        messages.append(Message("assistant", resp.content, tool_calls=resp.tool_calls))

        for tc in resp.tool_calls:
            # 工具错误一律作为结果回灌给 LLM，让其自我纠正（在 max_iterations 内自然重试）
            try:
                result = await self.tools.call(tc.name, tc.args)
            except Exception as e:
                result = {"error": f"工具 {tc.name} 执行失败：{e}"}
            await self.history.save_tool_result(session_id, tc.id, tc.name, result)
            messages.append(Message("tool", json.dumps(result), tool_call_id=tc.id, name=tc.name))
            yield Event("tool_result", {"name": tc.name, "result": result})

    yield Event("truncated", {"reason": "max_iterations_exceeded"})
```

事件通过 SSE 推给 `/api/sessions/{id}/messages` 的客户端。

### 6.3 历史管理

- 每轮：拉取最近 `max_history` 条 messages，前置 system prompt
- 超过上限时直接截断（v1 不做摘要；v2 可加摘要步骤）
- 工具结果存为 `role=tool` 消息，token_count 由 provider 响应估算

### 6.4 定时调度

```python
# app/agents/scheduler.py
# APScheduler，Redis job store（多 worker 共享 + 重启恢复）
def register(agent):
    if not agent.schedule_cron: return
    scheduler.add_job(
        run_scheduled, trigger=CronTrigger.from_crontab(agent.schedule_cron),
        args=[agent.id, agent.schedule_input], id=f"agent-{agent.id}",
        replace_existing=True,
    )

async def run_scheduled(agent_id, input_text):
    agent = await agent_repo.get(agent_id)
    session = await session_repo.create(agent_id, user_id=SYSTEM_USER, title=f"定时:{input_text[:30]}")
    async for event in runtime.run(agent, input_text, session.id):
        pass  # v1: 仅持久化到 session；v2: 加通知
    log.info("scheduled run done", agent=agent.name, session=session.id)
```

启动时遍历所有 `enabled=true` 且有 `schedule_cron` 的 agent，注册 job。Agent 配置变更时（API 更新）同步 upsert job。

## 7. Tools Registry 详细设计

```python
# app/tools/registry.py
_registry: dict[str, Tool] = {}

def tool(name: str, description: str):
    def deco(fn):
        schema = build_schema_from_signature(fn)  # 参数名 + 类型注解 → JSON schema
        _registry[name] = Tool(name=name, description=description,
                               fn=fn, schema=schema)
        return fn
    return deco

async def call(name: str, args: dict) -> dict:
    t = _registry[name]
    return await maybe_await(t.fn(**args))

def schemas_for(names: list[str]) -> list[dict]:
    return [_registry[n].schema for n in names]
```

**v1 内置工具（仅用于自测，PM/PjM 工具在后续子项目实现）**：
- `echo(text: str)` — 回显，测试调用链路
- `http_get(url: str)` — 简单 HTTP 取数，测试外部依赖

后续 PM/PjM 模块通过 `@tool` 装饰器注册业务工具（`create_task` / `query_prd` / `list_roadmap` 等），不动 runtime 代码。

## 8. API 设计（FastAPI）

| 方法 | 路径 | 角色 | 说明 |
|---|---|---|---|
| POST | `/api/auth/login` | any | email+password → JWT |
| GET/POST/PATCH/DELETE | `/api/providers` | owner | CRUD provider 配置 |
| POST | `/api/providers/{id}/test` | owner | ping + 列出可用模型 |
| GET/POST/PATCH | `/api/agents` | owner | CRUD agent 配置 |
| POST | `/api/agents/{id}/test` | any | 用一行 input 触发一次 dry-run |
| POST | `/api/sessions` | any | body: `{agent_id, title?}` → 新建 session |
| GET | `/api/sessions/{id}/messages` | any | 拉取历史，分页 |
| POST | `/api/sessions/{id}/messages` | any | body: `{content}`，返回 SSE 流（content_delta / tool_result / done / truncated） |
| GET | `/api/usage` | any | 查询 token 计费，按 user/agent/provider/日期筛选；member 只能看自己 |
| GET | `/api/health` | any | liveness |

**鉴权**：JWT（PyJWT），24h 过期；`Depends(get_current_user)` 注入；owner-only 路由用 `require_role("owner")` 二次校验。

**SSE 协议**：每个事件 `data: {type, payload}\n\n`，type ∈ `content_delta` / `tool_result` / `done` / `truncated` / `error`。

## 9. 配置文件

```yaml
# config.yaml
server:
  host: 0.0.0.0
  port: 8000
  workers: 1   # SQLite 单 worker；切 PG 后可调高
database:
  url: sqlite:///./data/agent_platform.db
  echo: false
redis:
  url: redis://localhost:6379/0
auth:
  jwt_secret: ${JWT_SECRET}    # 强制环境变量，不写死
  jwt_expiry_hours: 24
scheduler:
  enabled: true
  timezone: Asia/Shanghai
logging:
  level: INFO
  format: json                 # 结构化日志，便于后续接入 ELK
routing:
  default_strategy: self_hosted_first
crypto:
  key: ${MASTER_KEY}           # 加密 provider.api_key 用
```

Provider 的 `api_key` 用 AES-GCM 加密后落库（`api_key_enc`），运行时解密。主密钥来自环境变量 `MASTER_KEY`，不入库不入 git。

## 10. 目录结构

```
/workspace/agent-platform/
  app/
    __init__.py
    main.py                   # FastAPI app factory + 路由注册
    config.py                 # pydantic-settings 加载 config.yaml + env
    db.py                     # SQLAlchemy engine + session factory
    logging.py                # structlog 配置
    models/                   # ORM（按表分文件）
      __init__.py
      user.py provider.py agent.py session.py usage.py audit.py
    auth/
      __init__.py
      jwt.py                  # 签发 + 校验
      deps.py                 # FastAPI dependencies
      crypto.py               # AES-GCM 包装
    providers/
      __init__.py
      base.py                 # LLMClient protocol + dataclasses
      router.py
      accounting.py
      adapters/
        __init__.py
        openai_compat.py
        anthropic.py          # v1 仅占位
        gemini.py             # v1 仅占位
    agents/
      __init__.py
      runtime.py              # ReAct 循环
      loader.py               # YAML → DB
      history.py              # session/message CRUD
      scheduler.py            # APScheduler 集成
    tools/
      __init__.py
      registry.py
      base.py
      builtin/
        __init__.py
        echo.py
        http_get.py
    api/
      __init__.py
      auth.py providers.py agents.py sessions.py usage.py
  agents/                     # 默认 agent YAML（启动时 upsert）
    pm-assistant.yaml
    pjm-report.yaml
  tests/
    conftest.py
    test_providers/
      test_openai_compat.py
      test_router.py
      test_accounting.py
    test_agents/
      test_runtime.py
      test_history.py
      test_loader.py
    test_tools/
      test_registry.py
    test_api/
      test_auth.py
      test_providers_api.py
      test_sessions_api.py
  data/                       # SQLite 文件 + scheduler 持久化（gitignore）
  config.yaml
  requirements.txt
  pyproject.toml
  README.md
```

## 11. 错误处理策略

| 错误类型 | 处理位置 | 行为 |
|---|---|---|
| Provider 5xx / 超时 / 429 | Router | 跳到下一个 provider（failover）；全部失败 → 抛 `AllProvidersFailed`，API 返回 502 + retryable hint |
| Provider 4xx（除 429） | Adapter | 抛 `ProviderRequestError`，不 failover；API 返回 502 + 错误明细 |
| 工具参数 JSON 无效 / 工具执行抛错 | Runtime | 错误回灌为 tool result，LLM 在 max_iterations 内自我纠正；超限则 `truncated` 事件结束 |
| Max iterations 超限 | Runtime | 发 `truncated` 事件正常结束（不抛异常） |
| 鉴权失败 | API 中间件 | 401 |
| 权限不足（member 访问 owner 路由） | API dependency | 403 |
| DB 写失败 | Repository 层 | 500 + 结构化日志（含 trace_id） |
| 配置缺失（如 `MASTER_KEY` 未设） | 启动时 | 直接退出，不启动服务 |

**显式不做的事**：
- 不为内部 caller 加输入校验（信任内部代码）
- 不加请求重试风暴（failover 已覆盖外部故障）
- 不加推测式 fallback（如 provider 全挂时不自动切到 mock）

## 12. 测试策略

| 层级 | 工具 | 覆盖 |
|---|---|---|
| Adapter 单测 | `respx` mock httpx | 请求体格式、响应解析、token 抽取（每厂商一个 fixture） |
| Router 单测 | 内存 stub provider | 3 种策略排序 + failover 顺序 + 计费落库 |
| Accounting 单测 | 内存 fixture | 成本计算公式 + 边界（零成本、超大 token） |
| ReAct loop 单测 | stub provider 返回脚本化 tool_calls | 正确的消息序列、终止条件、max_iterations 截断 |
| Tools registry 单测 | 假工具 | schema 生成 + 调用 + 错误传播 |
| API 集成 | FastAPI TestClient + JWT fixture | 端到端：login → create session → 发消息 → 收 SSE 事件 |
| 烟测 | docker-compose 起 one-api mock | CI 跑一次，确认 OpenAI-compat 链路通 |

覆盖率目标：providers/ 和 agents/ ≥ 85%，tools/ ≥ 90%，api/ ≥ 70%。

## 13. 部署与运维

- **本地开发**：`uvicorn app.main:app --reload`，SQLite + 内存 scheduler（关闭 Redis job store）
- **生产部署**：systemd unit（参考 `price-monitor/deploy/price-monitor.service` 模式），SQLite WAL + Redis 单实例
- **数据库迁移**：Alembic，初始 migration 建全部表
- **日志**：structlog JSON 输出，每条带 trace_id（请求级），便于后续接 ELK
- **健康检查**：`GET /api/health` 检 DB 连通 + Redis 连通 + scheduler 心跳

## 14. 后续子项目接入点

| 后续模块 | 接入方式 | 不动 |
|---|---|---|
| 产品管理模块 | 在 `app/tools/builtin/` 加 `create_prd` / `query_prd` / `list_roadmap` 等工具 + 对应 ORM 表 | Provider/Agent Runtime 代码 |
| 项目管理模块 | 加 `create_task` / `update_status` / `burndown` 工具 | 同上 |
| RAG/向量检索 | 在 tools 里加 `search_docs`，向量库独立部署 | 不嵌入 runtime |
| 飞书/Slack 通知 | 在 scheduler `run_scheduled` 末尾加 notifier 钩子 | runtime 主流程不动 |
| 多租户 | 在 `users` 表加 `org_id`，所有查询加 filter；权限模型升级 | 表结构平滑扩展 |

## 15. 工作量与里程碑（仅作参考，不承诺时间）

- M1: Provider Gateway（adapters + router + accounting + 配置 API）→ 可单独验收
- M2: Agent Runtime（loader + ReAct + history）→ 用 echo 工具跑通端到端
- M3: Scheduler + Auth + Sessions API + Usage API → 平台完整可跑
- M4: 内置 tools + 烟测 + 文档

每个里程碑独立可验收，避免一次性大爆炸。

## 16. 风险与缓解

| 风险 | 缓解 |
|---|---|
| ReAct 循环手写出 bug | 用脚本化 stub provider 做端到端测试；脚本里覆盖 0/1/多工具调用、错误重试、max_iter 截断 |
| Token 计费漏算（如 failover 时只记成功那次） | 计费在 Router 层，每次 provider.chat 调用后立即落库，包括失败的（status=failed） |
| 自建 vLLM 不可用时无 fallback | 默认策略 `self_hosted_first` 自动 failover 到商用 API；owner 可改 |
| api_key 泄露 | AES-GCM 加密落库，主密钥仅环境变量；不入日志、不入 audit detail |
| SQLite 并发写瓶颈 | WAL 模式 + 单 worker；切 PG 仅改 connection string |
| Agent YAML 改坏导致 scheduler 崩 | loader 启动时严格校验，单个 agent 失败不影响其他 agent 注册 |
