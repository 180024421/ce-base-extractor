from __future__ import annotations

from collections import Counter
from pathlib import Path

from ce_base_extractor.models import ExtractConfig, PointerChain
from ce_base_extractor.parsers.ptr_parser import load_ptr
from ce_base_extractor.parsers.sqlite_parser import load_sqlite


def _load_file(path: Path, ptrid: int | None) -> list[PointerChain]:
    suffix = path.suffix.lower()
    if suffix in (".db", ".sqlite", ".sqlite3"):
        chains, _ = load_sqlite(path, ptrid=ptrid)
        return chains
    if suffix == ".ptr":
        chains, _ = load_ptr(path)
        return chains
    raise ValueError(f"不支持的文件: {path}")


def cross_validate_files(
    files: list[str | Path],
    min_occurrences: int = 2,
    ptrid: int | None = None,
) -> tuple[list[PointerChain], dict]:
    if len(files) < min_occurrences:
        raise ValueError(f"交叉验证至少需要 {min_occurrences} 个文件")

    counter: Counter[tuple] = Counter()
    exemplar: dict[tuple, PointerChain] = {}

    for fp in files:
        path = Path(fp)
        for chain in _load_file(path, ptrid):
            key = chain.dedupe_key()
            counter[key] += 1
            if key not in exemplar:
                exemplar[key] = chain

    stable: list[PointerChain] = []
    for key, count in counter.items():
        if count >= min_occurrences:
            chain = exemplar[key]
            stable.append(
                PointerChain(
                    module_name=chain.module_name,
                    module_offset=chain.module_offset,
                    offsets=chain.offsets,
                    score=float(count),
                    source=f"cross_validate:{count}/{len(files)}",
                )
            )

    meta = {
        "files": [str(Path(f)) for f in files],
        "min_occurrences": min_occurrences,
        "unique_keys": len(counter),
        "stable_keys": len(stable),
    }
    return stable, meta
