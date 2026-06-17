from unittest.mock import MagicMock, patch

from ce_base_extractor.models import PointerChain
from ce_base_extractor.verify.restart_verify import verify_restart_stability


def _chain(name: str = "gold") -> PointerChain:
    return PointerChain(
        "libil2cpp.so",
        0x1000,
        (0x18, 0x20),
        field_name=name,
        value_type="int32",
    )


@patch("ce_base_extractor.verify.restart_verify.ProcessMemory")
@patch("ce_base_extractor.verify.restart_verify.read_chain_value")
def test_verify_readable_is_stable(mock_read, mock_pm):
    mem = MagicMock()
    mock_pm.auto_attach.return_value = mem
    mem.__enter__ = MagicMock(return_value=mem)
    mem.__exit__ = MagicMock(return_value=False)
    mem.resolve_chain.return_value = 0x12345
    mock_read.return_value = 999

    results = verify_restart_stability(
        [_chain()],
        {"gold": 100},
        require_value_match=False,
    )
    assert len(results) == 1
    assert results[0].readable is True
    assert results[0].stable is True
    assert results[0].value_unchanged is False


@patch("ce_base_extractor.verify.restart_verify.ProcessMemory")
@patch("ce_base_extractor.verify.restart_verify.read_chain_value")
def test_verify_require_value_match(mock_read, mock_pm):
    mem = MagicMock()
    mock_pm.auto_attach.return_value = mem
    mem.__enter__ = MagicMock(return_value=mem)
    mem.__exit__ = MagicMock(return_value=False)
    mem.resolve_chain.return_value = 0x12345
    mock_read.return_value = 100

    results = verify_restart_stability(
        [_chain()],
        {"gold": 100},
        require_value_match=True,
    )
    assert results[0].stable is True
    assert results[0].value_unchanged is True


@patch("ce_base_extractor.verify.restart_verify.ProcessMemory")
def test_verify_attach_failure(mock_pm):
    mock_pm.auto_attach.side_effect = ProcessLookupError("no process")
    results = verify_restart_stability([_chain()], {})
    assert results[0].stable is False
    assert results[0].error
