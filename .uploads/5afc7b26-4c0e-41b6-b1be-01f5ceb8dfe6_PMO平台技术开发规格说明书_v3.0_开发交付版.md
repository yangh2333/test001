# PMO 运维管理平台　技术开发规格说明书（TSD）

> 版本：**v3.0（开发交付版）**　日期：2026-11-01　状态：**可开工**
> 上游文档：`PMO运维管理平台开发Spec_v2.0_定稿.md`（方案层，已生效）
> 配套附件：`02_部署清单与三年TCO测算表.md`、`03_集成接口清单.md`、`04_外部账号与权限矩阵.md`、`05_推广与运营章程.md`
> 适用对象：AI 算力芯片公司（约 3000 人）｜建设方式：2.5 人 + AI 辅助编码，P1 周期 6 个月

---

## 0. 文档说明

### 0.1 本文档与 v2.0 的关系

| 文档 | 回答的问题 | 受众 |
| --- | --- | --- |
| v2.0 定稿 | **做什么、为什么做、花多少钱** | 决策层、PMO |
| **v3.0 本文档** | **怎么做、做成什么样、怎么验收** | 开发、测试、实施 |

v3.0 **不重复论证方案合理性**，只把 v2.0 的结论翻译成可执行的工程约束。两者冲突时，**以 v3.0 为准**（v3.0 是更细的一层）；v3.0 未覆盖的业务判断，回到 v2.0。

### 0.2 如何驱动 AI 编码工具使用本文档

推荐喂给编码工具的顺序（每一轮只喂一段，避免上下文稀释）：

1. **先喂 §2（技术栈与工程结构）+ §12（编码规范）** → 让它搭骨架、建目录、跑通 hello world；
2. **再喂 §3 某一节（如 3.3 任务域）** → 让它生成该域的 model / schema / migration / CRUD；
3. **再喂 §4 对应接口段** → 让它生成 router / service / 测试；
4. **最后喂 §6 权限引擎** → 让它把数据访问层收口。

**禁止**一次性把整篇文档丢给编码工具然后说"把它实现出来"。

### 0.3 全局约定（对所有模块生效，不得违反）

| 项 | 约定 |
| --- | --- |
| 主键 | `id BIGSERIAL`（内部）＋ `code VARCHAR(64) UNIQUE`（业务编号，对外用）。**列表/详情/关联一律用 id，code 仅用于展示与导入匹配** |
| 业务编号规则 | 项目 `PRJ-{TYPE}-{YYYYMM}-{3位序号}`；工单 `TK-{YYYYMMDD}-{4位序号}`；风险 `RK-{项目code}-{序号}`；批次 `BT-{TYPE}-{YYYYMM}-{序号}` |
| 时间 | 数据库存 `TIMESTAMPTZ`（UTC）；API 出入参用 ISO8601 带时区；前端按用户时区渲染；纯日期字段用 `DATE` |
| 金额 | `NUMERIC(14,2)`，**禁止 float** |
| 百分比 | `NUMERIC(5,2)`，存 0–100 数值，不存 0–1 |
| 软删除 | 业务实体一律 `deleted_at TIMESTAMPTZ NULL`，**禁止物理删除**；唯一索引需带 `WHERE deleted_at IS NULL` |
| 审计字段 | 所有业务表必带 `created_by BIGINT`、`created_at`、`updated_at`；关键表带 `updated_by` |
| 枚举 | 用 `VARCHAR(32)` + 应用层枚举类，**不用数据库 enum 类型**（改枚举要改表，迁移痛苦）；字典类走 `dictionary` 表 |
| JSON 字段 | 用 `JSONB`；**仅用于非检索的弹性结构**（如 checklist items、表单白名单），需要检索的字段必须独立成列 |
| 时区与工作日 | 工作日 = 周一至周五，法定节假日走 `dictionary: holiday` 维护，关键路径与 SLA 计算必须排除 |
| 幂等 | 所有写接口支持 `Idempotency-Key` 请求头（导入、审批、状态流转必接） |
| 字符编码 | UTF-8；数据库 `LC_COLLATE=C` 以避免中文排序性能问题，中文排序在应用层做 |

### 0.4 术语与缩写

TSD（技术规格说明书）、PM（项目经理）、PMO（项目管理办公室）、BU（业务部门）、Gate（阶段门禁）、WBS（工作分解结构）、RACI（责任分配矩阵）、SLA（服务时限）、TCO（总拥有成本）、DoD（完成定义）。

---

## 1. 系统概览

### 1.1 一句话定位

**面向芯片研发全链条的项目协同平台**：把"谁负责什么、卡在哪里、什么时候交"三件事从 Excel 和会议里搬到线上，用系统承担"催人、背锅、汇总"的成本。

### 1.2 P1 范围边界（硬边界，超出即属范围蔓延）

**P1 必须交付（第 1–6 月）：**

| 编号 | 能力 | 交付判定 |
| --- | --- | --- |
| F-01 | 双源账号同步（LDAP + 企微）+ 登录 | 能登录，冲突进待办 |
| F-02 | RBAC + 数据域 + 密级 | 三类过滤均生效 |
| F-03 | 项目立项（带模板、密级）+ 项目卡片 | 十大类型可实例化 |
| F-04 | WBS 4 级 + 任务 CRUD + 唯一 accountable owner | 建任务必填 owner |
| F-05 | 甘特（frappe-gantt）+ 依赖 + 关键路径高亮 + 基线对比 | 5000 任务可渲染 |
| F-06 | Excel 导入器（项目/任务/里程碑/历史工时） | 带校验、错误报告、回滚 |
| F-07 | 承诺制 Gate + 评审记录 + Checklist 缺口登记 | 未过不硬锁，持续告警 |
| F-08 | 协同工单（RACI + SLA + 升级 + 满意度） | 跨部门请求 100% 可走工单 |
| F-09 | 统一待办中心 + 企微卡片推送（IM 内可处理） | 5 类待办汇聚 |
| F-10 | 会议决议 → 待办（含未闭环催办） | 决议可转待办 |
| F-11 | 周报自动生成（草稿）+ 三级汇聚 + PM 补充发布 | 自动出草稿 |
| F-12 | AI 三场景：周报摘要 / 项目问答 / 待办排序 | 含降级开关 |
| F-13 | 最小驾驶舱：关键节点总览 / 阻塞清单 / 待决策事项 | 三张卡片 |
| F-14 | 审计日志 + 通知中心（企微/邮件/站内） | 敏感操作可查 |
| F-15 | CI Webhook 单向回写发布状态 | 一个 BU 打通即可 |
| F-16 | M2 Program 挂载 + 跨项目依赖 + 延期推演（P1 尾） | 一颗芯片多专项可见 |

**P1 明确不做（开发看到需求请直接驳回并引用本条）：**

- ❌ Jira / Gerrit / GitLab **双向**同步（单向 CI Webhook 除外）
- ❌ 财务、北森 HR、ATE 机台系统对接
- ❌ 自有大模型训练 / GPU 采购 / 本地推理
- ❌ 独立移动 App（只做企微 H5）
- ❌ 客户门户、供应商门户（P2 立项，需 DMZ 端口审批）
- ❌ 资源平台 M3、风险变更 M5、工时 M7、完整驾驶舱 M8、知识库 M9
- ❌ 微服务拆分、Kafka、Elasticsearch、ClickHouse、K8s
- ❌ 中英双语实施（仅预留 i18n key）

### 1.3 角色与权限总表

| 角色 code | 名称 | 作用域 | 关键权限 | 数据范围 |
| --- | --- | --- | --- | --- |
| `pmo_admin` | PMO 管理员 | 全局 | 模板/字典/Checklist 治理、数据稽核、运营报表、同步冲突裁决 | 全量（受密级约束） |
| `pmo_secrecy` | 密级管理员 | 全局 | 密级设定与变更审批 | 全量 |
| `pm` | 项目经理 | 项目 | 本人项目全权；跨项目只读 | 本人项目 + 跨项目只读 |
| `dept_head` | 部门主管 | 部门 | 本部门人员/资源/工时明细；工单升级受理 | 本部门树 |
| `member` | 项目成员 | 项目 | 本人任务与工时；所属项目只读 | 所属项目 |
| `program_owner` | 专项负责人 | Program | 专项全权 + 涉及资源可见 | 本 Program 下项目 |
| `exec` | 高管/经营层 | 全局 | 只读 + 待决策审批 | 全量只读 |
| `finance` | 财务接口人 | 全局 | 预算与成本台账维护（手工/导入） | 预算成本数据 |
| `qa` | 质量体系 | 全局 | 质量数据读写、流程审计 | 全量 |
| `external_*` | 外部账号 | 项目 | 见 `04_外部账号与权限矩阵.md` | 字段级白名单 |

**角色可叠加**，一人可同时是 `pm`（A 项目）与 `member`（B 项目）。

### 1.4 十大项目类型与 Stage-Gate 配置

十类类型的阶段与门禁定义见 **附录 A（可直接作为 seed 数据）**。开发注意事项：

- 模板是**配置数据不是代码**，通过 seed 脚本写入 `project_type / stage_template / gate_template / checklist_template`；
- 项目实例化时**快照**一份到 `project_stage / gate / checklist_instance`，模板改版不影响历史项目；
- 阶段/门禁**可裁剪但留痕**：`project_stage.is_tailored=true` + `tailor_reason` 必填；**核心 Gate 不可裁剪**（`gate_template.is_core=true`）；
- 芯片设计类的 Tapeout、NPI 类的 MP 放行**必须设 `is_high_risk=true`**（触发强制会签）。

---

## 2. 技术栈与工程结构

### 2.1 选型（版本钉死，升级需评审）

| 层 | 选型 | 版本 | 说明 |
| --- | --- | --- | --- |
| 前端框架 | React + TypeScript | React 18.3 / TS 5.5 | 不用 19（AntD 兼容性未稳） |
| 构建 | Vite | 5.4 | — |
| UI 库 | Ant Design | 5.20 | 中文后台生态成熟 |
| 甘特 | **frappe-gantt** | 0.6.x（MIT） | **D-5 已定**，不自研渲染层；封装为 `GanttChart.tsx` |
| 图表 | ECharts | 5.5 | 驾驶舱用，按需引入 |
| 状态 | Zustand | 4.5 | 不用 Redux（过重） |
| 请求 | TanStack Query | 5.x | 缓存与失效 |
| 路由 | React Router | 6.26 | — |
| 后端 | Python + FastAPI | Python 3.11 / FastAPI 0.115 | 单体模块化 |
| ORM | SQLAlchemy | 2.0（**必须用 2.0 风格 `Mapped[]`**） | — |
| 迁移 | Alembic | 1.13 | 每个 Sprint 一个迁移文件 |
| 校验 | Pydantic | v2 | — |
| 任务调度 | APScheduler（PG 持久化） | 3.10 | 同步作业、SLA 扫描、周报生成 |
| 数据库 | PostgreSQL | 15 | 含 `pg_trgm` 全文检索 |
| 缓存/队列 | Redis | 7.2 | 会话 + 轻量队列 + 报表缓存 |
| 对象存储 | MinIO | RELEASE.2024 | 附件（S3 协议，便于迁移） |
| 测试 | pytest + Playwright | — | 后端单测覆盖率 ≥ 60%（核心域 ≥ 80%） |
| 部署 | Docker Compose | v2 | 原型期单机；正式期 2 节点 |

**明确不引入**：Kafka、Elasticsearch、ClickHouse、Celery（用 APScheduler + Redis Stream 足够）、K8s、微前端。

### 2.2 后端目录结构

```
pmo-server/
├── alembic/                      # 迁移脚本，每 Sprint 一个版本文件
│   └── versions/
├── app/
│   ├── main.py                   # FastAPI 入口，装配 router
│   ├── core/
│   │   ├── config.py             # pydantic-settings，读环境变量
│   │   ├── security.py           # JWT 签发/校验、密码策略
│   │   ├── deps.py               # 依赖注入：current_user / db session
│   │   ├── errors.py             # 统一异常与错误码（附录 B）
│   │   ├── logging.py            # 结构化日志 + trace_id
│   │   └── audit.py              # 审计装饰器 @audited(action, obj_type)
│   ├── access/                   # ★统一数据访问层（见 §6）
│   │   ├── engine.py             # 权限判定主入口 can_access()
│   │   ├── scope.py              # 数据域表达式求值
│   │   ├── secrecy.py            # 密级过滤
│   │   └── query.py              # 所有列表查询必须走这里
│   ├── domains/                  # 按域隔离，域间只通过 service 调用
│   │   ├── identity/             # M10：user/dept/role/sync
│   │   ├── project/              # M1 + M4：project/stage/gate/review
│   │   ├── task/                 # M1：wbs/task/dependency/baseline/gantt
│   │   ├── program/              # M2：program/跨项目依赖/交接物
│   │   ├── collab/               # M6：ticket/todo/meeting/weekly_report
│   │   ├── notify/               # M10：notification/频道/频控
│   │   ├── report/               # M8：健康度/驾驶舱/物化视图
│   │   ├── resource/             # M3（P2 占位，P1 仅建表）
│   │   ├── risk/                 # M5（P2 占位，P1 仅建表）
│   │   └── ai/                   # AI 网关代理与脱敏
│   ├── integrations/
│   │   ├── ldap_sync.py
│   │   ├── wecom.py              # 通讯录 + 消息卡片
│   │   ├── ci_webhook.py
│   │   ├── cmdb.py
│   │   ├── mail_parser.py        # 供应商回执解析
│   │   └── ai_gateway.py         # 出网代理 + 脱敏 + 配额
│   ├── jobs/                     # APScheduler 任务
│   │   ├── sync_ldap.py  sync_wecom.py  sla_scan.py
│   │   ├── weekly_report_gen.py  baseline_snapshot.py
│   │   └── health_recalc.py
│   └── models/                   # SQLAlchemy 模型，按域分文件
├── scripts/seed/                 # 十类模板 seed、字典 seed、演示数据
├── tests/
└── pyproject.toml
```

**域间调用规则**：`domains/` 内各域**不得跨域直接 import 对方的 model**；需要跨域数据一律调用对方 `service.py` 暴露的函数，或走 `access/query.py` 的只读查询。违反此规则的代码不予合入（2.5 人团队防耦合的唯一手段）。

### 2.3 前端目录结构

```
pmo-web/
├── src/
│   ├── api/                      # 按域封装请求，与后端 router 一一对应
│   ├── layouts/                  # AdminLayout / MobileLayout
│   ├── components/
│   │   ├── GanttChart.tsx        # frappe-gantt 封装（唯一甘特入口）
│   │   ├── UserPicker.tsx        # 人员选择（带技能标签）
│   │   ├── ProjectPicker.tsx
│   │   ├── SecrecyBadge.tsx      # 密级徽标
│   │   ├── HealthTag.tsx         # 红/黄/绿
│   │   └── AuditTimeline.tsx
│   ├── pages/
│   │   ├── dashboard/            # 驾驶舱
│   │   ├── project/              # 项目列表/详情/WBS/甘特/门禁
│   │   ├── program/              # 项目集
│   │   ├── todo/                 # 统一待办
│   │   ├── ticket/               # 协同工单
│   │   ├── weekly/               # 周报
│   │   ├── admin/                # 模板/字典/权限/密级/集成/同步冲突
│   │   └── m/                    # 企微 H5 精简页
│   ├── stores/
│   ├── hooks/
│   ├── utils/
│   └── styles/tokens.ts          # 设计令牌（见 §9.4）
└── vite.config.ts
```

### 2.4 环境搭建命令

