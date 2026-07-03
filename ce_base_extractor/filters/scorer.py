from __future__ import annotations

import fnmatch

from ce_base_extractor.filters.emulator_rules import EMULATOR_HOST_PATTERNS, module_tier
from ce_base_extractor.filters.fuzzy_dedupe import merge_fuzzy_duplicates
from ce_base_extractor.filters.presets import get_preset
from ce_base_extractor.models import ExtractConfig, PointerChain


def _module_allowed(name: str, cfg: ExtractConfig) -> bool:
    lower = name.lower()
    if cfg.module_blacklist:
        for pattern in cfg.module_blacklist:
            if fnmatch.fnmatch(lower, pattern.lower()):
                return False
    if cfg.module_whitelist:
        return any(fnmatch.fnmatch(lower, p.lower()) for p in cfg.module_whitelist)
    return True


def _chain_passes(chain: PointerChain, cfg: ExtractConfig) -> bool:
    if chain.module_name == "<absolute>":
        return False
    if not _module_allowed(chain.module_name, cfg):
        return False
    if chain.depth > cfg.max_depth or chain.depth == 0:
        return False
    if any(o < 0 for o in chain.offsets):
        return False
    if any(o > cfg.max_single_offset for o in chain.offsets):
        return False
    if cfg.required_end_offset is not None and chain.offsets:
        if chain.offsets[-1] != cfg.required_end_offset:
            return False
    if module_tier(chain.module_name, cfg.emulator_mode, cfg.preset) < 0:
        return False
    return True


def _score_chain(chain: PointerChain, cfg: ExtractConfig) -> float:
    tier = module_tier(chain.module_name, cfg.emulator_mode, cfg.preset)
    score = float(tier) * 100.0

    if chain.source.startswith("cross_validate:"):
        try:
            part = chain.source.split(":", 1)[1]
            hits, total = part.split("/")
            ratio = int(hits) / max(int(total), 1)
            score += ratio * 80.0
            if int(hits) == int(total):
                score += 25.0
        except (ValueError, ZeroDivisionError):
            pass
    elif chain.score > 0:
        score += chain.score * 10.0

    score += max(0, (cfg.max_depth - chain.depth + 1)) * 8.0

    if 3 <= chain.depth <= 5:
        score += 12.0

    avg_offset = sum(chain.offsets) / len(chain.offsets)
    if avg_offset < 0x100:
        score += 15.0
    elif avg_offset < 0x400:
        score += 8.0
    elif avg_offset > 0x8000:
        score -= 10.0

    if chain.offsets and all(o % 8 == 0 for o in chain.offsets):
        score += 10.0
    elif chain.offsets and chain.offsets[-1] % 8 == 0:
        score += 5.0

    if chain.module_offset > 0x00FFFFFF:
        score -= 20.0
    elif chain.module_offset > 0x00FFFFFF // 4:
        score -= 8.0

    lower = chain.module_name.lower()
    if any(p.search(lower) for p in EMULATOR_HOST_PATTERNS):
        score -= 15.0

    preset = get_preset(cfg.preset) if cfg.emulator_mode else None
    if preset:
        for bonus_mod in preset.score_bonus_modules:
            if bonus_mod.lower() in lower:
                score += 30.0
                break
        for pref in preset.preferred_modules:
            if pref.lower() in lower:
                score += 10.0

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
                field_name=chain.field_name,
                value_type=chain.value_type,
                verified=chain.verified,
                il2cpp_symbol=chain.il2cpp_symbol,
            )
        )

    if cfg.fuzzy_dedupe and len(filtered) > 1:
        filtered = merge_fuzzy_duplicates(
            filtered,
            last_offset_tolerance=cfg.fuzzy_last_offset_step,
        )

    filtered.sort(key=lambda c: (-c.score, c.depth, c.module_name.lower()))
    return filtered[: cfg.top_n]
