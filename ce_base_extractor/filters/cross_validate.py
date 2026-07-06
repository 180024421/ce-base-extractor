from __future__ import annotations

from pathlib import Path

from ce_base_extractor.filters.fuzzy_dedupe import fuzzy_dedupe_key
from ce_base_extractor.filters.key_store import DEFAULT_SQLITE_THRESHOLD, ChainKeyCounter
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
    sqlite_threshold: int = DEFAULT_SQLITE_THRESHOLD,
    force_sqlite_backend: bool = False,
) -> tuple[list[PointerChain], dict]:
    if len(files) < min_occurrences:
        raise ValueError(f"交叉验证至少需要 {min_occurrences} 个文件")

    def _key(chain: PointerChain) -> tuple:
        if fuzzy:
            return fuzzy_dedupe_key(
                chain,
                last_offset_tolerance=fuzzy_last_offset_step,
                ignore_last_offset=True,
            )
        return chain.dedupe_key()

    counter = ChainKeyCounter(
        sqlite_threshold=sqlite_threshold,
        force_sqlite=force_sqlite_backend,
    )

    try:
        for fp in files:
            path = Path(fp)
            seen_in_file: dict[tuple, PointerChain] = {}
            for chain in iter_file_chains(path, ptrid=ptrid, module_ids=module_ids):
                key = _key(chain)
                if key not in seen_in_file:
                    seen_in_file[key] = chain
            counter.add_file_keys(seen_in_file)

        total_files = len(files)
        min_hits = total_files if require_all else min_occurrences

        stable: list[PointerChain] = []
        for chain, count in counter.items_at_least(min_hits):
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

        in_all = counter.count_in_all()
        meta = {
            "files": [str(Path(f)) for f in files],
            "min_occurrences": min_occurrences,
            "unique_keys": counter.unique_count(),
            "stable_keys": len(stable),
            "in_all": in_all,
            "stability_ratio": round(in_all / max(counter.unique_count(), 1), 4),
            "require_all": require_all,
            "fuzzy": fuzzy,
            "module_prefilter": sorted(module_ids) if module_ids else None,
            "streaming": True,
            "key_backend": counter.backend,
        }
        return stable, meta
    finally:
        counter.close()