```bash
# 后端
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # 填写 §2.5 变量
docker compose up -d pg redis minio
alembic upgrade head
python -m scripts.seed.run    # 十类模板 + 字典 + 演示数据
uvicorn app.main:app --reload --port 8000

# 前端
pnpm install
pnpm dev                      # 端口 5173，代理 /api -> 8000
pnpm test:e2e                 # Playwright
```

### 2.5 环境变量清单（`.env.example`）

| 变量 | 必填 | 说明 |
| --- | --- | --- |
| `DATABASE_URL` | ✅ | `postgresql+psycopg://…` |
| `REDIS_URL` | ✅ | — |
| `MINIO_ENDPOINT / ACCESS_KEY / SECRET_KEY / BUCKET` | ✅ | 附件 |
| `JWT_SECRET / JWT_EXPIRE_MIN` | ✅ | 会话 480 分钟（一个工作日） |
| `LDAP_URI / LDAP_BIND_DN / LDAP_BIND_PW / LDAP_BASE_DN` | ✅ | 只读账号 |
| `WECOM_CORP_ID / WECOM_SECRET / WECOM_AGENT_ID` | ✅ | 通讯录与消息 |
| `AI_PROXY_URL / AI_API_KEY_A / AI_API_KEY_B / AI_MONTHLY_BUDGET` | ✅ | 两家热备 |
| `CI_WEBHOOK_TOKEN` | ✅ | Webhook 签名校验 |
| `CMDB_API_URL / CMDB_TOKEN` | ⬜ | P2 |
| `MAIL_PARSE_MAILBOX / MAIL_PARSE_INTERVAL` | ⬜ | 供应商回执（P1 末） |
| `SECRECY_EXPORT_WATERMARK` | ✅ | 导出水印文本模板 |
| `ENV` | ✅ | `dev` / `staging` / `prod`；prod 下禁止 seed 与调试路由 |

**密钥一律经环境变量注入，禁止入库、禁止进代码库、禁止写进 `integration_config.params` 明文**（该字段落库需 AES 加密，密钥取自环境变量）。

### 2.6 分支与发布策略

| 分支 | 用途 | 保护 |
| --- | --- | --- |
| `main` | 生产 | 需 PR + 1 人评审 + CI 绿 |
| `release/*` | 预发 | 灰度部门试用 |
| `develop` | 集成 | 需 PR |
| `feat/*`、`fix/*` | 开发 | — |

发布节奏：**双周迭代，季度大版本**（F9）。每次发布必须附**回滚脚本**（`alembic downgrade` 的验证记录 + 数据补偿 SQL），无回滚方案不予上线。

---

## 3. 数据模型（完整数据字典）

### 3.0 约定

- 所有表默认含 `id BIGSERIAL PK`、`created_at TIMESTAMPTZ NOT NULL DEFAULT now()`、`updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`、`deleted_at TIMESTAMPTZ NULL`（下表不再重复列出，除非有特殊说明）；
- `✅` = NOT NULL；`⬜` = 可空；
- **索引建议**单列于 §3.10，不在表内重复。

---

### 3.1 组织与身份域（M10）

#### `dept` 部门（组织树主源：企微）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `name` | VARCHAR(128) | ✅ | 部门名 |
| `parent_id` | BIGINT | ⬜ | 自关联，根为 NULL |
| `source_id` | VARCHAR(64) | ✅ | 企微部门 id |
| `path` | VARCHAR(512) | ✅ | 物化路径 `/1/12/35/`，用于子树查询 |
| `manager_user_id` | BIGINT | ⬜ | 部门主管 |
| `order_no` | INT | ✅ | 同级排序 |
| `status` | VARCHAR(16) | ✅ | `active` / `archived` |

#### `user` 用户（双源合并结果）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `employee_no` | VARCHAR(32) | ✅ | 工号，**唯一键**（`UNIQUE WHERE deleted_at IS NULL`） |
| `name` | VARCHAR(64) | ✅ | 姓名 |
| `email` | VARCHAR(128) | ✅ | LDAP 主源 |
| `dept_id` | BIGINT | ⬜ | 企微主源 |
| `title` | VARCHAR(64) | ⬜ | 岗位 |
| `avatar_url` | VARCHAR(512) | ⬜ | 企微头像 |
| `status` | VARCHAR(16) | ✅ | `active` / `disabled` / `pending`；**以 LDAP 为准** |
| `src_ldap` | BOOLEAN | ✅ | 是否在 LDAP 中存在 |
| `src_wechat` | BOOLEAN | ✅ | 是否在企微中存在 |
| `src_synced_at` | TIMESTAMPTZ | ⬜ | 最近一次成功同步 |
| `password_hash` | VARCHAR(255) | ⬜ | 仅应急登录用；生产走 LDAP/企微扫码 |
| `is_external` | BOOLEAN | ✅ | 默认 false；外部账号不进本表 |
| `last_login_at` | TIMESTAMPTZ | ⬜ | — |

#### `external_account` 外部账号（独立池，P2 启用，P1 建表）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `login_name` | VARCHAR(64) | ✅ | 唯一 |
| `display_name` | VARCHAR(64) | ✅ | — |
| `acct_type` | VARCHAR(32) | ✅ | `supplier` / `outsourcing` / `customer` / `ate_vendor` |
| `org_name` | VARCHAR(128) | ✅ | 外部单位名 |
| `project_ids` | JSONB | ✅ | 可访问项目 id 数组，**空数组 = 无任何访问权** |
| `field_whitelist` | JSONB | ✅ | `{"batch":["lot_no","status","eta"],"milestone":["name","plan_date"]}` 结构 |
| `status` | VARCHAR(16) | ✅ | `invited` / `active` / `expired` / `frozen` |
| `mfa_secret` | VARCHAR(128) | ⬜ | 首次登录强制绑定 |
| `expires_at` | TIMESTAMPTZ | ✅ | 默认开通 +6 个月 |
| `last_login_at` | TIMESTAMPTZ | ⬜ | 连续 90 天未登录自动停用 |
| `password_hash` | VARCHAR(255) | ✅ | 独立密码策略 |

#### `sync_conflict` 双源同步冲突

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `employee_no` | VARCHAR(32) | ✅ | — |
| `conflict_type` | VARCHAR(32) | ✅ | `status_mismatch` / `dept_mismatch` / `missing_in_ldap` / `missing_in_wechat` / `duplicate_name` |
| `ldap_payload` | JSONB | ⬜ | — |
| `wechat_payload` | JSONB | ⬜ | — |
| `status` | VARCHAR(16) | ✅ | `pending` / `resolved` / `ignored` |
| `resolved_by` | BIGINT | ⬜ | PMO |
| `resolution` | VARCHAR(32) | ⬜ | `keep_ldap` / `keep_wechat` / `merge` / `mark_left` |
| `resolved_at` | TIMESTAMPTZ | ⬜ | — |

#### `role` / `role_binding` / `data_domain`

| 表 | 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| `role` | `code` | VARCHAR(32) | ✅ | 唯一，见 §1.3 |
| | `name` | VARCHAR(64) | ✅ | — |
| | `scope` | VARCHAR(16) | ✅ | `global` / `project` / `dept` |
| | `builtin` | BOOLEAN | ✅ | 内置角色不可删除 |
| `role_binding` | `user_id` | BIGINT | ✅ | — |
| | `role_id` | BIGINT | ✅ | — |
| | `project_id` | BIGINT | ⬜ | 项目级角色必填 |
| | `dept_id` | BIGINT | ⬜ | 部门级角色必填 |
| | `granted_by` | BIGINT | ✅ | — |
| | `expires_at` | TIMESTAMPTZ | ⬜ | 到期自动回收（防权限泛滥） |
| `data_domain` | `code` / `name` | VARCHAR | ✅ | 自定义数据域，如"芯片设计类项目" |
| | `expr` | JSONB | ✅ | 见 §6.2 表达式规范 |

---

### 3.2 项目与门禁域（M1 + M4）

#### `program` 项目集

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `code` | VARCHAR(64) | ✅ | 唯一，如 `PGM-X2` |
| `name` | VARCHAR(128) | ✅ | 如"X2 芯片产品" |
| `owner_user_id` | BIGINT | ✅ | Program 负责人 |
| `secrecy_level` | VARCHAR(16) | ✅ | `public`/`internal`/`confidential`/`secret` |
| `target_date` | DATE | ⬜ | 产品交付目标 |
| `status` | VARCHAR(16) | ✅ | `active` / `closed` |
| `description` | TEXT | ⬜ | — |

#### `project_type` 项目类型（seed 数据，见附录 A）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `code` | VARCHAR(32) | ✅ | `chip_design` / `pkg_design` / `test_eng` / `hw_board` / `software` / `system` / `cluster` / `npi` / `delivery` / `solution` |
| `name` | VARCHAR(64) | ✅ | 中文名 |
| `sort_order` | INT | ✅ | — |
| `enabled` | BOOLEAN | ✅ | — |

#### `project` 项目

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `code` | VARCHAR(64) | ✅ | 唯一，见 §0.3 编号规则 |
| `name` | VARCHAR(200) | ✅ | — |
| `program_id` | BIGINT | ⬜ | 挂载的项目集 |
| `type_id` | BIGINT | ✅ | 项目类型 |
| `pm_user_id` | BIGINT | ✅ | 项目经理 |
| `dept_id` | BIGINT | ✅ | 归属部门 |
| `status` | VARCHAR(16) | ✅ | `draft`/`applying`/`active`/`suspended`/`closed`/`cancelled` |
| `secrecy_level` | VARCHAR(16) | ✅ | **立项必填（A2）**；变更需双人审批 |
| `current_stage_id` | BIGINT | ⬜ | 当前阶段冗余字段，便于列表展示 |
| `progress_pct` | NUMERIC(5,2) | ✅ | 由任务加权自动计算，PM 确认 |
| `health` | VARCHAR(8) | ✅ | `red`/`yellow`/`green`/`na`，由 §7.2 计算 |
| `health_updated_at` | TIMESTAMPTZ | ⬜ | — |
| `plan_start` / `plan_end` | DATE | ✅ | — |
| `actual_start` / `actual_end` | DATE | ⬜ | — |
| `baseline_id` | BIGINT | ⬜ | 当前生效基线 |
| `data_pedigree` | VARCHAR(16) | ✅ | `trial`（试点期"待校准"）/ `official`；**F2 试点数据标注用** |
| `milestone_summary` | JSONB | ⬜ | 冗余：下一关键节点，供驾驶舱免联表 |

#### `project_stakeholder` 干系人

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `project_id` | BIGINT | ✅ | — |
| `user_id` | BIGINT | ✅ | — |
| `role_label` | VARCHAR(32) | ✅ | `sponsor`/`qa`/`finance`/`customer`/`other` |

#### `stage_template` 阶段模板

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `type_id` | BIGINT | ✅ | — |
| `code` / `name` | VARCHAR | ✅ | — |
| `order_no` | INT | ✅ | — |
| `is_core` | BOOLEAN | ✅ | 核心阶段不可裁剪 |
| `typical_days` | INT | ⬜ | 实例化时自动排期参考 |

#### `gate_template` 门禁模板

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `type_id` / `stage_template_id` | BIGINT | ✅ | 归属 |
| `code` / `name` | VARCHAR | ✅ | 如 `G3_tapeout` |
| `order_no` | INT | ✅ | — |
| `is_core` | BOOLEAN | ✅ | 核心 Gate 不可裁剪（如 Tapeout、MP 放行） |
| `is_high_risk` | BOOLEAN | ✅ | 高危：强制会签 + 强制 Checklist |
| `signoff_roles` | JSONB | ⬜ | `["cto_office","qa","pmo"]` |
| `checklist_template_id` | BIGINT | ⬜ | 关联 Checklist 模板 |
| `enforce_mode` | VARCHAR(16) | ✅ | `strict`（强制）/ `commitment`（承诺制，默认） |

#### `checklist_template` Checklist 模板（版本化）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `code` / `name` | VARCHAR | ✅ | — |
| `version` | INT | ✅ | 每次修改 +1 |
| `items` | JSONB | ✅ | `[{"key":"cov_report","label":"验证覆盖率报告","required":true,"evidence":"file"}]` |
| `status` | VARCHAR(16) | ✅ | `draft`/`published`/`deprecated` |

#### `project_stage` 项目阶段实例

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `project_id` | BIGINT | ✅ | — |
| `template_id` | BIGINT | ⬜ | 裁剪出模板时为 NULL |
| `name` / `order_no` | / | ✅ | — |
| `status` | VARCHAR(16) | ✅ | `not_started`/`in_progress`/`done`/`skipped` |
| `plan_start` / `plan_end` | DATE | ⬜ | — |
| `actual_start` / `actual_end` | DATE | ⬜ | — |
| `is_tailored` | BOOLEAN | ✅ | 裁剪留痕 |
| `tailor_reason` | TEXT | ⬜ | `is_tailored=true` 时必填 |

#### `gate` 门禁实例

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `project_id` / `stage_id` | BIGINT | ✅ | — |
| `template_id` | BIGINT | ⬜ | — |
| `name` | VARCHAR(128) | ✅ | — |
| `status` | VARCHAR(16) | ✅ | `not_started`/`material_ready`/`in_review`/`passed`/`conditional`/`failed`/`waived` |
| `decision` | VARCHAR(16) | ⬜ | `pass`/`conditional`/`fail`/`waive` |
| `decided_by` / `decided_at` | / | ⬜ | — |
| `is_high_risk` | BOOLEAN | ✅ | 继承模板 |
| `enforce_mode` | VARCHAR(16) | ✅ | 继承模板，P1 默认 `commitment` |
| `gap_items` | JSONB | ⬜ | **承诺制缺口清单**：`[{"key":"cov_report","reason":"待补","owner":123,"due":"2026-12-01"}]` |
| `waive_reason` | TEXT | ⬜ | 风险接受说明，进承诺台账 |
| `blocked_flag` | BOOLEAN | ✅ | 未过 Gate 时为 true → **持续红色告警并抄送**，但不锁任务 |

#### `checklist_instance` Checklist 实例

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `gate_id` | BIGINT | ✅ | — |
| `template_id` / `template_version` | / | ✅ | 快照版本 |
| `items` | JSONB | ✅ | 模板 items 副本 + `done` / `evidence_file` / `done_by` / `done_at` |
| `total_count` / `done_count` | INT | ✅ | — |

#### `review` 评审

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `gate_id` | BIGINT | ✅ | — |
| `title` | VARCHAR(200) | ✅ | — |
| `scheduled_at` | TIMESTAMPTZ | ⬜ | — |
| `status` | VARCHAR(16) | ✅ | `draft`/`scheduled`/`held`/`closed` |
| `conclusion` | TEXT | ⬜ | 决议正文 |
| `minutes_url` | VARCHAR(512) | ⬜ | xwiki 链接 |
| `created_by` | BIGINT | ✅ | — |

#### `review_item` 评审问题/行动项

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `review_id` | BIGINT | ✅ | — |
| `kind` | VARCHAR(16) | ✅ | `issue` / `action` |
| `content` | TEXT | ✅ | — |
| `owner_user_id` | BIGINT | ✅ | **必填 Owner**（无主不闭环） |
| `due_date` | DATE | ⬜ | — |
| `status` | VARCHAR(16) | ✅ | `open`/`closed`/`waived` |
| `todo_id` | BIGINT | ⬜ | 关联生成的待办 |

#### `review_signoff` 电子签核

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `review_id` | BIGINT | ✅ | — |
| `role_code` | VARCHAR(32) | ✅ | 会签角色 |
| `user_id` | BIGINT | ✅ | 实际签署人 |
| `status` | VARCHAR(16) | ✅ | `pending`/`signed`/`rejected`/`delegated` |
| `delegated_from` | BIGINT | ⬜ | 委托来源 |
| `signed_at` / `comment` | / | ⬜ | — |

