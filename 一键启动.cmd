@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo 未检测到虚拟环境，正在安装...
  call "%~dp0安装环境.cmd"
)

".venv\Scripts\python.exe" -m ce_base_extractor --gui
