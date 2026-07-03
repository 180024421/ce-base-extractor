from unittest.mock import MagicMock, patch

from ce_base_extractor.models import ExtractConfig, PointerChain
from ce_base_extractor.verify.live_probe import probe_chains


def test_probe_bonus_on_success():
    chains = [PointerChain("libil2cpp.so", 0x1000, (0x10, 0x20), score=200)]
    cfg = ExtractConfig(live_probe=True, probe_top_n=1)

    mem = MagicMock()
    with patch("ce_base_extractor.verify.live_probe.ProcessMemory.auto_attach", return_value=mem):
        mem.__enter__ = MagicMock(return_value=mem)
        mem.__exit__ = MagicMock(return_value=False)
        mem.resolve_chain.return_value = 0x1234
        with patch("ce_base_extractor.verify.live_probe.read_chain_value", return_value=99):
            out, results = probe_chains(chains, cfg)
    assert results[0].readable is True
    assert out[0].verified is True
    assert out[0].score > chains[0].score


def test_probe_penalty_on_fail():
    chains = [PointerChain("libil2cpp.so", 0x1000, (0x10, 0x20), score=200)]
    cfg = ExtractConfig(live_probe=True, probe_top_n=1)

    with patch(
        "ce_base_extractor.verify.live_probe.ProcessMemory.auto_attach",
        side_effect=ProcessLookupError("no process"),
    ):
        out, results = probe_chains(chains, cfg)
    assert results[0].readable is False
    assert out[0].score < chains[0].score
