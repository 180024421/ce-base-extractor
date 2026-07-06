from __future__ import annotations

from collections import Counter
from pathlib import Path

from ce_base_extractor.filters.fuzzy_dedupe import fuzzy_dedupe_key
from ce_base_extractor.models import PointerChain
from ce_base_extractor.parsers.chain_io import iter_file_chains


def cross_validate_files(
    files: list[str | Path],
    min_occurrences: int = 2,
    ptrid: int | None = None,
    *,
    require_all: bool = False,
    module_ids: set[int] | None = None,
    fuzzy: bool = True,
    fuzzy_last_offset_step: int = 0x8,
) -> tuple[list[PointerChain], dict]:
    if len(files) < min_occurrences:
        raise ValueError(f"交叉验证至少需要 {min_occurrences} 个文件")

    counter: Counter[tuple] = Counter()
    exemplar: dict[tuple, PointerChain] = {}

    def _key(chain: PointerChain) -> tuple:
        if fuzzy:
            return fuzzy_dedupe_key(
                chain,
                last_offset_tolerance=fuzzy_last_offset_step,
                ignore_last_offset=True,
            )
        return chain.dedupe_key()

    for fp in files:
        path = Path(fp)
        seen_in_file: set[tuple] = set()
        for chain in iter_file_chains(path, ptrid=ptrid, module_ids=module_ids):
            key = _key(chain)
            if key in seen_in_file:
                continue
            seen_in_file.add(key)
            counter[key] += 1
            if key not in exemplar:
                exemplar[key] = chain

    total_files = len(files)
    min_hits = total_files if require_all else min_occurrences

    stable: list[PointerChain] = []
    for key, count in counter.items():
        if count >= min_hits:
            chain = exemplar[key]
            stable.append(
                PointerChain(
                    module_name=chain.module_name,
                    module_offset=chain.module_offset,
                    offsets=chain.offsets,
                    score=float(count),
                    source=f"cross_validate:{count}/{total_files}",
                )
            )

    stable.sort(
        key=lambda c: (
            -int(c.source.split(":")[1].split("/")[0]) if ":" in c.source else 0,
            c.module_name.lower(),
        )
    )

    in_all = sum(1 for c in counter.values() if c == total_files)
    meta = {
        "files": [str(Path(f)) for f in files],
        "min_occurrences": min_occurrences,
        "unique_keys": len(counter),
        "stable_keys": len(stable),
        "in_all": in_all,
        "stability_ratio": round(in_all / max(len(counter), 1), 4),
        "require_all": require_all,
        "fuzzy": fuzzy,
        "module_prefilter": sorted(module_ids) if module_ids else None,
        "streaming": True,
    }
    return stable, meta
