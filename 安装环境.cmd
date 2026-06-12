@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [1/2] 创建虚拟环境...
  python -m venv .venv
)

echo [2/2] 安装依赖...
".venv\Scripts\pip" install -r requirements.txt
echo.
echo 安装完成。双击 一键启动.cmd 运行。
pause
