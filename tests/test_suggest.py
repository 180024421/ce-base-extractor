from ce_base_extractor.models import PointerChain
from ce_base_extractor.suggest.field_names import suggest_field_names


def test_suggest_names():
    chains = [
        PointerChain("libil2cpp.so", 0x1000, (0x18, 0x20)),
        PointerChain("libunity.so", 0x2000, (0x10,), il2cpp_symbol="Player.HP"),
    ]
    out = suggest_field_names(chains)
    assert out[0].field_name.startswith("il2cpp")
    assert out[1].field_name == "hp"
