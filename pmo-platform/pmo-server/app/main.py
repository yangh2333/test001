"""PMO 平台后端入口。"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.core.config import settings
from app.core.db import init_db, Base, engine
from app.core.errors import register_error_handlers
from app.routers import (
    auth, users, projects, tasks, tickets, todos,
    dashboard, admin, gantt, meetings, weekly, gates,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时建表
    Base.metadata.create_all(bind=engine)
    from app.core.seed import ensure_seed
    ensure_seed()
    yield


app = FastAPI(
    title="PMO 运维管理平台",
    version="1.0.0",
    description="面向芯片研发全链条的项目协同平台",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)

# 路由
app.include_router(auth.router, prefix="/api/v1", tags=["认证"])
app.include_router(users.router, prefix="/api/v1", tags=["组织与人员"])
app.include_router(projects.router, prefix="/api/v1", tags=["项目"])
app.include_router(tasks.router, prefix="/api/v1", tags=["任务与WBS"])
app.include_router(gantt.router, prefix="/api/v1", tags=["甘特图"])
app.include_router(gates.router, prefix="/api/v1", tags=["门禁与评审"])
app.include_router(tickets.router, prefix="/api/v1", tags=["协同工单"])
app.include_router(todos.router, prefix="/api/v1", tags=["统一待办"])
app.include_router(meetings.router, prefix="/api/v1", tags=["会议与决议"])
app.include_router(weekly.router, prefix="/api/v1", tags=["周报"])
app.include_router(dashboard.router, prefix="/api/v1", tags=["驾驶舱与报表"])
app.include_router(admin.router, prefix="/api/v1", tags=["管理后台"])


@app.get("/api/v1/health")
def health():
    return {"code": 0, "data": {"status": "ok", "env": settings.ENV}}


# 静态文件（前端构建产物）
# main.py 位于 pmo-platform/pmo-server/app/main.py，需上溯两级到 pmo-platform/
web_dir = Path(__file__).resolve().parent.parent.parent / "pmo-web" / "dist"
if web_dir.exists():
    app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="web")
