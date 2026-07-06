from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Callable

from ce_base_extractor.export.formatter import save_result
from ce_base_extractor.filters.cross_validate import cross_validate_files
from ce_base_extractor.filters.presets import get_preset
from ce_base_extractor.filters.scorer import filter_and_rank
from ce_base_extractor.filters.stream_rank import filter_and_rank_stream, module_stats_from_counts
from ce_base_extractor.il2cpp.mapper import apply_il2cpp_hints, load_il2cpp_map
from ce_base_extractor.models import ExtractConfig, ExtractResult, PointerChain
from ce_base_extractor.parsers.chain_io import iter_file_chains
from ce_base_extractor.parsers.ptr_parser import iter_ptr_chains, load_ptr_meta
from ce_base_extractor.parsers.sqlite_parser import load_sqlite, load_sqlite_meta
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


def _resolve_module_ids(input_path: Path, ptrid: int | None, cfg: ExtractConfig) -> set[int] | None:
    if not cfg.sqlite_module_prefilter or not cfg.emulator_mode:
        return None
    meta = load_sqlite_meta(input_path, ptrid=ptrid or cfg.ptrid)
    return _preferred_module_ids(meta.get("module_map", {}), cfg.preset)


def _load_chains(
    input_path: Path,
    ptrid: int | None,
    cfg: ExtractConfig,
    *,
    on_progress: Callable[[int], None] | None = None,
) -> tuple[list[PointerChain], dict]:
    suffix = input_path.suffix.lower()
    if suffix in (".db", ".sqlite", ".sqlite3"):
        resolved_ptrid = ptrid or cfg.ptrid
        module_ids = _resolve_module_ids(input_path, resolved_ptrid, cfg)
        if cfg.stream_single_file:
            meta = load_sqlite_meta(input_path, ptrid=resolved_ptrid)
            if module_ids is None and cfg.sqlite_module_prefilter:
                module_ids = _preferred_module_ids(meta.get("module_map", {}), cfg.preset)
            it = iter_file_chains(input_path, ptrid=resolved_ptrid, module_ids=module_ids)
            chains, total, mod_counts = filter_and_rank_stream(it, cfg, on_progress=on_progress)
            return chains, {
                "ptrid": meta.get("ptrid"),
                "ptrids_available": meta.get("ptrids_available", []),
                "module_count": meta.get("module_count", 0),
                "modules": meta.get("modules", []),
                "result_count": total,
                "module_prefilter": sorted(module_ids) if module_ids else None,
                "_module_counts": mod_counts,
                "_streamed": True,
            }
        return load_sqlite(input_path, ptrid=resolved_ptrid, module_ids=module_ids)
    if suffix == ".ptr":
        if cfg.stream_single_file:
            it = iter_ptr_chains(input_path)
            chains, total, mod_counts = filter_and_rank_stream(it, cfg, on_progress=on_progress)
            meta = load_ptr_meta(input_path)
            meta["result_count"] = total
            meta["_module_counts"] = mod_counts
            meta["_streamed"] = True
            return chains, meta
        from ce_base_extractor.parsers.ptr_parser import load_ptr

        return load_ptr(input_path)
    raise ValueError(f"不支持的文件类型: {suffix}，请使用 .sqlite / .db 或 .PTR")


def extract(
    input_file: str | Path,
    config: ExtractConfig | None = None,
    config_path: str | Path | None = None,
    extra_files: list[str | Path] | None = None,
    *,
    on_progress: Callable[[int], None] | None = None,
) -> ExtractResult:
    cfg = config or load_config(config_path)
    input_path = Path(input_file)

    cross_meta: dict | None = None
    ptrid: int | None = None
    modules_seen: list[str] = []
    live_probe_meta: list[dict] | None = None
    module_counts: dict[str, int] | None = None
    chains: list[PointerChain]
    streamed = False

    if extra_files:
        all_files = [input_path, *[Path(f) for f in extra_files]]
        min_occ = max(cfg.cross_validate_min, 2)
        module_ids = _resolve_module_ids(input_path, cfg.ptrid, cfg)
        chains, cross_meta = cross_validate_files(
            all_files,
            min_occurrences=min_occ,
            ptrid=cfg.ptrid,
            require_all=cfg.cross_validate_require_all,
            module_ids=module_ids,
            fuzzy=cfg.cross_validate_fuzzy,
            fuzzy_last_offset_step=cfg.fuzzy_last_offset_step,
            sqlite_threshold=cfg.cross_validate_sqlite_threshold,
            force_sqlite_backend=cfg.cross_validate_force_sqlite,
            cfg=cfg,
        )
        total_raw = int(cross_meta.get("stable_keys", len(chains)))
        if cross_meta.get("ranked"):
            streamed = True
            module_counts = cross_meta.get("_module_counts")
        modules_seen = sorted({c.module_name for c in chains})
        ptrid = cfg.ptrid
        source = ", ".join(str(p.name) for p in all_files)
    else:
        loaded, meta = _load_chains(input_path, cfg.ptrid, cfg, on_progress=on_progress)
        streamed = bool(meta.get("_streamed"))
        if streamed:
            chains = loaded
            total_raw = int(meta.get("result_count", len(chains)))
            module_counts = meta.get("_module_counts")
        else:
            chains = loaded
            total_raw = int(meta.get("result_count", len(chains)))
        modules_seen = list(meta.get("modules", []))
        ptrid = meta.get("ptrid")
        source = str(input_path)

    il2cpp_map = load_il2cpp_map(cfg.il2cpp_map_path)
    if il2cpp_map:
        chains = apply_il2cpp_hints(chains, il2cpp_map)

    if streamed:
        ranked = chains
    else:
        ranked = filter_and_rank(chains, cfg)

    if cfg.live_probe and ranked:
        ranked, probe_results = probe_chains(ranked, cfg, il2cpp_map=il2cpp_map or None)
        live_probe_meta = [
            {
                "readable": r.readable,
                "error": r.error,
                "module": r.chain.module_name,
                "offsets": list(r.chain.offsets),
                "value_type": r.chain.value_type,
            }
            for r in probe_results
        ]
        ranked = ranked[: cfg.top_n]

    if module_counts is not None:
        stats = module_stats_from_counts(module_counts, cfg.emulator_mode)
    else:
        from ce_base_extractor.stats.module_stats import compute_module_stats

        stats = compute_module_stats(ranked, cfg.emulator_mode)

    if not modules_seen:
        modules_seen = sorted({c.module_name for c in ranked})

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