---

### 3.3 任务与进度域（M1）

#### `wbs` 工作分解结构

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `project_id` | BIGINT | ✅ | — |
| `parent_id` | BIGINT | ⬜ | 自关联，**最多 4 级**（应用层校验 `level<=4`） |
| `code` | VARCHAR(64) | ✅ | 如 `1.2.3` |
| `name` | VARCHAR(200) | ✅ | — |
| `level` | SMALLINT | ✅ | 1–4 |
| `order_no` | INT | ✅ | — |

#### `task` 任务

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `project_id` / `wbs_id` | BIGINT | ✅ | **Task 必填所属 WBS** |
| `parent_id` | BIGINT | ⬜ | 父子任务 |
| `name` | VARCHAR(200) | ✅ | — |
| `description` | TEXT | ⬜ | — |
| `owner_user_id` | BIGINT | ✅ | **唯一 accountable owner（D5 防推诿，不得为空）** |
| `assignee_ids` | JSONB | ⬜ | 执行人（R），可多人 |
| `consult_ids` / `inform_ids` | JSONB | ⬜ | RACI 中的 C / I |
| `plan_start` / `plan_end` | DATE | ✅ | **计划日期必填** |
| `actual_start` / `actual_end` | DATE | ⬜ | — |
| `est_hours` | NUMERIC(8,2) | ⬜ | 工时预估 |
| `progress_pct` | NUMERIC(5,2) | ✅ | 默认 0；里程碑任务由状态驱动 |
| `status` | VARCHAR(16) | ✅ | `not_started`/`in_progress`/`blocked`/`done`/`cancelled` |
| `blocked_reason` | TEXT | ⬜ | `status=blocked` 时**必填** |
| `blocked_help_user_id` | BIGINT | ⬜ | 求助对象，`blocked` 时**必填**（对应 D5） |
| `priority` | SMALLINT | ✅ | 1(最高)–5；由 §7.5 重算 |
| `is_milestone` | BOOLEAN | ✅ | 零工期节点 |
| `is_critical` | BOOLEAN | ✅ | 是否在关键路径上（由 CPM 回写） |
| `ci_status` | VARCHAR(16) | ⬜ | `unknown`/`success`/`failed`；CI Webhook 回写 |
| `ci_ref` | VARCHAR(128) | ⬜ | 构建号/制品版本 |
| `baseline_offset_days` | INT | ⬜ | 相对基线的偏移天数，供甘特对比 |
| `external_ref` | VARCHAR(128) | ⬜ | 导入来源系统的原始 ID（Excel 导入留存） |

#### `task_raci` 任务职责矩阵

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `task_id` / `user_id` | BIGINT | ✅ | — |
| `raci` | VARCHAR(1) | ✅ | `R`/`A`/`C`/`I` |
| `is_primary_accountable` | BOOLEAN | ✅ | **同一 task 下有且仅有一条 A=true**（唯一约束 `UNIQUE(task_id) WHERE is_primary_accountable`） |

#### `dependency` 依赖

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `predecessor_task_id` / `successor_task_id` | BIGINT | ✅ | — |
| `dep_type` | VARCHAR(2) | ✅ | `FS`/`SS`/`FF`/`SF`，默认 `FS` |
| `lag_days` | INT | ✅ | 默认 0，可为负 |
| `cross_project` | BOOLEAN | ✅ | 跨项目依赖（M2 用） |
| | | | **唯一约束**：`(predecessor, successor)`；**应用层禁止成环** |

#### `baseline` / `baseline_task` 基线快照

| 表 | 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| `baseline` | `project_id` | BIGINT | ✅ | — |
| | `name` | VARCHAR(100) | ✅ | — |
| | `kind` | VARCHAR(16) | ✅ | `gate`（Gate 评审时）/ `monthly` / `manual` |
| | `snapshot_at` | TIMESTAMPTZ | ✅ | — |
| | `created_by` | BIGINT | ✅ | — |
| `baseline_task` | `baseline_id` / `task_id` | BIGINT | ✅ | — |
| | `plan_start` / `plan_end` | DATE | ✅ | 快照值 |
| | `est_hours` / `progress_pct` | NUMERIC | ⬜ | 快照值 |

> 基线采用**全量快照**而非增量：单项目 5000 任务 × 每次约 500KB，20 项目 × 12 次/年 ≈ 120MB/年，可接受。

#### `milestone` 里程碑（冗余视图，由 `task.is_milestone=true` 派生）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `project_id` / `task_id` | BIGINT | ✅ | — |
| `name` | VARCHAR(200) | ✅ | — |
| `kind` | VARCHAR(32) | ⬜ | `tapeout`/`pkg_back`/`cp_pass`/`evt`/`mp`/`delivery` 等，供驾驶舱分类 |
| `plan_date` / `actual_date` | DATE | ✅/⬜ | — |
| `status` | VARCHAR(16) | ✅ | `pending`/`done`/`delayed` |
| `is_critical` | BOOLEAN | ✅ | — |

---

### 3.4 协同域（M6，P1 核心）

#### `ticket` 协同工单

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `code` | VARCHAR(64) | ✅ | 唯一，见 §0.3 |
| `title` | VARCHAR(200) | ✅ | — |
| `ticket_type` | VARCHAR(16) | ✅ | `resource`（借人/借资源）/ `support`（技术支持）/ `decision`（请决策） |
| `project_id` | BIGINT | ⬜ | 关联项目 |
| `requester_user_id` | BIGINT | ✅ | 发起人 |
| `target_dept_id` | BIGINT | ✅ | 被请求部门 |
| `target_user_id` | BIGINT | ⬜ | 被请求人；**为空时"找不到责任人"由部门主管分派**（D5 核心场景） |
| `description` | TEXT | ✅ | — |
| `priority` | SMALLINT | ✅ | 1–5 |
| `status` | VARCHAR(16) | ✅ | 见 §5.4 状态机 |
| `sla_due_at` | TIMESTAMPTZ | ✅ | 创建时按 SLA 规则计算（默认 1 个工作日响应） |
| `responded_at` / `resolved_at` | TIMESTAMPTZ | ⬜ | — |
| `escalate_level` | SMALLINT | ✅ | 0=未升级，1=主管，2=分管副总（F5：72h 未果升 2 级） |
| `satisfaction_score` | SMALLINT | ⬜ | 1–5，关闭后由发起人评价 |
| `closed_by` / `close_comment` | / | ⬜ | — |

#### `ticket_action` 工单流转日志

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `ticket_id` | BIGINT | ✅ | — |
| `actor_user_id` | BIGINT | ✅ | — |
| `action` | VARCHAR(32) | ✅ | `create`/`assign`/`accept`/`reject`/`comment`/`resolve`/`escalate`/`close` |
| `from_status` / `to_status` | VARCHAR(16) | ⬜ | — |
| `comment` | TEXT | ⬜ | — |

#### `meeting` / `meeting_decision` 会议与决议

| 表 | 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| `meeting` | `project_id` | BIGINT | ⬜ | — |
| | `title` | VARCHAR(200) | ✅ | — |
| | `start_at` | TIMESTAMPTZ | ✅ | — |
| | `attendees` | JSONB | ⬜ | `[{"user_id":1,"role":"owner"}]` |
| | `minutes_url` | VARCHAR(512) | ⬜ | xwiki |
| | `created_by` | BIGINT | ✅ | — |
| `meeting_decision` | `meeting_id` | BIGINT | ✅ | — |
| | `content` | TEXT | ✅ | — |
| | `owner_user_id` | BIGINT | ✅ | 必填 |
| | `due_date` | DATE | ✅ | 必填 |
| | `status` | VARCHAR(16) | ✅ | `open`/`done`/`dropped` |
| | `todo_id` | BIGINT | ⬜ | 生成的待办 |

#### `weekly_report` 周报

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `project_id` | BIGINT | ✅ | — |
| `week_start` / `week_end` | DATE | ✅ | 周一至周日 |
| `auto_content` | JSONB | ✅ | 系统生成：`{done_tasks:[],progress_delta:[],risk_change:[],next_week:[],need_decision:[]}` |
| `ai_summary` | TEXT | ⬜ | AI 摘要（可降级为空） |
| `pm_comment` | TEXT | ⬜ | **PM 自由补充区（D4）** |
| `risk_supplement` | TEXT | ⬜ | 风险补充（D4） |
| `status` | VARCHAR(16) | ✅ | `draft`/`published`/`overdue` |
| `published_at` / `published_by` | / | ⬜ | — |
| | | | **唯一约束** `(project_id, week_start)` |

#### `todo_item` 统一待办

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `user_id` | BIGINT | ✅ | — |
| `kind` | VARCHAR(16) | ✅ | `task`/`approval`/`review`/`risk`/`ticket`/`handoff`/`meeting`/`sync_conflict` |
| `ref_type` / `ref_id` | VARCHAR(32)/BIGINT | ✅ | 指向源对象 |
| `title` | VARCHAR(200) | ✅ | — |
| `due_at` | TIMESTAMPTZ | ⬜ | — |
| `status` | VARCHAR(16) | ✅ | `open`/`done`/`snoozed` |
| `priority_score` | NUMERIC(6,2) | ✅ | §7.5 排序分，AI 不可用时回落规则分 |
| `source_channel` | VARCHAR(16) | ✅ | `system`/`ai`/`manual` |
| `done_at` | TIMESTAMPTZ | ⬜ | — |

#### `notification` 通知

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `user_id` | BIGINT | ✅ | — |
| `channel` | VARCHAR(16) | ✅ | `wecom`/`email`/`inapp` |
| `event_type` | VARCHAR(64) | ✅ | 见 §8.3 事件表 |
| `payload` | JSONB | ✅ | 渲染模板所需数据 |
| `status` | VARCHAR(16) | ✅ | `pending`/`sent`/`failed`/`skipped`（频控命中） |
| `dedup_key` | VARCHAR(128) | ⬜ | 频控去重键，如 `task_overdue:123:20261101` |
| `sent_at` / `fail_reason` | / | ⬜ | — |
| `retry_count` | SMALLINT | ✅ | ≥3 进死信，降级邮件/站内 |

#### `notification_rule` 通知频控规则（默认分级订阅 D6）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `event_type` | VARCHAR(64) | ✅ | — |
| `channels` | JSONB | ✅ | `["wecom","inapp"]` |
| `freq_limit` | VARCHAR(32) | ✅ | `realtime` / `daily_digest` / `weekly` |
| `user_override` | JSONB | ⬜ | 个人偏好覆盖（尊重员工 D6） |
| `enabled` | BOOLEAN | ✅ | — |

---

### 3.5 资源与成本域（M3/M7，P1 建表，P2 实现）

> P1 阶段这些表**只建结构不开发页面**，但 `skill`、`member_skill` 因"人责地图"检索需要，**P1 需实现只读检索接口**。

#### `skill` 技能标签（自建字典，PMO 治理）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `code` / `name` | VARCHAR | ✅ | 如 `dft`、`si`、`fpga`、`driver`、`cluster_ops` |
| `category` | VARCHAR(32) | ✅ | 技能分组 |
| `status` | VARCHAR(16) | ✅ | `active`/`merged`/`deprecated` |
| `merged_to` | BIGINT | ⬜ | 合并去向（字典治理） |

#### `member_skill` 人员技能

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `user_id` / `skill_id` | BIGINT | ✅ | 唯一约束 |
| `level` | SMALLINT | ✅ | 1–5 |
| `source` | VARCHAR(16) | ✅ | `self`/`leader`/`pmo` |
| `verified_by` | BIGINT | ⬜ | — |

#### `resource_pool` 资源池

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `res_type` | VARCHAR(16) | ✅ | `person`/`lab`/`equipment`/`external_capacity`/`cluster` |
| `name` | VARCHAR(128) | ✅ | — |
| `dept_id` | BIGINT | ⬜ | — |
| `owner_user_id` | BIGINT | ⬜ | 资源负责人 |
| `capacity_unit` | VARCHAR(16) | ⬜ | `percent`/`hour`/`slot`/`unit` |
| `status` | VARCHAR(16) | ✅ | `active`/`maintenance`/`retired` |

#### `reservation` 资源预约与承诺

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `project_id` | BIGINT | ✅ | — |
| `res_type` | VARCHAR(16) | ✅ | — |
| `resource_id` | BIGINT | ✅ | 人员时为 user_id |
| `percent` | NUMERIC(5,2) | ✅ | 投入占比，**同一资源同一时段累计 ≤ 100**（超需审批） |
| `start_date` / `end_date` | DATE | ✅ | — |
| `status` | VARCHAR(16) | ✅ | `requested`/`approved`/`rejected`/`released` |
| `approved_by` | BIGINT | ⬜ | 部门主管审批 |

#### `lab_resource` / `lab_booking` 实验室

| 表 | 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| `lab_resource` | `name` / `location` | VARCHAR | ✅ | — |
| | `env_spec` | TEXT | ⬜ | 环境配置说明 |
| | `access_level` | VARCHAR(16) | ✅ | 权限等级 |
| | `status` | VARCHAR(16) | ✅ | `available`/`maintenance`/`disabled` |
| `lab_booking` | `lab_resource_id` / `project_id` / `user_id` | BIGINT | ✅ | — |
| | `start_at` / `end_at` | TIMESTAMPTZ | ✅ | 时段冲突唯一约束（排除 `cancelled`） |
| | `status` | VARCHAR(16) | ✅ | `booked`/`using`/`done`/`cancelled` |

#### `batch` 批次（流片/封装/基板）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `project_id` | BIGINT | ✅ | — |
| `batch_type` | VARCHAR(16) | ✅ | `tapeout`/`package`/`substrate` |
| `vendor_name` | VARCHAR(128) | ✅ | 封测厂/Foundry/基板厂 |
| `lot_no` | VARCHAR(64) | ⬜ | 批次号 |
| `status` | VARCHAR(16) | ✅ | `planned`/`released`/`wip`/`out`/`finished`/`abnormal` |
| `plan_release_date` / `actual_release_date` | DATE | ⬜ | 投料 |
| `plan_out_date` / `actual_out_date` | DATE | ⬜ | 出片 |
| `qty` | INT | ⬜ | — |
| `shared_batch_id` | BIGINT | ⬜ | 共享批次拼单主批次 |
| `source` | VARCHAR(16) | ✅ | `manual`/`email_parse`/`supplier_portal` |

#### `batch_milestone` 批次节点

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `batch_id` | BIGINT | ✅ | — |
| `name` | VARCHAR(64) | ✅ | `投料`/`出片`/`交期`/`良率` |
| `plan_date` / `actual_date` | DATE | ⬜ | — |
| `status` | VARCHAR(16) | ✅ | `pending`/`done`/`delayed` |
| `source` | VARCHAR(16) | ✅ | 数据来源（区分邮件解析/供应商回填/手工） |

#### `cost_share` 批次费用分摊

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `batch_id` / `project_id` | BIGINT | ✅ | — |
| `amount` | NUMERIC(14,2) | ✅ | — |
| `share_rule` | VARCHAR(32) | ✅ | `by_qty`/`by_area`/`equal`/`manual` |
| `confirmed` | BOOLEAN | ✅ | 财务确认后才计入成本 |

#### `budget` / `cost_ledger` 预算与成本台账（无财务集成）

| 表 | 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| `budget` | `project_id` | BIGINT | ✅ | — |
| | `category` | VARCHAR(16) | ✅ | `hr`/`external`/`purchase`/`other` |
| | `year_month` | CHAR(7) | ✅ | `2026-11` |
| | `planned_amount` | NUMERIC(14,2) | ✅ | — |
| `cost_ledger` | `project_id` / `year_month` / `category` | / | ✅ | — |
| | `amount` | NUMERIC(14,2) | ✅ | — |
| | `source` | VARCHAR(16) | ✅ | `import`/`manual` |
| | `import_job_id` | BIGINT | ⬜ | 追溯导入批次 |

