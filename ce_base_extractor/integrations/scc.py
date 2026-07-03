"""script-control-center / 自动化脚本加载 SCC 基址配置。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def load_bases(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    fmt = data.get("format", "")
    if not str(fmt).startswith("ce-base-extractor"):
        raise ValueError(f"非 ce-base-extractor SCC 格式: {fmt!r}")
    return data


def chain_to_reader_args(chain: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": chain["name"],
        "module": chain["module"],
        "module_offset": chain["module_offset"],
        "offsets": chain["offsets"],
        "type": chain.get("type", "int32"),
    }


def list_chain_names(path: str | Path) -> list[str]:
    return [c["name"] for c in load_bases(path).get("chains", [])]


@dataclass
class ScheduledRecheckResult:
    profile: str
    stable: int
    total: int
    details: list[dict[str, Any]]

    @property
    def ok(self) -> bool:
        return self.stable == self.total and self.total > 0


def scheduled_recheck_profile(
    profile_name: str,
    *,
    scc_path: str | Path | None = None,
    preset_id: str = "ldplayer",
    pointer_size: int = 8,
    pid: int | None = None,
) -> ScheduledRecheckResult:
    """SCC 定时复检：加载 profile/SCC 并执行重启可读性验证。"""
    from ce_base_extractor.profiles.store import ProfileStore
    from ce_base_extractor.verify.restart_verify import verify_restart_stability

    if scc_path:
        bases = load_bases(scc_path)
        from ce_base_extractor.models import PointerChain

        chains = [
            PointerChain(
                module_name=c["module"],
                module_offset=int(c["module_offset"]),
                offsets=tuple(int(o) for o in c["offsets"]),
                field_name=c.get("name", ""),
                value_type=c.get("type", "int32"),
            )
            for c in bases.get("chains", [])
        ]
        preset_id = bases.get("preset", preset_id)
    else:
        profile = ProfileStore().load(profile_name)
        chains = profile.to_result().chains
        preset_id = profile.preset
        pointer_size = profile.pointer_size
        pid = pid or profile.target_pid

    results = verify_restart_stability(
        chains,
        {},
        preset_id=preset_id,
        pointer_size=pointer_size,
        pid=pid,
    )
    details = []
    for i, r in enumerate(results, 1):
        details.append(
            {
                "name": r.chain.export_name(i),
                "stable": r.stable,
                "error": r.error,
                "value_unchanged": r.value_unchanged,
            }
        )
    stable = sum(1 for r in results if r.stable)
    return ScheduledRecheckResult(
        profile=profile_name,
        stable=stable,
        total=len(results),
        details=details,
    )
