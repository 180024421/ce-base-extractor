"""script-control-center / 自动化脚本加载 SCC 基址配置。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_bases(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    fmt = data.get("format", "")
    if not str(fmt).startswith("ce-base-extractor"):
        raise ValueError(f"非 ce-base-extractor SCC 格式: {fmt!r}")
    return data


def chain_to_reader_args(chain: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": chain["name"],
        "module": chain["module"],
        "module_offset": chain["module_offset"],
        "offsets": chain["offsets"],
        "type": chain.get("type", "int32"),
    }


def list_chain_names(path: str | Path) -> list[str]:
    return [c["name"] for c in load_bases(path).get("chains", [])]