#### `timesheet` 工时（P2）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `project_id` / `task_id` / `user_id` | BIGINT | ✅ | — |
| `week_start` | DATE | ✅ | 周报式填报（D3） |
| `hours` | NUMERIC(6,2) | ✅ | 单日上限 12h，异常提醒 |
| `note` | TEXT | ⬜ | — |
| `status` | VARCHAR(16) | ✅ | `draft`/`submitted`/`approved`/`rejected` |
| `approver_id` | BIGINT | ⬜ | PM → 主管 |

> **写入使用章程（G 组风险）**：`timesheet` 报表仅输出到**部门聚合匿名层**，个人明细仅本人与直属主管可见（D9），前端需在报表页固定展示"工时仅用于成本与负载分析，不用于绩效问责"提示。

---

### 3.6 风险域（M5，P2）

#### `risk` 风险登记册

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `project_id` | BIGINT | ✅ | — |
| `code` | VARCHAR(64) | ✅ | 唯一 |
| `title` / `description` | / | ✅ | — |
| `probability` / `impact` | SMALLINT | ✅ | 1–5 |
| `level` | VARCHAR(8) | ✅ | 由 P×I 计算：`high`/`medium`/`low` |
| `owner_user_id` | BIGINT | ✅ | — |
| `mitigation` | TEXT | ⬜ | 缓解计划 |
| `trigger_condition` | TEXT | ⬜ | 触发条件 |
| `review_cycle_days` | INT | ✅ | 复审周期，默认 14 |
| `next_review_at` | TIMESTAMPTZ | ✅ | 到期自动提醒并升级 |
| `status` | VARCHAR(16) | ✅ | `open`/`monitoring`/`closed` |
| `in_library` | BOOLEAN | ✅ | 是否入公司风险库 |

#### `issue` 问题

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `project_id` | BIGINT | ✅ | — |
| `code` / `title` | / | ✅ | — |
| `severity` | VARCHAR(8) | ✅ | `p0`/`p1`/`p2`/`p3` |
| `owner_user_id` | BIGINT | ✅ | — |
| `status` | VARCHAR(16) | ✅ | `open`/`processing`/`resolved`/`closed` |
| `due_at` / `escalated_at` | TIMESTAMPTZ | ⬜ | 超 48h 未响应自动升级至部门主管 |

#### `change_request` 变更申请

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `project_id` | BIGINT | ✅ | — |
| `code` / `title` | / | ✅ | — |
| `change_type` | VARCHAR(16) | ✅ | `scope`/`schedule`/`spec` |
| `impact` | JSONB | ⬜ | 自动带出受影响任务/资源/成本 |
| `status` | VARCHAR(16) | ✅ | `draft`/`assessing`/`approved`/`rejected` |
| `approved_by` | BIGINT | ⬜ | CCB 审批 |
| `baseline_id` | BIGINT | ⬜ | 通过后生成新基线 |

---

### 3.7 交接物（M2）

#### `deliverable` 交接物（Handoff）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `project_id` | BIGINT | ✅ | 所属项目 |
| `name` | VARCHAR(200) | ✅ | 如"测试规格书" |
| `deliver_type` | VARCHAR(32) | ✅ | `spec`/`version`/`report`/`file` |
| `from_project_id` / `to_project_id` | BIGINT | ⬜ | 跨项目交接 |
| `from_user_id` / `to_user_id` | BIGINT | ✅ | 双方 |
| `due_date` | DATE | ✅ | — |
| `file_url` | VARCHAR(512) | ⬜ | 附件 |
| `status` | VARCHAR(16) | ✅ | `pending`/`delivered`/`accepted`/`rejected`/`overdue` |
| `delivered_at` / `accepted_at` | TIMESTAMPTZ | ⬜ | 超期自动升级 |

---

### 3.8 平台底座（M10）

#### `attachment` 附件（统一）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `object_type` | VARCHAR(32) | ✅ | `task`/`review`/`deliverable`/`ticket`/`risk` |
| `object_id` | BIGINT | ✅ | — |
| `file_name` | VARCHAR(255) | ✅ | — |
| `size_bytes` | BIGINT | ✅ | 单文件上限 200MB |
| `storage_key` | VARCHAR(512) | ✅ | MinIO key |
| `uploaded_by` | BIGINT | ✅ | — |

#### `audit_log` 审计日志（按月分区）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `actor_user_id` | BIGINT | ⬜ | 系统操作为 NULL |
| `actor_type` | VARCHAR(16) | ✅ | `internal`/`external`/`system` |
| `action` | VARCHAR(64) | ✅ | `create`/`update`/`delete`/`approve`/`export`/`login`/`perm_change`/`secrecy_change`/`baseline_change` |
| `object_type` / `object_id` | / | ✅ | — |
| `before` / `after` | JSONB | ⬜ | 变更前后快照（敏感字段脱敏） |
| `ip` / `user_agent` | / | ⬜ | — |
| `trace_id` | VARCHAR(64) | ✅ | 串联一次请求的所有日志 |
| `created_at` | TIMESTAMPTZ | ✅ | **分区键（按月 RANGE 分区）** |

> 单独审计视图（只读）：权限变更、Gate 结论、密级变更、基线修改、导出行为 —— 由 `action` 白名单过滤。

#### `import_job` 导入任务

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `import_type` | VARCHAR(32) | ✅ | `project`/`task`/`milestone`/`timesheet`/`cost_ledger`/`leave` |
| `file_url` | VARCHAR(512) | ✅ | — |
| `mapping` | JSONB | ✅ | Excel 列 → 字段映射 |
| `status` | VARCHAR(16) | ✅ | 见 §5.7 |
| `total_rows` / `success_rows` / `failed_rows` | INT | ✅ | — |
| `error_report_url` | VARCHAR(512) | ⬜ | 失败行明细下载 |
| `operator_id` | BIGINT | ✅ | — |
| `rollback_token` | VARCHAR(64) | ✅ | 一次性回滚令牌，30 分钟内有效 |

#### `dictionary` 字典

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `category` | VARCHAR(32) | ✅ | `holiday`/`severity`/`ticket_type`/`milestone_kind`/`cost_category` |
| `code` / `name` | VARCHAR | ✅ | — |
| `sort_order` | INT | ✅ | — |
| `status` | VARCHAR(16) | ✅ | `active`/`disabled` |

#### `template` 模板中心

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `tpl_type` | VARCHAR(16) | ✅ | `project`/`checklist`/`report`/`doc_dir` |
| `code` / `name` | VARCHAR | ✅ | — |
| `version` | INT | ✅ | — |
| `content` | JSONB | ✅ | 模板内容 |
| `status` | VARCHAR(16) | ✅ | `draft`/`published`/`deprecated` |
| `tailorable` | BOOLEAN | ✅ | 是否允许 PM 裁剪 |

#### `secrecy_change_request` 密级变更（双人审批）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `project_id` | BIGINT | ✅ | — |
| `from_level` / `to_level` | VARCHAR(16) | ✅ | — |
| `reason` | TEXT | ✅ | — |
| `requested_by` | BIGINT | ✅ | — |
| `approver1_id` / `approver2_id` | BIGINT | ✅ | 密级管理员 + 项目负责人，**两人均通过才生效** |
| `status` | VARCHAR(16) | ✅ | `pending`/`approved`/`rejected` |

#### `integration_config` 集成配置

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `code` | VARCHAR(32) | ✅ | `ldap`/`wecom`/`ci`/`cmdb`/`xwiki`/`ai` |
| `name` | VARCHAR(64) | ✅ | — |
| `enabled` | BOOLEAN | ✅ | — |
| `params` | BYTEA | ⬜ | **AES 加密后的 JSON**，密钥取自环境变量 |
| `last_sync_at` | TIMESTAMPTZ | ⬜ | — |
| `last_status` | VARCHAR(16) | ⬜ | `success`/`failed`/`frozen` |
| `fail_count` | SMALLINT | ✅ | 连续 3 次失败冻结并告警 |

#### `ai_call_log` AI 调用留痕

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `user_id` | BIGINT | ✅ | — |
| `scene` | VARCHAR(32) | ✅ | `weekly_summary`/`qa`/`todo_rank` |
| `provider` | VARCHAR(32) | ✅ | 供应商标识（两家热备） |
| `token_in` / `token_out` | INT | ✅ | — |
| `cost_cent` | NUMERIC(10,4) | ✅ | 本次费用（分） |
| `latency_ms` | INT | ✅ | — |
| `status` | VARCHAR(16) | ✅ | `success`/`failed`/`degraded` |
| `request_digest` | VARCHAR(255) | ✅ | **只存摘要不存原文**（合规） |

---

### 3.9 索引与分区清单（建表即建）

| 表 | 索引 | 类型 | 用途 |
| --- | --- | --- | --- |
| `user` | `(employee_no) WHERE deleted_at IS NULL` | UNIQUE | 登录与同步 |
| `user` | `(dept_id, status)` | BTREE | 部门人员列表 |
| `user` | `(name) gin_trgm` | GIN(pg_trgm) | 人员模糊检索 |
| `dept` | `(path)` | BTREE | 子树查询 |
| `project` | `(code) WHERE deleted_at IS NULL` | UNIQUE | — |
| `project` | `(pm_user_id, status)`、`(program_id)`、`(type_id, status)` | BTREE | 列表筛选 |
| `project` | `(name) gin_trgm` | GIN | 项目搜索 |
| `task` | `(project_id, status)`、`(owner_user_id, status)` | BTREE | 我的任务/项目任务 |
| `task` | `(plan_end) WHERE status<>'done'` | 部分索引 | 逾期扫描 |
| `dependency` | `(predecessor_task_id)`、`(successor_task_id)` | BTREE | CPM 遍历 |
| `ticket` | `(target_dept_id, status)`、`(requester_user_id)`、`(sla_due_at) WHERE status NOT IN ('closed','resolved')` | BTREE/部分 | SLA 扫描（**关键**） |
| `todo_item` | `(user_id, status, priority_score DESC)` | BTREE | 待办中心排序 |
| `review_item` | `(owner_user_id, status, due_date)` | BTREE | 闭环跟踪 |
| `risk` | `(next_review_at) WHERE status<>'closed'` | 部分 | 复审提醒 |
| `notification` | `(status, created_at)`、`(dedup_key)` | BTREE | 发送队列与去重 |
| `audit_log` | `(object_type, object_id)`、`(actor_user_id, created_at)` | BTREE | 审计查询 |
| `audit_log` | `created_at` | **RANGE 分区（月）** | 保留 180 天后归档 |
| `deliverable` | `(to_user_id, status, due_date)` | BTREE | 签收提醒 |
| `reservation` | `(resource_id, start_date, end_date)` | BTREE | 冲突检测 |

**全文检索**：用户/项目/任务名称走 `pg_trgm` + `similarity` 排序，**不引入 ES**。经验库与文档检索走 xwiki 自带检索（M9 退化）。

---

## 4. API 契约

### 4.0 通用约定

| 项 | 约定 |
| --- | --- |
| 基础路径 | `/api/v1` |
| 鉴权 | `Authorization: Bearer <JWT>`；外部账号走 `/api/v1/ext/*` 独立前缀 + 独立 JWT（claims 含 `project_ids` 与 `field_whitelist`） |
| 统一响应 | 成功 `{"code":0,"data":{...},"trace_id":"..."}`；失败 `{"code":<错误码>,"message":"...","detail":{...}}` |
| 分页 | `?page=1&size=20&sort=plan_end:asc`；返回 `{"items":[],"total":100,"page":1,"size":20}`；`size` 上限 200 |
| 字段选择 | `?fields=id,name,status`（列表默认返回精简字段，详情返回全字段） |
| 幂等 | 写接口接受 `Idempotency-Key`，服务端缓存 24h；重复请求返回首次结果 |
| 批量 | 批量操作放 `/bulk` 子路径，单次上限 200 条，返回逐条结果 |
| 审计 | 所有写操作由 `@audited` 装饰器自动落 `audit_log`，**业务代码不得手写审计** |
| 权限 | 列表类接口**必须**经 `access/query.py`，禁止裸 SQLAlchemy `select()` 直出 |
| 错误码 | 见附录 B |

### 4.1 认证与组织（M10）

| Method | Path | 权限 | 说明 |
| --- | --- | --- | --- |
| POST | `/auth/login` | 公开 | 工号 + 密码（应急通道），返回 JWT |
| POST | `/auth/wecom/callback` | 公开 | 企微扫码登录 |
| GET | `/auth/me` | 登录 | 当前用户 + 角色 + 数据域 |
| POST | `/auth/logout` | 登录 | 令牌失效（Redis 黑名单） |
| GET | `/depts` | 登录 | 部门树（缓存 1h） |
| GET | `/users` | 登录 | 人员列表，支持 `q`（姓名/工号）、`skill`（技能 code）、`dept_id` |
| GET | `/users/{id}` | 登录 | 人员详情（含技能、负载概要） |
| GET | `/users/{id}/availability` | 登录 | 可用窗口（P2；P1 返回承诺占比） |
| GET | `/skills` | 登录 | 技能字典树 |
| GET | `/admin/sync-conflicts` | `pmo_admin` | 同步冲突清单 |
| POST | `/admin/sync-conflicts/{id}/resolve` | `pmo_admin` | 裁决（keep_ldap/keep_wechat/merge/mark_left） |
| POST | `/admin/sync/run` | `pmo_admin` | 手动触发同步（调试用，prod 限流 1 次/10min） |
| GET | `/admin/roles`、`/admin/data-domains` | `pmo_admin` | 角色与数据域 |
| POST | `/admin/role-bindings` | `pmo_admin` | 授权（必填 `expires_at`） |
| DELETE | `/admin/role-bindings/{id}` | `pmo_admin` | 回收 |

### 4.2 项目（M1）

