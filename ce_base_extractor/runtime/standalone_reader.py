"""自包含 ProcessMemory，供导出脚本内嵌（勿添加外部依赖）。

与 ce_base_extractor.runtime.win_memory 能力对齐：
模块缓存、PID 校验、模糊模块名匹配、缓存失效。
"""

from __future__ import annotations

import ctypes
import struct
from ctypes import wintypes

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
TH32CS_SNAPPROCESS = 0x00000002
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", ctypes.c_char * 260),
    ]


class MODULEENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("th32ModuleID", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("GlblcntUsage", wintypes.DWORD),
        ("ProccntUsage", wintypes.DWORD),
        ("modBaseAddr", ctypes.POINTER(ctypes.c_byte)),
        ("modBaseSize", wintypes.DWORD),
        ("hModule", wintypes.HMODULE),
        ("szModule", ctypes.c_char * 256),
        ("szExePath", ctypes.c_char * 260),
    ]


def _raise_last_error(msg: str) -> None:
    err = ctypes.get_last_error()
    raise OSError(err, f"{msg} (winerror={err})")


class ProcessMemory:
    def __init__(self, pid: int, process_name: str) -> None:
        self.pid = pid
        self.process_name = process_name
        self._handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
        if not self._handle:
            _raise_last_error(f"无法打开进程 PID={pid}")
        self._module_cache: dict[str, int] | None = None

    def close(self) -> None:
        if self._handle:
            kernel32.CloseHandle(self._handle)
            self._handle = None

    def __enter__(self) -> ProcessMemory:
        return self

    def __exit__(self, *_args) -> None:
        self.close()

    @classmethod
    def list_matching(cls, process_names) -> list[tuple[int, str]]:
        names = {n.lower() for n in process_names}
        snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if snap == INVALID_HANDLE_VALUE:
            _raise_last_error("CreateToolhelp32Snapshot 失败")
        entry = PROCESSENTRY32()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32)
        found: list[tuple[int, str]] = []
        try:
            if not kernel32.Process32First(snap, ctypes.byref(entry)):
                _raise_last_error("Process32First 失败")
            while True:
                exe = entry.szExeFile.decode("utf-8", errors="ignore")
                if exe.lower() in names:
                    found.append((int(entry.th32ProcessID), exe))
                if not kernel32.Process32Next(snap, ctypes.byref(entry)):
                    break
        finally:
            kernel32.CloseHandle(snap)
        return found

    @classmethod
    def auto_attach(cls, process_names, pid=None) -> ProcessMemory:
        if pid is not None:
            matches = cls.list_matching(process_names)
            for found_pid, name in matches:
                if found_pid == int(pid):
                    return cls(found_pid, name)
            known = [f"{p}({n})" for p, n in matches]
            raise ProcessLookupError(
                f"PID {pid} 不在预设进程 {list(process_names)} 中；当前匹配: {known or '无'}"
            )
        matches = cls.list_matching(process_names)
        if not matches:
            raise ProcessLookupError(f"未找到进程: {list(process_names)}")
        return cls(matches[0][0], matches[0][1])

    def invalidate_module_cache(self) -> None:
        self._module_cache = None

    def list_modules(self, refresh: bool = False) -> dict[str, int]:
        if self._module_cache is not None and not refresh:
            return self._module_cache
        snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, self.pid)
        if snap == INVALID_HANDLE_VALUE:
            _raise_last_error("模块枚举失败")
        entry = MODULEENTRY32()
        entry.dwSize = ctypes.sizeof(MODULEENTRY32)
        modules: dict[str, int] = {}
        try:
            if not kernel32.Module32First(snap, ctypes.byref(entry)):
                _raise_last_error("Module32First 失败")
            while True:
                name = entry.szModule.decode("utf-8", errors="ignore")
                base = ctypes.cast(entry.modBaseAddr, ctypes.c_void_p).value or 0
                modules[name.lower()] = int(base)
                if not kernel32.Module32Next(snap, ctypes.byref(entry)):
                    break
        finally:
            kernel32.CloseHandle(snap)
        self._module_cache = modules
        return modules

    def get_module_base(self, module_name: str) -> int:
        modules = self.list_modules()
        key = module_name.lower()
        if key in modules:
            return modules[key]
        basename = key.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        if basename in modules:
            return modules[basename]
        candidates: list[tuple[str, int]] = []
        for name, base in modules.items():
            if name == basename or name.endswith(f"/{basename}") or name.endswith(f"\\{basename}"):
                return base
            if name.endswith(key) or key.endswith(name):
                candidates.append((name, base))
        if candidates:
            candidates.sort(key=lambda x: (len(x[0]), x[0]))
            return candidates[0][1]
        sample = ", ".join(sorted(modules.keys())[:6])
        raise KeyError(f"模块未找到: {module_name}；示例: {sample}")

    def read_bytes(self, address: int, size: int) -> bytes:
        buf = ctypes.create_string_buffer(size)
        read = ctypes.c_size_t(0)
        ok = kernel32.ReadProcessMemory(
            self._handle,
            ctypes.c_void_p(address),
            buf,
            size,
            ctypes.byref(read),
        )
        if not ok or read.value < size:
            self.invalidate_module_cache()
            _raise_last_error(f"读取内存失败 @ 0x{address:X}")
        return buf.raw

    def read_i32(self, address: int) -> int:
        return struct.unpack("<i", self.read_bytes(address, 4))[0]

    def read_u32(self, address: int) -> int:
        return struct.unpack("<I", self.read_bytes(address, 4))[0]

    def read_i64(self, address: int) -> int:
        return struct.unpack("<q", self.read_bytes(address, 8))[0]

    def read_u64(self, address: int) -> int:
        return struct.unpack("<Q", self.read_bytes(address, 8))[0]

    def read_f32(self, address: int) -> float:
        return struct.unpack("<f", self.read_bytes(address, 4))[0]

    def read_f64(self, address: int) -> float:
        return struct.unpack("<d", self.read_bytes(address, 8))[0]

    def read_pointer(self, address: int, pointer_size: int = 8) -> int:
        if pointer_size == 8:
            return self.read_u64(address)
        return self.read_u32(address)

    def resolve_chain(
        self, module_name: str, module_offset: int, offsets, pointer_size: int = 8
    ) -> int:
        address = self.get_module_base(module_name) + module_offset
        if not offsets:
            return address
        for i, off in enumerate(offsets):
            if i < len(offsets) - 1:
                address = self.read_pointer(address + off, pointer_size)
                if address == 0:
                    raise ValueError(f"指针链断裂 @ index {i}")
            else:
                address = address + off
        return address
