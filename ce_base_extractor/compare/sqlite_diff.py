from __future__ import annotations

from pathlib import Path

from ce_base_extractor.filters.fuzzy_dedupe import fuzzy_dedupe_key
from ce_base_extractor.filters.key_store import DEFAULT_SQLITE_THRESHOLD, ChainKeyCounter
from ce_base_extractor.parsers.chain_io import iter_file_chains


def _keys_from_file(
    path: str | Path,
    ptrid: int | None,
    *,
    fuzzy: bool = True,
    fuzzy_last_offset_step: int = 0x8,
) -> dict[tuple, int]:
    keys: dict[tuple, int] = {}
    for chain in iter_file_chains(path, ptrid=ptrid):
        if fuzzy:
            key = fuzzy_dedupe_key(
                chain,
                last_offset_tolerance=fuzzy_last_offset_step,
                ignore_last_offset=True,
            )
        else:
            key = chain.dedupe_key()
        keys[key] = keys.get(key, 0) + 1
    return keys


def diff_sqlite_files(
    file_a: str | Path,
    file_b: str | Path,
    ptrid: int | None = None,
    *,
    fuzzy: bool = True,
    fuzzy_last_offset_step: int = 0x8,
    sqlite_threshold: int = DEFAULT_SQLITE_THRESHOLD,
    force_sqlite_backend: bool = False,
) -> dict:
    """两份 SQLite 对比（ChainKeyCounter，与 N 文件版一致，避免大文件 OOM）。"""
    return diff_sqlite_many(
        [file_a, file_b],
        ptrid=ptrid,
        fuzzy=fuzzy,
        fuzzy_last_offset_step=fuzzy_last_offset_step,
        sqlite_threshold=sqlite_threshold,
        force_sqlite_backend=force_sqlite_backend,
    )


def diff_sqlite_many(
    files: list[str | Path],
    ptrid: int | None = None,
    *,
    fuzzy: bool = True,
    fuzzy_last_offset_step: int = 0x8,
    sqlite_threshold: int = DEFAULT_SQLITE_THRESHOLD,
    force_sqlite_backend: bool = False,
) -> dict:
    """N 份 SQLite 对比：统计每条链出现在多少份扫描中。"""
    if len(files) < 2:
        raise ValueError("至少需要 2 个 SQLite 文件")

    paths = [Path(f) for f in files]
    counter = ChainKeyCounter(
        sqlite_threshold=sqlite_threshold,
        force_sqlite=force_sqlite_backend,
    )
    per_file_counts: list[int] = []

    try:
        for path in paths:
            seen: dict[tuple, object] = {}
            for chain in iter_file_chains(path, ptrid=ptrid):
                if fuzzy:
                    key = fuzzy_dedupe_key(
                        chain,
                        last_offset_tolerance=fuzzy_last_offset_step,
                        ignore_last_offset=True,
                    )
                else:
                    key = chain.dedupe_key()
                if key not in seen:
                    seen[key] = chain
            per_file_counts.append(len(seen))
            counter.add_file_keys(seen)  # type: ignore[arg-type]

        n = len(paths)
        histogram: dict[int, int] = {}
        for _chain, count in counter.iter_items_at_least(1):
            histogram[count] = histogram.get(count, 0) + 1

        in_all = counter.count_in_all()
        union_size = counter.unique_count()
        return {
            "files": [str(p) for p in paths],
            "file_count": n,
            "counts_per_file": per_file_counts,
            "union": union_size,
            "in_all": in_all,
            "stability_ratio": round(in_all / max(union_size, 1), 4),
            "occurrence_histogram": dict(sorted(histogram.items())),
            "fuzzy": fuzzy,
            "common_keys": [],
            "key_backend": counter.backend,
        }
    finally:
        counter.close()
