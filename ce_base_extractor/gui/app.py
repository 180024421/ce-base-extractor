from __future__ import annotations

import tkinter as tk

from ce_base_extractor.gui.app_imports import HAS_WINDND, load_config, wizard_completed
from ce_base_extractor.gui.mixins import AuxMixin, CoreMixin, CrossMixin, ExtractMixin, ShellMixin
from ce_base_extractor.gui.theme import THEME, apply_theme
from ce_base_extractor.gui.wizard import show_first_run_wizard
from ce_base_extractor.history.store import HistoryStore
from ce_base_extractor.profiles.store import ProfileStore
from ce_base_extractor.watch.incremental_cross import IncrementalCrossValidator

try:
    import windnd
except ImportError:
    windnd = None  # type: ignore[assignment]


class App(
    tk.Tk,
    ShellMixin,
    CoreMixin,
    ExtractMixin,
    CrossMixin,
    AuxMixin,
):
    def __init__(self) -> None:
        super().__init__()
        self.title("CE 基址提取器")
        self.geometry("1140x760")
        self.minsize(960, 640)

        apply_theme(self)
        self.configure(bg=THEME["bg"])

        self._config = load_config()
        self._current_file = None
        self._extra_files: list = []
        self._result = None
        self._result_text = ""
        self._history = HistoryStore()
        self._watcher = None
        self._module_vars: dict = {}
        self._before_verify: dict = {}
        self._target_pid = self._config.target_pid
        self._profiles = ProfileStore()
        self._monitor_running = False
        self._monitor_job = None
        self._monitor_prev: dict = {}
        self._monitor_errors = 0
        self._extract_busy = False
        self._incremental_cross: IncrementalCrossValidator | None = None
        self._monitor_mem = None

        self._build_ui()
        if HAS_WINDND and windnd is not None:
            windnd.hook_dropfiles(self, func=self._on_drop)
        if not wizard_completed():
            self.after(300, lambda: show_first_run_wizard(self))


def run_gui() -> None:
    app = App()
    app.mainloop()
