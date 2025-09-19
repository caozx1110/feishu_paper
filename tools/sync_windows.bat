@echo off
REM Windows 批处理文件，用于启动 ArXiv 论文同步

echo ==========================================
echo ArXiv 论文定时同步系统 - Windows 启动器
echo ==========================================

REM 设置工作目录
cd /d "%~dp0.."

REM 检查 Python 是否可用
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Python，请确保 Python 已安装并在 PATH 中
    pause
    exit /b 1
)

REM 检查配置文件
if not exist "conf" (
    echo 错误: 配置目录不存在
    pause
    exit /b 1
)

REM 设置环境变量（可选）
set SYNC_INTERVAL=86400
set LOG_LEVEL=INFO

echo 开始执行同步...
echo.

REM 执行同步
python scripts\simple_sync.py

echo.
echo 同步完成，按任意键退出...
pause >nul
