from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


@pytest.fixture
def sample_sqlite(tmp_path: Path) -> Path:
    db = tmp_path / "sample.sqlite"
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE pointerfiles (ptrid INTEGER PRIMARY KEY, name TEXT, maxlevel INTEGER)"
    )
    conn.execute(
        "INSERT INTO pointerfiles VALUES (1, 'test-scan', 4)"
    )
    conn.execute(
        "CREATE TABLE modules (ptrid INTEGER, moduleid INTEGER, name TEXT, "
        "PRIMARY KEY (ptrid, moduleid))"
    )
    modules = [
        (1, 0, "dnplayer.exe"),
        (1, 1, "libil2cpp.so"),
        (1, 2, "ntdll.dll"),
    ]
    conn.executemany("INSERT INTO modules VALUES (?, ?, ?)", modules)
    conn.execute(
        "CREATE TABLE results ("
        "ptrid INTEGER, resultid INTEGER, offsetcount INTEGER, "
        "moduleid INTEGER, moduleoffset BIGINT, "
        "offset1 INTEGER, offset2 INTEGER, offset3 INTEGER, offset4 INTEGER, "
        "PRIMARY KEY (ptrid, resultid))"
    )
    rows = [
        # 好链：libil2cpp
        (1, 1, 3, 1, 0x12345678, 0x18, 0x20, 0x0, 0),
        # 差链：ntdll
        (1, 2, 2, 2, 0x1000, 0x50, 0, 0, 0),
        # 差链：层级过深
        (1, 3, 6, 1, 0x2000, 0x10, 0x10, 0x10, 0x10),
        # 重复链
        (1, 4, 3, 1, 0x12345678, 0x18, 0x20, 0x0, 0),
    ]
    conn.executemany(
        "INSERT INTO results VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()
    return db
