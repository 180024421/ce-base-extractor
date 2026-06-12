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

## 功能一览（v0.3）

| 功能 | 说明 |
|------|------|
| 交叉验证 | 多 SQLite 流式取交集 |
| 字段名/类型 | gold、hp + int32/float/int64 等 |
| 雷电多开 | `--list-processes` / GUI 选 PID |
| 重启验证 | 记录读数 → 重启 → 对比稳定性 |
| Python 脚本 | 内嵌读取器，可直接运行 |
| SCC JSON | 供 script-control-center 导入 |
| Il2Cpp 映射 | json/cs 自动建议字段名 |
| 压缩 PTR | 支持 compressed PTR 解析 |
| 指针宽度 | 4 / 8 字节可切换 |
| 首次向导 | 启动时快速指引 |
| 打包 EXE | `build_exe.ps1` |

## 快速开始

```powershell
cd E:\xiangmu\ce-base-extractor
.\安装环境.cmd
.\一键启动.cmd
```

### 命令行

```powershell
# 交叉验证 + Python + 指定 PID
.\.venv\Scripts\python -m ce_base_extractor r1.sqlite --cross r2.sqlite r3.sqlite `
  --format py --game mygame --pid 12345 --pointer-size 8

# Il2Cpp 映射 + SCC 导出
.\.venv\Scripts\python -m ce_base_extractor scan.sqlite --il2cpp-map dump.json --format scc
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
