from ce_base_extractor.filters.cross_validate import cross_validate_files
from ce_base_extractor.models import ExtractConfig
from ce_base_extractor.pipeline import extract
from ce_base_extractor.profiles.migrate import compare_profiles
from ce_base_extractor.profiles.store import GameProfile, ProfileStore


def _make_db(tmp_path, name, last_offset):
    import sqlite3

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
        "INSERT INTO results VALUES (1, 1, 2, 0, 0x1000, 0x18, ?)",
        (last_offset,),
    )
    conn.commit()
    conn.close()
    return db


def test_cross_validate_fuzzy_matches_offset_drift(tmp_path):
    db1 = _make_db(tmp_path, "a.sqlite", 0x20)
    db2 = _make_db(tmp_path, "b.sqlite", 0x28)
    stable, meta = cross_validate_files([db1, db2], min_occurrences=2, fuzzy=True)
    assert len(stable) == 1
    assert meta["fuzzy"] is True


def test_profile_snapshots_roundtrip(tmp_path):
    store = ProfileStore(tmp_path)
    profile = GameProfile(game_name="demo")
    profile.record_snapshots({"gold": 100, "hp": 50.5})
    store.save(profile)
    loaded = store.load("demo")
    snaps = loaded.snapshot_values()
    assert snaps["gold"] == 100
    assert snaps["hp"] == 50.5


def test_compare_profiles_fuzzy_matched():
    old = GameProfile(
        game_name="g",
        chains=[
            {
                "field_name": "gold",
                "module": "libil2cpp.so",
                "module_offset": 0x1000,
                "offsets": [0x18, 0x20],
            }
        ],
    )
    new = GameProfile(
        game_name="g",
        chains=[
            {
                "field_name": "gold",
                "module": "libil2cpp.so",
                "module_offset": 0x1000,
                "offsets": [0x18, 0x28],
            }
        ],
    )
    report = compare_profiles(old, new)
    assert report.fuzzy_matched
    assert "gold" in report.fuzzy_matched[0][0]


def test_extract_config_validation():
    import pytest

    with pytest.raises(ValueError):
        ExtractConfig.from_dict({"top_n": 0})


def test_stream_extract(sample_sqlite):
    cfg = ExtractConfig(stream_single_file=True, live_probe=False, top_n=5)
    result = extract(sample_sqlite, config=cfg)
    assert result.chains
    assert result.total_raw >= 1
