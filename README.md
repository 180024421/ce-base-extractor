# CE 基址提取器 (ce-base-extractor)

从 **Cheat Engine 指针扫描** 导出结果中，一键提取稳定基址与偏移链。针对 **模拟器进程**（雷电 / 夜神 / MuMu / 蓝叠等）优化，优先 `libil2cpp.so`、`libunity.so` 等 Android 游戏模块。

## 功能

- 解析 CE 导出的 **SQLite**（推荐）与 **PTR** 文件
- 自动过滤：层级过深、偏移过大、系统 DLL、随机模块
- 模拟器模式：Android 游戏模块加权排序
- 输出 CE 地址表可直接使用的指针表达式
- 支持 GUI 拖放、CLI、导出 TXT/JSON

## 快速开始

### 1. 安装

```powershell
cd E:\xiangmu\ce-base-extractor
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

或双击 `安装环境.cmd`。

### 2. CE 侧操作

1. 附加到模拟器中的游戏进程
2. 数值扫描 → 指针扫描 → Rescan 过滤
3. 指针扫描窗口：**File → Export to sqlite database**
4. 保存为 `.sqlite` 文件

### 3. 一键提取

**GUI（推荐）**：双击 `一键启动.cmd`，拖入 `.sqlite` 文件，点击「提取基址」。

**命令行**：

```powershell
.\.venv\Scripts\python -m ce_base_extractor scan.sqlite
.\.venv\Scripts\python -m ce_base_extractor scan.sqlite -o result.json --format json --top 10
```

## 输出示例

```text
[1] libil2cpp.so+0x12345678 → +0x18 → +0x20  (score=356.0)
    CE: "libil2cpp.so"+0x12345678,0x18,0x20
```

双击结果行可复制 CE 表达式。

## 配置

编辑 `config.default.json`：

| 字段 | 默认 | 说明 |
|------|------|------|
| `max_depth` | 5 | 最大偏移层级 |
| `max_single_offset` | 4096 | 单级偏移上限 |
| `top_n` | 20 | 输出条数 |
| `emulator_mode` | true | 模拟器模块优先 |

## 模拟器模块策略

**优先**：`libil2cpp.so`、`libunity.so`、`libmain.so`、`libgame.so` 等

**降权**：`ntdll.dll`、`kernel32.dll`、`libc.so`、`libart.so` 等系统模块

**降权**：随机名临时 DLL / 过长的十六进制模块名

## 目录结构

```
ce-base-extractor/
  ce_base_extractor/   # 核心代码
  scripts/               # CE Lua 辅助脚本
  tests/                 # 单元测试
  一键启动.cmd
  安装环境.cmd
```

## 开发

```powershell
.\.venv\Scripts\python -m pytest tests -q
```

## 许可

仅供学习与研究使用。请遵守游戏服务条款与当地法律法规。
