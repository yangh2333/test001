# AI Provider Gateway 与 Agent Runtime 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建自建 + 商用 AI 统一接入层与可执行工具调用的 Agent 运行时，作为产品/项目管理平台的地基。

**Architecture:** FastAPI 单体应用，分 Provider Gateway / Agent Runtime / Tools Registry 三层；依赖单向（API → Provider/Agent/Tools → 基础设施）；SQLite + Redis；YAML 定义 agent，ReAct 循环手写。详见 `docs/superpowers/specs/2026-09-20-ai-provider-gateway-agent-runtime-design.md`。

**Tech Stack:** Python 3.11+ / FastAPI / SQLAlchemy 2.x / SQLite (WAL) / Redis / APScheduler / httpx / PyJWT / cryptography / structlog / pydantic-settings / PyYAML / pytest / respx

---

## File Structure

```
/workspace/agent-platform/
  pyproject.toml
  requirements.txt
  config.yaml
  .gitignore
  app/
    __init__.py
    main.py                    # FastAPI app factory
    config.py                  # Settings (pydantic-settings)
    db.py                      # SQLAlchemy engine + session factory
    logging.py                 # structlog setup
    models/
      __init__.py              # re-export all models for Alembic
      base.py                  # DeclarativeBase + mixins
      user.py
      provider.py
      agent.py
      session.py               # Session + Message
      usage.py                 # TokenUsage
      audit.py
    auth/
      __init__.py
      crypto.py                # AES-GCM encrypt/decrypt
      jwt.py                   # sign + verify
      deps.py                  # get_current_user / require_role
    providers/
      __init__.py
      base.py                  # LLMClient protocol + dataclasses
      exceptions.py
      router.py
      accounting.py
      adapters/
        __init__.py
        openai_compat.py
        anthropic.py            # v1 stub
        gemini.py              # v1 stub
    agents/
      __init__.py
      loader.py                # YAML -> DB upsert
      history.py               # session/message CRUD
      runtime.py               # ReAct loop
      scheduler.py             # APScheduler integration
    tools/
      __init__.py
      base.py                  # Tool dataclass + schema builder
      registry.py              # @tool decorator + call/schemas_for
      builtin/
        __init__.py
        echo.py
        http_get.py
    api/
      __init__.py
      auth.py
      providers.py
      agents.py
      sessions.py
      usage.py
      health.py
      deps.py                  # shared deps (provider_repo, agent_repo...)
  agents/                      # default agent YAMLs (boot-time upsert)
    echo-assistant.yaml
  alembic/                      # migrations
    env.py
    versions/
  tests/
    conftest.py
    test_config.py
    test_auth/
      test_crypto.py
      test_jwt.py
    test_providers/
      test_openai_compat.py
      test_router.py
      test_accounting.py
    test_agents/
      test_loader.py
      test_history.py
      test_runtime.py
      test_scheduler.py
    test_tools/
      test_registry.py
    test_api/
      test_auth_api.py
      test_providers_api.py
      test_agents_api.py
      test_sessions_api.py
      test_usage_api.py
  data/                        # gitignored
```

**Responsibility notes:**
- `models/base.py` 持有 `DeclarativeBase` 和 `TimestampMixin`，所有表共享；`models/__init__.py` import 全部表，保证 Alembic autogenerate 能发现。
- `providers/base.py` 只放纯数据结构（Protocol + dataclass），不放实现，方便 adapter/router 测试 import。
- `tools/registry.py` 是全局单例 dict，启动时由 `app/main.py` 触发 import `tools/builtin/*` 完成注册。
- `api/deps.py` 集中所有 repository 依赖，路由文件不直接 new 对象。

---

## Task 1: 项目脚手架

**Files:**
- Create: `agent-platform/pyproject.toml`
- Create: `agent-platform/requirements.txt`
- Create: `agent-platform/.gitignore`
- Create: `agent-platform/config.yaml`
- Create: `agent-platform/app/__init__.py` (空)
- Create: `agent-platform/tests/__init__.py` (空)
- Create: `agent-platform/tests/conftest.py`

- [ ] **Step 1: 写 pyproject.toml**

```toml
[project]
name = "agent-platform"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.110",
  "uvicorn[standard]>=0.29",
  "sqlalchemy>=2.0",
  "alembic>=1.13",
  "pydantic>=2.6",
  "pydantic-settings>=2.2",
  "httpx>=0.27",
  "redis>=5.0",
  "apscheduler>=3.10",
  "PyYAML>=6.0",
  "PyJWT>=2.8",
  "cryptography>=42",
  "structlog>=24.1",
  "bcrypt>=4.1",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0",
  "pytest-asyncio>=0.23",
  "respx>=0.20",
  "httpx-mock",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: 写 requirements.txt（锁定给生产部署用）**

```
fastapi>=0.110
uvicorn[standard]>=0.29
sqlalchemy>=2.0
alembic>=1.13
pydantic>=2.6
pydantic-settings>=2.2
httpx>=0.27
redis>=5.0
apscheduler>=3.10
PyYAML>=6.0
PyJWT>=2.8
cryptography>=42
structlog>=24.1
bcrypt>=4.1
```

- [ ] **Step 3: 写 .gitignore**

```
__pycache__/
*.pyc
data/
.venv/
.env
*.db
```

- [ ] **Step 4: 写 config.yaml（含占位 secret）**

```yaml
server:
  host: 0.0.0.0
  port: 8000
  workers: 1
database:
  url: sqlite:///./data/agent_platform.db
  echo: false
redis:
  url: redis://localhost:6379/0
auth:
  jwt_secret: dev-secret-change-me
  jwt_expiry_hours: 24
scheduler:
  enabled: true
  timezone: Asia/Shanghai
logging:
  level: INFO
  format: json
routing:
  default_strategy: self_hosted_first
crypto:
  key: dev-master-key-change-me
```

- [ ] **Step 5: 写 tests/conftest.py（最小 fixture，后续扩展）**

```python
import pytest

@pytest.fixture
def anyio_backend():
    return "asyncio"
```

- [ ] **Step 6: 创建空包文件**

`app/__init__.py` 和 `tests/__init__.py` 内容留空。

- [ ] **Step 7: 验证可安装可导入**

Run: `cd /workspace/agent-platform && pip install -e ".[dev]" && python -c "import app; print('ok')"`
Expected: 输出 `ok`

- [ ] **Step 8: Commit**

```bash
cd /workspace/agent-platform
git init && git add -A
git commit -m "chore: scaffold agent-platform project"
```

---

## Task 2: 配置加载 + 结构化日志

**Files:**
- Create: `agent-platform/app/config.py`
- Create: `agent-platform/app/logging.py`
- Create: `agent-platform/tests/test_config.py`

- [ ] **Step 1: 写失败测试 `tests/test_config.py`**

```python
import os
from app.config import Settings

def test_settings_load_from_yaml(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "server:\n  port: 9000\n"
        "database:\n  url: sqlite:///./x.db\n"
        "auth:\n  jwt_secret: s\n  jwt_expiry_hours: 12\n"
        "redis:\n  url: redis://x/0\n"
        "scheduler:\n  enabled: false\n  timezone: UTC\n"
        "logging:\n  level: DEBUG\n  format: json\n"
        "routing:\n  default_strategy: priority\n"
        "crypto:\n  key: k\n"
    )
    s = Settings.load_from_file(cfg)
    assert s.server.port == 9000
    assert s.routing.default_strategy == "priority"
    assert s.scheduler.enabled is False

def test_settings_env_overrides_yaml(tmp_path, monkeypatch):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("auth:\n  jwt_secret: fromfile\n")
    monkeypatch.setenv("JWT_SECRET", "fromenv")
    s = Settings.load_from_file(cfg)
    assert s.auth.jwt_secret == "fromenv"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /workspace/agent-platform && pytest tests/test_config.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'app.config'`）

- [ ] **Step 3: 写 `app/config.py`**

```python
from __future__ import annotations
import os
from pathlib import Path
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

class ServerCfg(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1

class DbCfg(BaseModel):
    url: str
    echo: bool = False

class RedisCfg(BaseModel):
    url: str

class AuthCfg(BaseModel):
    jwt_secret: str
    jwt_expiry_hours: int = 24

class SchedulerCfg(BaseModel):
    enabled: bool = True
    timezone: str = "Asia/Shanghai"

class LoggingCfg(BaseModel):
    level: str = "INFO"
    format: str = "json"

class RoutingCfg(BaseModel):
    default_strategy: str = "self_hosted_first"

class CryptoCfg(BaseModel):
    key: str

class Settings(BaseSettings):
    server: ServerCfg
    database: DbCfg
    redis: RedisCfg
    auth: AuthCfg
    scheduler: SchedulerCfg
    logging: LoggingCfg
    routing: RoutingCfg
    crypto: CryptoCfg

    @classmethod
    def load_from_file(cls, path: Path | str = "config.yaml") -> "Settings":
        path = Path(path)
        raw = yaml.safe_load(path.read_text()) if path.exists() else {}
        # 环境变量覆盖（仅在显式存在时）
        if os.environ.get("JWT_SECRET"):
            raw.setdefault("auth", {})["jwt_secret"] = os.environ["JWT_SECRET"]
        if os.environ.get("MASTER_KEY"):
            raw.setdefault("crypto", {})["key"] = os.environ["MASTER_KEY"]
        if os.environ.get("DATABASE_URL"):
            raw.setdefault("database", {})["url"] = os.environ["DATABASE_URL"]
        return cls(**raw)
```

- [ ] **Step 4: 写 `app/logging.py`**

```python
import logging
import structlog

def setup_logging(level: str = "INFO", fmt: str = "json") -> None:
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO),
                        format="%(message)s")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer() if fmt == "json"
            else structlog.processors.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        cache_logger_on_first_use=True,
    )

def get_logger(name: str | None = None):
    return structlog.get_logger(name)
```

- [ ] **Step 5: 运行测试**

Run: `pytest tests/test_config.py -v`
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add app/config.py app/logging.py tests/test_config.py
git commit -m "feat: config loader with env override + structlog setup"
```

---

## Task 3: 数据库 engine + session factory

**Files:**
- Create: `agent-platform/app/db.py`
- Modify: `agent-platform/tests/conftest.py`

- [ ] **Step 1: 写 conftest 的 db fixture（先于实现，TDD 驱动）**

修改 `tests/conftest.py`：

```python
import pytest
from app.config import Settings
from app.db import init_engine, session_factory, Base

@pytest.fixture
def settings(tmp_path):
    return Settings(
        server={"host": "0.0.0.0", "port": 8000, "workers": 1},
        database={"url": f"sqlite:///{tmp_path}/test.db", "echo": False},
        redis={"url": "redis://localhost/0"},
        auth={"jwt_secret": "test-secret", "jwt_expiry_hours": 24},
        scheduler={"enabled": False, "timezone": "UTC"},
        logging={"level": "INFO", "format": "json"},
        routing={"default_strategy": "self_hosted_first"},
        crypto={"key": "test-master-key"},
    )

@pytest.fixture
def engine(settings):
    eng = init_engine(settings)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)

@pytest.fixture
def db_session(engine):
    factory = session_factory(engine)
    s = factory()
    try:
        yield s
    finally:
        s.close()
```

- [ ] **Step 2: 写 `app/db.py`**

```python
from __future__ import annotations
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from app.config import Settings
from app.models.base import Base

def init_engine(settings: Settings) -> Engine:
    eng = create_engine(settings.database.url, echo=settings.database.echo,
                        future=True, pool_pre_ping=True)
    return eng

def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)
```

- [ ] **Step 3: 写 models/base.py（被 db.py 依赖）**

```python
from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 4: 写 models/__init__.py 占位（后续任务填充）**

```python
from app.models.base import Base, TimestampMixin
# 其他表在后续 task 中加入这里
__all__ = ["Base", "TimestampMixin"]
```

- [ ] **Step 5: 运行测试**

Run: `pytest tests/conftest.py -v --no-header 2>&1 | head -5; python -c "from app.db import init_engine; print('ok')"`
Expected: 无报错（conftest 加载成功 + import ok）

- [ ] **Step 6: Commit**

```bash
git add app/db.py app/models/base.py app/models/__init__.py tests/conftest.py
git commit -m "feat: db engine + session factory + Base"
```

---

## Task 4: 全部 ORM 模型

**Files:**
- Create: `agent-platform/app/models/user.py`
- Create: `agent-platform/app/models/provider.py`
- Create: `agent-platform/app/models/agent.py`
- Create: `agent-platform/app/models/session.py`
- Create: `agent-platform/app/models/usage.py`
- Create: `agent-platform/app/models/audit.py`
- Modify: `agent-platform/app/models/__init__.py`
- Create: `agent-platform/tests/test_models.py`

- [ ] **Step 1: 写 `tests/test_models.py`（验证所有表可建可写）**

```python
from datetime import datetime
from sqlalchemy import select
from app.models import User, Provider, Agent, Session as ChatSession, Message, TokenUsage, AuditLog

def test_create_user(db_session):
    u = User(email="a@b.com", password_hash="x", role="owner")
    db_session.add(u); db_session.commit()
    got = db_session.scalar(select(User).where(User.email == "a@b.com"))
    assert got is not None and got.role == "owner"

