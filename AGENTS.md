# AGENTS.md — ce-base-extractor

CE 指针扫描 → 稳定基址 → Python/Frida/SCC 导出工具，默认优化雷电模拟器。

## 模块地图

| 模块 | 路径 | 职责 |
|------|------|------|
| 流水线 | `pipeline.py` | 加载配置、extract、交叉验证入口 |
| 解析 | `parsers/sqlite_parser.py`, `ptr_parser.py` | CE SQLite / PTR |
| 过滤 | `filters/scorer.py`, `cross_validate.py` | 评分、交集 |
| 运行时 | `runtime/win_memory.py`, `standalone_reader.py` | Windows 读内存 |
| 导出 | `export/python_script.py`, `scc_export.py`, … | 多格式导出 |
| GUI | `gui/` | Tkinter 主界面（含「特征码」页） |
| 特征码 | `signature/` | 多样本对比生成 AOB + 进程扫描验证 |
| 集成 | `integrations/scc.py` | script-control-center 加载 |

## 开发

```powershell
.\安装环境.cmd
.\.venv\Scripts\pip install -r requirements-dev.txt
pytest tests -q
ruff check .
```

## 约定

- 导出脚本的 ProcessMemory 以 `runtime/standalone_reader.py` 为唯一内嵌源
- 用户数据目录：`%USERPROFILE%\Documents\ce-exports\`
- 配置：`config.default.json` + 用户 `user_config.json`
- 打包 EXE 时 `pipeline._bundle_dir()` 读取 `sys._MEIPASS`

## CLI

```powershell
python -m ce_base_extractor extract scan.sqlite --cross r2.sqlite --format all --game mygame
python -m ce_base_extractor diff r1.sqlite r2.sqlite r3.sqlite
python -m ce_base_extractor watch --auto-extract
python -m ce_base_extractor import-scc mygame_scc.json --format py
python -m ce_base_extractor verify --profile mygame
```

## 测试

- 不依赖真实 CE 进程或模拟器
- 使用 `tests/conftest.py` 内存 SQLite fixture