| Method | Path | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/projects` | 登录（受数据域/密级过滤） | 列表：支持 `type_id`/`status`/`health`/`pm_user_id`/`program_id`/`q` |
| POST | `/projects` | `pm` / `pmo_admin` | 立项申请（**密级必填**） |
| GET | `/projects/{id}` | 项目可见者 | 详情（含阶段、健康度、干系人） |
| PATCH | `/projects/{id}` | `pm`(本人项目) / `pmo_admin` | 变更基本信息 |
| POST | `/projects/{id}/submit` | `pm` | 提交立项审批 |
| POST | `/projects/{id}/approve` | `pmo_admin` | 审批通过 → 生成编号与空间 |
| POST | `/projects/{id}/stage-transition` | `pm` | 推进阶段（承诺制下允许带缺口推进） |
| GET | `/projects/{id}/health` | 项目可见者 | 健康度明细（各权重分项） |
| POST | `/projects/{id}/baseline` | `pm` | 创建基线快照 |
| GET | `/projects/{id}/baselines` | 项目可见者 | 基线列表 |
| GET | `/project-types` | 登录 | 十大类型 + 阶段/门禁模板 |
| GET | `/projects/{id}/stakeholders` | 项目可见者 | 干系人 |
| PUT | `/projects/{id}/stakeholders` | `pm` | 批量设置 |
| POST | `/projects/{id}/secrecy-change` | `pm` | 申请密级变更 |
| POST | `/admin/secrecy-change/{id}/approve` | `pmo_secrecy` | 会签（第二人通过才生效） |

**立项请求示例**

```jsonc
POST /api/v1/projects
{
  "name": "X2 芯片设计",
  "type_id": 1,
  "program_id": 3,
  "pm_user_id": 1001,
  "dept_id": 12,
  "secrecy_level": "confidential",
  "plan_start": "2026-11-01",
  "plan_end": "2028-04-30",
  "template_version": 1,
  "tailored_stages": [          // 可选裁剪
    { "stage_code": "post_silicon_debug", "action": "keep" }
  ],
  "stakeholders": [{"user_id": 2001, "role_label": "sponsor"}]
}
// 响应 data: { "id": 501, "code": "PRJ-CHIP-202611-001", "status": "applying" }
```

### 4.3 WBS / 任务 / 依赖 / 基线（M1）

| Method | Path | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/projects/{id}/wbs` | 项目可见者 | WBS 树（含任务计数） |
| POST | `/projects/{id}/wbs` | `pm` | 新建 WBS 节点（level ≤ 4 校验） |
| PATCH/DELETE | `/wbs/{id}` | `pm` | 编辑/删除（有子任务时禁止删除） |
| GET | `/projects/{id}/tasks` | 项目可见者 | 任务列表（支持 `status`/`owner_id`/`wbs_id`/`is_milestone`/`is_critical`） |
| POST | `/projects/{id}/tasks` | `pm` / `member`(本 WBS) | 建任务（**owner 必填**） |
| GET | `/tasks/{id}` | 可见者 | 详情（含 RACI、依赖、变更记录） |
| PATCH | `/tasks/{id}` | `pm` / owner | 更新；`status=blocked` 时 `blocked_reason` + `blocked_help_user_id` 必填 |
| POST | `/tasks/{id}/progress` | owner | 报进度（自动上滚 WBS 与项目进度） |
| POST | `/tasks/{id}/raci` | `pm` | 设置 RACI，**A 必须且仅一个** |
| POST | `/tasks/bulk-update` | `pm` | 批量改状态/负责人（≤200） |
| GET | `/projects/{id}/dependencies` | 项目可见者 | 依赖列表 |
| POST | `/projects/{id}/dependencies` | `pm` | 新建依赖（**成环校验**，返回 409 + 环路路径） |
| DELETE | `/dependencies/{id}` | `pm` | — |
| GET | `/projects/{id}/gantt` | 项目可见者 | 甘特数据（任务 + 依赖 + 基线 + 关键路径标记） |
| POST | `/projects/{id}/critical-path/recalc` | `pm` | 触发 CPM 重算（也由任务变更事件自动触发） |
| GET | `/projects/{id}/milestones` | 项目可见者 | 里程碑列表 |
| GET | `/projects/{id}/baseline/compare` | 项目可见者 | 当前 vs 基线的偏移清单 |

**甘特响应结构（前端直接喂 frappe-gantt）**

```jsonc
GET /api/v1/projects/501/gantt?baseline_id=9
{
  "code": 0,
  "data": {
    "tasks": [
      {
        "id": "t1001", "name": "RTL Freeze", "start": "2026-11-10", "end": "2026-12-20",
        "progress": 45, "dependencies": "t1000",
        "custom_class": "is-critical",           // 关键路径高亮
        "owner": {"id":1001,"name":"张三"},
        "baseline": {"start":"2026-11-05","end":"2026-12-10","offset_days":10},
        "is_milestone": false, "status": "in_progress"
      }
    ],
    "critical_path": ["t1000","t1001","t1007"],
    "baseline_name": "G2 基线"
  }
}
```

### 4.4 门禁与评审（M4）

| Method | Path | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/projects/{id}/gates` | 项目可见者 | 门禁列表（含状态、缺口数） |
| GET | `/gates/{id}` | 项目可见者 | 详情（含 Checklist 实例） |
| POST | `/gates/{id}/checklist` | `pm` | 勾选 Checklist 项 + 上传证据 |
| POST | `/gates/{id}/submit-review` | `pm` | 提交评审；Checklist 未完成时**二次确认 + 记录缺口清单**（承诺制） |
| POST | `/gates/{id}/review` | `pm` | 创建/更新评审（时间、参会人、纪要链接） |
| POST | `/reviews/{id}/items` | `pm` | 新增问题/行动项（Owner + 期限必填） |
| PATCH | `/review-items/{id}` | owner / `pm` | 关闭问题项 |
| POST | `/reviews/{id}/signoff` | 会签角色 | 电子签核（支持 `delegate_to`） |
| POST | `/gates/{id}/decision` | 会签完成者 | 结论：`pass`/`conditional`/`fail`/`waive` |
| POST | `/gates/{id}/waive` | `pm` | 风险接受说明（进承诺台账，抄送主管 + PMO） |
| GET | `/admin/commitment-ledger` | `pmo_admin` | **承诺台账**：所有 waive/带缺口通过的清单 |

### 4.5 协同工单与待办（M6）

| Method | Path | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/tickets` | 登录 | 列表（我发起的 / 指派我的 / 本部门的） |
| POST | `/tickets` | 登录 | 发起工单；`target_user_id` 为空时 → 生成"部门分派"待办给主管 |
| GET | `/tickets/{id}` | 相关方 | 详情（含流转日志） |
| POST | `/tickets/{id}/assign` | 部门主管 | 分派责任人（**解决"找不到责任人"**） |
| POST | `/tickets/{id}/accept` | 被请求人 | 受理（停止响应 SLA 计时） |
| POST | `/tickets/{id}/reject` | 被请求人 | 驳回（必填理由，退回发起人） |
| POST | `/tickets/{id}/resolve` | 被请求人 | 标记解决 |
| POST | `/tickets/{id}/close` | 发起人 | 关闭 + 满意度评分 |
| POST | `/tickets/{id}/comment` | 相关方 | 评论 |
| GET | `/tickets/sla-overdue` | `dept_head` / `pmo_admin` | 超时清单 |
| GET | `/todos` | 本人 | 统一待办（按 `priority_score` 排序，支持 `kind` 过滤） |
| PATCH | `/todos/{id}` | 本人 | 完成/稍后处理 |
| GET | `/todos/stats` | 本人 | 待办分类计数 |

**工单发起示例**

```jsonc
POST /api/v1/tickets
{
  "ticket_type": "resource",
  "title": "借调 1 名 DFT 工程师支持 X2 两周",
  "project_id": 501,
  "target_dept_id": 12,
  "target_user_id": null,          // 不知道找谁 → 由部门主管分派
  "description": "需要在 12/10 前完成 scan chain 插入...",
  "priority": 2,
  "need_by": "2026-12-01"
}
// 响应：sla_due_at = 下一个工作日 18:00；同时向 dept 12 的主管推送分派待办
```

### 4.6 会议、周报、通知（M6）

| Method | Path | 权限 | 说明 |
| --- | --- | --- | --- |
| POST | `/meetings` | `pm` | 创建会议（关联项目 + 参会人） |
| POST | `/meetings/{id}/decisions` | `pm` | 录入决议（Owner + 期限必填）→ 自动生成待办 |
| GET | `/meetings/{id}` | 参会者 | 详情（含决议闭环状态） |
| GET | `/projects/{id}/weekly-reports` | 项目可见者 | 周报列表 |
| GET | `/projects/{id}/weekly-reports/current` | `pm` | 获取本周草稿（不存在则实时生成） |
| POST | `/projects/{id}/weekly-reports/generate` | `pm` | 强制重新生成草稿（AI 摘要可重算） |
| PATCH | `/weekly-reports/{id}` | `pm` | 补充 `pm_comment` / `risk_supplement` |
| POST | `/weekly-reports/{id}/publish` | `pm` | 发布 → 触发三级汇聚 |
| GET | `/weekly-reports/aggregate` | `dept_head` / `pmo_admin` / `exec` | 部门/PMO/经营周报汇聚视图 |
| GET | `/notifications` | 本人 | 站内消息 |
| PATCH | `/notifications/{id}/read` | 本人 | 已读 |
| GET | `/notification-preferences` | 本人 | 个人通知偏好（D6 尊重员工） |
| PUT | `/notification-preferences` | 本人 | 设置（事件 × 渠道 × 频次） |

### 4.7 导入导出与文件

| Method | Path | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/import/template/{import_type}` | 登录 | 下载 Excel 模板 |
| POST | `/import/upload` | `pm` / `pmo_admin` | 上传文件 → 返回 `job_id` + 列映射建议 |
| POST | `/import/{job_id}/validate` | 同上 | 试校验，返回错误行预览（不落库） |
| POST | `/import/{job_id}/execute` | 同上 | 执行导入 |
| GET | `/import/{job_id}` | 操作者 | 进度与结果 |
| GET | `/import/{job_id}/errors` | 操作者 | 下载失败行报告 |
| POST | `/import/{job_id}/rollback` | 操作者 | 回滚（30 分钟内有效） |
| POST | `/attachments` | 登录 | 上传（返回 `storage_key`） |
| GET | `/attachments/{id}/download` | 可见者 | 下载；**受限项目 + 密级 ≥ confidential 时加水印** |
| POST | `/export/{object_type}` | 登录 | 导出；受限项目禁止导出，其余按密级加水印并落审计 |

### 4.8 报表与驾驶舱（M8）

| Method | Path | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/dashboard/exec` | `exec` / `pmo_admin` | **高管驾驶舱**：关键节点总览 / 阻塞清单 / 待决策事项 |
| GET | `/dashboard/pm` | `pm` | PM 工作台：我的项目健康度、今日待办、需决策、资源缺口 |
| GET | `/dashboard/dept/{dept_id}` | `dept_head` | 部门看板：承接任务、负载、SLA 达成率 |
| GET | `/dashboard/pmo` | `pmo_admin` | PMO 运营：模板使用率、周报及时率、评审闭环率、风险复审及时率 |
| GET | `/reports/milestone-waterfall` | `exec` | 全公司重大节点瀑布（可按 Program/类型过滤） |
| GET | `/reports/blockers` | 登录 | 阻塞清单（受阻任务 + 超期工单） |
| GET | `/reports/pending-decisions` | 登录 | 待决策事项（含滞留天数） |
| GET | `/reports/health-trend` | 项目可见者 | 项目健康度趋势（按周） |

> 报表读接口一律加 Redis 缓存（TTL 10min）+ `T+10min` 预计算物化视图 `mv_project_health_daily`；驾驶舱接口 QPS 上限 20/人/分钟。

### 4.9 管理配置（M10）

| Method | Path | 权限 | 说明 |
| --- | --- | --- | --- |
| GET/POST/PATCH | `/admin/templates` | `pmo_admin` | 项目/报告模板（版本化） |
| POST | `/admin/templates/{id}/publish` | `pmo_admin` | 发布新版本（历史项目不受影响） |
| GET/POST/PATCH | `/admin/checklist-templates` | `pmo_admin` | Checklist 模板 |
| GET/POST | `/admin/dictionaries` | `pmo_admin` | 字典（含节假日，影响 SLA 与 CPM） |
| POST | `/admin/dictionaries/merge` | `pmo_admin` | 字典合并（技能标签治理） |
| GET/PUT | `/admin/integrations` | `pmo_admin` | 集成开关与参数（**密钥加密落库**） |
| POST | `/admin/integrations/{code}/test` | `pmo_admin` | 连通性测试 |
| GET | `/admin/audit-logs` | `pmo_admin` / `qa` | 审计查询（`action` 白名单视图单独路径 `/admin/audit-logs/sensitive`） |
| GET | `/admin/health-check` | 公开（内网） | 存活探针（DB/Redis/MinIO 状态） |

### 4.10 Webhook 入站（CI，单向）

| Method | Path | 鉴权 | 说明 |
| --- | --- | --- | --- |
| POST | `/webhooks/ci/{project_code}` | `X-CI-Token` 签名 | 构建/发布状态回写：`{"job":"x2-fw","status":"success","build_no":"#128","version":"v1.2.0","ref_task_code":"..."}` |
| POST | `/webhooks/wecom` | 企微回调签名 | 消息卡片点击回执、通讯录变更事件 |

**CI Webhook 规则**：只写 `task.ci_status/ci_ref` 与里程碑状态；**不触发流水线、不回写 CI**；签名不匹配返回 401 并告警；连续失败 3 次标记数据陈旧。

### 4.11 AI 服务接口（内部，前端不直接调用）

| Method | Path | 说明 |
| --- | --- | --- |
| POST | `/internal/ai/weekly-summary` | 输入结构化周报数据 → 输出摘要；超时 8s 降级为模板输出 |
| POST | `/internal/ai/qa` | 项目问答（RAG：只检索该用户有权限的项目，向量存 PG `pgvector` 或走关键词检索） |
| POST | `/internal/ai/todo-rank` | 待办重排序建议（返回 score 与理由，前端可忽略） |
| GET | `/internal/ai/usage` | 用量与费用看板 |

**AI 调用前置流程（必须）**：权限过滤 → 字段脱敏（项目名/人名/成本替换） → 配额检查 → 出网代理 → 回执留痕（`ai_call_log`）→ 回填映射。任一步失败走降级。

---

## 5. 状态机

### 5.1 项目状态机

```
draft ──submit──> applying ──approve──> active ──> closed
                     │                    │
                     └──reject──> draft   ├──suspend──> suspended ──resume──> active
                                          └──cancel──> cancelled
```

- `applying → active`：写 `project.code`、实例化阶段与门禁、创建首条基线 `baseline(kind='gate')`；
- `active → closed`：所有核心 Gate 通过 + 结项复盘（M9，P3 轻量时可跳过）；
- 状态变更一律落审计 + 通知干系人。

### 5.2 任务状态机

```
not_started ──start──> in_progress ──complete──> done
      │                    │  │
      │                    │  └──block──> blocked ──unblock──> in_progress
      │                    │                 │
      │                    │                 └──escalate──> (生成求助工单 + 待办)
      └──cancel──> cancelled
```

约束：

- `→ blocked`：**必须**填 `blocked_reason` + `blocked_help_user_id`（校验在 service 层，前端需同时拦截）；
- `→ done`：若 `is_milestone=true`，同步更新 `milestone.status`，并触发下游依赖重算（CPM）与 Program 推演；
- 进度上滚：`task.progress_pct` 变化 → 按 `est_hours` 加权更新父任务与 `project.progress_pct`；**PM 只做确认不做计算**。

### 5.3 Gate 状态机（承诺制，A3）

```
not_started ──materials_ready──> material_ready ──submit──> in_review
      in_review ──signoff_all──> passed | conditional | failed
      in_review ──waive──> waived（填风险接受说明）
      failed ──resubmit──> in_review
```

**承诺制核心规则（与 v1.2 强管控的关键差异）**：

| 规则 | 实现 |
| --- | --- |
| 未过 Gate **不锁**下一阶段任务 | `gate.blocked_flag=true` 仅触发告警，**不拦截** `project_stage` 推进与任务创建 |
| 未过 → 持续红色告警 | 项目卡片与驾驶舱标红；每日 09:00 向 PM + PM 主管 + PMO 推送（频控：同一 Gate 每日 1 次） |
| 绕过 → 记账 | `waive_reason` 必填，写入承诺台账，PMO 月度通报 |
| 高危 Gate 例外 | `is_high_risk=true`（Tapeout / MP 放行等）：Checklist 强制 + 强制会签，**未通过不得推进阶段** |
| Checklist 未完成 | 承诺制下为**警告 + 二次确认**，缺口进 `gate.gap_items`，每项需 Owner + 期限 |

### 5.4 工单状态机 + SLA

```
draft ──submit──> pending ──assign/accept──> accepted ──resolve──> resolved ──close──> closed
                     │            │
                     │            └──reject──> rejected ──> closed
                     └──超时未响应──> escalated(level 1→2) ──> 回到 pending/accepted
```

SLA 规则：

