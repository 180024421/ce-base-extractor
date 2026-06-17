# 打包为单文件 EXE（需先安装 pyinstaller）
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    python -m venv .venv
    .\.venv\Scripts\pip install -r requirements.txt pyinstaller
}

.\.venv\Scripts\pip install pyinstaller -q
.\.venv\Scripts\pyinstaller --noconfirm --onefile --windowed `
    --name "CE基址提取器" `
    --add-data "config.default.json;." `
    --hidden-import ce_base_extractor.runtime.standalone_reader `
    --collect-submodules ce_base_extractor `
    -m ce_base_extractor

Write-Host "完成: dist\CE基址提取器.exe"
