from ce_base_extractor.parsers.sqlite_parser import load_sqlite
from ce_base_extractor.pipeline import extract


def test_load_sqlite(sample_sqlite):
    chains, meta = load_sqlite(sample_sqlite)
    assert meta["result_count"] == 4
    assert "libil2cpp.so" in meta["modules"]


def test_extract_prefers_il2cpp(sample_sqlite):
    result = extract(sample_sqlite)
    assert result.chains
    assert result.chains[0].module_name == "libil2cpp.so"
    assert len(result.chains) <= 20
