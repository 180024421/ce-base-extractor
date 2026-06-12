from __future__ import annotations

from collections import defaultdict

from ce_base_extractor.filters.emulator_rules import module_tier
from ce_base_extractor.models import PointerChain


def compute_module_stats(
    chains: list[PointerChain],
    emulator_mode: bool = True,
) -> list[dict]:
    buckets: dict[str, list[PointerChain]] = defaultdict(list)
    for chain in chains:
        buckets[chain.module_name].append(chain)

    stats: list[dict] = []
    for name, items in buckets.items():
        depths = [c.depth for c in items]
        stats.append(
            {
                "module": name,
                "count": len(items),
                "tier": module_tier(name, emulator_mode),
                "avg_depth": round(sum(depths) / len(depths), 2),
                "min_depth": min(depths),
                "max_depth": max(depths),
            }
        )

    stats.sort(key=lambda s: (-s["tier"], -s["count"], s["module"].lower()))
    return stats
