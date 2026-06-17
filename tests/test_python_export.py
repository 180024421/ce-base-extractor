from ce_base_extractor.export.python_script import chains_to_python_script
from ce_base_extractor.filters.presets import get_preset
from ce_base_extractor.models import PointerChain


def test_python_script_contains_reader():
    chains = [
        PointerChain(
            "libil2cpp.so",
            0x1000,
            (0x18, 0x20),
            score=100,
            field_name="gold",
            value_type="int32",
        ),
    ]
    preset = get_preset("ldplayer")
    code = chains_to_python_script(
        chains, preset=preset, game_name="testgame", pointer_size=8, target_pid=1234
    )
    assert "dnplayer.exe" in code
    assert "gold" in code
    assert "TARGET_PID = 1234" in code
    assert "resolve_chain" in code
    assert "standalone_reader" not in code or "class ProcessMemory" in code
    assert "--list-processes" in code
