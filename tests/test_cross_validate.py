from ce_base_extractor.filters.cross_validate import cross_validate_files
from ce_base_extractor.pipeline import extract


def _make_db(tmp_path, name, module_offset):
    import sqlite3

    db = tmp_path / name
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE pointerfiles (ptrid INTEGER PRIMARY KEY, name TEXT, maxlevel INTEGER)")
    conn.execute("INSERT INTO pointerfiles VALUES (1, 'scan', 4)")
    conn.execute("CREATE TABLE modules (ptrid INTEGER, moduleid INTEGER, name TEXT, PRIMARY KEY (ptrid, moduleid))")
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
    return db


def test_cross_validate_finds_stable(tmp_path):
    db1 = _make_db(tmp_path, "a.sqlite", 0x1000)
    db2 = _make_db(tmp_path, "b.sqlite", 0x1000)
    db3 = _make_db(tmp_path, "c.sqlite", 0x2000)

    stable, meta = cross_validate_files([db1, db2, db3], min_occurrences=2)
    assert len(stable) == 1
    assert stable[0].module_offset == 0x1000
    assert meta["stable_keys"] == 1


def test_extract_with_cross(tmp_path):
    db1 = _make_db(tmp_path, "r1.sqlite", 0x12345678)
    db2 = _make_db(tmp_path, "r2.sqlite", 0x12345678)
    result = extract(db1, extra_files=[db2])
    assert result.chains
    assert result.chains[0].module_name == "libil2cpp.so"
