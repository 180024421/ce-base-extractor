from ce_base_extractor.filters.fuzzy_dedupe import fuzzy_dedupe_key, merge_fuzzy_duplicates
from ce_base_extractor.models import PointerChain


def test_fuzzy_dedupe_merges_similar_last_offset():
    chains = [
        PointerChain("libil2cpp.so", 0x1000, (0x10, 0x20, 0x30), score=100),
        PointerChain("libil2cpp.so", 0x1000, (0x10, 0x20, 0x38), score=90),
        PointerChain("libil2cpp.so", 0x2000, (0x10, 0x20), score=80),
    ]
    merged = merge_fuzzy_duplicates(chains, last_offset_tolerance=0x8)
    assert len(merged) == 2
    assert merged[0].module_offset == 0x1000
    assert merged[0].score == 100


def test_fuzzy_key_ignores_last_offset_bucket():
    c = PointerChain("libil2cpp.so", 0x1000, (0x10, 0x20, 0x31))
    k1 = fuzzy_dedupe_key(c, last_offset_tolerance=0x8, ignore_last_offset=True)
    k2 = fuzzy_dedupe_key(
        PointerChain("libil2cpp.so", 0x1000, (0x10, 0x20, 0x39)),
        last_offset_tolerance=0x8,
        ignore_last_offset=True,
    )
    assert k1 == k2
