"""GUI 模块共享导入（供 mixins 与 app 使用）。"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from ce_base_extractor.compare.sqlite_diff import diff_sqlite_files, diff_sqlite_many
from ce_base_extractor.export.batch_export import export_all
from ce_base_extractor.export.context import load_export_context
from ce_base_extractor.export.ct_export import result_to_ct
from ce_base_extractor.export.formatter import format_ce_table, to_json, to_text
from ce_base_extractor.export.lua_script import save_lua_script
from ce_base_extractor.export.python_script import save_python_script
from ce_base_extractor.export.scc_export import save_scc_json
from ce_base_extractor.filters.presets import PRESETS, get_preset
from ce_base_extractor.filters.scorer import filter_and_rank
from ce_base_extractor.gui.chain_dialog import open_chain_editor
from ce_base_extractor.gui.process_picker import pick_process
from ce_base_extractor.gui.wizard import show_first_run_wizard
from ce_base_extractor.history.store import HistoryStore
from ce_base_extractor.integrations.scc import scheduled_recheck_profile
from ce_base_extractor.io.scc_import import import_scc_to_result
from ce_base_extractor.models import ExtractConfig, ExtractResult, PointerChain
from ce_base_extractor.parsers.sqlite_parser import list_ptrids
from ce_base_extractor.pipeline import extract, load_config, save_config, wizard_completed
from ce_base_extractor.profiles.migrate import compare_profiles
from ce_base_extractor.profiles.store import GameProfile, ProfileStore
from ce_base_extractor.runtime.win_memory import ProcessMemory, read_chain_value
from ce_base_extractor.suggest.field_names import suggest_field_names
from ce_base_extractor.verify.restart_verify import verify_restart_stability
from ce_base_extractor.watch.folder_watcher import FolderWatcher
from ce_base_extractor.watch.incremental_cross import IncrementalCrossValidator

WATCH_DIR = Path.home() / "Documents" / "ce-exports"

HAS_WINDND = importlib.util.find_spec("windnd") is not None

__all__ = [
    "WATCH_DIR",
    "HAS_WINDND",
    "PRESETS",
    "ExtractConfig",
    "ExtractResult",
    "PointerChain",
    "GameProfile",
    "ProfileStore",
    "HistoryStore",
    "ProcessMemory",
    "IncrementalCrossValidator",
    "FolderWatcher",
    "extract",
    "load_config",
    "save_config",
    "wizard_completed",
    "show_first_run_wizard",
    "format_ce_table",
    "to_text",
    "to_json",
    "export_all",
    "load_export_context",
    "result_to_ct",
    "save_python_script",
    "save_lua_script",
    "save_scc_json",
    "import_scc_to_result",
    "verify_restart_stability",
    "read_chain_value",
    "scheduled_recheck_profile",
    "compare_profiles",
    "diff_sqlite_files",
    "diff_sqlite_many",
    "filter_and_rank",
    "suggest_field_names",
    "open_chain_editor",
    "pick_process",
    "get_preset",
    "list_ptrids",
]
