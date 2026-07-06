"""从 CE 导出文件流式读取指针链（公共 API）。"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from ce_base_extractor.models import PointerChain
from ce_base_extractor.parsers.ptr_parser import load_ptr
from ce_base_extractor.parsers.sqlite_parser import iter_sqlite_chains


def iter_file_chains(
    path: str | Path,
    ptrid: int | None = None,
    *,
    module_ids: set[int] | None = None,
) -> Iterator[PointerChain]:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in (".db", ".sqlite", ".sqlite3"):
        yield from iter_sqlite_chains(path, ptrid=ptrid, module_ids=module_ids)
        return
    if suffix == ".ptr":
        chains, _ = load_ptr(path)
        yield from chains
        return
    raise ValueError(f"不支持的文件: {path}")