| 计时 | 起点 | 时限 | 超时动作 |
| --- | --- | --- | --- |
| 响应 SLA | `pending` 创建 | **1 个工作日**（D5 目标） | 升级至 `target_dept` 主管，推送企微 + 邮件 |
| 解决 SLA | `accepted` | 由 `ticket_type` + `priority` 决定，默认 5 个工作日 | 提醒 + 计入部门 SLA 达成率 |
| 升级 | 首次升级后 72h 未果（F5） | — | `escalate_level=2` → 分管副总，驾驶舱可见 |

- `target_user_id` 为空的工单：`pending` 状态下**同时**向部门主管生成"待分派"待办，分派后 SLA 重新起算（但保留原创建时间用于统计）；
- 工作日均需排除 `dictionary: holiday`。

### 5.5 评审状态机

```
draft ──schedule──> scheduled ──hold──> held ──all_items_closed──> closed
```

- `held`：录入结论 + 问题项；问题项全关闭才能 `closed`；
- 未闭环问题项 → 自动生成 owner 待办，超期每日催办（频控 1 次/日）。

### 5.6 交接物状态机

```
pending ──upload──> delivered ──accept──> accepted
                        │
                        ├──reject──> rejected ──> 回 pending
                        └──超期──> overdue（自动升级至双方主管）
```

### 5.7 导入任务状态机

```
uploaded ──validate──> validated(failed_rows 可 >0) ──execute──> running ──> succeeded | partial | failed
                                                                      │
                                                              rollback ──> rolled_back
```

- `validate` 阶段不落业务数据，只出错误报告；
- `execute` 在单事务内完成，`failed_rows > 0` 时按"整批失败"或"跳过错误行"两种模式（由操作者选择，默认整批失败）；
- `rollback` 依赖 `rollback_token`，30 分钟有效，回滚只删本次导入产生的记录（靠 `import_job_id` 反查）。

---

## 6. 权限与密级引擎（实现规范）

> **这是全系统唯一的安全收口点。** 任何绕过 `access/query.py` 的查询都视为缺陷，Code Review 一律打回。

### 6.1 判定顺序（伪代码，实现必须严格遵循）

```python
def can_access(user, obj_type, obj_id, action) -> bool:
    # 1) 外部账号：先走白名单，不参与内部 RBAC
    if user.is_external:
        return external_whitelist_check(user, obj_type, obj_id, action)

    # 2) 密级：最高优先级，先判"能不能碰这类数据"
    level = get_secrecy_level(obj_type, obj_id)
    if not secrecy_allows(user, level):
        return False

    # 3) 功能权限（RBAC）：角色是否允许该 action
    if not rbac_allows(user.roles, obj_type, action):
        return False

    # 4) 数据范围（组织树 × 项目空间 × 数据域）
    return data_scope_allows(user, obj_type, obj_id)

def list_query(user, obj_type, filters):
    """所有列表查询的唯一入口"""
    q = base_query(obj_type)
    q = apply_secrecy_filter(q, user)     # 强制注入
    q = apply_scope_filter(q, user)       # 强制注入
    q = apply_business_filters(q, filters)
    return q
```

**四条铁律**：

1. 密级 > 角色 > 数据域，顺序不可颠倒（密级是最高约束）；
2. **默认拒绝**：未命中任何授权规则一律不可见；
3. 列表查询必须注入过滤，**不允许先查后筛**（分页会错、性能会崩）；
4. 导出 = 读权限 + 额外导出权限 + 水印 + 审计，四者缺一不可。

### 6.2 数据域表达式（`data_domain.expr`）

```jsonc
{
  "any": [
    { "field": "project.type_id",   "op": "in",     "value": [1, 2, 3] },   // 芯片设计类项目
    { "field": "project.dept_id",   "op": "in_subtree", "value": 12 },
    { "field": "project.secrecy_level", "op": "<=", "value": "internal" }
  ]
}
```

支持的 op：`=`、`!=`、`in`、`not_in`、`<=`、`>=`、`in_subtree`（部门树）、`is_member`（项目空间成员）。**表达式求值在 `access/scope.py`**，禁止拼接 SQL 字符串（防注入）。

### 6.3 密级过滤规则

| 密级 | 可见范围 | 导出 | 外部账号 |
| --- | --- | --- | --- |
| `public` | 全员 | 允许 | 按白名单 |
| `internal` | 全员（登录） | 允许（带水印） | 按白名单 |
| `confidential` | 项目成员 + 主管 + PMO + 高管 | **禁止导出** | **一律不可见** |
| `secret` | 项目成员 + 密级管理员 | **禁止导出** | 不可见；不设外部通道 |

- 密级在**立项时必填**，变更走 `secrecy_change_request` 双人审批；
- 密级校验放在 `access/secrecy.py`，被 `list_query` 与 `can_access` 共同调用；
- **每周一次越权扫描任务**（job）：模拟低权限用户遍历受限项目，命中即告警（G 组已勾风险）。

### 6.4 外部账号校验

```python
def external_whitelist_check(user, obj_type, obj_id, action):
    if obj_id not in user.project_ids:      # 项目空间边界
        return False
    allowed_fields = user.field_whitelist.get(obj_type, [])
    if not allowed_fields:                   # 未开白名单 = 不可见
        return False
    if user.status != 'active' or user.expires_at < now():
        return False
    audit_log(actor_type='external', ...)    # 全量留痕
    return action in ('read', 'limited_write')
```

外部账号**一律禁止导出**（前端不渲染导出按钮，后端二次校验）。

### 6.5 必须接入统一访问层的位置（Checklist）

- [ ] 所有 `/api/v1/**` 列表接口
- [ ] 所有详情接口的首次取数
- [ ] 导出与下载接口
- [ ] 报表与驾驶舱聚合查询（含物化视图）
- [ ] AI 检索的语料过滤（**RAG 必须按用户权限过滤，否则等于越权外泄**）
- [ ] 通知推送前的数据范围校验（不能把机密项目信息推给无权限的人）

---

## 7. 关键算法规格

### 7.1 关键路径（CPM）

**输入**：项目内全部 task（`plan_start`/`plan_end`/工期）、dependency（`dep_type` + `lag_days`）。
**输出**：`task.is_critical` 标记 + 关键路径任务 id 有序列表 + 项目最早完成日。

**算法**（自研部分，约 300–500 行，放 `domains/task/cpm.py`）：

1. 拓扑排序（Kahn）；**检测到环 → 抛出 `CIRCULAR_DEPENDENCY` 错误并返回环路路径**，不静默处理；
2. 正推 ES/EF：`ES = max(前置 EF + lag)`，无前置则 `ES = plan_start`；`EF = ES + duration`；
3. 逆推 LS/LF：`LF = min(后继 LS - lag)`，无后继则 `LF = 项目 EF`；`LS = LF - duration`；
4. 总浮动 `TF = LS - ES`；**`TF <= 0` 即关键路径**；
5. 工期按**工作日**计算（排除周末 + `dictionary: holiday`）；
6. 里程碑任务 duration = 0。

**性能边界**：单项目 5000 任务 / 10000 依赖，全量重算 < 500ms。超过则**增量重算**（仅重算受影响子图，从变更任务出发沿依赖正向传播）。

**触发时机**：任务日期/状态变更、依赖变更、基线创建后。异步执行（Redis Stream），完成后回写 `is_critical` 并推送甘特刷新事件。

### 7.2 项目健康度（P1 只启用三项可解释权重）

```
score = 100
      - W1 × 进度偏差惩罚     (W1 = 40)
      - W2 × 超期阻塞惩罚     (W2 = 35)
      - W3 × 门禁状态惩罚     (W3 = 25)

进度偏差惩罚 = clamp(|plan_progress - actual_progress| / 10, 0, 1)      // 每偏差 10% 扣满
超期阻塞惩罚 = min(1, (超期未响应工单数 × 0.3 + 受阻任务数 × 0.15))
门禁状态惩罚 = 1 if 存在 blocked_flag=true 的核心 Gate else 0

红：score < 60    黄：60 ≤ score < 80    绿：score ≥ 80    数据不足：na
```

- 权重存 `dictionary` 可配置，**P1 固定上述三组权重且不外露调整界面**（冷启动无数据支撑调参）；
- 每日 02:30 批量重算，写入 `project.health`，变更时推送；
- **必须在 UI 上可解释**：点击健康度标签展示三项分值明细，不允许黑箱。

### 7.3 进度加权计算

```
父任务进度 = Σ(子任务 est_hours × progress) / Σ(子任务 est_hours)     // est_hours 缺失时按 1 计
项目进度   = Σ(一级 WBS 下所有叶子任务 est_hours × progress) / Σ(est_hours)
```

里程碑任务：`done` → 100%，其余 → 0%。阶段进度 = 该阶段下任务加权。

### 7.4 资源可用工时（降级算法，无 HR 接口）

```
可用工时(周) = 标准工时 40h
             − Σ(该用户在 [start,end] 内 approved 的 reservation.percent × 40)
             − 请假工时（Excel 导入的 leave 数据）
可用窗口 = 可用工时 > 8h 的周
```

不依赖 HR 接口，请假数据走导入；**导入缺失时按 0 处理并在页面标注"请假数据未更新"**。

### 7.5 待办智能排序（AI 场景③）

**规则分（AI 不可用时兜底，必须实现）**：

```
priority_score = 100
  − 逾期天数 × 5
  + (kind 权重：approval 30 / review 20 / ticket 15 / task 10 / meeting 5)
  + (是否阻塞他人 25)
  + (是否关键路径任务 20)
  − 已滞留天数 × 0.5
```

**AI 增强**：每日 08:00 对每人待办调用一次，返回 0–10 的调整量与一句话理由，写入 `priority_score` 与 `source_channel='ai'`；**AI 失败或超时 3s 直接回落规则分**，前端展示排序但标注"按规则排序"。

### 7.6 周报自动生成（F-11）

自动生成内容（`auto_content`，不可被 PM 修改，PM 只补充）：

| 区块 | 数据来源 |
| --- | --- |
| 本周完成任务 | 本周 `status→done` 的任务 |
| 进度偏差 | 当前进度 vs 上周快照 vs 基线 |
| 风险/问题变化 | 本周新增/关闭/升级的 risk 与 issue |
| 下周计划 | `plan_start` 落在下周的任务 |
| 需决策事项 | 状态为 `pending` 且 `ticket_type=decision` 的工单 + 未签核 Gate |

AI 摘要：对上述结构化数据生成 ≤ 200 字摘要，**超时 8s / 失败 / 超预算 → `ai_summary` 留空，前端隐藏该区块**（不阻塞发布）。

三级汇聚：项目周报发布 → 部门周报（聚合本部门项目）→ PMO/经营周报（聚合全公司）。汇聚为**链接式聚合**（保留下钻），不做二次 AI 生成以省 token。

### 7.7 RAG 问答（AI 场景②）

- 语料：`project` / `task` / `milestone` / `risk` 的文本字段，**检索前必须按用户权限过滤**（§6.5）；
- P1 用 `pg_trgm` 关键词检索 + 结构化查询取数，再交给 LLM 组织答案（**不上向量库**，规模不到）；
- 答案必须附**引用来源**（项目/任务 id + 链接），无法检索到时明确回答"未找到"，**禁止编造**；
- 每次调用写 `ai_call_log`（只存摘要）。

---

## 8. 集成作业规格

> 详细接口参数见 `03_集成接口清单.md`，本节定义**工程实现要求**（调度、幂等、重试、降级）。

### 8.1 LDAP 同步（`jobs/sync_ldap.py`）

| 项 | 要求 |
| --- | --- |
| 调度 | 每日 02:00 全量比对 + 工作日每小时增量 |
| 逻辑 | 以 `employee_no` 为键 upsert `user`；仅更新 `email/status/title`；**不覆盖** `dept_id`（企微主源） |
| 冲突 | 状态/部门不一致 → 写 `sync_conflict`，不自动改数据 |
| 幂等 | 按 `employee_no` 幂等；重复执行不产生重复记录 |
| 失败 | 连续 3 次失败 → `integration_config.last_status='frozen'` + 告警；已同步用户可登录 |
| 审计 | 每次同步写一条汇总审计（变更数） |

### 8.2 企微通讯录同步

| 项 | 要求 |
| --- | --- |
| 调度 | 每日 03:00 |
| 逻辑 | 拉取部门树 → upsert `dept`（维护 `path`）；拉取成员 → upsert `user.dept_id/title/avatar`；**不覆盖** `status`（LDAP 主源） |
| 离职处理 | 企微中已删除且 LDAP 已禁用 → `user.status='disabled'`，保留历史数据 |
| 失败 | 同上，冻结 + 告警；组织树沿用上次快照（缓存 1h 供前端） |

### 8.3 企微消息推送

| 事件类型（`event_type`） | 默认渠道 | 默认频控 |
| --- | --- | --- |
| `task_assigned` | wecom + inapp | realtime |
| `task_overdue` | wecom + inapp | daily_digest 09:00 |
| `ticket_created` / `ticket_escalated` | wecom + email | realtime |
| `gate_pending` | wecom + email | daily_digest |
| `risk_review_due` | wecom + inapp | daily_digest |
| `deliverable_overdue` | wecom | daily_digest |
| `weekly_report_draft_ready` | wecom + inapp | 每周五 17:00 |
| `decision_pending`（高管） | wecom + email | realtime（**带一键批准入口**） |

**实现要求**：

- 消息先落 `notification(status='pending')`，由发送协程消费；**业务代码不直接调企微 API**；
- 频控：同 `dedup_key` 在窗口期内合并，`freq_limit` 决定聚合策略；
- 重试：3 次指数退避，仍失败 → 降级邮件（重要）/站内，最终进死信队列并告警；
- 卡片点击回执走 `/webhooks/wecom`，回写 `notification.status`；
- 个人偏好优先于默认规则（D6），用户可关闭某类通知。

### 8.4 CI Webhook

| 项 | 要求 |
| --- | --- |
| 鉴权 | `X-CI-Token` + HMAC-SHA256 签名（body + 时间戳），时间戳偏差 > 5min 拒绝 |
| 映射 | `ref_task_code` → task；无匹配时按 `job` 名模糊匹配里程碑，仍无匹配 → 丢弃并记录 |
| 幂等 | 同 `build_no` 重复到达只处理一次 |
| 失败 | 返回 4xx/5xx 给 CI（CI 侧自行重试）；平台侧不做业务补偿 |

### 8.5 CMDB 只读（P2，P1 预留开关）

每日拉取一次，写入 `resource_pool(res_type='cluster')`；失败标记数据陈旧，集群资源申请转人工工单。

### 8.6 xwiki SSO

平台只生成**目录链接与命名规范**（`/spaces/{project_code}/{stage_code}/...`）；不做内容同步；单点失败时链接降级为 xwiki 首页。

### 8.7 AI 网关（出网代理 + 脱敏 + 配额）

```
业务请求 → 权限过滤 → 脱敏映射表（项目名→P-001，人名→角色，成本→删除）
        → 配额检查（按人/按天/按月预算） → 代理机 443 → 外购 API
        → 响应回填映射 → ai_call_log（只存摘要） → 返回
```

| 项 | 要求 |
| --- | --- |
| 脱敏 | 建立内存映射表，**仅当次请求有效**；响应回填后销毁 |
| 供应商 | 主备两家，主失败自动切备，切换告警 |
| 配额 | 单用户 20 次/天；月度预算 80% 时告警，100% 时全局降级为模板输出 |
| 超时 | 摘要 8s / 排序 3s / 问答 10s；超时即降级，**不重试**（省钱） |
| 日志 | 留存 180 天，只存 `request_digest`、`token`、`cost`、`status` |

### 8.8 邮件回执解析（供应商批次，一期免端口方案）