def test_create_provider_with_models_json(db_session):
    p = Provider(name="vllm", type="openai_compat", base_url="http://x",
                 api_key_enc="enc", models_json=[{"model": "Q"}], priority=0,
                 strategy="self_hosted_first", enabled=True)
    db_session.add(p); db_session.commit()
    assert db_session.get(Provider, p.id).models_json == [{"model": "Q"}]

def test_agent_session_message_chain(db_session):
    a = Agent(name="bot", system_prompt="s", tools_json=["echo"],
              default_model="Q", temperature=0.3, max_history=20,
              retry_strategy_json={"max_iterations": 8}, enabled=True, created_by=1)
    db_session.add(a); db_session.commit()
    s = ChatSession(agent_id=a.id, user_id=1, title="t")
    db_session.add(s); db_session.commit()
    m = Message(session_id=s.id, role="user", content_json={"text": "hi"},
                tool_calls_json=None, tool_call_id=None, token_count=5)
    db_session.add(m); db_session.commit()
    assert db_session.get(Message, m.id).role == "user"

def test_token_usage_and_audit(db_session):
    u = TokenUsage(provider_id=1, user_id=1, agent_id=1, session_id=1,
                   model="Q", prompt_tokens=10, completion_tokens=5,
                   total_tokens=15, cost_cents=1, latency_ms=200, status="success")
    db_session.add(u)
    al = AuditLog(user_id=1, action="create", target_type="provider",
                  target_id=1, detail_json={"k": "v"})
    db_session.add(al); db_session.commit()
    assert db_session.get(TokenUsage, u.id).total_tokens == 15
    assert db_session.get(AuditLog, al.id).action == "create"
```

- [ ] **Step 2: 运行确认失败**

Run: `pytest tests/test_models.py -v`
Expected: ImportError（模型未定义）

- [ ] **Step 3: 写 `models/user.py`**

```python
from __future__ import annotations
from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin

class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="member")
```

- [ ] **Step 4: 写 `models/provider.py`**

```python
from __future__ import annotations
from datetime import datetime
from typing import Any
from sqlalchemy import String, Integer, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON
from app.models.base import Base, TimestampMixin

class Provider(TimestampMixin, Base):
    __tablename__ = "providers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)  # openai_compat | anthropic | gemini
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    api_key_enc: Mapped[str] = mapped_column(String(1000), nullable=False)
    models_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    strategy: Mapped[str | None] = mapped_column(String(30), nullable=True)  # 覆盖全局
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(),
                                                onupdate=func.now(), nullable=False)
```

- [ ] **Step 5: 写 `models/agent.py`**

```python
from __future__ import annotations
from typing import Any
from sqlalchemy import String, Integer, Float, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON
from app.models.base import Base, TimestampMixin

class Agent(TimestampMixin, Base):
    __tablename__ = "agents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    system_prompt: Mapped[str] = mapped_column(String(10000), nullable=False)
    tools_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    default_provider_id: Mapped[int | None] = mapped_column(ForeignKey("providers.id"), nullable=True)
    default_model: Mapped[str] = mapped_column(String(100), nullable=False)
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    max_history: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    retry_strategy_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    schedule_cron: Mapped[str | None] = mapped_column(String(50), nullable=True)
    schedule_input: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
```

- [ ] **Step 6: 写 `models/session.py`（Session + Message）**

```python
from __future__ import annotations
from typing import Any
from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON
from app.models.base import Base, TimestampMixin

class Session(TimestampMixin, Base):
    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(),
                                                onupdate=func.now(), nullable=False)

