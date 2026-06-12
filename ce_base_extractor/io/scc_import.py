from __future__ import annotations

import json
from pathlib import Path

from ce_base_extractor.models import ExtractResult, PointerChain


def import_scc_json(path: str | Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if "chains" not in data:
        raise ValueError("无效的 SCC JSON：缺少 chains 字段")
    return data


def import_scc_to_result(path: str | Path) -> ExtractResult:
    data = import_scc_json(path)
    chains: list[PointerChain] = []
    for c in data["chains"]:
        off_hex = c.get("module_offset_hex", "")
        module_offset = int(off_hex, 16) if off_hex else int(c["module_offset"])
        offsets = c.get("offsets")
        if offsets is None and "offsets_hex" in c:
            offsets = [int(x, 16) for x in c["offsets_hex"]]
        chains.append(
            PointerChain(
                module_name=c["module"],
                module_offset=module_offset,
                offsets=tuple(int(o) for o in offsets),
                score=float(c.get("score", 0)),
                source="scc-import",
                field_name=c.get("name", ""),
                value_type=c.get("type", "int32"),
                verified=bool(c.get("verified", False)),
                il2cpp_symbol=c.get("il2cpp_symbol", ""),
            )
        )
    return ExtractResult(
        chains=chains,
        total_raw=len(chains),
        total_after_filter=len(chains),
        modules_seen=sorted({c.module_name for c in chains}),
        source_file=str(path),
    )
