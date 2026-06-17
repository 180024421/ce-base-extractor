from ce_base_extractor.export.frida_script import chains_to_frida_script
from ce_base_extractor.models import PointerChain


def test_frida_script_contains_chains():
    chains = [
        PointerChain("libil2cpp.so", 0x1000, (0x18, 0x20), field_name="gold", value_type="int32"),
    ]
    code = chains_to_frida_script(chains, game_name="demo", preset_id="ldplayer")
    assert "gold" in code
    assert "libil2cpp.so" in code
    assert "dnplayer.exe" in code
    assert "Android" in code or "子进程" in code
