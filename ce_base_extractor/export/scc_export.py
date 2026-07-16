"""script-control-center 可导入的基址 JSON 格式。"""

from __future__ import annotations

import json
from pathlib import Path

from ce_base_extractor.filters.presets import get_preset
from ce_base_extractor.models import ExtractResult


def result_to_scc_json(
    result: ExtractResult,
    preset_id: str = "ldplayer",
    *,
    snapshots: dict[str, dict] | None = None,
    android_package: str = "",
    signatures: list[dict] | None = None,
) -> str:
    preset = get_preset(preset_id)
    payload = {
        "format": "ce-base-extractor/scc-v2",
        "game": preset_id,
        "preset": preset_id,
        "process_names": list(preset.process_names) if preset else ["dnplayer.exe"],
        "android_package": android_package,
        "source": result.source_file,
        "live_probe_meta": result.live_probe_meta,
        "snapshots": snapshots or {},
        "signatures": signatures or [],
        "chains": [
            {
                "name": c.export_name(i + 1),
                "module": c.module_name,
                "module_offset": c.module_offset,
                "module_offset_hex": f"0x{c.module_offset:X}",
                "offsets": list(c.offsets),
                "offsets_hex": [f"0x{o:X}" for o in c.offsets],
                "type": c.value_type,
                "score": round(c.score, 2),
                "verified": c.verified,
                "il2cpp_symbol": c.il2cpp_symbol,
            }
            for i, c in enumerate(result.chains)
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def save_scc_json(
    result: ExtractResult,
    output: str | Path,
    preset_id: str = "ldplayer",
    *,
    snapshots: dict[str, dict] | None = None,
    android_package: str = "",
    signatures: list[dict] | None = None,
) -> Path:
    path = Path(output)
    path.write_text(
        result_to_scc_json(
            result,
            preset_id,
            snapshots=snapshots,
            android_package=android_package,
            signatures=signatures,
        ),
        encoding="utf-8",
    )
    return path
