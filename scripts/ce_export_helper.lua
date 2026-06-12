--[[
  CE 指针扫描 → 表 → 脚本 → Execute Script
  雷电模拟器：导出 SQLite 到固定目录，供 ce-base-extractor 自动监视
]]

local exportDir = os.getenv("USERPROFILE") .. "\\Documents\\ce-exports\\"
os.execute('mkdir "' .. exportDir .. '" 2>nul')

local stamp = os.date("%Y%m%d_%H%M%S")
local suggested = exportDir .. "ldplayer_scan_" .. stamp .. ".sqlite"

showMessage(
  "【雷电模拟器 · CE 导出指引】\n\n" ..
  "1. 指针扫描窗口 → File → Export to sqlite database\n" ..
  "2. 建议保存到：\n" .. suggested .. "\n\n" ..
  "3. 打开 ce-base-extractor，勾选「监视导出目录」\n" ..
  "   或拖入该文件 → 导出 Python 脚本\n\n" ..
  "4. 运行生成的 xxx_reader.py 读取游戏数据"
)
