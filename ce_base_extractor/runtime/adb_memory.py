"""ADB 侧内存读取骨架（guest 进程，需 root 或可读 /proc/pid/mem）。"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass


@dataclass
class AdbProcess:
    pid: int
    name: str


class AdbMemoryReader:
    """通过 adb shell 枚举进程并读取 maps（骨架，不依赖真实设备测试）。"""

    def __init__(self, serial: str | None = None, adb: str = "adb") -> None:
        self.serial = serial
        self.adb = adb

    def _adb(self, *args: str) -> str:
        cmd = [self.adb]
        if self.serial:
            cmd.extend(["-s", self.serial])
        cmd.extend(args)
        proc = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore"
        )
        return (proc.stdout or proc.stderr or "").strip()

    def list_processes(self, filter_sub: str = "") -> list[AdbProcess]:
        out = self._adb("shell", "ps", "-A")
        procs: list[AdbProcess] = []
        for line in out.splitlines()[1:]:
            parts = line.split()
            if len(parts) < 9:
                continue
            pid = int(parts[1])
            name = parts[-1]
            if filter_sub and filter_sub not in name:
                continue
            procs.append(AdbProcess(pid=pid, name=name))
        return procs

    def module_base_from_maps(self, pid: int, module_sub: str) -> int | None:
        maps = self._adb("shell", "cat", f"/proc/{pid}/maps")
        for line in maps.splitlines():
            if module_sub.lower() not in line.lower():
                continue
            m = re.match(r"([0-9a-f]+)-", line)
            if m:
                return int(m.group(1), 16)
        return None
