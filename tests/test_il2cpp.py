from ce_base_extractor.il2cpp.mapper import apply_il2cpp_hints, load_il2cpp_map
from ce_base_extractor.models import PointerChain


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
