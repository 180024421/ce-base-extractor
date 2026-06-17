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

## 功能一览（v0.4.1）

| 功能 | 说明 |
|------|------|
| 交叉验证 | 多 SQLite 流式取交集 + 稳定率 |
| 字段名/类型 | 自定义 gold/hp + int32/float 等 |
| **智能命名** | 模块/偏移/Il2Cpp + 常见字段词典 |
| **实时监控** | GUI 定时刷新，数值变化高亮 |
| **游戏配置** | 保存/加载完整基址方案 |
| **一键导出全部** | py + scc + ct + json + frida + module |
| **SCC 集成** | `integrations.scc` 供 script-control-center 加载 |
| **SQLite 对比** | 2～N 份扫描差异与稳定率 |
| **CLI 子命令** | diff / verify / watch / import-scc |
| **Frida 脚本** | 导出 `*_frida.js`（含模拟器说明） |
| 重启验证 | 以指针链可读为主，数值变化仅提示 |
| 打包 EXE | `build_exe.ps1`（支持 frozen 配置路径） |

## 快速开始

```powershell
cd E:\xiangmu\ce-base-extractor
.\安装环境.cmd
.\一键启动.cmd
```

### 命令行

```powershell
# 向后兼容：直接传 SQLite
.\.venv\Scripts\python -m ce_base_extractor r1.sqlite --cross r2.sqlite r3.sqlite `
  --format all --game mygame -o ./mygame_export

# 子命令
.\.venv\Scripts\python -m ce_base_extractor diff r1.sqlite r2.sqlite r3.sqlite
.\.venv\Scripts\python -m ce_base_extractor watch --auto-extract
.\.venv\Scripts\python -m ce_base_extractor import-scc mygame_scc.json --format py
.\.venv\Scripts\python -m ce_base_extractor verify --profile mygame
```

### Python 脚本

```powershell
python mygame_reader.py --list-processes   # 雷电多开
python mygame_reader.py --pid 12345
python mygame_reader.py --chain gold
```

### SCC 集成

```python
from ce_base_extractor.integrations.scc import load_bases, chain_to_reader_args

cfg = load_bases("mygame_scc.json")
for chain in cfg["chains"]:
    print(chain_to_reader_args(chain))
```

## 重启验证（GUI）

1. 提取结果后为字段命名（双击或「编辑字段」）
2. 点「记录读数」
3. 重启雷电模拟器
4. 点「重启验证」→ **链可读**即标记 ✓（金币变化会提示但不判失败）

## 故障排查

见 [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

## 开发

```powershell
pip install -r requirements-dev.txt
pytest tests -q
ruff check .
```

Agent 指南见 [AGENTS.md](AGENTS.md)

## 许可

MIT · 仅供学习与研究。请遵守游戏服务条款与当地法律法规。
