from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable


class FolderWatcher:
    """监视 CE 导出目录，新 .sqlite 文件出现时回调。"""

    def __init__(
        self,
        folder: str | Path,
        on_new_file: Callable[[Path], None],
        interval: float = 2.0,
        on_error: Callable[[Path, Exception], None] | None = None,
    ) -> None:
        self.folder = Path(folder)
        self.on_new_file = on_new_file
        self.on_error = on_error
        self.interval = interval
        self._seen: set[str] = set()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _scan_existing(self) -> None:
        if not self.folder.is_dir():
            return
        for pattern in ("*.sqlite", "*.db", "*.sqlite3"):
            for p in self.folder.glob(pattern):
                self._seen.add(str(p.resolve()))

    def start(self) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        self._scan_existing()
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    def _loop(self) -> None:
        while not self._stop.is_set():
            if self.folder.is_dir():
                for pattern in ("*.sqlite", "*.db", "*.sqlite3"):
                    for path in self.folder.glob(pattern):
                        key = str(path.resolve())
                        if key not in self._seen:
                            self._seen.add(key)
                            try:
                                self.on_new_file(path)
                            except Exception as exc:
                                if self.on_error:
                                    self.on_error(path, exc)
            time.sleep(self.interval)
