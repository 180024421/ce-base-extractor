@echo off
chcp 65001 >nul
cd /d "%~dp0"
setlocal EnableExtensions

echo ========================================
echo   CE 基址提取器 · 安装环境
echo ========================================
echo.

set "PY="
where py >nul 2>&1
if not errorlevel 1 (
  py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
  if not errorlevel 1 set "PY=py -3"
)
if not defined PY (
  where python >nul 2>&1
  if not errorlevel 1 (
    python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
    if not errorlevel 1 set "PY=python"
  )
)

if not defined PY (
  echo [错误] 未找到 Python 3.10+。
  echo.
  echo 请先安装 Python 3.10 或更高版本，并勾选「Add python.exe to PATH」：
  echo   https://www.python.org/downloads/
  echo.
  echo 安装后重新打开本窗口，再运行 安装环境.cmd
  pause
  exit /b 1
)

echo [0/2] 使用解释器: %PY%
%PY% -c "import sys; print('  Python', sys.version.split()[0])"
if errorlevel 1 (
  echo [错误] Python 无法启动
  pause
  exit /b 1
)

%PY% -c "import tkinter" >nul 2>&1
if errorlevel 1 (
  echo [错误] 当前 Python 缺少 Tkinter（GUI 依赖）。
  echo 请重装官方 Python 安装包，并确保勾选 tcl/tk。
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/2] 创建虚拟环境...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo [错误] 创建虚拟环境失败
    pause
    exit /b 1
  )
) else (
  echo [1/2] 虚拟环境已存在，跳过创建
)

echo [2/2] 安装依赖...
".venv\Scripts\python.exe" -m pip install -q --upgrade pip
if errorlevel 1 (
  echo [错误] 升级 pip 失败
  pause
  exit /b 1
)
".venv\Scripts\pip.exe" install -r requirements.txt
if errorlevel 1 (
  echo [错误] 依赖安装失败，请检查网络后重试
  pause
  exit /b 1
)

echo.
echo 安装完成。双击 一键启动.cmd 运行。
pause
endlocal
exit /b 0
