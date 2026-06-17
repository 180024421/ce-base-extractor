from ce_base_extractor.compare.sqlite_diff import diff_sqlite_files, diff_sqlite_many
from ce_base_extractor.models import PointerChain


def _make_chain(mod: str, base: int, offs: tuple[int, ...]) -> PointerChain:
    return PointerChain(mod, base, offs)


def test_diff_two_files(sample_sqlite_pair):
    r1, r2 = sample_sqlite_pair
    diff = diff_sqlite_files(r1, r2)
    assert diff["count_a"] >= 1
    assert diff["common"] >= 1
    assert 0 <= diff["stability_ratio"] <= 1


def test_diff_many_files(sample_sqlite_pair):
    r1, r2 = sample_sqlite_pair
    diff = diff_sqlite_many([r1, r2])
    assert diff["file_count"] == 2
    assert diff["in_all"] >= 1
    assert "occurrence_histogram" in diff


def test_diff_many_requires_two():
    import pytest

    with pytest.raises(ValueError, match="至少"):
        diff_sqlite_many(["only_one.sqlite"])
