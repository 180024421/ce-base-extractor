--[[
  CE 指针扫描窗口 → 表 → 脚本 → Execute Script
  作用：提示导出 SQLite 的路径，便于拖入 ce-base-extractor
]]

local exportDir = os.getenv("USERPROFILE") .. "\\Documents\\ce-exports\\"
os.execute('mkdir "' .. exportDir .. '" 2>nul')

showMessage(
  "请在指针扫描窗口使用：\n" ..
  "File → Export to sqlite database\n\n" ..
  "建议保存到：\n" .. exportDir .. "\n\n" ..
  "然后将 .sqlite 文件拖入 CE 基址提取器。"
)
