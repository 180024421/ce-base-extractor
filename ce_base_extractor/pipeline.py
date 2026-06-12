from __future__ import annotations

import json
from pathlib import Path

from ce_base_extractor.export.formatter import save_result
from ce_base_extractor.filters.scorer import filter_and_rank
from ce_base_extractor.models import ExtractConfig, ExtractResult, PointerChain
from ce_base_extractor.parsers.ptr_parser import load_ptr
from ce_base_extractor.parsers.sqlite_parser import load_sqlite


def _default_config_path() -> Path:
    return Path(__file__).resolve().parent.parent / "config.default.json"


def load_config(path: str | Path | None = None) -> ExtractConfig:
    if path is None:
        path = _default_config_path()
    cfg_path = Path(path)
    if not cfg_path.is_file():
        return ExtractConfig()
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    return ExtractConfig.from_dict(data)


def _load_chains(input_path: Path, ptrid: int | None) -> tuple[list[PointerChain], dict]:
    suffix = input_path.suffix.lower()
    if suffix in (".db", ".sqlite", ".sqlite3"):
        return load_sqlite(input_path, ptrid=ptrid)
    if suffix == ".ptr":
        return load_ptr(input_path)
    raise ValueError(f"不支持的文件类型: {suffix}，请使用 .sqlite / .db 或 .PTR")


def extract(
    input_file: str | Path,
    config: ExtractConfig | None = None,
    config_path: str | Path | None = None,
) -> ExtractResult:
    cfg = config or load_config(config_path)
    input_path = Path(input_file)

    chains, meta = _load_chains(input_path, cfg.ptrid)
    ranked = filter_and_rank(chains, cfg)

    modules_seen = meta.get("modules", [])
    if not modules_seen:
        modules_seen = sorted({c.module_name for c in chains})

    return ExtractResult(
        chains=ranked,
        total_raw=int(meta.get("result_count", len(chains))),
        total_after_filter=len(ranked),
        modules_seen=list(modules_seen),
        source_file=str(input_path),
        ptrid=meta.get("ptrid"),
    )


def extract_and_save(
    input_file: str | Path,
    output_file: str | Path | None = None,
    fmt: str = "txt",
    config: ExtractConfig | None = None,
) -> ExtractResult:
    result = extract(input_file, config=config)
    if output_file:
        save_result(result, output_file, fmt=fmt)
    return result
