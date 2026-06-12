# CE 基址提取器 (ce-base-extractor)

从 **Cheat Engine 指针扫描** 结果一键提取稳定基址，并生成 **Python 内存读取脚本**。默认针对 **雷电模拟器**（`dnplayer.exe`）优化。

仓库：https://github.com/180024421/ce-base-extractor

## 功能一览

| 功能 | 说明 |
|------|------|
| SQLite / PTR 解析 | CE 导出文件一键分析 |
| 雷电模拟器预设 | 优先 `libil2cpp.so`，附加 `dnplayer.exe` |
| 多轮交叉验证 | 2～3 个 Rescan SQLite 取交集，找最稳基址 |
| 模块白名单 | GUI 勾选只看指定模块 |
| 模块统计 | 各模块指针数量与优先级 |
| 导出 Python 脚本 | 内嵌内存读取器，直接 `python game_reader.py` |
| 导出 CE 表 (.CT) | 双击导入 CE |
| 收藏历史 | 按游戏名保存已验证基址 |
| 监视导出目录 | 自动监视 `Documents\ce-exports\` |
| GUI 测试读取 | 附加雷电进程，实时验证前 5 条 |

## 快速开始

### 1. 安装

```powershell
cd E:\xiangmu\ce-base-extractor
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

或双击 `安装环境.cmd`。

### 2. CE 操作（雷电模拟器）

1. CE 附加到 `dnplayer.exe`（或游戏 Android 进程）
2. 数值扫描 → 指针扫描 → **Rescan 2～3 次**
3. 每次 Rescan 后：`File → Export to sqlite database`
4. 建议保存到 `%USERPROFILE%\Documents\ce-exports\`

### 3. 提取并生成 Python 脚本

**GUI**：双击 `一键启动.cmd`

1. 「交叉验证」页添加 2～3 个 SQLite →「交叉验证提取」
2. 「单文件提取」页 →「导出 Python 脚本」
3. 可选：勾选「监视导出目录」实现自动提取

**命令行**：

```powershell
# 单文件
.\.venv\Scripts\python -m ce_base_extractor scan.sqlite --format py --game mygame

# 交叉验证（3 个 Rescan 文件）
.\.venv\Scripts\python -m ce_base_extractor rescan1.sqlite --cross rescan2.sqlite rescan3.sqlite --format py --game mygame

# 只要 libil2cpp 模块
.\.venv\Scripts\python -m ce_base_extractor scan.sqlite --whitelist libil2cpp.so --format py
```

### 4. 运行 Python 脚本读取数据

```powershell
python mygame_reader.py
python mygame_reader.py --chain chain_1
python mygame_reader.py --list-modules
```

示例输出：

```text
chain_1: 12345  (libil2cpp.so+0x12345678)
```

## 生成的 Python 脚本说明

脚本内嵌 `ProcessMemory` 类，通过 Windows API 附加雷电进程并解析指针链：

```python
# 自动附加 dnplayer.exe
mem = ProcessMemory.auto_attach(PROCESS_NAMES)
addr = mem.resolve_chain("libil2cpp.so", 0x12345678, [0x18, 0x20])
value = mem.read_i32(addr)   # 读取 int32
```

支持类型：`int32`、`uint32`、`float`（在 CHAINS 配置中设置 `type` 字段）。

## 配置

`config.default.json` 或用户配置 `%USERPROFILE%\Documents\ce-exports\user_config.json`：

| 字段 | 默认 | 说明 |
|------|------|------|
| `preset` | `ldplayer` | 模拟器预设 |
| `max_depth` | 5 | 最大偏移层级 |
| `max_single_offset` | 4096 | 单级偏移上限 |
| `top_n` | 20 | 输出条数 |
| `cross_validate_min` | 2 | 交叉验证最少出现次数 |
| `module_blacklist` | 系统 DLL | 自动排除 |

## 推荐工作流（雷电）

```
CE 扫描 → Rescan ×3 → 各导出 SQLite
    ↓
ce-base-extractor 交叉验证提取
    ↓
导出 mygame_reader.py
    ↓
python mygame_reader.py  →  拿到游戏数值
    ↓
集成到你的自动化脚本（script-control-center 等）
```

## 开发

```powershell
.\.venv\Scripts\python -m pytest tests -q
```

## 许可

仅供学习与研究。请遵守游戏服务条款与当地法律法规。
