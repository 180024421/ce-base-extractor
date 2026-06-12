from __future__ import annotations

from pathlib import Path

from ce_base_extractor.parsers.sqlite_parser import iter_sqlite_chains


def diff_sqlite_files(
    file_a: str | Path,
    file_b: str | Path,
    ptrid: int | None = None,
) -> dict:
    set_a: set[tuple] = set()
    set_b: set[tuple] = set()

    for chain in iter_sqlite_chains(file_a, ptrid=ptrid):
        set_a.add(chain.dedupe_key())
    for chain in iter_sqlite_chains(file_b, ptrid=ptrid):
        set_b.add(chain.dedupe_key())

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
