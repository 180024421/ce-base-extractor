from ce_base_extractor.filters.scorer import filter_and_rank
from ce_base_extractor.models import ExtractConfig, PointerChain


def test_dedupe_and_depth_filter():
    chains = [
        PointerChain("libil2cpp.so", 0x1000, (0x10, 0x20)),
        PointerChain("libil2cpp.so", 0x1000, (0x10, 0x20)),
        PointerChain("libil2cpp.so", 0x2000, (0x10,) * 6),
    ]
    cfg = ExtractConfig(max_depth=5, top_n=10)
    out = filter_and_rank(chains, cfg)
    assert len(out) == 1
    assert out[0].module_offset == 0x1000
