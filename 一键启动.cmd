@echo off
chcp 65001 >nul
cd /d "%~dp0"
setlocal EnableExtensions

if not exist ".venv\Scripts\python.exe" (
  echo 未检测到虚拟环境，正在安装...
  call "%~dp0安装环境.cmd"
  if errorlevel 1 (
    echo [错误] 环境安装失败，无法启动
    pause
    exit /b 1
  )
)

if not exist ".venv\Scripts\python.exe" (
  echo [错误] 仍未找到 .venv\Scripts\python.exe
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -m ce_base_extractor --gui
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
  echo.
  echo [错误] 程序异常退出，代码: %EXIT_CODE%
  pause
)

endlocal & exit /b %EXIT_CODE%
