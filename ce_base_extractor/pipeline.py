from __future__ import annotations

import json
import sys
from pathlib import Path

from ce_base_extractor.export.formatter import save_result
from ce_base_extractor.filters.cross_validate import cross_validate_files
from ce_base_extractor.filters.presets import get_preset
from ce_base_extractor.filters.scorer import filter_and_rank
from ce_base_extractor.il2cpp.mapper import apply_il2cpp_hints, load_il2cpp_map
from ce_base_extractor.models import ExtractConfig, ExtractResult, PointerChain
from ce_base_extractor.parsers.ptr_parser import load_ptr
from ce_base_extractor.parsers.sqlite_parser import load_sqlite
from ce_base_extractor.stats.module_stats import compute_module_stats
from ce_base_extractor.verify.live_probe import probe_chains


def _bundle_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def _default_config_path() -> Path:
    return _bundle_dir() / "config.default.json"


def _user_config_path() -> Path:
    return Path.home() / "Documents" / "ce-exports" / "user_config.json"


def _wizard_flag_path() -> Path:
    return Path.home() / "Documents" / "ce-exports" / ".wizard_done"


def wizard_completed() -> bool:
    return _wizard_flag_path().is_file()


def mark_wizard_done() -> None:
    _wizard_flag_path().parent.mkdir(parents=True, exist_ok=True)
    _wizard_flag_path().write_text("1", encoding="utf-8")


def load_config(path: str | Path | None = None) -> ExtractConfig:
    if path is None:
        path = _user_config_path() if _user_config_path().is_file() else _default_config_path()
    cfg_path = Path(path)
    if not cfg_path.is_file():
        return ExtractConfig()
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    return ExtractConfig.from_dict(data)


def save_config(cfg: ExtractConfig, path: str | Path | None = None) -> Path:
    out = Path(path) if path else _user_config_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    from dataclasses import asdict

    out.write_text(json.dumps(asdict(cfg), ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def _preferred_module_ids(modules: dict[int, str], preset_id: str) -> set[int] | None:
    preset = get_preset(preset_id)
    if not preset:
        return None
    ids: set[int] = set()
    for mid, name in modules.items():
        lower = name.lower()
        for pref in preset.preferred_modules:
            if pref.lower() in lower:
                ids.add(mid)
                break
    return ids or None


def _load_chains(
    input_path: Path,
    ptrid: int | None,
    cfg: ExtractConfig,
) -> tuple[list[PointerChain], dict]:
    suffix = input_path.suffix.lower()
    if suffix in (".db", ".sqlite", ".sqlite3"):
        module_ids = None
        if cfg.sqlite_module_prefilter and cfg.emulator_mode:
            import sqlite3

            conn = sqlite3.connect(f"file:{input_path.as_posix()}?mode=ro", uri=True)
            try:
                from ce_base_extractor.parsers.sqlite_parser import _load_modules, _resolve_ptrid

                resolved = _resolve_ptrid(conn, ptrid or cfg.ptrid)
                modules = _load_modules(conn, resolved)
                module_ids = _preferred_module_ids(modules, cfg.preset)
            finally:
                conn.close()
        return load_sqlite(input_path, ptrid=ptrid or cfg.ptrid, module_ids=module_ids)
    if suffix == ".ptr":
        return load_ptr(input_path)
    raise ValueError(f"不支持的文件类型: {suffix}，请使用 .sqlite / .db 或 .PTR")


def extract(
    input_file: str | Path,
    config: ExtractConfig | None = None,
    config_path: str | Path | None = None,
    extra_files: list[str | Path] | None = None,
) -> ExtractResult:
    cfg = config or load_config(config_path)
    input_path = Path(input_file)

    cross_meta: dict | None = None
    ptrid: int | None = None
    modules_seen: list[str] = []
    live_probe_meta: list[dict] | None = None

    if extra_files:
        all_files = [input_path, *[Path(f) for f in extra_files]]
        min_occ = max(cfg.cross_validate_min, 2)
        chains, cross_meta = cross_validate_files(
            all_files,
            min_occurrences=min_occ,
            ptrid=cfg.ptrid,
            require_all=cfg.cross_validate_require_all,
        )
        total_raw = int(cross_meta.get("stable_keys", len(chains)))
        modules_seen = sorted({c.module_name for c in chains})
        ptrid = cfg.ptrid
        source = ", ".join(str(p.name) for p in all_files)
    else:
        chains, meta = _load_chains(input_path, cfg.ptrid, cfg)
        total_raw = int(meta.get("result_count", len(chains)))
        modules_seen = list(meta.get("modules", []))
        ptrid = meta.get("ptrid")
        source = str(input_path)

    il2cpp_map = load_il2cpp_map(cfg.il2cpp_map_path)
    if il2cpp_map:
        chains = apply_il2cpp_hints(chains, il2cpp_map)

    ranked = filter_and_rank(chains, cfg)

    if cfg.live_probe and ranked:
        ranked, probe_results = probe_chains(ranked, cfg)
        live_probe_meta = [
            {
                "readable": r.readable,
                "error": r.error,
                "module": r.chain.module_name,
                "offsets": list(r.chain.offsets),
            }
            for r in probe_results
        ]
        ranked = ranked[: cfg.top_n]

    stats = compute_module_stats(chains, cfg.emulator_mode)

    if not modules_seen:
        modules_seen = sorted({c.module_name for c in chains})

    return ExtractResult(
        chains=ranked,
        total_raw=total_raw,
        total_after_filter=len(ranked),
        modules_seen=modules_seen,
        source_file=source,
        ptrid=ptrid,
        cross_validate_meta=cross_meta,
        module_stats=stats,
        live_probe_meta=live_probe_meta,
    )


def extract_and_save(
    input_file: str | Path,
    output_file: str | Path | None = None,
    fmt: str = "txt",
    config: ExtractConfig | None = None,
    extra_files: list[str | Path] | None = None,
) -> ExtractResult:
    result = extract(input_file, config=config, extra_files=extra_files)
    if output_file:
        save_result(result, output_file, fmt=fmt)
    return result
