"""流式过滤与 Top-N 排序，避免大 SQLite 全量进内存。"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterator
from typing import Any

from ce_base_extractor.filters.fuzzy_dedupe import merge_fuzzy_duplicates
from ce_base_extractor.filters.scorer import _chain_passes, _score_chain
from ce_base_extractor.models import ExtractConfig, PointerChain


def filter_and_rank_stream(
    chain_iter: Iterator[PointerChain],
    cfg: ExtractConfig,
    *,
    on_progress: Callable[[int], None] | None = None,
    progress_interval: int = 5000,
    max_buffer: int | None = None,
) -> tuple[list[PointerChain], int, dict[str, int]]:
    buf_cap = max_buffer or max(cfg.top_n * 20, 500)
    seen: set[tuple] = set()
    module_counts: dict[str, int] = defaultdict(int)
    filtered: list[PointerChain] = []
    total = 0

    for chain in chain_iter:
        total += 1
        if on_progress and total % progress_interval == 0:
            on_progress(total)
        module_counts[chain.module_name] += 1
        if not _chain_passes(chain, cfg):
            continue
        key = chain.dedupe_key()
        if cfg.dedupe and key in seen:
            continue
        seen.add(key)
        score = _score_chain(chain, cfg)
        if score < cfg.min_score:
            continue
        filtered.append(
            PointerChain(
                module_name=chain.module_name,
                module_offset=chain.module_offset,
                offsets=chain.offsets,
                score=score,
                source=chain.source,
                field_name=chain.field_name,
                value_type=chain.value_type,
                verified=chain.verified,
                il2cpp_symbol=chain.il2cpp_symbol,
            )
        )
        if len(filtered) > buf_cap:
            filtered.sort(key=lambda c: (-c.score, c.depth, c.module_name.lower()))
            filtered = filtered[:buf_cap]

    if cfg.fuzzy_dedupe and len(filtered) > 1:
        filtered = merge_fuzzy_duplicates(
            filtered,
            last_offset_tolerance=cfg.fuzzy_last_offset_step,
        )

    filtered.sort(key=lambda c: (-c.score, c.depth, c.module_name.lower()))
    return filtered[: cfg.top_n], total, dict(module_counts)


def module_stats_from_counts(
    module_counts: dict[str, int],
    emulator_mode: bool = True,
) -> list[dict[str, Any]]:
    from ce_base_extractor.filters.emulator_rules import module_tier

    stats = [
        {
            "module": name,
            "count": count,
            "tier": module_tier(name, emulator_mode),
            "avg_depth": 0,
            "min_depth": 0,
            "max_depth": 0,
        }
        for name, count in module_counts.items()
    ]
    stats.sort(key=lambda s: (-s["tier"], -s["count"], s["module"].lower()))
    return stats
