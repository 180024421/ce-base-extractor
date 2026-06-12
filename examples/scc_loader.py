"""script-control-center 脚本中加载 CE 基址配置的示例。"""
from __future__ import annotations

import json
from pathlib import Path


def load_bases(path: str | Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("format", "").startswith("ce-base-extractor"):
        return data
    raise ValueError("非 ce-base-extractor SCC 格式")


def chain_to_reader_args(chain: dict) -> dict:
    return {
        "name": chain["name"],
        "module": chain["module"],
        "module_offset": chain["module_offset"],
        "offsets": chain["offsets"],
        "type": chain.get("type", "int32"),
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python scc_loader.py mygame_scc.json")
        raise SystemExit(1)
    cfg = load_bases(sys.argv[1])
    print(f"游戏配置: {cfg.get('preset')}  链数: {len(cfg['chains'])}")
    for c in cfg["chains"]:
        print(chain_to_reader_args(c))
