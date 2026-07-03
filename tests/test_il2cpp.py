from ce_base_extractor.il2cpp.mapper import apply_il2cpp_hints, load_il2cpp_map
from ce_base_extractor.models import PointerChain


def test_il2cpp_script_json_field_offset(tmp_path):
    data = {
        "ScriptClass": [
            {
                "Name": "PlayerData",
                "Fields": [{"Name": "gold", "Offset": 0x48}],
            }
        ]
    }
    p = tmp_path / "script.json"
    import json

    p.write_text(json.dumps(data), encoding="utf-8")
    mapping = load_il2cpp_map(p)
    assert mapping[0x48] == "PlayerData.gold"
    chains = apply_il2cpp_hints(
        [PointerChain("libil2cpp.so", 0x1000, (0x10, 0x48))],
        mapping,
    )
    assert chains[0].il2cpp_symbol == "PlayerData.gold"
    assert chains[0].field_name == "playerdata_gold"


def test_il2cpp_json_map(tmp_path):
    p = tmp_path / "map.json"
    p.write_text('{"0x1000": "Player.gold"}', encoding="utf-8")
    m = load_il2cpp_map(p)
    assert m[0x1000] == "Player.gold"
    chains = apply_il2cpp_hints(
        [PointerChain("libil2cpp.so", 0x1000, (0x10,))],
        m,
    )
    assert chains[0].field_name == "player_gold"
    assert chains[0].il2cpp_symbol == "Player.gold"
