from ce_base_extractor.export.signature_export import (
    build_ass_fields_table,
    signatures_to_lua,
)
from ce_base_extractor.models import PointerChain
from ce_base_extractor.signature import (
    GeneratedSignature,
    SavedSignature,
    SignatureSample,
    find_pattern_in_buffer,
    format_pattern,
    generate_from_samples,
    minimize_unique_pattern,
    parse_address,
    parse_pattern,
    samples_from_json,
    samples_to_json,
)


def test_parse_pattern_wildcards():
    values, mask = parse_pattern("48 8B ?? 00 ?")
    assert values == bytes([0x48, 0x8B, 0, 0x00, 0])
    assert mask == bytes([0xFF, 0xFF, 0, 0xFF, 0])
    assert format_pattern(values, mask) == "48 8B ?? 00 ??"


def test_generate_from_three_samples_trims_edges():
    s1 = SignatureSample(0x1000, bytes([0x11, 0x22, 0x33, 0x44, 0xAA, 0xBB, 0xCC, 0x01]), 4, 4)
    s2 = SignatureSample(0x2000, bytes([0x99, 0x22, 0x33, 0x44, 0xAA, 0xBB, 0xCC, 0x02]), 4, 4)
    s3 = SignatureSample(0x3000, bytes([0x77, 0x22, 0x33, 0x44, 0xAA, 0xBB, 0xCC, 0x03]), 4, 4)
    gen = generate_from_samples([s1, s2, s3])
    assert isinstance(gen, GeneratedSignature)
    assert gen.pattern == "22 33 44 AA BB CC"
    assert gen.fixed_bytes == 6
    assert gen.wildcard_bytes == 0
    assert gen.offset_to_target == 3


def test_generate_inserts_wildcards_for_diff():
    s1 = SignatureSample(1, bytes([0x10, 0x20, 0x30, 0x40]), 2, 2, note="a")
    s2 = SignatureSample(2, bytes([0x10, 0x21, 0x30, 0x40]), 2, 2, note="b")
    s3 = SignatureSample(3, bytes([0x10, 0x22, 0x30, 0x40]), 2, 2, note="c")
    gen = generate_from_samples([s1, s2, s3])
    assert gen.pattern == "10 ?? 30 40"
    assert gen.offset_to_target == 2


def test_generate_requires_min_samples():
    s = SignatureSample(1, bytes([1, 2, 3, 4]), 2, 2)
    try:
        generate_from_samples([s, s])
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "至少需要 3" in str(exc)


def test_parse_address():
    assert parse_address("0x1234") == 0x1234
    assert parse_address("4660") == 4660


def test_find_pattern_in_buffer():
    buf = bytes([0, 0x10, 0x20, 0x99, 0x30, 0x40, 1])
    pattern, mask = parse_pattern("10 20 ?? 30 40")
    hits = find_pattern_in_buffer(buf, pattern, mask, base_address=0x1000)
    assert hits == [0x1001]


def test_sample_json_roundtrip():
    s = SignatureSample(0xABC, bytes([1, 2, 3, 4]), 2, 2, note="n1")
    text = samples_to_json([s])
    back = samples_from_json(text)
    assert len(back) == 1
    assert back[0].address == 0xABC
    assert back[0].data == bytes([1, 2, 3, 4])
    assert back[0].note == "n1"


def test_minimize_unique_pattern():
    gen = GeneratedSignature(
        pattern="AA BB CC DD EE FF",
        offset_to_target=5,
        fixed_bytes=6,
        wildcard_bytes=0,
        sample_count=3,
        window_before=5,
        window_after=1,
    )

    def count_fn(pat: str) -> int:
        # 只有中间 4 字节唯一
        if pat == "BB CC DD EE":
            return 1
        if pat == "AA BB CC DD EE FF":
            return 3
        if len(pat.split()) >= 4:
            return 2
        return 5

    out = minimize_unique_pattern(gen, count_fn, min_fixed=4, max_hits=1)
    assert out.minimized
    assert out.pattern == "BB CC DD EE"
    assert out.offset_to_target == 4  # 5 - 1


def test_ass_fields_table():
    chains = [
        PointerChain("mod.so", 0x100, (0x10, 0x20), field_name="gold", value_type="int32"),
    ]
    sigs = [
        SavedSignature("silver", "11 22 ?? 33", 2, value_type="float", module_hint="mod.so"),
    ]
    table = build_ass_fields_table(chains=chains, signatures=sigs, android_package="com.g", game_name="g")
    assert table["format"] == "ce-base-extractor/ass-fields-v1"
    assert len(table["fields"]) == 2
    assert table["fields"][1]["kind"] == "aob"
    lua = signatures_to_lua(sigs, game_name="g")
    assert "SIGS" in lua
    assert "11 22 ?? 33" in lua
    assert "mem.aob_scan" in lua
    assert "mem.read" in lua


def test_pattern_hash_and_history(tmp_path, monkeypatch):
    from ce_base_extractor.signature.history import append_history, list_history, pattern_hash

    monkeypatch.setattr(
        "ce_base_extractor.signature.history._history_dir",
        lambda: tmp_path,
    )
    gen = GeneratedSignature(
        pattern="AA BB CC",
        offset_to_target=2,
        fixed_bytes=3,
        wildcard_bytes=0,
        sample_count=3,
        window_before=2,
        window_after=1,
    )
    assert len(pattern_hash(gen.pattern)) == 12
    path = append_history(game="demo", field_name="hp", gen=gen, value_type="int32")
    assert path.is_file()
    items = list_history(10)
    assert len(items) == 1
    assert items[0]["field_name"] == "hp"
    assert items[0]["pattern"] == "AA BB CC"
