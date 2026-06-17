import json

from ce_base_extractor.integrations.scc import chain_to_reader_args, list_chain_names, load_bases


def test_load_scc_format(tmp_path):
    data = {
        "format": "ce-base-extractor/scc-v1",
        "preset": "ldplayer",
        "chains": [
            {
                "name": "gold",
                "module": "libil2cpp.so",
                "module_offset": 4096,
                "offsets": [24, 32],
                "type": "int32",
            }
        ],
    }
    path = tmp_path / "test_scc.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    loaded = load_bases(path)
    assert loaded["format"].startswith("ce-base-extractor")
    assert list_chain_names(path) == ["gold"]
    args = chain_to_reader_args(loaded["chains"][0])
    assert args["name"] == "gold"
    assert args["module"] == "libil2cpp.so"