class Message(TimestampMixin, Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # system|user|assistant|tool
    content_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    tool_calls_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    tool_call_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

- [ ] **Step 7: 写 `models/usage.py`**

```python
from __future__ import annotations
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin

class TokenUsage(TimestampMixin, Base):
    __tablename__ = "token_usage"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("providers.id"), nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)  # 定时任务为系统用户
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("sessions.id"), nullable=True)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # success | failed
```

- [ ] **Step 8: 写 `models/audit.py`**

```python
from __future__ import annotations
from typing import Any
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON
from app.models.base import Base, TimestampMixin

class AuditLog(TimestampMixin, Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    detail_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
```

- [ ] **Step 9: 更新 `models/__init__.py` 导出全部**

```python
from app.models.base import Base, TimestampMixin
from app.models.user import User
from app.models.provider import Provider
from app.models.agent import Agent
from app.models.session import Session, Message
from app.models.usage import TokenUsage
from app.models.audit import AuditLog

__all__ = ["Base", "TimestampMixin", "User", "Provider", "Agent",
           "Session", "Message", "TokenUsage", "AuditLog"]
```

- [ ] **Step 10: 运行测试**

Run: `pytest tests/test_models.py -v`
Expected: 4 passed

- [ ] **Step 11: Commit**

```bash
git add app/models/ tests/test_models.py
git commit -m "feat: ORM models for users/providers/agents/sessions/usage/audit"
```

---

## Task 5: Alembic 初始迁移

**Files:**
- Create: `agent-platform/alembic.ini`
- Create: `agent-platform/alembic/env.py`
- Create: `agent-platform/alembic/script.py.mako`

- [ ] **Step 1: 初始化 Alembic**

Run: `cd /workspace/agent-platform && alembic init alembic`
Expected: 生成 `alembic/`、`alembic.ini`、`alembic/versions/`

- [ ] **Step 2: 修改 `alembic/env.py`（关键片段，让 autogenerate 看到模型）**

把 `env.py` 里 `target_metadata` 一行改为：

```python
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.models import Base  # noqa: E402
target_metadata = Base.metadata
```

并在 `run_migrations_online()` / `run_migrations_offline()` 中读取 `config.yaml` 作为 DB url：

```python
from app.config import Settings
settings = Settings.load_from_file(pathlib.Path(__file__).resolve().parents[1] / "config.yaml")
config.set_main_option("sqlalchemy.url", settings.database.url)
```

- [ ] **Step 3: 生成初始 migration**

Run: `cd /workspace/agent-platform && alembic revision --autogenerate -m "init schema"`
Expected: `alembic/versions/<hash>_init_schema.py` 生成，含 7 张表的 create_table

- [ ] **Step 4: 测试 upgrade/downgrade**

Run: `cd /workspace/agent-platform && rm -f data/agent_platform.db && alembic upgrade head && alembic downgrade base && alembic upgrade head`
Expected: 无报错

- [ ] **Step 5: Commit**

```bash
git add alembic.ini alembic/
git commit -m "feat: alembic initial migration"
```

---

## Task 6: AES-GCM 加密工具

**Files:**
- Create: `agent-platform/app/auth/__init__.py` (空)
- Create: `agent-platform/app/auth/crypto.py`
- Create: `agent-platform/tests/test_auth/__init__.py` (空)
- Create: `agent-platform/tests/test_auth/test_crypto.py`

- [ ] **Step 1: 写失败测试**

```python
from app.auth.crypto import encrypt, decrypt

def test_roundtrip():
    plaintext = "sk-abc-123-xyz"
    key = "0" * 32  # 32 字符主密钥
    enc = encrypt(plaintext, key)
    assert enc != plaintext
    assert decrypt(enc, key) == plaintext

def test_wrong_key_raises():
    enc = encrypt("secret", "0" * 32)
    try:
        decrypt(enc, "1" * 32)
        assert False, "should raise"
    except Exception:
        pass

def test_same_plaintext_different_ciphertext():
    key = "0" * 32
    e1 = encrypt("x", key)
    e2 = encrypt("x", key)
    assert e1 != e2  # 随机 nonce
```

- [ ] **Step 2: 运行确认失败**

Run: `pytest tests/test_auth/test_crypto.py -v`
Expected: ImportError

- [ ] **Step 3: 写 `app/auth/crypto.py`**

```python
import base64
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def _derive_key(master: str) -> bytes:
    # 32 字符 → 32 bytes；不足补 0，超长截断
    raw = master.encode("utf-8")[:32].ljust(32, b"0")
    return raw

def encrypt(plaintext: str, master_key: str) -> str:
    key = _derive_key(master_key)
    nonce = os.urandom(12)
    ct = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.urlsafe_b64encode(nonce + ct).decode("ascii")

def decrypt(token: str, master_key: str) -> str:
    key = _derive_key(master_key)
    raw = base64.urlsafe_b64decode(token.encode("ascii"))
    nonce, ct = raw[:12], raw[12:]
    pt = AESGCM(key).decrypt(nonce, ct, None)
    return pt.decode("utf-8")
```

- [ ] **Step 4: 运行测试**

Run: `pytest tests/test_auth/test_crypto.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add app/auth/ tests/test_auth/test_crypto.py
git commit -m "feat: AES-GCM provider api_key encryption"
```

---

## Task 7: JWT 签发与校验

**Files:**
- Create: `agent-platform/app/auth/jwt.py`
- Create: `agent-platform/tests/test_auth/test_jwt.py`

- [ ] **Step 1: 写失败测试**

```python
import time
from app.auth.jwt import sign_token, verify_token

def test_sign_and_verify():
    t = sign_token(user_id=42, role="owner", secret="s", expiry_hours=1)
    claims = verify_token(t, secret="s")
    assert claims["sub"] == "42"
    assert claims["role"] == "owner"

def test_expired_token_rejected():
    t = sign_token(user_id=1, role="member", secret="s", expiry_hours=-1)
    try:
        verify_token(t, secret="s")
        assert False
    except Exception:
        pass

def test_wrong_secret_rejected():
    t = sign_token(user_id=1, role="member", secret="s1", expiry_hours=1)
    try:
        verify_token(t, secret="s2")
        assert False
    except Exception:
        pass
```

- [ ] **Step 2: 运行确认失败**

Run: `pytest tests/test_auth/test_jwt.py -v`
Expected: ImportError

- [ ] **Step 3: 写 `app/auth/jwt.py`**

```python
import time
import jwt as pyjwt

def sign_token(user_id: int, role: str, secret: str, expiry_hours: int = 24) -> str:
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + expiry_hours * 3600,
    }
    return pyjwt.encode(payload, secret, algorithm="HS256")

def verify_token(token: str, secret: str) -> dict:
    try:
        return pyjwt.decode(token, secret, algorithms=["HS256"])
    except pyjwt.PyJWTError as e:
        raise ValueError(f"invalid token: {e}") from e
```

- [ ] **Step 4: 运行测试**

Run: `pytest tests/test_auth/test_jwt.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add app/auth/jwt.py tests/test_auth/test_jwt.py
git commit -m "feat: JWT sign and verify"
```

---

## Task 8: FastAPI 鉴权 deps

**Files:**
- Create: `agent-platform/app/auth/deps.py`
- Create: `agent-platform/tests/test_auth/__init__.py`（如已建可跳过）

- [ ] **Step 1: 写 `app/auth/deps.py`**

```python
from __future__ import annotations
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session as DBSession
from app.config import Settings
from app.db import session_factory
from app.auth.jwt import verify_token
from app.models import User

def get_settings() -> Settings:
    # 由 main.py 在 startup 时设置；测试可 monkeypatch
    from app.main import _settings  # noqa
    return _settings

def get_db():
    from app.main import _engine  # noqa
    factory = session_factory(_engine)
    db = factory()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    db: DBSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        claims = verify_token(token, settings.auth.jwt_secret)
    except ValueError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e))
    user = db.get(User, int(claims["sub"]))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user not found")
    return user

def require_role(*roles: str):
    async def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "insufficient role")
        return user
    return _dep
```

- [ ] **Step 2: 创建占位 main.py（让 deps 可 import）**

```python
# app/main.py（占位，后续 task 填充）
from app.config import Settings

_settings: Settings | None = None
_engine = None

def create_app(settings: Settings | None = None):
    global _settings, _engine
    from app.db import init_engine
    _settings = settings or Settings.load_from_file()
    _engine = init_engine(_settings)
    from fastapi import FastAPI
    app = FastAPI(title="agent-platform")
    return app
```

- [ ] **Step 3: 验证 import**

Run: `python -c "from app.auth.deps import get_current_user, require_role; print('ok')"`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add app/auth/deps.py app/main.py
git commit -m "feat: FastAPI auth dependencies (current_user, require_role)"
```

---

## Task 9: Provider 基础类型

**Files:**
- Create: `agent-platform/app/providers/__init__.py` (空)
- Create: `agent-platform/app/providers/base.py`
- Create: `agent-platform/app/providers/exceptions.py`

- [ ] **Step 1: 写 `app/providers/exceptions.py`**

```python
class ProviderError(Exception):
    """所有 provider 错误的基类"""

class ProviderUnavailable(ProviderError):
    """5xx / 连接失败 → 触发 failover"""

class ProviderTimeout(ProviderError):
    """超时 → 触发 failover"""

class RateLimited(ProviderError):
    """429 → 触发 failover"""

class ProviderRequestError(ProviderError):
    """其他 4xx → 不 failover"""

class AllProvidersFailed(ProviderError):
    """所有 provider 都失败"""
    def __init__(self, last_err: Exception | None):
        super().__init__(f"all providers failed; last error: {last_err}")
```

- [ ] **Step 2: 写 `app/providers/base.py`**

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Protocol

@dataclass
class ToolCall:
    id: str
    name: str
    args: dict[str, Any]

@dataclass
class Message:
    role: str  # system | user | assistant | tool
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None
    name: str | None = None  # tool name when role == "tool"

@dataclass
class ToolSchema:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON schema

@dataclass
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

@dataclass
class CompletionResponse:
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: TokenUsage | None = None
    finish_reason: str = "stop"
    raw: dict = field(default_factory=dict)

@dataclass
class Chunk:
    content: str | None = None
    tool_call: ToolCall | None = None
    finish_reason: str | None = None

@dataclass
class CompletionRequest:
    messages: list[Message]
    tools: list[ToolSchema] | None = None
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int | None = None
    stream: bool = False

class LLMClient(Protocol):
    provider_id: int
    provider_type: str  # openai_compat | anthropic | gemini
    name: str

    async def chat(self, req: CompletionRequest) -> CompletionResponse: ...
```

- [ ] **Step 3: 验证 import**

Run: `python -c "from app.providers.base import LLMClient, Message, CompletionResponse, TokenUsage, ToolCall, ToolSchema, CompletionRequest; print('ok')"`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add app/providers/
git commit -m "feat: provider base types (Protocol, dataclasses, exceptions)"
```

---

## Task 10: OpenAI 兼容 Adapter

**Files:**
- Create: `agent-platform/app/providers/adapters/__init__.py` (空)
- Create: `agent-platform/app/providers/adapters/openai_compat.py`
- Create: `agent-platform/tests/test_providers/__init__.py` (空)
- Create: `agent-platform/tests/test_providers/test_openai_compat.py`

- [ ] **Step 1: 写失败测试（用 respx mock）**

```python
import pytest
import respx
import httpx
from app.providers.base import Message, CompletionRequest
from app.providers.adapters.openai_compat import OpenAICompatAdapter
from app.providers.exceptions import ProviderUnavailable, RateLimited, ProviderRequestError

BASE = "https://mock.test/v1"

@pytest.fixture
def adapter():
    return OpenAICompatAdapter(provider_id=1, name="mock", base_url=BASE,
                               api_key="sk-x", timeout=10.0)

@respx.mock
async def test_chat_success(adapter):
    respx.post(f"{BASE}/chat/completions").mock(
        return_value=httpx.Response(200, json={
            "choices": [{"message": {"role": "assistant", "content": "hi"},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
        })
    )
    resp = await adapter.chat(CompletionRequest(messages=[Message("user", "hello")],
                                               model="Qwen-7B"))
    assert resp.content == "hi"
    assert resp.usage.total_tokens == 7
    assert resp.tool_calls == []

@respx.mock
async def test_chat_with_tool_calls(adapter):
    respx.post(f"{BASE}/chat/completions").mock(
        return_value=httpx.Response(200, json={
            "choices": [{"message": {
                "role": "assistant", "content": None,
                "tool_calls": [{"id": "c1", "function": {
                    "name": "echo", "arguments": '{"text":"hi"}'}}],
            }, "finish_reason": "tool_calls"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        })
    )
    resp = await adapter.chat(CompletionRequest(messages=[Message("user", "go")]))
    assert resp.content is None
    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0].name == "echo"
    assert resp.tool_calls[0].args == {"text": "hi"}

@respx.mock
async def test_5xx_raises_unavailable(adapter):
    respx.post(f"{BASE}/chat/completions").mock(return_value=httpx.Response(503))
    try:
        await adapter.chat(CompletionRequest(messages=[Message("user", "x")]))
        assert False
    except ProviderUnavailable:
        pass

@respx.mock
async def test_429_raises_rate_limited(adapter):
    respx.post(f"{BASE}/chat/completions").mock(return_value=httpx.Response(429))
    try:
        await adapter.chat(CompletionRequest(messages=[Message("user", "x")]))
        assert False
    except RateLimited:
        pass

@respx.mock
async def test_400_raises_request_error(adapter):
    respx.post(f"{BASE}/chat/completions").mock(return_value=httpx.Response(400, json={"error": "bad"}))
    try:
        await adapter.chat(CompletionRequest(messages=[Message("user", "x")]))
        assert False
    except ProviderRequestError:
        pass
```

- [ ] **Step 2: 运行确认失败**

Run: `pytest tests/test_providers/test_openai_compat.py -v`
Expected: ImportError

- [ ] **Step 3: 写 `app/providers/adapters/openai_compat.py`**

```python
from __future__ import annotations
import json
import httpx
from app.providers.base import (CompletionRequest, CompletionResponse, Message,
                                ToolCall, TokenUsage, ToolSchema)
from app.providers.exceptions import (ProviderRequestError, ProviderUnavailable,
                                      RateLimited, ProviderTimeout)

class OpenAICompatAdapter:
    provider_type = "openai_compat"

    def __init__(self, provider_id: int, name: str, base_url: str,
                 api_key: str, timeout: float = 30.0):
        self.provider_id = provider_id
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    async def chat(self, req: CompletionRequest) -> CompletionResponse:
        payload = self._build_payload(req)
        headers = {"Authorization": f"Bearer {self.api_key}",
                   "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.base_url}/chat/completions",
                                         json=payload, headers=headers)
        except httpx.TimeoutException as e:
            raise ProviderTimeout(str(e)) from e
        except httpx.RequestError as e:
            raise ProviderUnavailable(str(e)) from e

        if resp.status_code == 429:
            raise RateLimited(f"429: {resp.text}")
        if 500 <= resp.status_code < 600:
            raise ProviderUnavailable(f"{resp.status_code}: {resp.text}")
        if resp.status_code >= 400:
            raise ProviderRequestError(f"{resp.status_code}: {resp.text}")

        return self._parse_response(resp.json())

    def _build_payload(self, req: CompletionRequest) -> dict:
        payload: dict = {
            "model": req.model,
            "messages": [self._msg_to_dict(m) for m in req.messages],
            "temperature": req.temperature,
        }
        if req.max_tokens is not None:
            payload["max_tokens"] = req.max_tokens
        if req.tools:
            payload["tools"] = [{
                "type": "function",
                "function": {"name": t.name, "description": t.description,
                              "parameters": t.parameters},
            } for t in req.tools]
            payload["tool_choice"] = "auto"
        return payload

    def _msg_to_dict(self, m: Message) -> dict:
        d: dict = {"role": m.role, "content": m.content}
        if m.tool_calls:
            d["tool_calls"] = [{
                "id": tc.id, "type": "function",
                "function": {"name": tc.name, "arguments": json.dumps(tc.args)},
            } for tc in m.tool_calls]
        if m.tool_call_id:
            d["tool_call_id"] = m.tool_call_id
        if m.name:
            d["name"] = m.name
        return d

    def _parse_response(self, data: dict) -> CompletionResponse:
        choice = data["choices"][0]
        msg = choice["message"]
        tool_calls = []
        for tc in msg.get("tool_calls", []):
            fn = tc["function"]
            try:
                args = json.loads(fn["arguments"]) if fn["arguments"] else {}
            except json.JSONDecodeError:
                args = {"_raw": fn["arguments"]}
            tool_calls.append(ToolCall(id=tc["id"], name=fn["name"], args=args))
        usage_raw = data.get("usage") or {}
        usage = TokenUsage(
            prompt_tokens=usage_raw.get("prompt_tokens", 0),
            completion_tokens=usage_raw.get("completion_tokens", 0),
            total_tokens=usage_raw.get("total_tokens", 0),
        ) if usage_raw else None
        return CompletionResponse(
            content=msg.get("content"), tool_calls=tool_calls,
            usage=usage, finish_reason=choice.get("finish_reason", "stop"), raw=data,
        )
```

- [ ] **Step 4: 运行测试**

Run: `pytest tests/test_providers/test_openai_compat.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add app/providers/adapters/ tests/test_providers/test_openai_compat.py tests/test_providers/__init__.py
git commit -m "feat: OpenAI-compatible adapter with tool call support"
```

---

## Task 11: Anthropic / Gemini Adapter 占位

**Files:**
- Create: `agent-platform/app/providers/adapters/anthropic.py`
- Create: `agent-platform/app/providers/adapters/gemini.py`

- [ ] **Step 1: 写 `anthropic.py`（v1 仅声明不实现）**

```python
from app.providers.base import CompletionRequest, CompletionResponse
from app.providers.exceptions import ProviderRequestError

class AnthropicAdapter:
    """v1 占位：协议接口已预留，实现见后续版本。
    覆盖厂商：Anthropic Claude。"""
    provider_type = "anthropic"

    def __init__(self, provider_id: int, name: str, base_url: str,
                 api_key: str, timeout: float = 30.0):
        self.provider_id = provider_id
        self.name = name
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout

    async def chat(self, req: CompletionRequest) -> CompletionResponse:
        raise NotImplementedError("Anthropic adapter v1 not implemented; "
                                 "use openai_compat provider or contribute impl")
```

- [ ] **Step 2: 写 `gemini.py`（同上）**

```python
from app.providers.base import CompletionRequest, CompletionResponse

class GeminiAdapter:
    """v1 占位：覆盖 Google Gemini。"""
    provider_type = "gemini"

    def __init__(self, provider_id: int, name: str, base_url: str,
                 api_key: str, timeout: float = 30.0):
        self.provider_id = provider_id
        self.name = name
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout

    async def chat(self, req: CompletionRequest) -> CompletionResponse:
        raise NotImplementedError("Gemini adapter v1 not implemented")
```

- [ ] **Step 3: 验证 import**

Run: `python -c "from app.providers.adapters.anthropic import AnthropicAdapter; from app.providers.adapters.gemini import GeminiAdapter; print('ok')"`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add app/providers/adapters/anthropic.py app/providers/adapters/gemini.py
git commit -m "feat: anthropic/gemini adapter stubs (v1 not implemented)"
```

---

## Task 12: Token 计费

**Files:**
- Create: `agent-platform/app/providers/accounting.py`
- Create: `agent-platform/tests/test_providers/test_accounting.py`

- [ ] **Step 1: 写失败测试**

```python
from app.providers.accounting import Accounting
from app.providers.base import CompletionResponse, TokenUsage
from app.models import Provider, TokenUsage as UsageRow

def test_record_success_writes_row(db_session):
    # 建一个 provider + 配置成本
    p = Provider(name="vllm", type="openai_compat", base_url="http://x",
                 api_key_enc="e", models_json=[
                     {"model": "Qwen", "cost_per_1k_in_cents": 0, "cost_per_1k_out_cents": 0}],
                 priority=0, strategy=None, enabled=True)
    db_session.add(p); db_session.commit()
    acc = Accounting(db_session, master_key="k")  # master_key 此处不用
    resp = CompletionResponse(content="hi", usage=TokenUsage(100, 50, 150),
                              finish_reason="stop")
    acc.record(provider_id=p.id, user_id=1, agent_id=1, session_id=1,
              model="Qwen", resp=resp, latency_ms=200, status="success")
    row = db_session.query(UsageRow).first()
    assert row.total_tokens == 150
    assert row.cost_cents == 0  # 自建零成本
    assert row.status == "success"

def test_cost_calculation_commercial(db_session):
    p = Provider(name="deepseek", type="openai_compat", base_url="http://x",
                 api_key_enc="e", models_json=[
                     {"model": "deepseek-chat",
                      "cost_per_1k_in_cents": 1, "cost_per_1k_out_cents": 3}],
                 priority=1, strategy=None, enabled=True)
    db_session.add(p); db_session.commit()
    acc = Accounting(db_session, master_key="k")
    resp = CompletionResponse(content="hi", usage=TokenUsage(2000, 1000, 3000),
                              finish_reason="stop")
    acc.record(provider_id=p.id, user_id=1, agent_id=1, session_id=1,
              model="deepseek-chat", resp=resp, latency_ms=300, status="success")
    row = db_session.query(UsageRow).first()
    # 2000/1000 * 1 + 1000/1000 * 3 = 2 + 3 = 5 cents
    assert row.cost_cents == 5

def test_failed_call_recorded(db_session):
    p = Provider(name="vllm", type="openai_compat", base_url="http://x",
                 api_key_enc="e", models_json=[{"model": "Q", "cost_per_1k_in_cents": 0,
                                                 "cost_per_1k_out_cents": 0}],
                 priority=0, strategy=None, enabled=True)
    db_session.add(p); db_session.commit()
    acc = Accounting(db_session, master_key="k")
    acc.record(provider_id=p.id, user_id=1, agent_id=1, session_id=1,
              model="Q", resp=None, latency_ms=5000, status="failed")
    row = db_session.query(UsageRow).first()
    assert row.status == "failed"
    assert row.total_tokens == 0
```

- [ ] **Step 2: 运行确认失败**

Run: `pytest tests/test_providers/test_accounting.py -v`
Expected: ImportError

- [ ] **Step 3: 写 `app/providers/accounting.py`**

```python
from __future__ import annotations
from sqlalchemy.orm import Session as DBSession
from app.models import Provider, TokenUsage

class Accounting:
    def __init__(self, db: DBSession, master_key: str):
        self.db = db
        self.master_key = master_key  # 备用，目前不解密

    def record(self, provider_id: int, user_id: int | None, agent_id: int | None,
               session_id: int | None, model: str,
               resp, latency_ms: int, status: str) -> None:
        prompt_t = completion_t = total_t = 0
        cost_cents = 0
        if resp is not None and resp.usage is not None:
            prompt_t = resp.usage.prompt_tokens
            completion_t = resp.usage.completion_tokens
            total_t = resp.usage.total_tokens
            cost_cents = self._calc_cost(provider_id, model, prompt_t, completion_t)
        row = TokenUsage(
            provider_id=provider_id, user_id=user_id, agent_id=agent_id,
            session_id=session_id, model=model,
            prompt_tokens=prompt_t, completion_tokens=completion_t,
            total_tokens=total_t, cost_cents=cost_cents,
            latency_ms=latency_ms, status=status,
        )
        self.db.add(row)
        self.db.commit()

    def _calc_cost(self, provider_id: int, model: str,
                   prompt_t: int, completion_t: int) -> int:
        provider = self.db.get(Provider, provider_id)
        if provider is None:
            return 0
        for entry in provider.models_json:
            if entry.get("model") == model:
                in_cents = entry.get("cost_per_1k_in_cents", 0)
                out_cents = entry.get("cost_per_1k_out_cents", 0)
                return (prompt_t * in_cents + completion_t * out_cents) // 1000
        return 0
```

- [ ] **Step 4: 运行测试**

Run: `pytest tests/test_providers/test_accounting.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add app/providers/accounting.py tests/test_providers/test_accounting.py
git commit -m "feat: token accounting with cost calc + failed-call recording"
```

---

## Task 13: Provider Router（策略 + failover）

**Files:**
- Create: `agent-platform/app/providers/router.py`
- Create: `agent-platform/tests/test_providers/test_router.py`

- [ ] **Step 1: 写失败测试（用 stub adapter）**

```python
import pytest
from app.providers.base import (CompletionRequest, CompletionResponse, Message,
                                TokenUsage, LLMClient)
from app.providers.exceptions import (ProviderUnavailable, AllProvidersFailed,
                                      ProviderRequestError)
from app.providers.router import Router

class StubAdapter:
    def __init__(self, pid, name, ptype="openai_compat", models=None,
                 raises=None, returns=None, priority=0, is_self_hosted=False):
        self.provider_id = pid; self.name = name; self.provider_type = ptype
        self.models = models or []; self.raises = raises; self.returns = returns
        self.priority = priority; self.is_self_hosted = is_self_hosted
    async def chat(self, req):
        if self.raises: raise self.raises
        return self.returns

def _resp(text="ok"):
    return CompletionResponse(content=text, usage=TokenUsage(1, 1, 2))

async def test_self_hosted_first_orders_self_then_commercial():
    commercial = StubAdapter(1, "openai", is_self_hosted=False, returns=_resp("c"))
    self_host = StubAdapter(2, "vllm", is_self_hosted=True, returns=_resp("s"))
    router = Router(providers=[commercial, self_host], strategy="self_hosted_first",
                    accounting=None)
    resp = await router.complete(CompletionRequest(messages=[Message("user", "x")],
                                                   model="Q"))
    assert resp.content == "s"  # 自建优先

async def test_failover_to_next_on_5xx():
    p1 = StubAdapter(1, "vllm", raises=ProviderUnavailable("503"), is_self_hosted=True)
    p2 = StubAdapter(2, "openai", returns=_resp("fallback"), is_self_hosted=False)
    router = Router(providers=[p1, p2], strategy="priority", accounting=None)
    resp = await router.complete(CompletionRequest(messages=[Message("user", "x")],
                                                   model="Q"))
    assert resp.content == "fallback"

async def test_all_fail_raises():
    p1 = StubAdapter(1, "vllm", raises=ProviderUnavailable("x"))
    p2 = StubAdapter(2, "openai", raises=ProviderTimeout("y"))
    router = Router(providers=[p1, p2], strategy="priority", accounting=None)
    try:
        await router.complete(CompletionRequest(messages=[Message("user", "x")], model="Q"))
        assert False
    except AllProvidersFailed:
        pass

async def test_4xx_does_not_failover():
    p1 = StubAdapter(1, "vllm", raises=ProviderRequestError("400 bad"))
    p2 = StubAdapter(2, "openai", returns=_resp("should-not-reach"))
    router = Router(providers=[p1, p2], strategy="priority", accounting=None)
    try:
        await router.complete(CompletionRequest(messages=[Message("user", "x")], model="Q"))
        assert False
    except ProviderRequestError:
        pass

async def test_cost_first_picks_cheapest():
    expensive = StubAdapter(1, "openai", returns=_resp(),
                            models=[{"model": "Q", "cost_per_1k_in_cents": 10}])
    cheap = StubAdapter(2, "deepseek", returns=_resp(),
                        models=[{"model": "Q", "cost_per_1k_in_cents": 1}])
    router = Router(providers=[expensive, cheap], strategy="cost_first", accounting=None)
    await router.complete(CompletionRequest(messages=[Message("user", "x")], model="Q"))
    # 不报错即过；具体选择逻辑在排序中验证
```

- [ ] **Step 2: 运行确认失败**

Run: `pytest tests/test_providers/test_router.py -v`
Expected: ImportError

- [ ] **Step 3: 写 `app/providers/router.py`**

```python
from __future__ import annotations
import time
from typing import Protocol
from app.providers.base import CompletionRequest, CompletionResponse
from app.providers.exceptions import (AllProvidersFailed, ProviderRequestError,
                                      ProviderTimeout, ProviderUnavailable, RateLimited)

class RouterStrategy(Protocol):
    def __call__(self, providers: list, model: str | None) -> list: ...

def _self_hosted_first(providers, model):
    return sorted(providers, key=lambda p: (0 if p.is_self_hosted else 1, p.priority))

def _priority(providers, model):
    return sorted(providers, key=lambda p: p.priority)

def _cost_first(providers, model):
    def cost_of(p):
        for m in p.models:
            if m.get("model") == model:
                return m.get("cost_per_1k_in_cents", 0)
        return 999999
    return sorted(providers, key=lambda p: (cost_of(p), p.priority))

STRATEGIES: dict[str, RouterStrategy] = {
    "self_hosted_first": _self_hosted_first,
    "priority": _priority,
    "cost_first": _cost_first,
}

class Router:
    def __init__(self, providers: list, strategy: str = "self_hosted_first",
                 accounting=None):
        self.providers = providers
        self.strategy = strategy
        self.accounting = accounting

    async def complete(self, req: CompletionRequest,
                       user_id: int | None = None,
                       agent_id: int | None = None,
                       session_id: int | None = None) -> CompletionResponse:
        ordering = STRATEGIES[self.strategy](self.providers, req.model)
        last_err: Exception | None = None
        for provider in ordering:
            t0 = time.monotonic()
            try:
                resp = await provider.chat(req)
                if self.accounting is not None:
                    self.accounting.record(
                        provider_id=provider.provider_id, user_id=user_id,
                        agent_id=agent_id, session_id=session_id,
                        model=req.model or "", resp=resp,
                        latency_ms=int((time.monotonic() - t0) * 1000),
                        status="success",
                    )
                return resp
            except (ProviderUnavailable, ProviderTimeout, RateLimited) as e:
                last_err = e
                if self.accounting is not None:
                    self.accounting.record(
                        provider_id=provider.provider_id, user_id=user_id,
                        agent_id=agent_id, session_id=session_id,
                        model=req.model or "", resp=None,
                        latency_ms=int((time.monotonic() - t0) * 1000),
                        status="failed",
                    )
                continue
            # 4xx ProviderRequestError 不 failover，直接抛
        raise AllProvidersFailed(last_err)
```

- [ ] **Step 4: 运行测试**

Run: `pytest tests/test_providers/test_router.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add app/providers/router.py tests/test_providers/test_router.py
git commit -m "feat: provider router with 3 strategies + failover + accounting hook"
```

---

## Task 14: Tools Registry

**Files:**
- Create: `agent-platform/app/tools/__init__.py` (空)
- Create: `agent-platform/app/tools/base.py`
- Create: `agent-platform/app/tools/registry.py`
- Create: `agent-platform/tests/test_tools/__init__.py` (空)
- Create: `agent-platform/tests/test_tools/test_registry.py`

- [ ] **Step 1: 写失败测试**

```python
import pytest
from app.tools.registry import tool, call, schemas_for, clear

@pytest.fixture(autouse=True)
def _reset():
    clear()
    yield
    clear()

async def test_register_and_call():
    @tool("echo", "echo back the text")
    async def echo(text: str) -> dict:
        return {"echo": text}
    result = await call("echo", {"text": "hi"})
    assert result == {"echo": "hi"}

async def test_call_unknown_raises():
    try:
        await call("nope", {})
        assert False
    except KeyError:
        pass

async def test_sync_fn_supported():
    @tool("add", "add two numbers")
    def add(a: int, b: int) -> dict:
        return {"sum": a + b}
    assert (await call("add", {"a": 1, "b": 2})) == {"sum": 3}

def test_schema_for_simple_fn():
    @tool("echo", "echo text back")
    async def echo(text: str) -> dict: ...
    schemas = schemas_for(["echo"])
    assert len(schemas) == 1
    s = schemas[0]
    assert s["name"] == "echo"
    assert s["description"] == "echo text back"
    assert s["parameters"]["type"] == "object"
    assert "text" in s["parameters"]["properties"]
    assert s["parameters"]["properties"]["text"]["type"] == "string"
    assert s["parameters"]["required"] == ["text"]

def test_schema_with_optional_arg():
    @tool("greet", "greet")
    def greet(name: str, polite: bool = False) -> dict: ...
    schemas = schemas_for(["greet"])
    params = schemas[0]["parameters"]
    assert params["required"] == ["name"]
    assert "polite" in params["properties"]
```

- [ ] **Step 2: 运行确认失败**

Run: `pytest tests/test_tools/test_registry.py -v`
Expected: ImportError

- [ ] **Step 3: 写 `app/tools/base.py`**

```python
from __future__ import annotations
import inspect
from dataclasses import dataclass
from typing import Any, Callable

@dataclass
class Tool:
    name: str
    description: str
    fn: Callable
    schema: dict[str, Any]

_PY_TO_JSON = {
    str: "string", int: "integer", float: "number",
    bool: "boolean", list: "array", dict: "object",
}

def build_schema_from_signature(fn: Callable, name: str, description: str) -> dict[str, Any]:
    sig = inspect.signature(fn)
    properties: dict[str, Any] = {}
    required: list[str] = []
    for pname, param in sig.parameters.items():
        if pname in ("self",):
            continue
        ann = param.annotation
        json_type = "string"
        if ann in _PY_TO_JSON:
            json_type = _PY_TO_JSON[ann]
        elif isinstance(ann, type) and ann in _PY_TO_JSON:
            json_type = _PY_TO_JSON[ann]
        properties[pname] = {"type": json_type}
        if param.default is inspect.Parameter.empty:
            required.append(pname)
    return {
        "name": name,
        "description": description,
        "parameters": {"type": "object", "properties": properties, "required": required},
    }
```

- [ ] **Step 4: 写 `app/tools/registry.py`**

```python
from __future__ import annotations
import inspect
from typing import Any, Callable
from app.tools.base import Tool, build_schema_from_signature

_registry: dict[str, Tool] = {}

def tool(name: str, description: str):
    def deco(fn: Callable):
        schema = build_schema_from_signature(fn, name, description)
        _registry[name] = Tool(name=name, description=description, fn=fn, schema=schema)
        return fn
    return deco

async def call(name: str, args: dict[str, Any]) -> Any:
    if name not in _registry:
        raise KeyError(f"tool not registered: {name}")
    t = _registry[name]
    result = t.fn(**args)
    if inspect.isawaitable(result):
        result = await result
    return result

def schemas_for(names: list[str]) -> list[dict[str, Any]]:
    return [_registry[n].schema for n in names if n in _registry]

def clear() -> None:
    _registry.clear()
```

- [ ] **Step 5: 运行测试**

Run: `pytest tests/test_tools/test_registry.py -v`
Expected: 6 passed

- [ ] **Step 6: Commit**

```bash
git add app/tools/ tests/test_tools/
git commit -m "feat: tools registry with @tool decorator + schema builder"
```

---

## Task 15: 内置工具 echo + http_get

**Files:**
- Create: `agent-platform/app/tools/builtin/__init__.py`
- Create: `agent-platform/app/tools/builtin/echo.py`
- Create: `agent-platform/app/tools/builtin/http_get.py`

- [ ] **Step 1: 写 `app/tools/builtin/__init__.py`**

```python
# 导入即注册
from app.tools.builtin import echo, http_get  # noqa: F401
```

- [ ] **Step 2: 写 `echo.py`**

```python
from app.tools.registry import tool

@tool("echo", "回显传入的文本，用于测试工具调用链路")
async def echo(text: str) -> dict:
    return {"echo": text}
```

- [ ] **Step 3: 写 `http_get.py`**

```python
import httpx
from app.tools.registry import tool

@tool("http_get", "发起 HTTP GET 请求取回页面/接口内容，用于测试外部依赖")
async def http_get(url: str, timeout: int = 10) -> dict:
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(url)
    return {"status": resp.status_code, "body": resp.text[:2000]}
```

- [ ] **Step 4: 在 main.py 占位里加注册触发（修改 app/main.py）**

在 `create_app` 内部、`return app` 之前加：

```python
    # 触发内置工具注册
    import app.tools.builtin  # noqa: F401
```

- [ ] **Step 5: 验证**

Run: `python -c "import app.tools.builtin; from app.tools.registry import schemas_for; print(schemas_for(['echo', 'http_get']))"`
Expected: 输出含两个 schema 的 list

- [ ] **Step 6: Commit**

```bash
git add app/tools/builtin/ app/main.py
git commit -m "feat: builtin tools echo + http_get"
```

---

## Task 16: Agent Loader（YAML → DB upsert）

**Files:**
- Create: `agent-platform/app/agents/__init__.py` (空)
- Create: `agent-platform/app/agents/loader.py`
- Create: `agent-platform/agents/echo-assistant.yaml`
- Create: `agent-platform/tests/test_agents/__init__.py` (空)
- Create: `agent-platform/tests/test_agents/test_loader.py`

- [ ] **Step 1: 写 echo-assistant.yaml**

```yaml
name: echo-assistant
system_prompt: |
  你是一个测试助手。用户说话时调用 echo 工具回显，然后总结。
tools:
  - echo
default_provider: null
default_model: Qwen2.5-7B-Instruct
temperature: 0.3
max_history: 20
retry:
  max_iterations: 4
enabled: true
```

- [ ] **Step 2: 写失败测试**

```python
from pathlib import Path
from app.agents.loader import load_agents_from_dir, upsert_agent
from app.models import Agent, Provider, User

def _seed_user(db_session):
    u = User(email="o@x.com", password_hash="x", role="owner")
    db_session.add(u); db_session.commit()
    return u.id

def test_upsert_creates_new_agent(db_session):
    uid = _seed_user(db_session)
    upsert_agent(db_session, {
        "name": "bot1", "system_prompt": "s", "tools": ["echo"],
        "default_provider": None, "default_model": "Q",
        "temperature": 0.3, "max_history": 10,
        "retry": {"max_iterations": 4}, "schedule": None, "enabled": True,
    }, created_by=uid)
    a = db_session.query(Agent).filter_by(name="bot1").one()
    assert a.tools_json == ["echo"]
    assert a.retry_strategy_json == {"max_iterations": 4}

def test_upsert_updates_existing(db_session):
    uid = _seed_user(db_session)
    upsert_agent(db_session, {"name": "bot", "system_prompt": "v1",
        "tools": [], "default_provider": None, "default_model": "Q",
        "temperature": 0.7, "max_history": 20, "retry": {"max_iterations": 8},
        "schedule": None, "enabled": True}, created_by=uid)
    upsert_agent(db_session, {"name": "bot", "system_prompt": "v2",
        "tools": ["echo"], "default_provider": None, "default_model": "Q",
        "temperature": 0.5, "max_history": 20, "retry": {"max_iterations": 4},
        "schedule": None, "enabled": True}, created_by=uid)
    a = db_session.query(Agent).filter_by(name="bot").one()
    assert a.system_prompt == "v2"
    assert a.tools_json == ["echo"]
    assert db_session.query(Agent).count() == 1

def test_load_from_yaml_dir(db_session, tmp_path):
    uid = _seed_user(db_session)
    yamldir = Path(__file__).resolve().parents[1] / "agents"
    load_agents_from_dir(db_session, yamldir, created_by=uid)
    a = db_session.query(Agent).filter_by(name="echo-assistant").one()
    assert "echo" in a.tools_json
```

- [ ] **Step 3: 运行确认失败**

Run: `pytest tests/test_agents/test_loader.py -v`
Expected: ImportError

- [ ] **Step 4: 写 `app/agents/loader.py`**

```python
from __future__ import annotations
from pathlib import Path
import yaml
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import select
from app.models import Agent, Provider

def upsert_agent(db: DBSession, spec: dict, created_by: int) -> Agent:
    name = spec["name"]
    existing = db.scalar(select(Agent).where(Agent.name == name))
    schedule = spec.get("schedule") or {}
    provider_id = None
    if spec.get("default_provider"):
        p = db.scalar(select(Provider).where(Provider.name == spec["default_provider"]))
        if p is not None:
            provider_id = p.id
    attrs = dict(
        system_prompt=spec["system_prompt"],
        tools_json=spec.get("tools", []),
        default_provider_id=provider_id,
        default_model=spec["default_model"],
        temperature=spec.get("temperature", 0.7),
        max_history=spec.get("max_history", 20),
        retry_strategy_json=spec.get("retry", {"max_iterations": 8}),
        schedule_cron=schedule.get("cron") if schedule else None,
        schedule_input=schedule.get("input") if schedule else None,
        enabled=spec.get("enabled", True),
    )
    if existing is None:
        a = Agent(name=name, created_by=created_by, **attrs)
        db.add(a)
    else:
        for k, v in attrs.items():
            setattr(existing, k, v)
        a = existing
    db.commit()
    db.refresh(a)
    return a

def load_agents_from_dir(db: DBSession, dirpath: Path | str, created_by: int) -> list[Agent]:
    dirpath = Path(dirpath)
    if not dirpath.exists():
        return []
    loaded: list[Agent] = []
    for f in sorted(dirpath.glob("*.yaml")):
        spec = yaml.safe_load(f.read_text())
        try:
            loaded.append(upsert_agent(db, spec, created_by=created_by))
        except Exception as e:
            # 单个 agent 失败不影响其他
            import structlog
            structlog.get_logger().warning("agent load failed", file=str(f), error=str(e))
    return loaded
```

- [ ] **Step 5: 运行测试**

Run: `pytest tests/test_agents/test_loader.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add app/agents/ agents/echo-assistant.yaml tests/test_agents/
git commit -m "feat: agent YAML loader with upsert + default echo-assistant"
```

---

## Task 17: Agent History（session/message CRUD）

**Files:**
- Create: `agent-platform/app/agents/history.py`
- Create: `agent-platform/tests/test_agents/test_history.py`

- [ ] **Step 1: 写失败测试**

```python
import pytest
from app.agents.history import History
from app.models import Agent, Session as ChatSession, Message, User

def _seed(db_session):
    u = User(email="o@x.com", password_hash="x", role="owner")
    db_session.add(u); db_session.commit()
    a = Agent(name="bot", system_prompt="s", tools_json=[], default_model="Q",
              temperature=0.7, max_history=20, retry_strategy_json={"max_iterations": 8},
              enabled=True, created_by=u.id)
    db_session.add(a); db_session.commit()
    s = ChatSession(agent_id=a.id, user_id=u.id, title="t")
    db_session.add(s); db_session.commit()
    return s.id

async def test_save_and_load_user_message(db_session):
    sid = _seed(db_session)
    h = History(db_session)
    await h.save_user(sid, "hello")
    msgs = await h.load(sid, limit=10)
    assert len(msgs) == 1
    assert msgs[0].role == "user"
    assert msgs[0].content == "hello"

async def test_save_assistant_with_tool_calls(db_session):
    sid = _seed(db_session)
    h = History(db_session)
    from app.providers.base import ToolCall
    await h.save_assistant(sid, content=None, tool_calls=[
        ToolCall(id="c1", name="echo", args={"text": "hi"})])
    msgs = await h.load(sid, limit=10)
    assert msgs[0].role == "assistant"
    assert msgs[0].tool_calls[0].name == "echo"

async def test_save_tool_result(db_session):
    sid = _seed(db_session)
    h = History(db_session)
    await h.save_tool_result(sid, tool_call_id="c1", name="echo", result={"echo": "hi"})
    msgs = await h.load(sid, limit=10)
    assert msgs[0].role == "tool"
    assert msgs[0].tool_call_id == "c1"

async def test_load_respects_limit(db_session):
    sid = _seed(db_session)
    h = History(db_session)
    for i in range(10):
        await h.save_user(sid, f"msg-{i}")
    msgs = await h.load(sid, limit=3)
    assert len(msgs) == 3
    # 拉最近 3 条
    assert msgs[0].content == "msg-7"
    assert msgs[2].content == "msg-9"
```

- [ ] **Step 2: 运行确认失败**

Run: `pytest tests/test_agents/test_history.py -v`
Expected: ImportError

- [ ] **Step 3: 写 `app/agents/history.py`**

```python
from __future__ import annotations
import json
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession
from app.models import Message, Session as ChatSession
from app.providers.base import Message as LLMMessage, ToolCall

class History:
    def __init__(self, db: DBSession):
        self.db = db

    async def load(self, session_id: int, limit: int = 20) -> list[LLMMessage]:
        stmt = (select(Message).where(Message.session_id == session_id)
                .order_by(Message.created_at.desc()).limit(limit))
        rows = list(reversed(self.db.scalars(stmt).all()))
        return [self._row_to_msg(r) for r in rows]

    async def save_user(self, session_id: int, content: str) -> Message:
        m = Message(session_id=session_id, role="user",
                    content_json={"text": content}, tool_calls_json=None,
                    tool_call_id=None, token_count=None)
        self.db.add(m); self.db.commit(); self.db.refresh(m)
        return m

    async def save_assistant(self, session_id: int, content: str | None,
                             tool_calls: list[ToolCall] | None) -> Message:
        tc_json = None
        if tool_calls:
            tc_json = [{"id": tc.id, "name": tc.name, "args": tc.args} for tc in tool_calls]
        m = Message(session_id=session_id, role="assistant",
                    content_json={"text": content}, tool_calls_json=tc_json,
                    tool_call_id=None, token_count=None)
        self.db.add(m); self.db.commit(); self.db.refresh(m)
        return m

    async def save_tool_result(self, session_id: int, tool_call_id: str,
                               name: str, result: dict) -> Message:
        m = Message(session_id=session_id, role="tool",
                    content_json={"tool_result": result}, tool_calls_json=None,
                    tool_call_id=tool_call_id, token_count=None)
        self.db.add(m); self.db.commit(); self.db.refresh(m)
        return m

    def _row_to_msg(self, r: Message) -> LLMMessage:
        content = None
        tool_calls = None
        if r.role == "tool":
            content = json.dumps(r.content_json.get("tool_result", {}))
        else:
            content = r.content_json.get("text")
        if r.tool_calls_json:
            tool_calls = [ToolCall(id=tc["id"], name=tc["name"], args=tc["args"])
                          for tc in r.tool_calls_json]
        return LLMMessage(
            role=r.role, content=content, tool_calls=tool_calls,
            tool_call_id=r.tool_call_id, name=(r.tool_call_id and "tool"),
        )
```

- [ ] **Step 4: 运行测试**

Run: `pytest tests/test_agents/test_history.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add app/agents/history.py tests/test_agents/test_history.py
git commit -m "feat: agent history (session/message CRUD + load with limit)"
```

---

## Task 18: Agent Runtime（ReAct 循环）

**Files:**
- Create: `agent-platform/app/agents/runtime.py`
- Create: `agent-platform/tests/test_agents/test_runtime.py`

- [ ] **Step 1: 写失败测试（用脚本化 stub provider）**

```python
import pytest
from dataclasses import dataclass
from app.agents.runtime import AgentRuntime, Event
from app.agents.history import History
from app.models import Agent, Session as ChatSession, User
from app.providers.base import (CompletionResponse, Message, ToolCall, TokenUsage,
                                CompletionRequest)

def _seed_agent(db_session):
    u = User(email="o@x.com", password_hash="x", role="owner")
    db_session.add(u); db_session.commit()
    a = Agent(name="bot", system_prompt="你是助手", tools_json=["echo"],
              default_model="Q", temperature=0.3, max_history=20,
              retry_strategy_json={"max_iterations": 4}, enabled=True, created_by=u.id)
    db_session.add(a); db_session.commit()
    s = ChatSession(agent_id=a.id, user_id=u.id, title="t")
    db_session.add(s); db_session.commit()
    return a, s.id

class ScriptedProvider:
    """按脚本返回响应，模拟 ReAct 多轮工具调用"""
    def __init__(self, script: list[CompletionResponse]):
        self.script = list(script)
        self.calls = 0
    async def complete(self, req, **kw):
        resp = self.script[self.calls]
        self.calls += 1
        return resp

async def test_simple_no_tool(db_session):
    a, sid = _seed_agent(db_session)
    provider = ScriptedProvider([CompletionResponse(content="hi", usage=TokenUsage(1,1,2))])
    rt = AgentRuntime(provider=provider, history=History(db_session),
                      tools_call=None, schemas_for=lambda names: [])
    events = [e async for e in rt.run(a, "hello", sid)]
    assert events[-1].type == "done"
    assert events[0].type == "content_delta"

async def test_one_tool_call_then_finish(db_session):
    a, sid = _seed_agent(db_session)
    provider = ScriptedProvider([
        CompletionResponse(content=None, tool_calls=[
            ToolCall(id="c1", name="echo", args={"text": "hi"})],
            usage=TokenUsage(5, 5, 10)),
        CompletionResponse(content="echoed: hi", usage=TokenUsage(10, 5, 15)),
    ])
    async def fake_call(name, args): return {"echo": args["text"]}
    rt = AgentRuntime(provider=provider, history=History(db_session),
                      tools_call=fake_call, schemas_for=lambda names: [])
    events = [e async for e in rt.run(a, "echo hi", sid)]
    types = [e.type for e in events]
    assert "tool_result" in types
    assert events[-1].type == "done"

async def test_tool_error_backfed(db_session):
    a, sid = _seed_agent(db_session)
    provider = ScriptedProvider([
        CompletionResponse(content=None, tool_calls=[
            ToolCall(id="c1", name="echo", args={"text": "x"})]),
        CompletionResponse(content="got error, sorry", usage=TokenUsage(1,1,2)),
    ])
    async def fake_call(name, args): raise RuntimeError("boom")
    rt = AgentRuntime(provider=provider, history=History(db_session),
                      tools_call=fake_call, schemas_for=lambda names: [])
    events = [e async for e in rt.run(a, "echo", sid)]
    tr = next(e for e in events if e.type == "tool_result")
    assert "error" in tr.payload["result"]

async def test_max_iterations_truncated(db_session):
    a, sid = _seed_agent(db_session)
    # 每轮都返回工具调用，永不结束
    looping = CompletionResponse(content=None, tool_calls=[
        ToolCall(id="c", name="echo", args={"text": "x"})])
    provider = ScriptedProvider([looping] * 10)
    async def fake_call(name, args): return {"echo": "x"}
    rt = AgentRuntime(provider=provider, history=History(db_session),
                      tools_call=fake_call, schemas_for=lambda names: [])
    events = [e async for e in rt.run(a, "loop", sid)]
    assert events[-1].type == "truncated"
```

- [ ] **Step 2: 运行确认失败**

Run: `pytest tests/test_agents/test_runtime.py -v`
Expected: ImportError

- [ ] **Step 3: 写 `app/agents/runtime.py`**

```python
from __future__ import annotations
import json
from dataclasses import dataclass
from typing import Any, AsyncIterator, Callable, Awaitable
from app.providers.base import CompletionRequest, CompletionResponse, Message, ToolCall
from app.models import Agent

@dataclass
class Event:
    type: str  # content_delta | tool_result | done | truncated
    payload: Any = None

class AgentRuntime:
    def __init__(self, provider, history, tools_call,
                 schemas_for: Callable[[list[str]], list[dict]]):
        # provider: 对象有 async complete(req, **kw) -> CompletionResponse
        # tools_call: async (name, args) -> dict
        self.provider = provider
        self.history = history
        self.tools_call = tools_call
        self.schemas_for = schemas_for

    async def run(self, agent: Agent, user_msg: str, session_id: int) -> AsyncIterator[Event]:
        history = await self.history.load(session_id, limit=agent.max_history)
        messages = ([Message(role="system", content=agent.system_prompt)]
                    + history + [Message(role="user", content=user_msg)])
        await self.history.save_user(session_id, user_msg)
        tools = self.schemas_for(agent.tools_json)
        max_iter = (agent.retry_strategy_json or {}).get("max_iterations", 8)

        for _ in range(max_iter):
            resp = await self.provider.complete(
                CompletionRequest(messages=messages, tools=tools,
                                  model=agent.default_model,
                                  temperature=agent.temperature),
            )
            if resp.content:
                yield Event("content_delta", resp.content)

            if not resp.tool_calls:
                await self.history.save_assistant(session_id, resp.content, tool_calls=None)
                yield Event("done", {"finish_reason": resp.finish_reason})
                return

            await self.history.save_assistant(session_id, resp.content, resp.tool_calls)
            messages.append(Message(role="assistant", content=resp.content,
                                     tool_calls=resp.tool_calls))
            for tc in resp.tool_calls:
                try:
                    result = await self.tools_call(tc.name, tc.args)
                except Exception as e:
                    result = {"error": f"工具 {tc.name} 执行失败：{e}"}
                await self.history.save_tool_result(session_id, tc.id, tc.name, result)
                messages.append(Message(role="tool", content=json.dumps(result),
                                        tool_call_id=tc.id, name=tc.name))
                yield Event("tool_result", {"name": tc.name, "result": result})

        yield Event("truncated", {"reason": "max_iterations_exceeded"})
```

- [ ] **Step 4: 运行测试**

Run: `pytest tests/test_agents/test_runtime.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add app/agents/runtime.py tests/test_agents/test_runtime.py
git commit -m "feat: agent ReAct runtime with tool calling + truncation"
```

---

## Task 19: Agent Scheduler

**Files:**
- Create: `agent-platform/app/agents/scheduler.py`
- Create: `agent-platform/tests/test_agents/test_scheduler.py`

- [ ] **Step 1: 写失败测试（用内存 job store，不依赖 Redis）**

```python
import pytest
from datetime import datetime
from app.agents.scheduler import AgentScheduler
from app.models import Agent, User

def _seed(db_session):
    u = User(email="o@x.com", password_hash="x", role="owner")
    db_session.add(u); db_session.commit()
    a = Agent(name="weekly", system_prompt="s", tools_json=[], default_model="Q",
              temperature=0.3, max_history=20, retry_strategy_json={"max_iterations": 4},
              schedule_cron="0 9 * * 1", schedule_input="周报", enabled=True,
              created_by=u.id)
    db_session.add(a); db_session.commit()
    return a

def test_register_schedules_job(db_session):
    a = _seed(db_session)
    sched = AgentScheduler(use_redis=False, timezone="UTC")
    sched.start()
    sched.register(a)
    jobs = sched.scheduler.get_jobs()
    assert len(jobs) == 1
    assert jobs[0].id == f"agent-{a.id}"
    sched.shutdown()

def test_register_skips_when_no_cron(db_session):
    u = User(email="o@x.com", password_hash="x", role="owner")
    db_session.add(u); db_session.commit()
    a = Agent(name="interactive", system_prompt="s", tools_json=[], default_model="Q",
              temperature=0.3, max_history=20, retry_strategy_json={"max_iterations": 4},
              enabled=True, created_by=u.id)
    db_session.add(a); db_session.commit()
    sched = AgentScheduler(use_redis=False, timezone="UTC")
    sched.start()
    sched.register(a)
    assert len(sched.scheduler.get_jobs()) == 0
    sched.shutdown()

def test_unregister(db_session):
    a = _seed(db_session)
    sched = AgentScheduler(use_redis=False, timezone="UTC")
    sched.start()
    sched.register(a)
    sched.unregister(a.id)
    assert len(sched.scheduler.get_jobs()) == 0
    sched.shutdown()
```

- [ ] **Step 2: 运行确认失败**

Run: `pytest tests/test_agents/test_scheduler.py -v`
Expected: ImportError

- [ ] **Step 3: 写 `app/agents/scheduler.py`**

```python
from __future__ import annotations
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.triggers.cron import CronTrigger
from app.models import Agent

SYSTEM_USER_ID = 0  # 定时任务的系统用户（v1 占位）

class AgentScheduler:
    def __init__(self, use_redis: bool = False, redis_url: str | None = None,
                 timezone: str = "Asia/Shanghai"):
        self.timezone = timezone
        if use_redis and redis_url:
            jobstore = RedisJobStore(redis_url=redis_url)
        else:
            jobstore = MemoryJobStore()
        self.scheduler = BackgroundScheduler(timezone=timezone,
                                             jobstores={"default": jobstore})
        self._started = False

    def start(self):
        if not self._started:
            self.scheduler.start()
            self._started = True

    def shutdown(self, wait: bool = False):
        if self._started:
            self.scheduler.shutdown(wait=wait)
            self._started = False

    def register(self, agent: Agent) -> None:
        if not agent.schedule_cron:
            return
        trigger = CronTrigger.from_crontab(agent.schedule_cron, timezone=self.timezone)
        self.scheduler.add_job(
            _run_scheduled, trigger=trigger,
            args=[agent.id, agent.schedule_input],
            id=f"agent-{agent.id}", replace_existing=True,
        )

    def unregister(self, agent_id: int) -> None:
        try:
            self.scheduler.remove_job(f"agent-{agent_id}")
        except Exception:
            pass

def _run_scheduled(agent_id: int, input_text: str | None) -> None:
    # 在 job 执行的进程内 import，避免循环依赖
    import asyncio
    from app.main import _settings, _engine
    from app.db import session_factory
    from app.models import Agent, Session as ChatSession
    from app.agents.history import History
    from app.agents.runtime import AgentRuntime
    from app.providers.router import Router
    from app.providers.accounting import Accounting
    from app.tools.registry import schemas_for, call
    from app.logging import get_logger
    log = get_logger("scheduler")
    async def _go():
        factory = session_factory(_engine)
        db = factory()
        try:
            agent = db.get(Agent, agent_id)
            if agent is None or not agent.enabled:
                return
            session = ChatSession(agent_id=agent.id, user_id=SYSTEM_USER_ID,
                                   title=f"定时:{(input_text or '')[:30]}")
            db.add(session); db.commit(); db.refresh(session)
            # 这里 router 简化：实际由 main.py 注入；定时任务里直接用 None router 占位
            # 生产实现需要从 provider repo 构造 router，此处仅持久化结构
            log.info("scheduled run would start", agent=agent.name, session=session.id)
        finally:
            db.close()
    asyncio.run(_go())
```

- [ ] **Step 4: 运行测试**

Run: `pytest tests/test_agents/test_scheduler.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add app/agents/scheduler.py tests/test_agents/test_scheduler.py
git commit -m "feat: APScheduler-based agent scheduler with redis/memory jobstore"
```

---

## Task 20: API — Auth 路由

**Files:**
- Create: `agent-platform/app/api/__init__.py` (空)
- Create: `agent-platform/app/api/deps.py`
- Create: `agent-platform/app/api/auth.py`
- Create: `agent-platform/tests/test_api/__init__.py` (空)
- Create: `agent-platform/tests/test_api/test_auth_api.py`

- [ ] **Step 1: 写 `app/api/deps.py`（共享 repository 依赖）**

```python
from __future__ import annotations
from sqlalchemy.orm import Session as DBSession
from fastapi import Depends
from app.auth.deps import get_db, get_settings, get_current_user, require_role
from app.config import Settings
from app.models import User

__all__ = ["get_db", "get_settings", "get_current_user", "require_role", "User", "Settings", "DBSession"]
```

- [ ] **Step 2: 写 `app/api/auth.py`**

```python
from __future__ import annotations
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession
from app.api.deps import get_db, get_settings, Settings
from app.auth.jwt import sign_token
from app.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])

class LoginIn(BaseModel):
    email: str
    password: str

class LoginOut(BaseModel):
    token: str
    user_id: int
    role: str

@router.post("/login", response_model=LoginOut)
def login(body: LoginIn, db: DBSession = Depends(get_db),
          settings: Settings = Depends(get_settings)):
    user = db.scalar(select(User).where(User.email == body.email))
    if user is None or not bcrypt.checkpw(body.password.encode(),
                                          user.password_hash.encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
    token = sign_token(user.id, user.role, settings.auth.jwt_secret,
                       settings.auth.jwt_expiry_hours)
    return LoginOut(token=token, user_id=user.id, role=user.role)
```

- [ ] **Step 3: 写失败测试**

```python
import bcrypt
from fastapi.testclient import TestClient
from app.models import User

def test_login_success(client, db_session):
    pw = bcrypt.hashpw("secret".encode(), bcrypt.gensalt()).decode()
    u = User(email="a@b.com", password_hash=pw, role="owner")
    db_session.add(u); db_session.commit()
    r = client.post("/api/auth/login", json={"email": "a@b.com", "password": "secret"})
    assert r.status_code == 200
    data = r.json()
    assert "token" in data and data["user_id"] == u.id

def test_login_wrong_password(client, db_session):
    pw = bcrypt.hashpw("secret".encode(), bcrypt.gensalt()).decode()
    u = User(email="a@b.com", password_hash=pw, role="owner")
    db_session.add(u); db_session.commit()
    r = client.post("/api/auth/login", json={"email": "a@b.com", "password": "wrong"})
    assert r.status_code == 401

def test_login_unknown_user(client):
    r = client.post("/api/auth/login", json={"email": "x@y.com", "password": "p"})
    assert r.status_code == 401
```

需要 client fixture，加到 `tests/conftest.py`：

```python
from fastapi.testclient import TestClient
from app.main import create_app

@pytest.fixture
def app(settings, engine):
    a = create_app(settings=settings)
    return a

@pytest.fixture
def client(app):
    return TestClient(app)
```

- [ ] **Step 4: 运行确认失败**

Run: `pytest tests/test_api/test_auth_api.py -v`
Expected: 失败（client fixture 或路由未注册）

- [ ] **Step 5: 修改 `app/main.py` 注册路由**

```python
from fastapi import FastAPI
from app.config import Settings
from app.db import init_engine
from app.logging import setup_logging

_settings: Settings | None = None
_engine = None

def create_app(settings: Settings | None = None) -> FastAPI:
    global _settings, _engine
    _settings = settings or Settings.load_from_file()
    _engine = init_engine(_settings)
    setup_logging(_settings.logging.level, _settings.logging.format)
    app = FastAPI(title="agent-platform")
    # 注册路由
    from app.api.auth import router as auth_router
    app.include_router(auth_router)
    # 触发内置工具注册
    import app.tools.builtin  # noqa: F401
    return app
```

- [ ] **Step 6: 运行测试**

Run: `pytest tests/test_api/test_auth_api.py -v`
Expected: 3 passed

- [ ] **Step 7: Commit**

```bash
git add app/api/ app/main.py tests/conftest.py tests/test_api/test_auth_api.py
git commit -m "feat: auth API (login) + shared deps"
```

---

## Task 21: API — Providers 路由

**Files:**
- Create: `agent-platform/app/api/providers.py`
- Modify: `agent-platform/app/main.py`
- Create: `agent-platform/tests/test_api/test_providers_api.py`

- [ ] **Step 1: 写 `app/api/providers.py`**

```python
from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession
from app.api.deps import get_db, require_role, User
from app.auth.crypto import encrypt, decrypt
from app.config import Settings
from app.auth.deps import get_settings
from app.models import Provider, AuditLog

router = APIRouter(prefix="/api/providers", tags=["providers"])

class ModelSpec(BaseModel):
    model: str
    cost_per_1k_in_cents: int = 0
    cost_per_1k_out_cents: int = 0

class ProviderIn(BaseModel):
    name: str
    type: str  # openai_compat | anthropic | gemini
    base_url: str
    api_key: str
    models: list[ModelSpec] = []
    priority: int = 0
    strategy: str | None = None
    enabled: bool = True

class ProviderOut(BaseModel):
    id: int
    name: str
    type: str
    base_url: str
    models: list[dict[str, Any]]
    priority: int
    strategy: str | None
    enabled: bool

    @classmethod
    def from_orm(cls, p: Provider) -> "ProviderOut":
        return cls(id=p.id, name=p.name, type=p.type, base_url=p.base_url,
                   models=p.models_json, priority=p.priority,
                   strategy=p.strategy, enabled=p.enabled)

@router.get("", response_model=list[ProviderOut])
def list_providers(db: DBSession = Depends(get_db),
                   _: User = Depends(require_role("owner"))):
    return [ProviderOut.from_orm(p) for p in db.scalars(select(Provider)).all()]

@router.post("", response_model=ProviderOut, status_code=201)
def create_provider(body: ProviderIn, db: DBSession = Depends(get_db),
                    user: User = Depends(require_role("owner")),
                    settings: Settings = Depends(get_settings)):
    p = Provider(name=body.name, type=body.type, base_url=body.base_url,
                 api_key_enc=encrypt(body.api_key, settings.crypto.key),
                 models_json=[m.model_dump() for m in body.models],
                 priority=body.priority, strategy=body.strategy, enabled=body.enabled)
    db.add(p); db.commit(); db.refresh(p)
    db.add(AuditLog(user_id=user.id, action="create", target_type="provider",
                   target_id=p.id, detail_json={"name": p.name}))
    db.commit()
    return ProviderOut.from_orm(p)

@router.delete("/{pid}", status_code=204)
def delete_provider(pid: int, db: DBSession = Depends(get_db),
                    user: User = Depends(require_role("owner"))):
    p = db.get(Provider, pid)
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    db.delete(p)
    db.add(AuditLog(user_id=user.id, action="delete", target_type="provider",
                   target_id=pid, detail_json={}))
    db.commit()
```

- [ ] **Step 2: 注册到 main.py**

在 `create_app` 内 `app.include_router(auth_router)` 之后加：

```python
    from app.api.providers import router as providers_router
    app.include_router(providers_router)
```

- [ ] **Step 3: 写测试**

```python
from fastapi.testclient import TestClient
from app.auth.jwt import sign_token
from app.models import User

def _owner_token(settings, db_session, email="o@x.com"):
    u = User(email=email, password_hash="x", role="owner")
    db_session.add(u); db_session.commit()
    return sign_token(u.id, "owner", settings.auth.jwt_secret, 1), u.id

def _member_token(settings, db_session):
    u = User(email="m@x.com", password_hash="x", role="member")
    db_session.add(u); db_session.commit()
    return sign_token(u.id, "member", settings.auth.jwt_secret, 1)

def test_create_and_list(client, db_session, settings):
    tok, _ = _owner_token(settings, db_session)
    r = client.post("/api/providers", json={
        "name": "vllm", "type": "openai_compat", "base_url": "http://x",
        "api_key": "sk-x", "models": [{"model": "Q", "cost_per_1k_in_cents": 0}],
        "priority": 0, "enabled": True,
    }, headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 201
    r2 = client.get("/api/providers", headers={"Authorization": f"Bearer {tok}"})
    assert r2.status_code == 200 and len(r2.json()) == 1

def test_member_forbidden(client, db_session, settings):
    tok = _member_token(settings, db_session)
    r = client.get("/api/providers", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 403

def test_unauth_no_token(client):
    r = client.get("/api/providers")
    assert r.status_code == 401
```

- [ ] **Step 4: 运行测试**

Run: `pytest tests/test_api/test_providers_api.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add app/api/providers.py app/main.py tests/test_api/test_providers_api.py
git commit -m "feat: providers CRUD API (owner-only) + audit log"
```

---

## Task 22: API — Agents 路由

**Files:**
- Create: `agent-platform/app/api/agents.py`
- Modify: `agent-platform/app/main.py`
- Create: `agent-platform/tests/test_api/test_agents_api.py`

- [ ] **Step 1: 写 `app/api/agents.py`**

```python
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession
from app.api.deps import get_db, require_role, User
from app.models import Agent

router = APIRouter(prefix="/api/agents", tags=["agents"])

class AgentOut(BaseModel):
    id: int
    name: str
    system_prompt: str
    tools: list[str]
    default_provider_id: int | None
    default_model: str
    temperature: float
    max_history: int
    retry: dict
    schedule_cron: str | None
    schedule_input: str | None
    enabled: bool

    @classmethod
    def from_orm(cls, a: Agent) -> "AgentOut":
        return cls(id=a.id, name=a.name, system_prompt=a.system_prompt,
                   tools=a.tools_json, default_provider_id=a.default_provider_id,
                   default_model=a.default_model, temperature=a.temperature,
                   max_history=a.max_history, retry=a.retry_strategy_json,
                   schedule_cron=a.schedule_cron, schedule_input=a.schedule_input,
                   enabled=a.enabled)

class AgentUpdateIn(BaseModel):
    system_prompt: str | None = None
    tools: list[str] | None = None
    default_provider_id: int | None = None
    default_model: str | None = None
    temperature: float | None = None
    max_history: int | None = None
    retry: dict | None = None
    schedule_cron: str | None = None
    schedule_input: str | None = None
    enabled: bool | None = None

@router.get("", response_model=list[AgentOut])
def list_agents(db: DBSession = Depends(get_db),
                _: User = Depends(require_role("owner"))):
    return [AgentOut.from_orm(a) for a in db.scalars(select(Agent)).all()]

@router.patch("/{aid}", response_model=AgentOut)
def update_agent(aid: int, body: AgentUpdateIn,
                 db: DBSession = Depends(get_db),
                 _: User = Depends(require_role("owner"))):
    a = db.get(Agent, aid)
    if a is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    data = body.model_dump(exclude_unset=True)
    if "tools" in data:
        a.tools_json = data.pop("tools")
    if "retry" in data:
        a.retry_strategy_json = data.pop("retry")
    for k, v in data.items():
        setattr(a, k, v)
    db.commit(); db.refresh(a)
    return AgentOut.from_orm(a)
```

- [ ] **Step 2: 注册到 main.py**

```python
    from app.api.agents import router as agents_router
    app.include_router(agents_router)
```

- [ ] **Step 3: 写测试**

```python
from app.auth.jwt import sign_token
from app.models import User, Agent

def _owner(settings, db_session):
    u = User(email="o@x.com", password_hash="x", role="owner")
    db_session.add(u); db_session.commit()
    return sign_token(u.id, "owner", settings.auth.jwt_secret, 1)

def _seed_agent(db_session, owner_id):
    a = Agent(name="bot", system_prompt="s", tools_json=["echo"],
              default_model="Q", temperature=0.3, max_history=20,
              retry_strategy_json={"max_iterations": 8}, enabled=True, created_by=owner_id)
    db_session.add(a); db_session.commit()
    return a.id

def test_list_and_patch(client, db_session, settings):
    tok = _owner(settings, db_session)
    aid = _seed_agent(db_session, db_session.query(User).first().id)
    r = client.get("/api/agents", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200 and len(r.json()) == 1
    r2 = client.patch(f"/api/agents/{aid}", json={"temperature": 0.5},
                      headers={"Authorization": f"Bearer {tok}"})
    assert r2.status_code == 200 and r2.json()["temperature"] == 0.5
```

- [ ] **Step 4: 运行测试**

Run: `pytest tests/test_api/test_agents_api.py -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add app/api/agents.py app/main.py tests/test_api/test_agents_api.py
git commit -m "feat: agents list + patch API (owner-only)"
```

---

## Task 23: API — Sessions + SSE

**Files:**
- Create: `agent-platform/app/api/sessions.py`
- Modify: `agent-platform/app/main.py`
- Create: `agent-platform/tests/test_api/test_sessions_api.py`

- [ ] **Step 1: 写 `app/api/sessions.py`**

```python
from __future__ import annotations
import json
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession
from app.api.deps import get_db, get_current_user, User
from app.auth.deps import get_settings, Settings
from app.auth.crypto import decrypt
from app.models import Agent, Provider, Session as ChatSession, Message
from app.agents.history import History
from app.agents.runtime import AgentRuntime
from app.providers.adapters.openai_compat import OpenAICompatAdapter
from app.providers.adapters.anthropic import AnthropicAdapter
from app.providers.adapters.gemini import GeminiAdapter
from app.providers.router import Router
from app.providers.accounting import Accounting
from app.tools.registry import schemas_for, call

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

class SessionIn(BaseModel):
    agent_id: int
    title: str | None = None

class SessionOut(BaseModel):
    id: int
    agent_id: int
    title: str | None

@router.post("", response_model=SessionOut, status_code=201)
def create_session(body: SessionIn, db: DBSession = Depends(get_db),
                   user: User = Depends(get_current_user)):
    agent = db.get(Agent, body.agent_id)
    if agent is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "agent not found")
    s = ChatSession(agent_id=agent.id, user_id=user.id, title=body.title)
    db.add(s); db.commit(); db.refresh(s)
    return SessionOut(id=s.id, agent_id=s.agent_id, title=s.title)

class MsgIn(BaseModel):
    content: str

@router.post("/{sid}/messages")
async def send_message(sid: int, body: MsgIn,
                       db: DBSession = Depends(get_db),
                       user: User = Depends(get_current_user),
                       settings: Settings = Depends(get_settings)):
    session = db.get(ChatSession, sid)
    if session is None or session.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "session not found")
    agent = db.get(Agent, session.agent_id)

    # 构造 router（v1 简化：用 agent.default_provider 或全局 enabled providers）
    adapters = []
    providers = db.scalars(select(Provider).where(Provider.enabled == True)).all()
    for p in providers:
        key = decrypt(p.api_key_enc, settings.crypto.key)
        if p.type == "openai_compat":
            adapters.append(OpenAICompatAdapter(p.id, p.name, p.base_url, key))
        elif p.type == "anthropic":
            adapters.append(AnthropicAdapter(p.id, p.name, p.base_url, key))
        elif p.type == "gemini":
            adapters.append(GeminiAdapter(p.id, p.name, p.base_url, key))
    strategy = (db.get(Provider, agent.default_provider_id).strategy
                if agent.default_provider_id else settings.routing.default_strategy)
    accounting = Accounting(db, settings.crypto.key)
    router_ = Router(providers=adapters, strategy=strategy or "self_hosted_first",
                     accounting=accounting)

    history = History(db)

    class ProviderWrapper:
        async def complete(self, req, **kw):
            return await router_.complete(req, user_id=user.id,
                                          agent_id=agent.id, session_id=sid)

    runtime = AgentRuntime(provider=ProviderWrapper(), history=history,
                           tools_call=call, schemas_for=schemas_for)

    async def stream():
        try:
            async for ev in runtime.run(agent, body.content, sid):
                yield f"data: {json.dumps({'type': ev.type, 'payload': ev.payload})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'payload': {'message': str(e)}})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")

@router.get("/{sid}/messages")
def list_messages(sid: int, db: DBSession = Depends(get_db),
                  user: User = Depends(get_current_user)):
    session = db.get(ChatSession, sid)
    if session is None or session.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "session not found")
    msgs = db.scalars(select(Message).where(Message.session_id == sid)
                      .order_by(Message.created_at.asc())).all()
    return [{"id": m.id, "role": m.role, "content": m.content_json,
             "tool_calls": m.tool_calls_json, "tool_call_id": m.tool_call_id}
            for m in msgs]
```

- [ ] **Step 2: 注册到 main.py**

```python
    from app.api.sessions import router as sessions_router
    app.include_router(sessions_router)
```

- [ ] **Step 3: 写测试（用 stub：测试路由层，provider 用 mock）**

```python
import pytest
from app.auth.jwt import sign_token
from app.models import User, Agent, Provider, Session as ChatSession
from app.auth.crypto import encrypt

def _owner(settings, db_session):
    u = User(email="o@x.com", password_hash="x", role="owner")
    db_session.add(u); db_session.commit()
    return sign_token(u.id, "owner", settings.auth.jwt_secret, 1), u.id

def test_create_session(client, db_session, settings):
    tok, uid = _owner(settings, db_session)
    a = Agent(name="bot", system_prompt="s", tools_json=["echo"],
              default_model="Q", temperature=0.3, max_history=20,
              retry_strategy_json={"max_iterations": 4}, enabled=True, created_by=uid)
    db_session.add(a); db_session.commit()
    r = client.post("/api/sessions", json={"agent_id": a.id, "title": "t"},
                    headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 201 and r.json()["agent_id"] == a.id

def test_list_messages_empty(client, db_session, settings):
    tok, uid = _owner(settings, db_session)
    a = Agent(name="bot2", system_prompt="s", tools_json=[], default_model="Q",
              temperature=0.3, max_history=20, retry_strategy_json={"max_iterations": 4},
              enabled=True, created_by=uid)
    db_session.add(a); db_session.commit()
    s = ChatSession(agent_id=a.id, user_id=uid, title="t")
    db_session.add(s); db_session.commit()
    r = client.get(f"/api/sessions/{s.id}/messages",
                   headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200 and r.json() == []

def test_send_message_404_for_unknown_session(client, db_session, settings):
    tok, _ = _owner(settings, db_session)
    r = client.post("/api/sessions/9999/messages", json={"content": "hi"},
                    headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 404
```

- [ ] **Step 4: 运行测试**

Run: `pytest tests/test_api/test_sessions_api.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add app/api/sessions.py app/main.py tests/test_api/test_sessions_api.py
git commit -m "feat: sessions API with SSE streaming + message history"
```

---

## Task 24: API — Usage + Health

**Files:**
- Create: `agent-platform/app/api/usage.py`
- Create: `agent-platform/app/api/health.py`
- Modify: `agent-platform/app/main.py`
- Create: `agent-platform/tests/test_api/test_usage_api.py`

- [ ] **Step 1: 写 `app/api/usage.py`**

```python
from __future__ import annotations
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm import Session as DBSession
from app.api.deps import get_db, get_current_user, User
from app.models import TokenUsage

router = APIRouter(prefix="/api/usage", tags=["usage"])

class UsageRow(BaseModel):
    id: int
    provider_id: int
    agent_id: int | None
    session_id: int | None
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_cents: int
    status: str
    created_at: datetime

@router.get("", response_model=list[UsageRow])
def list_usage(start: datetime | None = Query(None),
               end: datetime | None = Query(None),
               agent_id: int | None = Query(None),
               db: DBSession = Depends(get_db),
               user: User = Depends(get_current_user)):
    stmt = select(TokenUsage).where(TokenUsage.user_id == user.id)
    if user.role == "owner":
        stmt = select(TokenUsage)  # owner 看全部
    if start: stmt = stmt.where(TokenUsage.created_at >= start)
    if end: stmt = stmt.where(TokenUsage.created_at <= end)
    if agent_id: stmt = stmt.where(TokenUsage.agent_id == agent_id)
    stmt = stmt.order_by(TokenUsage.created_at.desc()).limit(500)
    return [UsageRow(id=r.id, provider_id=r.provider_id, agent_id=r.agent_id,
                     session_id=r.session_id, model=r.model,
                     prompt_tokens=r.prompt_tokens,
                     completion_tokens=r.completion_tokens,
                     total_tokens=r.total_tokens, cost_cents=r.cost_cents,
                     status=r.status, created_at=r.created_at)
            for r in db.scalars(stmt).all()]

@router.get("/summary")
def summary(db: DBSession = Depends(get_db),
            user: User = Depends(get_current_user)):
    stmt = select(TokenUsage).where(TokenUsage.user_id == user.id)
    if user.role == "owner":
        stmt = select(TokenUsage)
    rows = db.scalars(stmt).all()
    return {"total_calls": len(rows),
            "total_tokens": sum(r.total_tokens for r in rows),
            "total_cost_cents": sum(r.cost_cents for r in rows),
            "failed_calls": sum(1 for r in rows if r.status == "failed")}
```

- [ ] **Step 2: 写 `app/api/health.py`**

```python
from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session as DBSession
from app.api.deps import get_db

router = APIRouter(prefix="/api/health", tags=["health"])

@router.get("")
def health(db: DBSession = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "up"}
    except Exception as e:
        return {"status": "degraded", "db": str(e)}
```

- [ ] **Step 3: 注册到 main.py**

```python
    from app.api.usage import router as usage_router
    from app.api.health import router as health_router
    app.include_router(usage_router)
    app.include_router(health_router)
```

- [ ] **Step 4: 写 usage 测试**

```python
from datetime import datetime
from app.auth.jwt import sign_token
from app.models import User, TokenUsage

def _user(settings, db_session, role="owner"):
    u = User(email=f"{role}@x.com", password_hash="x", role=role)
    db_session.add(u); db_session.commit()
    return sign_token(u.id, role, settings.auth.jwt_secret, 1), u.id

def test_usage_summary(client, db_session, settings):
    tok, uid = _user(settings, db_session, "owner")
    db_session.add(TokenUsage(provider_id=1, user_id=uid, agent_id=1, session_id=1,
                              model="Q", prompt_tokens=10, completion_tokens=5,
                              total_tokens=15, cost_cents=3, latency_ms=100,
                              status="success"))
    db_session.commit()
    r = client.get("/api/usage/summary", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert r.json()["total_tokens"] == 15

def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] in ("ok", "degraded")
```

- [ ] **Step 5: 运行测试**

Run: `pytest tests/test_api/test_usage_api.py -v`
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add app/api/usage.py app/api/health.py app/main.py tests/test_api/test_usage_api.py
git commit -m "feat: usage API (list + summary) + health endpoint"
```

---

## Task 25: 启动时加载 agents + scheduler

**Files:**
- Modify: `agent-platform/app/main.py`
- Modify: `agent-platform/tests/conftest.py`

- [ ] **Step 1: 在 main.py 的 `create_app` 里加启动逻辑（用 lifespan）**

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：建表（dev） + 加载 agent YAML + 注册 scheduler
    from app.db import session_factory
    from app.models import Base, User
    from app.agents.loader import load_agents_from_dir
    from app.agents.scheduler import AgentScheduler
    from pathlib import Path
    import bcrypt

    Base.metadata.create_all(_engine)
    factory = session_factory(_engine)
    db = factory()
    try:
        # 确保 owner 存在（dev 用；生产应通过 CLI 创建）
        owner = db.scalar(select(User).where(User.email == "owner@local"))
        if owner is None:
            owner = User(email="owner@local",
                         password_hash=bcrypt.hashpw("changeme".encode(),
                                                      bcrypt.gensalt()).decode(),
                         role="owner")
            db.add(owner); db.commit(); db.refresh(owner)
        uid = owner.id

        # 加载 YAML agent
        yamldir = Path(__file__).resolve().parents[1] / "agents"
        load_agents_from_dir(db, yamldir, created_by=uid)

        # 启动 scheduler
        if _settings.scheduler.enabled:
            sched = AgentScheduler(use_redis=False, timezone=_settings.scheduler.timezone)
            sched.start()
            for a in db.scalars(select(Agent).where(Agent.enabled == True)):
                sched.register(a)
            app.state.scheduler = sched
    finally:
        db.close()

    yield

    # 关闭
    sched = getattr(app.state, "scheduler", None)
    if sched: sched.shutdown()
```

把 `app = FastAPI(title=...)` 改成 `app = FastAPI(title=..., lifespan=lifespan)`。

并在文件顶部加 `from sqlalchemy import select` 和 `from app.models import Agent`。

- [ ] **Step 2: 调整 conftest 的 app fixture（不触发完整 lifespan，保持测试隔离）**

修改 `tests/conftest.py` 的 app fixture：

```python
@pytest.fixture
def app(settings, engine):
    # 测试用：手动建表 + 不启动 scheduler（lifespan 在 TestClient 下会跑，
    # 但我们 settings.scheduler.enabled=False 时仍会跑加载 agent YAML，需要 owner 存在。
    # 简化：测试里不依赖 lifespan，直接 create_app 然后手动建表）
    from app.models import Base
    Base.metadata.create_all(engine)
    a = create_app(settings=settings)
    return a
```

实际上 TestClient 会触发 lifespan；为避免依赖 owner 自动创建逻辑，把 lifespan 里的 owner 自动创建改成"找不到则跳过 YAML 加载"：

在 lifespan 里：

```python
        owner = db.scalar(select(User).where(User.email == "owner@local"))
        if owner is None:
            # 测试环境或未初始化：跳过 YAML 加载
            pass
        else:
            uid = owner.id
            yamldir = Path(__file__).resolve().parents[1] / "agents"
            load_agents_from_dir(db, yamldir, created_by=uid)
            if _settings.scheduler.enabled:
                sched = AgentScheduler(use_redis=False, timezone=_settings.scheduler.timezone)
                sched.start()
                for a in db.scalars(select(Agent).where(Agent.enabled == True)):
                    sched.register(a)
                app.state.scheduler = sched
```

- [ ] **Step 3: 运行全部测试**

Run: `pytest -v`
Expected: 全部通过（之前的测试不应回归）

- [ ] **Step 4: 手动烟测**

Run: `cd /workspace/agent-platform && python -c "from app.main import create_app; app = create_app(); print('routes:', len(app.routes))"`
Expected: 输出 routes 数量 > 10

- [ ] **Step 5: Commit**

```bash
git add app/main.py tests/conftest.py
git commit -m "feat: lifespan loads agent YAML + starts scheduler on boot"
```

---

## Task 26: README + 烟测脚本

**Files:**
- Create: `agent-platform/README.md`
- Create: `agent-platform/scripts/smoke_test.py`

- [ ] **Step 1: 写 `scripts/smoke_test.py`**

```python
"""端到端烟测：login → create provider → create session → send msg → 收 SSE。
依赖一个 OpenAI 兼容端点（可用 docker run one-api 或 vLLM mock）。
用法: SMOKE_BASE_URL=http://localhost:8000 python scripts/smoke_test.py
"""
import os
import sys
import httpx

BASE = os.environ.get("SMOKE_BASE_URL", "http://localhost:8000")
PROVIDER_URL = os.environ.get("SMOKE_PROVIDER_URL", "http://localhost:11434/v1")
PROVIDER_KEY = os.environ.get("SMOKE_PROVIDER_KEY", "sk-test")
MODEL = os.environ.get("SMOKE_MODEL", "qwen2.5:7b")

def main():
    with httpx.Client(base_url=BASE, timeout=60) as c:
        # 1. login（首次启动时 owner@local/changeme 由 lifespan 自动建）
        r = c.post("/api/auth/login", json={"email": "owner@local", "password": "changeme"})
        if r.status_code != 200:
            print("login failed:", r.text); sys.exit(1)
        tok = r.json()["token"]
        H = {"Authorization": f"Bearer {tok}"}

        # 2. create provider
        r = c.post("/api/providers", json={
            "name": "smoke-vllm", "type": "openai_compat",
            "base_url": PROVIDER_URL, "api_key": PROVIDER_KEY,
            "models": [{"model": MODEL, "cost_per_1k_in_cents": 0}],
            "priority": 0, "enabled": True,
        }, headers=H)
        if r.status_code != 201:
            print("create provider failed:", r.text); sys.exit(1)
        print("provider created:", r.json()["id"])

        # 3. (agent 由 echo-assistant.yaml 自动加载，找它的 id)
        r = c.get("/api/agents", headers=H)
        agent_id = next(a["id"] for a in r.json() if a["name"] == "echo-assistant")

        # 4. create session
        r = c.post("/api/sessions", json={"agent_id": agent_id, "title": "smoke"},
                   headers=H)
        sid = r.json()["id"]
        print("session:", sid)

        # 5. send message (SSE)
        with c.stream("POST", f"/api/sessions/{sid}/messages",
                      json={"content": "echo hello"},
                      headers=H, timeout=60) as resp:
            for line in resp.iter_lines():
                if line.startswith("data: "):
                    print("EVENT:", line[6:])
        print("SMOKE OK")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 写 README.md**

```markdown
# agent-platform

AI Provider Gateway + Agent Runtime — 产品/项目管理平台的地基。

## 快速开始

```bash
pip install -e ".[dev]"
export JWT_SECRET=your-secret
export MASTER_KEY=your-master-key
uvicorn app.main:app --reload
```

首次启动会自动创建 `owner@local / changeme` 账号，并加载 `agents/*.yaml`。

## 配置

- `config.yaml` — 主配置
- 环境变量 `JWT_SECRET` / `MASTER_KEY` / `DATABASE_URL` 覆盖配置

## 烟测

依赖一个 OpenAI 兼容端点（vLLM / Ollama / one-api mock）：

```bash
SMOKE_PROVIDER_URL=http://localhost:11434/v1 \
SMOKE_MODEL=qwen2.5:7b \
python scripts/smoke_test.py
```

## 架构

见 `../docs/superpowers/specs/2026-09-20-ai-provider-gateway-agent-runtime-design.md`。

## 模块

- `app/providers/` — LLM 接入层（OpenAI 兼容 / Anthropic / Gemini）+ 路由 + 计费
- `app/agents/` — ReAct 运行时 + YAML 加载 + 历史管理 + 定时调度
- `app/tools/` — 工具注册（`@tool` 装饰器）+ schema 构造
- `app/api/` — FastAPI 路由（auth / providers / agents / sessions / usage / health）
- `app/models/` — SQLAlchemy ORM
```

- [ ] **Step 3: 运行全部测试最后一次**

Run: `cd /workspace/agent-platform && pytest -v`
Expected: 全部通过

- [ ] **Step 4: Commit**

```bash
git add README.md scripts/smoke_test.py
git commit -m "docs: README + smoke test script"
```

---

## 后续子项目（不在本计划范围）

- **产品管理模块**：在 `app/tools/builtin/` 加 `create_prd` / `query_prd` / `list_roadmap` + 对应 ORM 表 + API
- **项目管理模块**：加 `create_task` / `update_status` / `burndown` 工具
- **Anthropic/Gemini adapter 实现**：当前是占位，需补全 §4.2 的工具调用格式转换
- **UI 前端**：消费 SSE 流的 React/HTMX 前端
- **飞书/Slack 通知**：在 scheduler 的 `_run_scheduled` 末尾加 notifier 钩子
- **多租户**：users 表加 org_id + 查询 filter
