--[[
  CE → 表 → 脚本 → Execute Script
  雷电：导出 SQLite 并复制建议路径到剪贴板
]]

local exportDir = os.getenv("USERPROFILE") .. "\\Documents\\ce-exports\\"
os.execute('mkdir "' .. exportDir .. '" 2>nul')

local stamp = os.date("%Y%m%d_%H%M%S")
local suggested = exportDir .. "ldplayer_scan_" .. stamp .. ".sqlite"

if writeToClipboard then
  writeToClipboard(suggested)
end

local clipNote = ""
if writeToClipboard then
  clipNote = "\n\n（路径已复制到剪贴板）"
end

showMessage(
  "【雷电 · CE 导出】\n\n" ..
  "File → Export to sqlite database\n" ..
  "保存到:\n" .. suggested .. clipNote .. "\n\n" ..
  "然后在 ce-base-extractor 中:\n" ..
  "· 交叉验证提取\n" ..
  "· 设置字段名后导出 Python 脚本"
)