| 项 | 要求 |
| --- | --- |
| 触发 | 每 30 分钟轮询指定邮箱（IMAP），只处理带约定 subject 前缀的邮件 |
| 模板 | 平台生成固定格式回执单（含 `batch_id` 二维码/明文标识），供应商回复后解析 |
| 解析 | 正则 + 键值对提取 `投料/出片/交期/良率/异常`；**置信度 < 0.8 时不自动入库**，进人工确认队列 |
| 入库 | 写 `batch_milestone(source='email_parse')` + `batch.status`；同一 `batch_id` 后到的邮件覆盖先到的（取最新 `sent_at`） |
| 失败 | 解析失败 → 邮件进"未识别"文件夹 + 每日汇总提醒 PMO |

### 8.9 Excel 导入器（P1 核心，F-06）

**支持的导入类型与必填列**：

| 类型 | 必填列 | 校验规则 |
| --- | --- | --- |
| `project` | 项目名称、类型 code、PM 工号、计划起止、密级 | 类型 code 合法；PM 工号存在于 `user`；密级合法 |
| `task` | 项目 code、WBS 路径、任务名、负责人工号、计划起止 | 项目存在且有权限；WBS 路径自动生成（≤4 级）；负责人存在 |
| `milestone` | 项目 code、里程碑名、计划日期、类型 | 日期合法 |
| `timesheet`（P2） | 工号、项目 code、周起始、工时 | 工时 ≤ 12h/天；人项目匹配 |
| `cost_ledger`（P2） | 项目 code、年月、科目、金额 | 金额数值合法 |
| `leave`（P2） | 工号、日期、时长 | 用于 §7.4 |

**实现要求**：

1. 模板文件由 `/import/template/{type}` 生成（含下拉字典 sheet 与示例行）；
2. 上传后先做**列映射建议**（按表头名模糊匹配），允许人工调整；
3. `validate` 阶段逐行校验，**错误报告为原文件 + 错误列高亮 + 错误原因列**，可下载；
4. 执行阶段：单事务；失败行 > 0 默认整批回滚；
5. 幂等：`external_ref` 列存在时按该键 upsert，重复导入不产生重复数据；
6. 回滚：30 分钟内可一键回滚；
7. **导入的存量数据默认 `data_pedigree='trial'`**，需 PM 在 Gate 复核后转 `official`（F2 防污染基线）。

---

## 9. 前端页面清单

### 9.1 路由表

| 路径 | 页面 | 阶段 | 关键组件 |
| --- | --- | --- | --- |
| `/` | 工作台（按角色分发） | P1 | PM 工作台 / 成员待办 / 高管驾驶舱 |
| `/dashboard/exec` | 高管驾驶舱 | P1 | 节点瀑布、阻塞清单、待决策 |
| `/projects` | 项目列表 | P1 | 筛选（类型/状态/健康度/PM）、密级徽标 |
| `/projects/:id` | 项目概览 | P1 | 信息卡、健康度明细、阶段条、干系人 |
| `/projects/:id/wbs` | WBS 与任务 | P1 | 树表 + 批量编辑 |
| `/projects/:id/gantt` | 甘特图 | P1 | **frappe-gantt**、基线对比、关键路径开关 |
| `/projects/:id/gates` | 门禁与评审 | P1 | Gate 卡片、Checklist、签核、承诺台账入口 |
| `/projects/:id/weekly` | 项目周报 | P1 | 自动草稿 + PM 补充区 |
| `/programs` / `/programs/:id` | 项目集与依赖 | P1 尾 | Program 时间轴、跨项目依赖、交接物 |
| `/todos` | 统一待办 | P1 | 分类标签、排序、IM 同款操作 |
| `/tickets` / `/tickets/:id` | 协同工单 | P1 | SLA 计时、流转日志、升级记录 |
| `/meetings/:id` | 会议决议 | P1 | 决议转待办 |
| `/reports/*` | 报表 | P1（最小）/ P2（完整） | — |
| `/admin/*` | 管理后台 | P1 | 模板、字典、权限、密级、集成、同步冲突、审计 |
| `/m/*` | 企微 H5 精简页 | P1 | 待办、审批、工单处理、查看 |

### 9.2 关键页面要点

**项目列表**：默认按健康度排序（红在前）；密级 ≥ confidential 的项目对无权限者**不出现在列表中也不出现在总数里**；空态引导"从 Excel 导入存量项目"。

**甘特页**：

- 唯一甘特实现封装在 `components/GanttChart.tsx`，**禁止在别处直接 import frappe-gantt**；
- 工具栏：视图缩放（月/周/季）、显示关键路径开关、基线对比下拉；
- 拖拽改期 → 乐观更新 + 失败回滚 + 提示"将影响 N 个下游任务"；
- 5000 任务渲染：按可视区间增量加载，**首屏 < 2.5s**（50 人并发验收）。

**统一待办**：

- 顶部 5 个分类标签（任务/审批/评审/工单/会议决议），默认按 `priority_score` 排序；
- 每条待办支持"完成 / 稍后 / 转派"；`blocked` 任务直接显示求助对象；
- AI 排序生效时右上角提示"智能排序"，点击可切回规则排序。

**协同工单发起页**（针对 D5 的核心设计）：

- `target_user_id` 可留空，此时展示提示"将由 {部门} 主管分派责任人"，**降低发起人的心理负担**；
- 表单字段精简到 5 个：类型、标题、关联项目、被请求部门、详细说明；
- 提交后即时展示"SLA 响应截止时间"，让双方都有预期。

**门禁页（承诺制）**：

- 未过 Gate 时展示橙色警示条而非红色阻断弹窗，文案："该 Gate 未完成，项目仍可推进，但将持续告警并计入承诺台账"；
- "提交评审"按钮在 Checklist 未完成时**可点击**，弹出二次确认 + 缺口清单填写表单；
- 高危 Gate（Tapeout/MP）走强制流程，UI 明确标识"高危门禁 · 必须通过"。

**管理后台 — 同步冲突**：表格列出冲突类型与两侧数据，操作为"以 LDAP 为准 / 以企微为准 / 合并 / 标记离职"，一键处理。

### 9.3 企微 H5 页面（`/m/*`）

只做 4 件事：**看待办、审批、处理工单、查看项目**。设计约束：

- 单页操作 ≤ 3 步，按钮热区 ≥ 44px；
- 不做甘特（移动端渲染 5000 任务无意义），只展示"我的任务 + 关键节点"；
- 复用企微 JS-SDK 的身份，免二次登录；
- 卡片点击直达对应 H5 页，处理完回写待办状态。

### 9.4 设计规范

| 项 | 约定 |
| --- | --- |
| 主色 | AntD 默认蓝 `#1677ff`；**延误/风险/阻塞 = 红 `#cf1322`，正常/达成 = 绿 `#389e0d`**（国内惯例，禁止反转） |
| 健康度 | 红 `#cf1322` / 黄 `#d46b08` / 绿 `#389e0d` / 无数据 灰 |
| 密级徽标 | 公开 灰 / 内部 蓝 / 机密 橙 / 绝密 红，全局统一 `SecrecyBadge` 组件 |
| 字号 | 正文 14px，列表密度"中等"，表格行高 48px |
| 表格 | 关键列表支持列设置与本地记忆；超宽表格横向滚动，首列固定 |
| 空态 | 每个列表必须有空态插画 + 一句引导文案 + 主操作按钮 |
| 加载 | 列表用骨架屏；写操作按钮 loading 防重复提交 |
| 错误 | 全局错误拦截 → `message.error` + 错误码（便于排查）；表单错误定位到字段 |
| i18n | 所有文案走 `t()`，P1 只维护中文，key 命名规范为 `{module}.{element}.{field}` |

---

## 10. 非功能需求与验收标准

### 10.1 性能指标（可测）

| 场景 | 指标 | 测试方法 |
| --- | --- | --- |
| 项目列表（100 项目） | P95 < 800ms | k6，50 并发循环 5min |
| 甘特（5000 任务）首屏 | < 2.5s | 50 并发（验收项，见 §8.1 上线标准） |
| 甘特拖拽响应 | < 300ms | 单用户操作计时 |
| 待办中心 | P95 < 500ms | 50 并发 |
| 驾驶舱三卡片 | < 1.5s（缓存命中）/ < 5s（未命中） | 10 并发 |
| CPM 全量重算（5000 任务） | < 500ms | 单测埋点 |
| Excel 导入（1000 行） | < 30s | 实测 |
| 峰值并发 | 300（周报集中提交时段） | k6 压测 |

**降级预案**：并发超 400 时，关闭甘特自动刷新与驾驶舱实时计算（只读缓存），保证核心读写可用。

### 10.2 安全要求（上线前 Checklist）

- [ ] 所有列表查询经统一访问层，Code Review 逐条确认
- [ ] 越权扫描 job 每周运行，无命中
- [ ] 密级 ≥ confidential 项目：导出按钮不渲染且后端拦截
- [ ] 导出文件带水印（用户名 + 时间）
- [ ] 密钥全部走环境变量，`integration_config.params` 加密落库
- [ ] 密码/令牌不明文落日志；日志脱敏中间件生效
- [ ] 审计日志覆盖：权限变更、Gate 结论、密级变更、基线修改、导出、登录
- [ ] 越权扫描、SQL 注入、XSS 三项目前无高危
- [ ] 依赖漏洞扫描（每周）无高危未修复项
- [ ] 渗透测试一次（预算已列 15 万），高危项闭环后才准上线

### 10.3 日志与可观测

- 结构化 JSON 日志，每条带 `trace_id`，同一请求全链路可串；
- 关键指标：`api_latency`、`job_status`、`notification_fail_rate`、`ai_cost_daily`、`import_fail_rate`；
- 告警阈值：API 错误率 > 3%、通知失败率 > 5%、任一 job 连续失败 3 次、AI 月度预算 > 80%；
- 告警渠道：企微机器人 → PMO + 开发。

### 10.4 备份与恢复

| 项 | 要求 |
| --- | --- |
| 备份 | 每日增量 + 每周全备；保留：日备 30 天，周备 12 周 |
| 对象存储 | MinIO 版本控制开启，附件不随数据库备份 |
| 恢复演练 | 每季度一次，记录 RTO；**目标 RTO < 4h，RPO < 24h**（D-3） |
| 灾备 | 无异地；数据库主备同机房（D-3 已确认接受） |

### 10.5 P1 验收用例（可勾选，全部通过才准上线）

**账号与权限**

1. 用 LDAP 账号可登录；企微扫码可登录
2. 离职账号（LDAP 禁用）登录被拒
3. 同步冲突出现在管理后台并可裁决
4. 机密项目对非成员不可见（列表与详情双验证）
5. 密级变更需两人审批，仅一人通过不生效
6. 外部账号（若有）只能看到白名单字段，导出按钮不存在

**项目与任务**

7. 十类项目模板均可实例化，裁剪留痕
8. 建任务不填 owner 无法保存
9. 任务置为受阻必须填原因与求助对象
10. 5000 任务项目可打开甘特，首屏 < 2.5s
11. 关键路径高亮正确（与手工计算比对 3 条路径）
12. 依赖成环时被拒绝并提示环路
13. 基线对比显示偏移天数正确
14. Excel 导入 1000 行任务成功；故意造 10 行错误数据，错误报告准确且可下载
15. 导入后 30 分钟内可一键回滚，数据复原

**门禁（承诺制）**

16. Checklist 未完成时仍可提交评审（二次确认 + 缺口登记）
17. 未过 Gate 时下一阶段任务**可以创建**（不阻断）
18. 未过 Gate 的项目在驾驶舱标红且每日推送一次
19. 高危 Gate（Tapeout）未通过时**无法推进阶段**
20. 承诺台账能查到所有 waive 与带缺口通过记录

**协同（D5 核心）**

21. 发起工单不指定责任人时，部门主管收到分派待办
22. 工单超 1 个工作日未响应，自动升级至主管并推送
23. 工单 72h 未解决升级至分管副总（F5）
24. 会议决议生成待办，未闭环每日催办一次
25. 统一待办汇聚 5 类来源，排序生效

**周报与 AI**

26. 周报草稿自动生成，5 个区块数据准确
27. PM 可补充备注与风险，发布后三级汇聚可见
28. AI 不可用时周报仍可发布（摘要区块隐藏）
29. AI 用量超预算后自动降级，页面提示

**驾驶舱与运营**

30. 高管驾驶舱三张卡片（节点总览 / 阻塞清单 / 待决策）数据正确，可下钻
31. PMO 运营报表四项 KPI（模板使用率 / 周报及时率 / 评审闭环率 / 风险复审及时率）可出数
32. 审计日志可查询并导出，敏感操作独立视图可用

**非功能**

33. 50 并发压测下核心接口 P95 达标
34. 渗透测试高危项全部闭环
35. 备份恢复演练一次，RTO < 4h

---

## 11. 开发任务 Backlog（P1，6 个月 / 12 个双周迭代）

> 人力假设：全栈 1 + 前端 1 + 测试 0.5 = **2.5 人**；一个双周迭代产能约 **25 人日**。

| Sprint | 周期 | 目标 | 主要任务 | 人日 |
| --- | --- | --- | --- | --- |
| **S0** | 第 1 月上半 | 骨架与底座 | 仓库/目录/CI/环境；`core`(config/security/errors/logging/audit)；统一访问层骨架；PG+Redis+MinIO 起容器；Alembic 初始化 | 22 |
| **S1** | 第 1 月下半 | 身份域 | `dept/user/role/role_binding` 建表；LDAP 同步作业；企微通讯录同步；登录（密码 + 扫码）；冲突清单页 | 26 |
| **S2** | 第 2 月上半 | 项目域 | `program/project/project_type/stage_template/gate_template` 建表；**十类模板 seed**；立项 + 审批 + 编号生成；项目列表/详情 | 26 |
| **S3** | 第 2 月下半 | 任务域 | `wbs/task/task_raci/dependency` 建表；任务 CRUD + RACI 唯一约束；WBS 树页；进度上滚计算 | 26 |
| **S4** | 第 3 月上半 | 甘特与 CPM | frappe-gantt 封装；依赖成环校验；**CPM 算法 + 单测**；关键路径高亮；基线快照与对比 | 28 |
| **S5** | 第 3 月下半 | 门禁与评审 | `gate/checklist_instance/review/review_item/review_signoff`；承诺制流程；二次确认与缺口登记；高危 Gate 强制校验；承诺台账 | 26 |
| **S6** | 第 4 月上半 | 协同工单 | `ticket/ticket_action`；发起/分派/受理/驳回/解决/关闭；**SLA 计算 + 扫描 job**；升级链路；满意度 | 26 |
| **S7** | 第 4 月下半 | 待办与通知 | `todo_item/notification/notification_rule`；统一待办中心；企微卡片推送 + 回执；频控与降级；个人偏好；H5 首版 | 26 |
| **S8** | 第 5 月上半 | 周报与会议 | `weekly_report` 自动生成；PM 补充与发布；三级汇聚；会议决议转待办；AI 摘要接入（含降级） | 26 |
| **S9** | 第 5 月下半 | 导入器 + AI | Excel 导入器（模板/映射/校验/执行/回滚）；AI 网关（脱敏/配额/两家热备/日志）；待办智能排序；RAG 问答 | 28 |
| **S10** | 第 6 月上半 | Program 与驾驶舱 | `program` 挂载；跨项目依赖与延期推演；交接物；驾驶舱三卡片；PM 工作台；PMO 运营报表 | 28 |
| **S11** | 第 6 月下半 | 安全加固与试点上线 | 越权扫描 job；导出水印；渗透测试整改；CI Webhook 打通 1 个 BU；性能压测；种子用户培训；试点 BU 上线 | 26 |
| **S12** | 缓冲 | 试点问题修复与验收 | 试点反馈修复；验收用例逐条走查；运维手册与 README 补齐 | 24 |

