"""生成示例 CE SQLite 供本地试跑。"""

from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _write(db: Path, module_offset: int) -> None:
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE pointerfiles (ptrid INTEGER PRIMARY KEY, name TEXT, maxlevel INTEGER)"
    )
    conn.execute("INSERT INTO pointerfiles VALUES (1, 'demo', 4)")
    conn.execute(
        "CREATE TABLE modules (ptrid INTEGER, moduleid INTEGER, name TEXT, PRIMARY KEY (ptrid, moduleid))"
    )
    conn.execute("INSERT INTO modules VALUES (1, 0, 'libil2cpp.so')")
    conn.execute(
        "CREATE TABLE results (ptrid INTEGER, resultid INTEGER, offsetcount INTEGER, "
        "moduleid INTEGER, moduleoffset BIGINT, offset1 INTEGER, offset2 INTEGER, "
        "PRIMARY KEY (ptrid, resultid))"
    )
    conn.execute(
        "INSERT INTO results VALUES (1, 1, 2, 0, ?, 0x18, 0x20)",
        (module_offset,),
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    _write(ROOT / "sample_r1.sqlite", 0x12345678)
    _write(ROOT / "sample_r2.sqlite", 0x12345678)
    _write(ROOT / "sample_r3_noise.sqlite", 0x99999999)
    print("已生成 examples/sample_r1.sqlite, sample_r2.sqlite")
