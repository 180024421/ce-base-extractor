"""v0.6 完整实现回归测试。"""

import json
from unittest.mock import patch

from ce_base_extractor.export.context import load_export_context
from ce_base_extractor.export.lua_script import result_to_lua_snippet, save_lua_script
from ce_base_extractor.filters.presets import PRESETS
from ce_base_extractor.models import ExtractResult, PointerChain
from ce_base_extractor.watch.incremental_cross import IncrementalCrossValidator


def test_new_presets_exist():
    assert "xiaoyao" in PRESETS
    assert "huawei" in PRESETS
    assert "ldplayer9" in PRESETS


def test_load_export_context_session_fallback():
    snapshots, pkg = load_export_context(
        "missing-game",
        session_values={"gold": 100},
        android_fallback="com.demo.game",
    )
    assert snapshots is not None
    assert snapshots["gold"]["value"] == 100
    assert pkg == "com.demo.game"


def test_lua_export_uses_bot_read_chain():
    result = ExtractResult(
        chains=[PointerChain("libil2cpp.so", 0x1000, (0x10,), value_type="int32")],
        total_raw=1,
        total_after_filter=1,
        modules_seen=["libil2cpp.so"],
        source_file="scan.sqlite",
    )
    lua = result_to_lua_snippet(result, game_name="demo")
    assert "bot.read_chain" in lua
    assert "bot.load_bases" in lua


def test_save_lua_writes_sidecar(tmp_path):
    result = ExtractResult(
        chains=[PointerChain("libil2cpp.so", 0x1000, (0x10,))],
        total_raw=1,
        total_after_filter=1,
        modules_seen=["libil2cpp.so"],
        source_file="scan.sqlite",
    )
    lua_path = save_lua_script(result, tmp_path / "demo_reader.lua", game_name="demo")
    scc_path = tmp_path / "demo_scc.json"
    assert lua_path.is_file()
    assert scc_path.is_file()
    data = json.loads(scc_path.read_text(encoding="utf-8"))
    assert data["format"].startswith("ce-base-extractor")


def test_incremental_ranked_stable_chains(sample_sqlite_pair):
    r1, r2 = sample_sqlite_pair
    from ce_base_extractor.models import ExtractConfig

    cfg = ExtractConfig(top_n=10, live_probe=False)
    inc = IncrementalCrossValidator(min_occurrences=2)
    inc.add_file(r1)
    inc.add_file(r2)
    chains, meta = inc.ranked_stable_chains(cfg)
    assert meta.get("ranked") is True
    assert isinstance(chains, list)


def test_adb_memory_list_modules_mock():
    from ce_base_extractor.runtime.adb_memory import AdbMemoryReader

    reader = AdbMemoryReader()
    maps = "7f0000000000-7f0000100000 r-xp 00000000 103:05 123 /system/lib/libc.so\n"
    with patch.object(reader, "_adb", return_value=maps):
        mods = reader.list_modules(1234)
    assert mods["libc.so"] == 0x7F0000000000


def test_api_health():
    from io import BytesIO

    from ce_base_extractor.api.server import ApiHandler

    class FakeHandler(ApiHandler):
        def __init__(self):
            self.headers = {}
            self.wfile = BytesIO()
            self.requestline = ""
            self.request_version = "HTTP/1.1"
            self.command = "GET"

        def send_response(self, code):
            self.status = code

        def send_header(self, key, value):
            pass

        def end_headers(self):
            pass

    handler = FakeHandler()
    handler.path = "/health"
    handler.do_GET()
    payload = json.loads(handler.wfile.getvalue().decode("utf-8"))
    assert payload["ok"] is True
