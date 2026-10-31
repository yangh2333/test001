# PMO 运维管理平台

面向芯片研发全链条的项目协同平台，基于《PMO平台技术开发规格说明书 v3.0》开发。

## 功能概览

| 模块 | 说明 |
| --- | --- |
| 🔐 认证授权 | 工号密码登录、JWT 令牌、RBAC 角色权限 |
| 📊 驾驶舱 | 项目健康度、阻塞任务、超期工单、待决策事项 |
| 📁 项目管理 | 项目立项、十大类型、阶段/门禁模板、干系人 |
| 📋 WBS 与任务 | 4 级 WBS、任务 CRUD、RACI 职责、依赖关系 |
| 📈 甘特图 | frappe-gantt 渲染、关键路径高亮、基线对比 |
| 🚦 门禁评审 | 承诺制 Gate、Checklist、评审决议、电子签核 |
| 🎫 协同工单 | RACI + SLA + 升级 + 满意度、跨部门请求 |
| ✅ 统一待办 | 5 类待办汇聚、智能排序、会议决议自动转待办 |
| 📝 周报中心 | 自动生成草稿、PM 补充、发布与汇聚 |
| ⚙️ 管理后台 | 用户/部门/角色/字典/审计日志管理 |

## 技术栈

- **后端**: Python 3.11+ / FastAPI / SQLAlchemy 2.0 / SQLite（零配置，可切 PostgreSQL）
- **前端**: React 18 / TypeScript / Ant Design 5 / Vite / Zustand
- **甘特图**: frappe-gantt
- **部署**: 单进程托管前后端，个人 PC 即可运行

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+

### 一键启动（推荐）

```bash
# Linux / macOS
chmod +x start.sh
./start.sh

# Windows
start.bat
```

启动后访问 **http://localhost:8000**，默认账号 `admin` / `admin123`。

### 手动启动

```bash
# 1. 后端
cd pmo-server
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000

# 2. 前端（另开终端）
cd pmo-web
npm install
npm run dev          # 开发模式 http://localhost:5173
# 或构建后由后端托管
npm run build
```

### 切换 PostgreSQL（可选）

编辑 `pmo-server/.env`：
```
DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/pmo
```

## 项目结构

```
pmo-platform/
├── pmo-server/           # 后端
│   ├── app/
│   │   ├── core/         # 配置、安全、数据库、依赖注入
│   │   ├── models/       # SQLAlchemy 模型（按 DDL）
│   │   └── routers/      # API 路由
│   └── requirements.txt
├── pmo-web/              # 前端
│   ├── src/
│   │   ├── api/          # API 客户端
│   │   ├── layouts/      # 布局
│   │   ├── pages/        # 页面
│   │   └── stores/       # 状态管理
│   └── package.json
├── start.sh              # Linux/macOS 启动脚本
└── start.bat             # Windows 启动脚本
```

## 数据库

默认使用 SQLite（`pmo-server/pmo.db`），首次启动自动建表并写入种子数据：
- 9 个内置角色（PMO 管理员、项目经理、部门主管等）
- 10 个项目类型（芯片设计、封装、测试等）
- 芯片设计类型的阶段+门禁模板
- 示例部门、管理员账号、演示项目

## 部署说明

本平台采用**单体架构**，后端 FastAPI 同时托管前端静态文件，无需 Nginx 反向代理：

1. 运行 `npm run build` 生成 `pmo-web/dist`
2. 启动后端 `uvicorn app.main:app`
3. 访问 `http://localhost:8000` 即可使用完整功能

如需修改端口，设置环境变量 `PORT=8080` 后运行 `start.sh`。
