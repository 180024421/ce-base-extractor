from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from ce_base_extractor.models import PointerChain

_OFFSET_COL_RE = re.compile(r"^offset(\d+)$", re.IGNORECASE)


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def _list_ptrids(conn: sqlite3.Connection) -> list[int]:
    if not _table_exists(conn, "pointerfiles"):
        return []
    rows = conn.execute("SELECT ptrid FROM pointerfiles ORDER BY ptrid").fetchall()
    return [int(r[0]) for r in rows]


def _resolve_ptrid(conn: sqlite3.Connection, ptrid: int | None) -> int:
    ids = _list_ptrids(conn)
    if not ids:
        raise ValueError("数据库中未找到 pointerfiles 表或没有任何扫描记录")
    if ptrid is None:
        return ids[-1]
    if ptrid not in ids:
        raise ValueError(f"ptrid={ptrid} 不存在，可用: {ids}")
    return ptrid


def _load_modules(conn: sqlite3.Connection, ptrid: int) -> dict[int, str]:
    if not _table_exists(conn, "modules"):
        raise ValueError("数据库缺少 modules 表，请确认由 CE 指针扫描导出")
    rows = conn.execute(
        "SELECT moduleid, name FROM modules WHERE ptrid=? ORDER BY moduleid",
        (ptrid,),
    ).fetchall()
    return {int(mid): str(name) for mid, name in rows}


def _offset_columns(conn: sqlite3.Connection) -> list[str]:
    cols = conn.execute("PRAGMA table_info(results)").fetchall()
    numbered: list[tuple[int, str]] = []
    for _cid, name, *_rest in cols:
        m = _OFFSET_COL_RE.match(name)
        if m:
            numbered.append((int(m.group(1)), name))
    numbered.sort(key=lambda x: x[0])
    return [name for _, name in numbered]


def load_sqlite(path: str | Path, ptrid: int | None = None) -> tuple[list[PointerChain], dict]:
    db_path = Path(path)
    if not db_path.is_file():
        raise FileNotFoundError(f"文件不存在: {db_path}")

    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    try:
        if not _table_exists(conn, "results"):
            raise ValueError("数据库缺少 results 表，请使用 CE 菜单 File → Export to sqlite database 导出")

        resolved_ptrid = _resolve_ptrid(conn, ptrid)
        modules = _load_modules(conn, resolved_ptrid)
        offset_cols = _offset_columns(conn)
        if not offset_cols:
            raise ValueError("results 表中没有 offset1/offset2... 列")

        select_cols = ["moduleid", "moduleoffset", "offsetcount", *offset_cols]
        sql = (
            f"SELECT {', '.join(select_cols)} FROM results "
            f"WHERE ptrid=? ORDER BY resultid"
        )
        rows = conn.execute(sql, (resolved_ptrid,)).fetchall()

        chains: list[PointerChain] = []
        for row in rows:
            module_id = int(row[0])
            module_offset = int(row[1])
            offset_count = int(row[2])
            raw_offsets = [int(v) for v in row[3:] if v is not None]
            offsets = tuple(raw_offsets[:offset_count])

            module_name = modules.get(module_id, f"<module#{module_id}>")
            chains.append(
                PointerChain(
                    module_name=module_name,
                    module_offset=module_offset,
                    offsets=offsets,
                    source="sqlite",
                )
            )

        meta = {
            "ptrid": resolved_ptrid,
            "ptrids_available": _list_ptrids(conn),
            "module_count": len(modules),
            "modules": sorted(modules.values()),
            "result_count": len(chains),
        }
        return chains, meta
    finally:
        conn.close()
