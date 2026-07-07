"""ADB 侧内存读取（guest 进程，需 root 或可读 /proc/pid/mem）。"""

from __future__ import annotations

import binascii
import re
import subprocess
from dataclasses import dataclass


@dataclass
class AdbProcess:
    pid: int
    name: str


class AdbMemoryReader:
    """通过 adb shell 枚举进程并读取 maps/mem。"""

    def __init__(self, serial: str | None = None, adb: str = "adb") -> None:
        self.serial = serial
        self.adb = adb
        self._module_cache: dict[int, dict[str, int]] = {}

    def _adb(self, *args: str) -> str:
        cmd = [self.adb]
        if self.serial:
            cmd.extend(["-s", self.serial])
        cmd.extend(args)
        proc = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore"
        )
        if proc.returncode != 0 and not (proc.stdout or proc.stderr):
            raise OSError(f"adb failed: {' '.join(cmd)}")
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

    def invalidate_module_cache(self, pid: int | None = None) -> None:
        if pid is None:
            self._module_cache.clear()
        else:
            self._module_cache.pop(pid, None)

    def list_modules(self, pid: int, refresh: bool = False) -> dict[str, int]:
        if not refresh and pid in self._module_cache:
            return dict(self._module_cache[pid])
        modules: dict[str, int] = {}
        maps = self._adb("shell", "cat", f"/proc/{pid}/maps")
        for line in maps.splitlines():
            if ".so" not in line and "bin" not in line:
                continue
            m = re.match(r"([0-9a-f]+)-[0-9a-f]+\s+\S+\s+\S+\s+\S+\s+\S+\s+(\S+)", line)
            if not m:
                continue
            base = int(m.group(1), 16)
            path = m.group(2)
            name = path.rsplit("/", 1)[-1]
            if name and name not in modules:
                modules[name] = base
        self._module_cache[pid] = modules
        return dict(modules)

    def get_module_base(self, pid: int, module_sub: str, refresh: bool = False) -> int | None:
        modules = self.list_modules(pid, refresh=refresh)
        if module_sub in modules:
            return modules[module_sub]
        key = module_sub.rsplit("/", 1)[-1]
        if key in modules:
            return modules[key]
        for name, base in modules.items():
            if module_sub.lower() in name.lower() or name.lower() in module_sub.lower():
                return base
        return None

    def module_base_from_maps(self, pid: int, module_sub: str) -> int | None:
        return self.get_module_base(pid, module_sub)

    def read_bytes(self, pid: int, address: int, size: int) -> bytes:
        """通过 su + dd 读取 guest 内存（需 root）。"""
        cmd = (
            f"dd if=/proc/{pid}/mem bs=1 skip={address} count={size} 2>/dev/null | xxd -p"
        )
        hex_out = self._adb("shell", "su", "-c", cmd).replace("\n", "").replace(" ", "")
        if not hex_out:
            raise OSError(f"read_bytes failed @ 0x{address:X} pid={pid}")
        data = binascii.unhexlify(hex_out)
        if len(data) < size:
            raise OSError(f"short read {len(data)}/{size} @ 0x{address:X}")
        return data[:size]

    def read_pointer(self, pid: int, address: int, pointer_size: int = 8) -> int:
        raw = self.read_bytes(pid, address, pointer_size)
        if pointer_size == 8:
            return int.from_bytes(raw, "little", signed=False)
        return int.from_bytes(raw[:4], "little", signed=False)

    def resolve_chain(
        self,
        pid: int,
        module_name: str,
        module_offset: int,
        offsets: tuple[int, ...] | list[int],
        pointer_size: int = 8,
    ) -> int:
        base = self.get_module_base(pid, module_name)
        if base is None:
            raise ValueError(f"module not found: {module_name}")
        address = base + module_offset
        if not offsets:
            return address
        for i, off in enumerate(offsets):
            if i < len(offsets) - 1:
                address = self.read_pointer(pid, address + off, pointer_size)
                if address == 0:
                    raise ValueError(f"指针链断裂 @ offset index {i}")
            else:
                address = address + off
        return address
