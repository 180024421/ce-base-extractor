from __future__ import annotations

from ce_base_extractor.filters.emulator_rules import module_tier
from ce_base_extractor.models import ExtractConfig, PointerChain


def _chain_passes(chain: PointerChain, cfg: ExtractConfig) -> bool:
    if chain.module_name == "<absolute>":
        return False
    if chain.depth > cfg.max_depth:
        return False
    if chain.depth == 0:
        return False
    if any(o < 0 for o in chain.offsets):
        return False
    if any(o > cfg.max_single_offset for o in chain.offsets):
        return False
    tier = module_tier(chain.module_name, cfg.emulator_mode)
    if tier < 0:
        return False
    return True


def _score_chain(chain: PointerChain, cfg: ExtractConfig) -> float:
    tier = module_tier(chain.module_name, cfg.emulator_mode)
    score = float(tier) * 100.0

    # 偏移链越短越稳定
    score += max(0, (cfg.max_depth - chain.depth + 1)) * 8.0

    # 偏移值越小通常越像结构体字段而非堆指针
    avg_offset = sum(chain.offsets) / len(chain.offsets)
    if avg_offset < 0x100:
        score += 15.0
    elif avg_offset < 0x400:
        score += 8.0
    elif avg_offset > 0x8000:
        score -= 10.0

    # 模块内偏移过大时降权（更像堆地址误标为模块偏移）
    if chain.module_offset > 0x00FFFFFF:
        score -= 20.0

    # 模拟器场景：libil2cpp / libunity 额外加分
    lower = chain.module_name.lower()
    if cfg.emulator_mode:
        if "libil2cpp" in lower:
            score += 25.0
        elif "libunity" in lower:
            score += 20.0
        elif "libmain" in lower or "libgame" in lower:
            score += 15.0

    return score


def filter_and_rank(
    chains: list[PointerChain],
    cfg: ExtractConfig,
) -> list[PointerChain]:
    filtered: list[PointerChain] = []
    seen: set[tuple] = set()

    for chain in chains:
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
            )
        )

    filtered.sort(key=lambda c: (-c.score, c.depth, c.module_name.lower()))
    return filtered[: cfg.top_n]
