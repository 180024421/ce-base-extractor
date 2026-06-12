from ce_base_extractor.io.scc_import import import_scc_to_result


def test_import_scc(tmp_path):
    p = tmp_path / "cfg.json"
    p.write_text(
        """{
  "format": "ce-base-extractor/scc-v1",
  "chains": [{
    "name": "gold",
    "module": "libil2cpp.so",
    "module_offset": 4096,
    "module_offset_hex": "0x1000",
    "offsets": [24, 32],
    "type": "int32"
  }]
}""",
        encoding="utf-8",
    )
    result = import_scc_to_result(p)
    assert result.chains[0].field_name == "gold"
    assert result.chains[0].module_offset == 0x1000
