from __future__ import annotations

from pathlib import Path

from ce_base_extractor.export.ct_export import result_to_ct
from ce_base_extractor.export.formatter import save_result
from ce_base_extractor.export.frida_script import save_frida_script
from ce_base_extractor.export.python_module import save_python_module
from ce_base_extractor.export.python_script import save_python_script
from ce_base_extractor.export.scc_export import save_scc_json
from ce_base_extractor.models import ExtractResult


def export_all(
    result: ExtractResult,
    output_dir: str | Path,
    game_name: str = "game",
    preset_id: str = "ldplayer",
    pointer_size: int = 8,
    target_pid: int | None = None,
) -> list[Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []

    files.append(save_result(result, out / f"{game_name}.bases.txt", fmt="txt"))
    files.append(save_result(result, out / f"{game_name}.bases.json", fmt="json"))
    files.append(save_scc_json(result, out / f"{game_name}_scc.json", preset_id=preset_id))
    (out / f"{game_name}.CT").write_text(result_to_ct(result, title=game_name), encoding="utf-8")
    files.append(out / f"{game_name}.CT")
    files.append(
        save_python_script(
            result,
            out / f"{game_name}_reader.py",
            preset_id=preset_id,
            game_name=game_name,
            pointer_size=pointer_size,
            target_pid=target_pid,
        )
    )
    files.append(
        save_python_module(
            result,
            out / f"{game_name}_memory.py",
            game_name=game_name,
            pointer_size=pointer_size,
            target_pid=target_pid,
        )
    )
    files.append(
        save_frida_script(
            result,
            out / f"{game_name}_frida.js",
            game_name=game_name,
            preset_id=preset_id,
        )
    )
    return files
