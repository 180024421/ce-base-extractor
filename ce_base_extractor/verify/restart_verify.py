from __future__ import annotations

from dataclasses import dataclass

from ce_base_extractor.filters.presets import get_preset
from ce_base_extractor.models import PointerChain
from ce_base_extractor.runtime.win_memory import ProcessMemory, read_chain_value


@dataclass
class RestartVerifyResult:
    chain: PointerChain
    before: int | float | bytes | None
    after: int | float | bytes | None
    stable: bool
    error: str = ""


def verify_restart_stability(
    chains: list[PointerChain],
    before_values: dict[str, int | float | bytes],
    preset_id: str = "ldplayer",
    pointer_size: int = 8,
    pid: int | None = None,
) -> list[RestartVerifyResult]:
    preset = get_preset(preset_id)
    names = list(preset.process_names) if preset else ["dnplayer.exe"]
    results: list[RestartVerifyResult] = []

    try:
        mem = ProcessMemory.auto_attach(names, pid=pid)
    except (ProcessLookupError, OSError) as exc:
        return [
            RestartVerifyResult(
                chain=c,
                before=before_values.get(c.export_name(i + 1)),
                after=None,
                stable=False,
                error=str(exc),
            )
            for i, c in enumerate(chains)
        ]

    with mem:
        for i, chain in enumerate(chains):
            name = chain.export_name(i + 1)
            before = before_values.get(name)
            try:
                after = read_chain_value(mem, chain, pointer_size)
                stable = before is not None and before == after
                results.append(
                    RestartVerifyResult(
                        chain=chain,
                        before=before,
                        after=after,
                        stable=stable,
                    )
                )
            except Exception as exc:
                results.append(
                    RestartVerifyResult(
                        chain=chain,
                        before=before,
                        after=None,
                        stable=False,
                        error=str(exc),
                    )
                )
    return results
