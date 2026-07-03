"""指针链模糊去重：末 offset 容差、结构相似合并。"""

from __future__ import annotations

from ce_base_extractor.models import PointerChain


def fuzzy_dedupe_key(
    chain: PointerChain,
    *,
    last_offset_tolerance: int = 0x8,
    ignore_last_offset: bool = False,
) -> tuple:
    offsets = chain.offsets
    if ignore_last_offset and len(offsets) > 1:
        offsets = offsets[:-1]
    elif last_offset_tolerance > 0 and offsets:
        last = offsets[-1]
        bucket = last - (last % max(last_offset_tolerance, 1))
        offsets = (*offsets[:-1], bucket)
    return (
        chain.module_name.lower(),
        chain.module_offset,
        offsets,
    )


def merge_fuzzy_duplicates(
    chains: list[PointerChain],
    *,
    last_offset_tolerance: int = 0x8,
) -> list[PointerChain]:
    """合并结构相似的链，保留得分最高的一条。"""
    best: dict[tuple, PointerChain] = {}
    for chain in chains:
        key = fuzzy_dedupe_key(
            chain,
            last_offset_tolerance=last_offset_tolerance,
            ignore_last_offset=True,
        )
        prev = best.get(key)
        if prev is None or chain.score > prev.score:
            best[key] = chain
    return list(best.values())
