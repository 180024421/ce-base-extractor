# Changelog

## Unreleased

### 特征码增强
- GUI「特征码」页：备注、模块过滤、进度条、后台扫描、读值验证、样本导入导出
- 同局多地址 / 重启多样本均可生成；支持「精简唯一」最短 AOB
- Profile 持久化 `signatures[]`；导出 Python / Lua / ASS 字段表 JSON
- 扫描可限制模块、跳过超大区域，避免界面卡死
- 扫描范围预设 `modules`/`heap`/`all` +「唯一即停」提前结束
- 粘贴多行地址批量采样；监控页「送特征码采样」
- chain↔AOB 对照读数；0 命中时版本漂移提醒；本地历史；导出向导；首次引导
- ASS 运行时：`mem.aob_scan` / `mem.read`；Lua 导出对接真实 API

## 0.5.3 (2026-07-06)

### 准确率 / 一致性
- GUI 实时监控：读失败时失效模块缓存，连续失败自动重连
- diff 默认 fuzzy，与交叉验证口径对齐（`--no-fuzzy` 可关闭）
- CT 导出按 `value_type` 映射 VariableType

### 性能
- 交叉验证流式 Top-N：`filter_and_rank_cross_stream`，不再全量驻内存
- key_store SQLite 批量 UPSERT（去掉逐键 SELECT）
- 单文件 `.PTR` 接入 `stream_rank` 流式管线

### CLI / 监视
- `--android-package` 传入 `export_all`
- watch 退出时 `incremental.close()`；FolderWatcher 支持 `.ptr`
- GUI 记录读数失败字段可见

## 0.5.2 (2026-07-06)

### 性能 / 架构
- **PTR mmap 流式**：`iter_ptr_chains()` 避免整文件读入内存
- **交叉验证键计数 spill**：`ChainKeyCounter` 超阈值自动落 SQLite（`cross_validate_sqlite_threshold`）
- **GUI 模块化**：`app.py` 拆为 Shell/Core/Extract/Cross/Aux mixins

### 测试
- `test_ptr_and_keystore.py`：PTR 迭代、Counter spill、SQLite backend

## 0.5.1 (2026-07-06)

### 准确率
- 交叉验证 fuzzy 与 filter 策略对齐
- Profile 快照持久化，CLI verify / scc-recheck 可用
- Live probe 类型推断（int32 vs float）
- `probe_drop_unreadable` 默认 true
- Profile migrate fuzzy 匹配
- 交叉验证 SQLite 模块预过滤
- `ProcessMemory` 模块缓存 + 精确匹配 + PID 校验

### 性能
- 单文件流式 top-N（`stream_single_file`）
- 模块统计基于流式计数

### UX / 生态
- GUI 高级选项、增量交叉监视、版本对比/复检按钮
- SCC v2（snapshots、probe 元数据）
- Lua 导出 ASS 友好模板
- Frida guest 可配置包名
- 大文件扫描进度

### 工程
- `ExtractConfig.validate()`、公共 `chain_io.iter_file_chains`
- CI：ruff format + pytest-cov
- 新增 test_v051_features 等

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