**合计约 322 人日 ≈ 2.5 人 × 6 个月（约 300 有效人日）**，S12 为缓冲。

**每个 Sprint 的 DoD（完成定义）**：

1. 代码合入 `develop`，CI 绿（lint + 单测 + 构建）；
2. 新增/修改的表有 Alembic 迁移，且 `downgrade` 已验证；
3. 新增接口有 ≥ 1 个正向单测 + 1 个权限/边界单测；
4. 该域 README 更新（数据模型 + 关键流程 + 已知坑，≤ 2 页）；
5. 演示环境可点通，PMO 侧能看见并试用。

---

## 12. 编码规范与 AI 编码纪律

### 12.1 通用规范

| 项 | 约定 |
| --- | --- |
| 命名 | 表/字段 `snake_case`；Python `snake_case`；TS 组件 `PascalCase`，变量 `camelCase` |
| 分层 | `router`（只做参数校验与鉴权）→ `service`（业务逻辑）→ `model`（持久化）；**router 不得写业务 SQL** |
| 事务 | 写操作必须显式事务；**跨聚合的一致性问题用事件+补偿，不用分布式事务** |
| 异常处理 | 抛业务异常（`errors.py` 定义的错误码），**禁止裸露 `except: pass`** |
| 日志 | 禁止 `print`；用 `logger.info(msg, extra={...})`；**禁止打印密码/令牌/身份证/完整手机号** |
| 分页 | 列表接口必须有 `size` 上限；**禁止无分页的全表查询** |
| N+1 | 列表接口禁止在循环里查库；用 `selectinload` 或批量查询 |
| 时间 | 统一 `datetime.now(UTC)`；**禁止 `datetime.now()` 不带时区** |
| 魔法值 | 枚举与字典值一律用常量或 `dictionary` 表，**禁止散落字面量** |

### 12.2 数据库规范

- 每张新表必须有 `created_at/updated_at`；业务表必须有 `deleted_at`；
- **禁止在业务高峰期执行 DDL**；迁移脚本必须可回滚；
- 新增索引需评估写入损耗；大表加索引用 `CREATE INDEX CONCURRENTLY`；
- **生产库禁止手工改数据**，一切变更走迁移或受审批的运维脚本（留审计）。

### 12.3 测试规范

| 层 | 要求 |
| --- | --- |
| 单元测试 | `domains/` 下 service 层覆盖率 ≥ 80%；CPM、权限引擎、SLA、健康度 **必须 100% 覆盖分支** |
| 接口测试 | 每个写接口至少一个"无权限"用例 |
| E2E（Playwright） | 覆盖 8 条主流程：登录→立项→建任务→甘特→提交 Gate→发起工单→发周报→看驾驶舱 |
| 数据 | 测试用独立库与种子数据，**禁止连生产库跑测试** |

### 12.4 AI 辅助编码红线（2.5 人团队的生命线）

**允许 AI 生成**：CRUD、DTO/校验、前端表单与表格、工具函数、测试用例草稿、README 草稿。

**禁止 AI 生成后直接合入（必须人工评审 + 单测）**：

1. `access/` 权限与密级引擎的全部代码；
2. 数据库迁移脚本（**禁止 AI 自动执行到生产**）；
3. CPM 关键路径算法、SLA 计算、健康度权重、金额计算；
4. 涉及出网的 AI 网关与脱敏逻辑；
5. LDAP/企微同步的冲突处理分支。

**流程纪律**：

- **先写契约后写代码**：本文件 §3（数据模型）与 §4（API）是契约，契约未定的模块不允许开始编码；
- 每个模块开写前，先把该模块的"数据模型 + 接口 + 状态机"三张表贴给 AI，再让它实现；
- 每周一次依赖漏洞扫描 + 依赖版本冻结；
- 每个模块必须有 ≤ 2 页 README（数据模型 / 关键流程 / 已知坑）；**这是小团队对抗人员流动的唯一保险**；
- 代码评审：即使只有 2 人，也必须互相 review，禁止直接 push `main`。

---

## 13. 交付物清单

| # | 交付物 | 时点 |
| --- | --- | --- |
| 1 | 源代码（前后端）+ 数据库迁移脚本 | 持续 |
| 2 | 部署包：`docker-compose.yml` + 环境变量样例 + 部署手册 | S0 / S11 |
| 3 | 十类项目模板 seed 脚本与模板配置表 | S2 |
| 4 | API 文档（OpenAPI，自动生成） | 持续 |
| 5 | 各模块 README（每模块 ≤ 2 页） | 每 Sprint |
| 6 | 测试用例与 E2E 脚本 | 持续 |
| 7 | 运维手册：备份恢复、告警处置、常见故障 | S11 |
| 8 | 用户手册：PM 指南、成员指南、管理员指南 | S11 |
| 9 | 培训材料（种子用户 2h 实操） | S11 |
| 10 | 验收报告（§10.5 逐条签字） | S12 |

---

## 14. 附录

### 附录 A　十大项目类型 Stage-Gate 配置（seed 数据）

> 直接作为 `scripts/seed/project_types.py` 的数据源。`is_core` = 不可裁剪；`is_high_risk` = 强制会签 + Checklist 强制。

#### A1 芯片设计 `chip_design`

| 阶段 code | 阶段名 | 顺序 | 核心 | 门禁 code | 门禁名 | 核心 | 高危 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `kickoff` | 立项 | 1 | ✅ | `G1_spec` | 规格冻结 | ✅ | — |
| `spec` | 规格定义 | 2 | ✅ | `G1_spec` | 规格冻结 | ✅ | — |
| `arch` | 架构设计 | 3 | ✅ | `G2_arch` | 架构评审通过 | ✅ | — |
| `rtl` | RTL 开发 | 4 | ✅ | `G2_rtl_freeze` | RTL Freeze | ✅ | — |
| `verify` | 验证 | 5 | ✅ | `G3_tapeout` | Tapeout 决策 | ✅ | **✅** |
| `tapeout` | 流片 | 6 | ✅ | `G3_tapeout` | Tapeout 决策 | ✅ | **✅** |
| `post_silicon` | 硅后调试 | 7 | — | `G4_silicon_pass` | 硅后功能通过 | ✅ | **✅** |
| `mp_import` | 量产导入 | 8 | — | `G5_mp_release` | 量产放行 | ✅ | **✅** |

**关键交付物**：Spec、验证计划与覆盖率报告、Tapeout 评审报告、硅后测试报告。

#### A2 芯片封装设计 `pkg_design`

| 阶段 | 门禁 | 核心/高危 |
| --- | --- | --- |
| 封装选型 | 封装方案评审 | ✅/— |
| 基板设计 | 基板设计评审 | — |
| 热/电/应力仿真 | 仿真报告通过 | ✅/— |
| 打线 / DFM 检查 | DFM 检查通过 | ✅/— |
| 封装厂投产 | 投产放行 | ✅/**✅** |

交付物：封装规格书、仿真报告、Gerber。

#### A3 芯片测试工程 `test_eng`

| 阶段 | 门禁 | 核心/高危 |
| --- | --- | --- |
| 测试计划 | 测试计划评审 | ✅/— |
| ATE 程序开发 | 程序评审 | — |
| CP/FT 调试 | 测试覆盖率门禁 | ✅/**✅** |
| 可靠性验证 | 可靠性通过 | ✅/— |
| 量产测试导入 | 量产测试放行 | ✅/**✅** |

交付物：测试计划、Pattern、Correlation 报告。

#### A4 硬件板卡设计 `hw_board`

| 阶段 | 门禁 | 核心/高危 |
| --- | --- | --- |
| 需求分析 | 需求评审 | ✅/— |
| 原理图 | 原理图评审 | ✅/— |
| Layout | Layout 评审 | ✅/— |
| 打样 | — | — |
| 调试 | EVT 放行 | ✅/**✅** |
| 认证 | 认证通过 | ✅/— |

交付物：原理图、BOM、测试报告。

#### A5 软件设计 `software`

| 阶段 | 门禁 | 核心/高危 |
| --- | --- | --- |
| 需求 | 需求评审 | ✅/— |
| 架构 | 架构评审 | ✅/**✅** |
| 开发 | 代码冻结 | ✅/— |
| 测试 | 测试报告通过 | ✅/— |
| 发布 | 发布放行 | ✅/**✅** |

交付物：架构文档、测试报告、Release Note。**CI Webhook 回写点：开发/发布阶段。**

#### A6 整机设计 `system`

| 阶段 | 门禁 | 核心/高危 |
| --- | --- | --- |
| 方案 | 方案评审 | ✅/**✅** |
| 结构/电源/散热设计 | 设计评审 | ✅/— |
| 样机 | 样机放行 | ✅/**✅** |
| 整机验证 | 整机验证通过 | ✅/**✅** |

交付物：整机规格、验证报告。

#### A7 集群调测 `cluster`

| 阶段 | 门禁 | 核心/高危 |
| --- | --- | --- |
| 单机联调 | 联调通过 | ✅/— |
| 小集群 | 小规模验证通过 | — |
| 大规模组网 | 组网通过 | ✅/— |
| 压测优化 | 性能达标 | ✅/**✅** |
| 现场部署 | 部署验收 | ✅/— |

交付物：调测报告、性能基线、部署手册。

#### A8 NPI 导入 `npi`

| 阶段 | 门禁 | 核心/高危 |
| --- | --- | --- |
| 转产评估 | 转产评估通过 | ✅/— |
| EVT | EVT 通过 | ✅/**✅** |
| DVT | DVT 通过 | ✅/**✅** |
| PVT | PVT 通过 | ✅/**✅** |
| 良率爬坡 | 良率达标 | ✅/**✅** |
| MP | **MP 放行** | ✅/**✅** |

交付物：NPI 计划、良率分析、量产文件包。

#### A9 客户交付专项 `delivery`

| 阶段 | 门禁 | 核心/高危 |
| --- | --- | --- |
| 合同评审 | 合同评审通过 | ✅/**✅** |
| 交付计划 | 计划确认 | ✅/— |
| 安装/部署 | 部署完成 | ✅/— |
| 验收 | 出厂验收 / 终验 | ✅/**✅** |
| 回款 | 回款确认 | — |

交付物：交付计划、验收报告。

#### A10 解决方案专项 `solution`

| 阶段 | 门禁 | 核心/高危 |
| --- | --- | --- |
| 需求分析 | 需求确认 | ✅/— |
| 方案设计 | 方案评审 | ✅/**✅** |
| POC | POC 通过 | ✅/**✅** |
| 投标/落地 | 中标/落地确认 | ✅/— |

交付物：方案书、POC 报告。

#### A11 里程碑 kind 字典（供驾驶舱聚合）

`tapeout`（流片）、`pkg_back`（封装回片）、`cp_pass`（CP 通过）、`ft_pass`、`board_evt`（板卡 EVT）、`system_int`（整机联调）、`cluster_stress`（集群压测）、`npi_mp`（NPI MP）、`delivery_accept`（客户验收）、`poc_pass`（POC 通过）。

### 附录 B　错误码表

| 码段 | 含义 | 示例 |
| --- | --- | --- |
| `0` | 成功 | — |
| `1000–1099` | 认证与鉴权 | `1001` 未登录、`1002` 令牌过期、`1003` 无权限、`1004` 外部账号字段不在白名单、`1005` 账号已过期 |
| `1100–1199` | 参数校验 | `1101` 必填缺失、`1102` 格式错误、`1103` 业务规则不满足（如 owner 为空） |
| `1200–1299` | 资源不存在/冲突 | `1201` 对象不存在、`1202` 唯一键冲突、`1203` **依赖成环**、`1204` 资源容量超限、`1205` 状态不允许该操作 |
| `1300–1399` | 导入导出 | `1301` 模板不匹配、`1302` 校验失败、`1303` 回滚令牌失效 |
| `1400–1499` | 集成 | `1401` LDAP 连接失败、`1402` 企微接口失败、`1403` AI 配额超限、`1404` AI 服务不可用（触发降级） |
| `1500–1599` | 系统 | `1501` 内部错误、`1502` 依赖服务不可用、`1503` 限流 |

**前端处理约定**：`1001/1002` 跳登录；`1003/1004` 提示无权限（不透露资源是否存在）；`1203` 展示环路路径；`1404` 静默降级不弹错；其余展示 `message` + 错误码。

### 附录 C　枚举字典（落 `dictionary` 表）

| category | code 取值 |
| --- | --- |
| `secrecy_level` | `public` / `internal` / `confidential` / `secret` |
| `project_status` | `draft`/`applying`/`active`/`suspended`/`closed`/`cancelled` |
| `task_status` | `not_started`/`in_progress`/`blocked`/`done`/`cancelled` |
| `gate_status` | `not_started`/`material_ready`/`in_review`/`passed`/`conditional`/`failed`/`waived` |
| `ticket_type` | `resource`/`support`/`decision` |
| `ticket_status` | `draft`/`pending`/`accepted`/`resolved`/`rejected`/`closed`/`escalated` |
| `risk_level` | `high`/`medium`/`low` |
| `issue_severity` | `p0`/`p1`/`p2`/`p3` |
| `dep_type` | `FS`/`SS`/`FF`/`SF` |
| `raci` | `R`/`A`/`C`/`I` |
| `batch_type` | `tapeout`/`package`/`substrate` |
| `milestone_kind` | 见附录 A11 |
| `health` | `red`/`yellow`/`green`/`na` |
| `holiday` | `YYYY-MM-DD` 列表（SLA 与 CPM 排除） |

### 附录 D　种子数据清单（演示与试点用）

| 数据 | 数量 | 说明 |
| --- | --- | --- |
| 部门树 | 8 个一级 / 30 个二级 | 脱敏虚构，含芯片 BU、系统硬件 BU |
| 用户 | 200 人 | 含 PM 15 人、主管 20 人、高管 5 人；**工号与姓名均虚构** |
| 技能标签 | 40 个 | 含 DFT、SI、FPGA、驱动、集群运维等 |
| 项目类型模板 | 10 类 | 附录 A 全量 |
| 项目 | 20 个（10 芯片设计 / 5 软件 / 3 硬件 / 2 NPI） | 其中 1 个含 5000 任务用于性能验收 |
| 任务 | 约 20000 条 | 含依赖与里程碑 |
| Program | 3 个 | 用于验证跨项目推演 |
| 工单 | 100 条 | 含各类状态与 SLA 场景 |

> **原型开发期（第 1–3 月）严禁导入真实组织架构与真实项目数据**（§5.2），全部使用本种子数据。

### 附录 E　术语表

| 术语 | 含义 |
| --- | --- |
| Gate | 阶段门禁评审；v2.0/v3.0 采用**承诺制**：未过不硬锁，持续告警并记账 |
| 承诺制 | 服务型 PMO 下的门禁策略：允许带缺口推进，但透明留痕 + 持续告警 + 进承诺台账 |
| Program | 项目集，围绕一颗芯片/一个客户的多个子项目集合 |
| Handoff | 交接物，跨子项目交付的工件，需双方签收闭环 |
| RACI | 任务级职责矩阵，**accountable owner 唯一**，用以消除推诿（D5） |
| 双源同步 | LDAP（账号状态）+ 企微（组织树）合并为用户主数据 |
| 数据域 | 自定义数据可见范围表达式，叠加在 RBAC 之上 |
| 密级 | 项目可见性分级，立项必填，变更双人审批 |
| CPM | 关键路径法，用于计算关键路径与浮动时间 |
| SLA | 工单响应/解决时限，超时自动升级 |
| 试点数据血缘 | `data_pedigree`：`trial`（待校准）/ `official`（Gate 复核后转正式） |

---

**文档结束。** 开发过程中如发现本文档与实现冲突，**先改实现，再提 PR 修订本文档**，不得两边各说各话。
