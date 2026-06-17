"""自包含 ProcessMemory，供导出脚本内嵌（勿添加外部依赖）。"""

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


class ProcessMemory:
    def __init__(self, pid: int, process_name: str) -> None:
        self.pid = pid
        self.process_name = process_name
        self._handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
        if not self._handle:
            raise OSError(f"无法打开进程 PID={pid}")

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
            raise OSError("CreateToolhelp32Snapshot 失败")
        entry = PROCESSENTRY32()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32)
        found: list[tuple[int, str]] = []
        try:
            if not kernel32.Process32First(snap, ctypes.byref(entry)):
                raise OSError("Process32First 失败")
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
            return cls(int(pid), "selected")
        matches = cls.list_matching(process_names)
        if not matches:
            raise ProcessLookupError(f"未找到进程: {list(process_names)}")
        return cls(matches[0][0], matches[0][1])

    def list_modules(self) -> dict[str, int]:
        snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, self.pid)
        if snap == INVALID_HANDLE_VALUE:
            raise OSError("模块枚举失败")
        entry = MODULEENTRY32()
        entry.dwSize = ctypes.sizeof(MODULEENTRY32)
        modules: dict[str, int] = {}
        try:
            if not kernel32.Module32First(snap, ctypes.byref(entry)):
                raise OSError("Module32First 失败")
            while True:
                name = entry.szModule.decode("utf-8", errors="ignore")
                base = ctypes.cast(entry.modBaseAddr, ctypes.c_void_p).value or 0
                modules[name.lower()] = int(base)
                if not kernel32.Module32Next(snap, ctypes.byref(entry)):
                    break
        finally:
            kernel32.CloseHandle(snap)
        return modules

    def get_module_base(self, module_name: str) -> int:
        modules = self.list_modules()
        key = module_name.lower()
        if key in modules:
            return modules[key]
        for name, base in modules.items():
            if key in name or name in key:
                return base
        raise KeyError(f"模块未找到: {module_name}")

    def read_bytes(self, address: int, size: int) -> bytes:
        buf = ctypes.create_string_buffer(size)
        read = ctypes.c_size_t(0)
        ok = kernel32.ReadProcessMemory(
            self._handle, ctypes.c_void_p(address), buf, size, ctypes.byref(read)
        )
        if not ok or read.value < size:
            raise OSError(f"读取失败 @ 0x{address:X}")
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
        fmt = "<Q" if pointer_size == 8 else "<I"
        return struct.unpack(fmt, self.read_bytes(address, pointer_size))[0]

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
