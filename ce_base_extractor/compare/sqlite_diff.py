from __future__ import annotations

from pathlib import Path

from ce_base_extractor.parsers.sqlite_parser import iter_sqlite_chains


def _keys_from_file(path: str | Path, ptrid: int | None) -> set[tuple]:
    return {chain.dedupe_key() for chain in iter_sqlite_chains(path, ptrid=ptrid)}


def diff_sqlite_files(
    file_a: str | Path,
    file_b: str | Path,
    ptrid: int | None = None,
) -> dict:
    set_a = _keys_from_file(file_a, ptrid)
    set_b = _keys_from_file(file_b, ptrid)
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
) -> dict:
    """N 份 SQLite 对比：统计每条链出现在多少份扫描中。"""
    if len(files) < 2:
        raise ValueError("至少需要 2 个 SQLite 文件")

    paths = [Path(f) for f in files]
    per_file: list[set[tuple]] = []
    key_counts: dict[tuple, int] = {}

    for path in paths:
        keys = _keys_from_file(path, ptrid)
        per_file.append(keys)
        for key in keys:
            key_counts[key] = key_counts.get(key, 0) + 1

    n = len(paths)
    all_keys = set().union(*per_file) if per_file else set()
    in_all = {k for k, c in key_counts.items() if c == n}
    counts_by_occurrence: dict[int, int] = {}
    for count in key_counts.values():
        counts_by_occurrence[count] = counts_by_occurrence.get(count, 0) + 1

    union_size = len(all_keys)
    return {
        "files": [str(p) for p in paths],
        "file_count": n,
        "counts_per_file": [len(s) for s in per_file],
        "union": union_size,
        "in_all": len(in_all),
        "stability_ratio": round(len(in_all) / max(union_size, 1), 4),
        "occurrence_histogram": dict(sorted(counts_by_occurrence.items())),
        "common_keys": list(in_all)[:50],
    }
