# 示例

## 快速试跑（无需真实 CE 文件）

**GUI**：启动后菜单「帮助 → 无 CE 试跑示例」，或底栏「试跑示例」。

```powershell
cd E:\xiangmu\ce-base-extractor
.\.venv\Scripts\python examples\make_sample_sqlite.py
.\.venv\Scripts\python -m ce_base_extractor extract examples\sample_r1.sqlite --cross examples\sample_r2.sqlite --format py --game demo
```

日常模式默认打开「交叉验证」；勾选顶栏「高级模式」显示特征码/模块/监控/收藏。
导出后可用「ASS 交接包」交给 Auto Script Studio。

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
