# 示例

## 快速试跑（无需真实 CE 文件）

```powershell
cd E:\xiangmu\ce-base-extractor
.\.venv\Scripts\python -m pytest tests -q
```

## 使用示例 SQLite

测试套件 `tests/conftest.py` 中有内存 SQLite fixture，等价于最小 CE 导出。

```powershell
# 生成交叉验证示例库
.\.venv\Scripts\python examples\make_sample_sqlite.py

# 提取并生成 Python 脚本
.\.venv\Scripts\python -m ce_base_extractor examples\sample_r1.sqlite --cross examples\sample_r2.sqlite --format py --game demo
python demo_reader.py --list-processes
```

## Il2Cpp 映射

将 `demo_il2cpp_map.json` 路径填入 GUI「Il2Cpp 映射」，可按 RVA 自动建议字段名。

## SCC 集成

导出 `*_bases_scc.json` 后，在 script-control-center 脚本中读取：

```python
import json
from pathlib import Path

data = json.loads(Path("mygame_bases_scc.json").read_text(encoding="utf-8"))
for chain in data["chains"]:
    print(chain["name"], chain["module"], chain["module_offset_hex"])
```
