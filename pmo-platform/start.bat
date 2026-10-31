@echo off
chcp 65001 >nul
REM =============================================================
REM PMO 运维管理平台 - Windows 一键启动脚本
REM =============================================================

cd /d "%~dp0"

echo ========================================
echo   PMO 运维管理平台 - 启动
echo ========================================

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.11+
    pause
    exit /b 1
)

REM 检查 Node
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Node.js，请先安装 Node.js 18+
    pause
    exit /b 1
)

set PORT=8000

REM 后端依赖
echo [1/4] 检查后端依赖...
if not exist "pmo-server\.venv" (
    echo   创建虚拟环境...
    cd pmo-server
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt -q
    cd ..
) else (
    call pmo-server\.venv\Scripts\activate.bat
)

REM 构建前端
echo [2/4] 构建前端...
if not exist "pmo-web\dist" (
    cd pmo-web
    if not exist "node_modules" npm install
    npm run build
    cd ..
)

REM 启动
echo [3/4] 启动服务...
echo   端口: %PORT%
echo   数据库: SQLite (pmo-server\pmo.db)

taskkill /f /im uvicorn.exe >nul 2>&1
timeout /t 1 /nobreak >nul

cd pmo-server
start "PMO Server" python -m uvicorn app.main:app --host 0.0.0.0 --port %PORT%
cd ..

timeout /t 5 /nobreak >nul

echo [4/4] 启动成功！
echo.
echo   访问地址: http://localhost:%PORT%
echo   默认账号: admin / admin123
echo.
echo   关闭服务请在 PMO Server 窗口按 Ctrl+C
start "" http://localhost:%PORT%
pause
