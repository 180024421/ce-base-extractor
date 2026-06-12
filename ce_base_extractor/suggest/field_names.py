from __future__ import annotations

import re

from ce_base_extractor.models import PointerChain

_KNOWN_END_OFFSETS: dict[int, str] = {
    0x0: "root",
    0x10: "field_10",
    0x18: "field_18",
    0x20: "value",
    0x28: "count",
    0x30: "data",
}


def suggest_field_names(chains: list[PointerChain]) -> list[PointerChain]:
    used: set[str] = set()
    result: list[PointerChain] = []

    for i, chain in enumerate(chains, 1):
        if chain.field_name.strip():
            result.append(chain)
            used.add(chain.field_name)
            continue

        name = _guess_name(chain, i)
        while name in used:
            name = f"{name}_{i}"
        used.add(name)

        result.append(
            PointerChain(
                module_name=chain.module_name,
                module_offset=chain.module_offset,
                offsets=chain.offsets,
                score=chain.score,
                source=chain.source,
                field_name=name,
                value_type=_guess_type(chain),
                verified=chain.verified,
                il2cpp_symbol=chain.il2cpp_symbol,
            )
        )
    return result


def _guess_name(chain: PointerChain, index: int) -> str:
    if chain.il2cpp_symbol:
        safe = re.sub(r"[^\w.]", "_", chain.il2cpp_symbol)
        return safe.replace(".", "_").lower()

    mod = chain.module_name.lower()
    if "il2cpp" in mod:
        base = "il2cpp"
    elif "unity" in mod:
        base = "unity"
    else:
        base = re.sub(r"[^\w]", "_", Path_stem(mod))

    if chain.offsets:
        last = chain.offsets[-1]
        hint = _KNOWN_END_OFFSETS.get(last, f"off_{last:X}")
        return f"{base}_{hint}"
    return f"{base}_{index}"


def _guess_type(chain: PointerChain) -> str:
    if not chain.offsets:
        return "int32"
    last = chain.offsets[-1]
    if last % 8 == 0 and chain.depth >= 3:
        return "int64"
    return "int32"


def Path_stem(name: str) -> str:
    if "." in name:
        return name.rsplit(".", 1)[0]
    return name
