# Changelog

## 0.4.1 (2025-06-17)

### 改进
- 消除 `standalone_reader.py` 与导出脚本的内嵌代码重复
- 重启验证以「指针链可读」为主，数值变化仅作提示
- SQLite 对比支持 N 份文件与稳定率统计
- CLI 新增 `diff` / `verify` / `watch` / `import-scc` 子命令
- GUI：提取进度条、监控数值变化高亮、交叉验证稳定率显示
- 智能命名增加常见游戏字段词典（gold/hp/exp 等）
- PyInstaller 打包支持 `sys._MEIPASS` 读取默认配置
- 新增 SCC 集成模块 `ce_base_extractor.integrations.scc`
- 补充测试、CI、文档（AGENTS.md、故障排查）

## 0.4.0
- 实时监控、游戏配置、批量导出、Frida/SCC 导入与智能命名

## 0.3.0
- 字段自定义、多开选进程、重启验证、SCC/Il2Cpp、压缩 PTR 与打包
