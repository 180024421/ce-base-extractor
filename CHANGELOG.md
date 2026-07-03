# Changelog

## 0.5.0 (2026-07-03)

### 准确率
- 在线探针：Top N 链自动 attach 验证可读性，可读加分、失败降权
- 交叉验证加权：3/3 优先于 2/3，支持 `cross_validate_require_all`
- 模糊去重：末 offset 容差合并结构相似链
- 打分增强：8 字节对齐、深度 3–5、模拟器宿主模块减分
- SQLite 按 preset 优选模块 `moduleid` 预过滤

### 工作流 / 生态
- CE SOP 首次向导步骤补全
- Lua 导出（Auto Script Studio 读链模板）
- SCC 定时复检 CLI：`scc-recheck`
- Profile 版本化与 `profile-migrate` 对比迁移
- watch 增量交叉验证 `--incremental-cross`

### 深度能力
- Il2CppDumper `script.json` 末 offset 反查字段
- Frida guest / ADB maps 读取骨架
- 一键导出含 Lua + Frida guest

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
