"""v0.5.3 回归测试。"""

from ce_base_extractor.compare.sqlite_diff import diff_sqlite_files
from ce_base_extractor.export.ct_export import chains_to_ct
from ce_base_extractor.filters.key_store import ChainKeyCounter, temp_key_counter
from ce_base_extractor.models import PointerChain
from ce_base_extractor.watch.folder_watcher import WATCH_PATTERNS


def test_diff_default_fuzzy(sample_sqlite_pair):
    r1, r2 = sample_sqlite_pair
    diff = diff_sqlite_files(r1, r2)
    assert diff["fuzzy"] is True


def test_diff_no_fuzzy(sample_sqlite_pair):
    r1, r2 = sample_sqlite_pair
    diff = diff_sqlite_files(r1, r2, fuzzy=False)
    assert diff["fuzzy"] is False


def test_ct_value_type_mapping():
    chains = [
        PointerChain("m", 0x1000, (0x10,), value_type="float"),
        PointerChain("m", 0x2000, (0x20,), value_type="int64"),
    ]
    ct = chains_to_ct(chains)
    assert "Float" in ct
    assert "8 Bytes" in ct


def test_key_store_count_at_least():
    counter = ChainKeyCounter(sqlite_threshold=1, force_sqlite=False)
    key = ("lib", 0x1000, (0x10,))
    chain = PointerChain("lib", 0x1000, (0x10,))
    try:
        counter.add_file_keys({key: chain})
        counter.add_file_keys({key: chain})
        assert counter.count_at_least(2) == 1
        assert counter.count_at_least(3) == 0
        items = list(counter.iter_items_at_least(2))
        assert len(items) == 1
    finally:
        counter.close()


def test_temp_key_counter_unlink():
    counter = temp_key_counter()
    path = counter.db_path
    assert path
    counter.close()
    from pathlib import Path

    assert not Path(path).exists()


def test_watch_patterns_include_ptr():
    assert any("ptr" in p.lower() for p in WATCH_PATTERNS)


def test_cross_validate_ranked(tmp_path):
    import sqlite3

    from ce_base_extractor.filters.cross_validate import cross_validate_files
    from ce_base_extractor.models import ExtractConfig

    def _db(name, off):
        db = tmp_path / name
        conn = sqlite3.connect(db)
        conn.execute(
            "CREATE TABLE pointerfiles (ptrid INTEGER PRIMARY KEY, name TEXT, maxlevel INTEGER)"
        )
        conn.execute("INSERT INTO pointerfiles VALUES (1, 'scan', 4)")
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
            (off,),
        )
        conn.commit()
        conn.close()
        return db

    db1 = _db("a.sqlite", 0x1000)
    db2 = _db("b.sqlite", 0x1000)
    cfg = ExtractConfig(top_n=5)
    stable, meta = cross_validate_files([db1, db2], cfg=cfg)
    assert meta["ranked"] is True
    assert meta["stable_keys"] == 1
    assert len(stable) == 1
