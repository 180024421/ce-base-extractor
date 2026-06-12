# CE 基址提取器 (ce-base-extractor)

从 **Cheat Engine 指针扫描** 结果一键提取稳定基址，并生成 **Python 内存读取脚本**。默认针对 **雷电模拟器**（`dnplayer.exe`）优化。

仓库：https://github.com/180024421/ce-base-extractor

## 工作流

```mermaid
flowchart LR
  A[CE 附加 dnplayer] --> B[指针扫描 + Rescan×3]
  B --> C[导出 SQLite]
  C --> D[交叉验证提取]
  D --> E[设置字段名/类型]
  E --> F[记录读数]
  F --> G[重启雷电]
  G --> H[重启验证]
  H --> I[导出 Python / SCC JSON]
  I --> J[python game_reader.py]
```

## 功能一览（v0.4）

| 功能 | 说明 |
|------|------|
| 交叉验证 | 多 SQLite 流式取交集 |
| 字段名/类型 | 自定义 gold/hp + int32/float 等 |
| **智能命名** | 一键根据模块/偏移建议字段名 |
| **实时监控** | GUI 定时刷新内存数值 |
| **游戏配置** | 保存/加载完整基址方案 |
| **一键导出全部** | py + scc + ct + json + frida + module |
| **SCC 导入** | 从 JSON 反向加载到 GUI |
| **SQLite 对比** | 两份扫描结果差异统计 |
| **Frida 脚本** | 导出 `*_frida.js` |
| **可 import 模块** | `*_memory.py` 供脚本引用 |
| 雷电多开 | 进程列表对话框选 PID |
| 重启验证 | 记录读数 → 重启 → 对比 |
| Il2Cpp 映射 | json/cs 自动建议字段名 |
| 打包 EXE | `build_exe.ps1` |

## 快速开始

```powershell
cd E:\xiangmu\ce-base-extractor
.\安装环境.cmd
.\一键启动.cmd
```

### 命令行

```powershell
# 交叉验证 + 一键导出全部格式
.\.venv\Scripts\python -m ce_base_extractor r1.sqlite --cross r2.sqlite r3.sqlite `
  --format all --game mygame -o ./mygame_export

# Frida / 可 import 模块
.\.venv\Scripts\python -m ce_base_extractor scan.sqlite --format frida --game mygame
.\.venv\Scripts\python -m ce_base_extractor scan.sqlite --format module --game mygame
```

### Python 脚本

```powershell
python mygame_reader.py --list-processes   # 雷电多开
python mygame_reader.py --pid 12345
python mygame_reader.py --chain gold
```

## 重启验证（GUI）

1. 提取结果后为字段命名（双击或「编辑字段」）
2. 点「记录读数」
3. 重启雷电模拟器
4. 点「重启验证」→ 稳定项自动标记 ✓ 并写入收藏

## 示例

见 [examples/README.md](examples/README.md)

```powershell
.\.venv\Scripts\python examples\make_sample_sqlite.py
.\.venv\Scripts\python -m ce_base_extractor examples\sample_r1.sqlite --cross examples\sample_r2.sqlite --format py --game demo
```

## 打包 EXE

```powershell
.\build_exe.ps1
# 输出: dist\CE基址提取器.exe
```

## 开发

```powershell
.\.venv\Scripts\python -m pytest tests -q
```

## 许可

仅供学习与研究。请遵守游戏服务条款与当地法律法规。
