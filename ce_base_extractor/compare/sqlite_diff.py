from __future__ import annotations

from pathlib import Path

from ce_base_extractor.filters.fuzzy_dedupe import fuzzy_dedupe_key
from ce_base_extractor.filters.key_store import DEFAULT_SQLITE_THRESHOLD, ChainKeyCounter
from ce_base_extractor.parsers.chain_io import iter_file_chains


def _keys_from_file(
    path: str | Path,
    ptrid: int | None,
    *,
    fuzzy: bool = False,
) -> dict[tuple, int]:
    keys: dict[tuple, int] = {}
    for chain in iter_file_chains(path, ptrid=ptrid):
        key = fuzzy_dedupe_key(chain, ignore_last_offset=True) if fuzzy else chain.dedupe_key()
        keys[key] = keys.get(key, 0) + 1
    return keys


def diff_sqlite_files(
    file_a: str | Path,
    file_b: str | Path,
    ptrid: int | None = None,
) -> dict:
    set_a = set(_keys_from_file(file_a, ptrid).keys())
    set_b = set(_keys_from_file(file_b, ptrid).keys())
    common = set_a & set_b
    only_a = set_a - set_b
    only_b = set_b - set_a
    return {
        "file_a": str(file_a),
        "file_b": str(file_b),
        "count_a": len(set_a),
        "count_b": len(set_b),
        "common": len(common),
        "only_a": len(only_a),
        "only_b": len(only_b),
        "stability_ratio": round(len(common) / max(len(set_a), 1), 4),
        "common_keys": list(common)[:50],
    }


def diff_sqlite_many(
    files: list[str | Path],
    ptrid: int | None = None,
    *,
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
                key = chain.dedupe_key()
                if key not in seen:
                    seen[key] = chain
            per_file_counts.append(len(seen))
            counter.add_file_keys(seen)  # type: ignore[arg-type]

        n = len(paths)
        histogram: dict[int, int] = {}
        for _chain, count in counter.items_at_least(1):
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
            "common_keys": [],
            "key_backend": counter.backend,
        }
    finally:
        counter.close()
