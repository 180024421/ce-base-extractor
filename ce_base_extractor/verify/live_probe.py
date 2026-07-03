"""提取后在线探针：验证 Top N 指针链可读。"""

from __future__ import annotations

from dataclasses import dataclass

from ce_base_extractor.filters.presets import get_preset
from ce_base_extractor.models import ExtractConfig, PointerChain
from ce_base_extractor.runtime.win_memory import ProcessMemory, read_chain_value


@dataclass
class LiveProbeResult:
    chain: PointerChain
    readable: bool
    value: int | float | bytes | None = None
    error: str = ""


def probe_chains(
    chains: list[PointerChain],
    cfg: ExtractConfig,
    *,
    top_n: int | None = None,
) -> tuple[list[PointerChain], list[LiveProbeResult]]:
    """对前 top_n 条链做内存探针；不可读的降权，可读加分。"""
    if not cfg.live_probe or not chains:
        return chains, []

    n = top_n if top_n is not None else cfg.probe_top_n
    targets = chains[: max(n, 0)]
    rest = chains[max(n, 0) :]

    preset = get_preset(cfg.preset)
    names = list(preset.process_names) if preset else ["dnplayer.exe"]
    results: list[LiveProbeResult] = []
    probed: list[PointerChain] = []

    try:
        mem = ProcessMemory.auto_attach(names, pid=cfg.target_pid)
    except (ProcessLookupError, OSError) as exc:
        for c in targets:
            results.append(LiveProbeResult(chain=c, readable=False, error=str(exc)))
            probed.append(
                PointerChain(
                    module_name=c.module_name,
                    module_offset=c.module_offset,
                    offsets=c.offsets,
                    score=max(0.0, c.score - 50.0),
                    source=c.source + "|probe_skip",
                    field_name=c.field_name,
                    value_type=c.value_type,
                    verified=False,
                    il2cpp_symbol=c.il2cpp_symbol,
                )
            )
        return probed + rest, results

    with mem:
        for chain in targets:
            try:
                mem.resolve_chain(
                    chain.module_name,
                    chain.module_offset,
                    chain.offsets,
                    cfg.pointer_size,
                )
                val = read_chain_value(mem, chain, cfg.pointer_size)
                bonus = 40.0
                probed.append(
                    PointerChain(
                        module_name=chain.module_name,
                        module_offset=chain.module_offset,
                        offsets=chain.offsets,
                        score=chain.score + bonus,
                        source=chain.source + "|probe_ok",
                        field_name=chain.field_name,
                        value_type=chain.value_type,
                        verified=True,
                        il2cpp_symbol=chain.il2cpp_symbol,
                    )
                )
                results.append(LiveProbeResult(chain=chain, readable=True, value=val))
            except Exception as exc:
                probed.append(
                    PointerChain(
                        module_name=chain.module_name,
                        module_offset=chain.module_offset,
                        offsets=chain.offsets,
                        score=max(0.0, chain.score - 80.0),
                        source=chain.source + "|probe_fail",
                        field_name=chain.field_name,
                        value_type=chain.value_type,
                        verified=False,
                        il2cpp_symbol=chain.il2cpp_symbol,
                    )
                )
                results.append(LiveProbeResult(chain=chain, readable=False, error=str(exc)))

    probed.sort(key=lambda c: -c.score)
    if cfg.probe_drop_unreadable:
        probed = [c for c in probed if c.verified or "|probe_ok" in c.source]
    return probed + rest, results
