from ce_base_extractor.export.lua_script import result_to_lua_snippet, save_lua_script
from ce_base_extractor.models import ExtractResult, PointerChain
from ce_base_extractor.profiles.migrate import compare_profiles
from ce_base_extractor.profiles.store import GameProfile, ProfileStore
from ce_base_extractor.watch.incremental_cross import IncrementalCrossValidator


def test_lua_export_contains_read_chain(tmp_path):
    result = ExtractResult(
        chains=[PointerChain("libil2cpp.so", 0x1000, (0x18,), field_name="gold")],
        total_raw=1,
        total_after_filter=1,
        modules_seen=["libil2cpp.so"],
        source_file="t",
    )
    text = result_to_lua_snippet(result)
    assert "read_chain" in text
    assert "gold" in text
    path = save_lua_script(result, tmp_path / "game.lua")
    assert path.is_file()


def test_profile_versioning(tmp_path):
    store = ProfileStore(tmp_path)
    p1 = GameProfile(game_name="demo", chains=[{"field_name": "gold", "module": "m", "module_offset": 1, "offsets": [2]}])
    store.save(p1)
    assert store.list_versions("demo")
    p2 = GameProfile(game_name="demo", chains=[])
    store.save(p2)
    assert len(store.list_versions("demo")) >= 2


def test_compare_profiles_detects_changes():
    old = GameProfile(
        game_name="g",
        chains=[{"field_name": "gold", "module": "m", "module_offset": 1, "offsets": [2]}],
    )
    new = GameProfile(
        game_name="g",
        chains=[{"field_name": "hp", "module": "m", "module_offset": 1, "offsets": [4]}],
    )
    report = compare_profiles(old, new)
    assert "gold" in report.removed
    assert "hp" in report.added


def test_incremental_cross_validator(sample_sqlite_pair):
    db1, db2 = sample_sqlite_pair
    v = IncrementalCrossValidator(min_occurrences=2)
    v.add_file(db1)
    info = v.add_file(db2)
    assert info["stable_keys"] == 1
    assert v.meta()["incremental"] is True
