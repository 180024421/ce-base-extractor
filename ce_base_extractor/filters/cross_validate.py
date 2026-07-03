from __future__ import annotations

from collections import Counter
from pathlib import Path

from ce_base_extractor.models import PointerChain
from ce_base_extractor.parsers.ptr_parser import load_ptr
from ce_base_extractor.parsers.sqlite_parser import iter_sqlite_chains


def _iter_file_chains(path: Path, ptrid: int | None):
    suffix = path.suffix.lower()
    if suffix in (".db", ".sqlite", ".sqlite3"):
        yield from iter_sqlite_chains(path, ptrid=ptrid)
        return
    if suffix == ".ptr":
        chains, _ = load_ptr(path)
        yield from chains
        return
    raise ValueError(f"不支持的文件: {path}")


def cross_validate_files(
    files: list[str | Path],
    min_occurrences: int = 2,
    ptrid: int | None = None,
    *,
    require_all: bool = False,
) -> tuple[list[PointerChain], dict]:
    if len(files) < min_occurrences:
        raise ValueError(f"交叉验证至少需要 {min_occurrences} 个文件")

    counter: Counter[tuple] = Counter()
    exemplar: dict[tuple, PointerChain] = {}

    for fp in files:
        path = Path(fp)
        seen_in_file: set[tuple] = set()
        for chain in _iter_file_chains(path, ptrid):
            key = chain.dedupe_key()
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
        "streaming": True,
    }
    return stable, meta
