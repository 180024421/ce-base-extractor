from pathlib import Path

from ce_base_extractor.export.python_script import _embedded_reader_source
from ce_base_extractor.runtime.standalone_reader import ProcessMemory


def test_embedded_reader_matches_standalone_file():
    src = _embedded_reader_source()
    assert "class ProcessMemory" in src
    assert "resolve_chain" in src
    assert (
        Path(__file__)
        .resolve()
        .parents[1]
        .joinpath("ce_base_extractor/runtime/standalone_reader.py")
        .is_file()
    )


def test_standalone_reader_list_matching_empty():
    # 不应抛错，仅返回列表
    result = ProcessMemory.list_matching(["__nonexistent_process__.exe"])
    assert result == []
