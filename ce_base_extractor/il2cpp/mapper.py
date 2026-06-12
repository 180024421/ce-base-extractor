from __future__ import annotations

import json
import re
from pathlib import Path

from ce_base_extractor.models import PointerChain

# 支持格式:
# 1) {"0x12345678": "PlayerData.gold"}
# 2) [{"offset": "0x12345678", "symbol": "PlayerData.gold"}]
# 3) dump.cs 简单行: // RVA: 0x12345678  PlayerData$$get_gold


def load_il2cpp_map(path: str | Path | None) -> dict[int, str]:
    if not path:
        return {}
    p = Path(path)
    if not p.is_file():
        return {}

    if p.suffix.lower() == ".json":
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {_parse_off(k): str(v) for k, v in data.items()}
        if isinstance(data, list):
            out: dict[int, str] = {}
            for item in data:
                off = _parse_off(item.get("offset") or item.get("rva"))
                sym = item.get("symbol") or item.get("name")
                if sym:
                    out[off] = str(sym)
            return out

    if p.suffix.lower() in (".cs", ".txt"):
        out: dict[int, str] = {}
        rva_re = re.compile(r"(?:RVA|Offset)\s*[:=]\s*(0x[0-9A-Fa-f]+)", re.I)
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            m = rva_re.search(line)
            if not m:
                continue
            off = int(m.group(1), 16)
            sym = line.split("//")[-1].strip() if "//" in line else line.strip()
            if sym:
                out[off] = sym
        return out

    return {}


def _parse_off(value: str | int | None) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    return int(str(value), 16) if str(value).lower().startswith("0x") else int(value)


def apply_il2cpp_hints(
    chains: list[PointerChain],
    mapping: dict[int, str],
) -> list[PointerChain]:
    if not mapping:
        return chains
    updated: list[PointerChain] = []
    for chain in chains:
        symbol = mapping.get(chain.module_offset, "")
        field_name = chain.field_name
        if symbol and not field_name:
            safe = re.sub(r"[^\w.]", "_", symbol)
            field_name = safe.replace(".", "_").lower()
        updated.append(
            PointerChain(
                module_name=chain.module_name,
                module_offset=chain.module_offset,
                offsets=chain.offsets,
                score=chain.score,
                source=chain.source,
                field_name=field_name or chain.field_name,
                value_type=chain.value_type,
                verified=chain.verified,
                il2cpp_symbol=symbol or chain.il2cpp_symbol,
            )
        )
    return updated
