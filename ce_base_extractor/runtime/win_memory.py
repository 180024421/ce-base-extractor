"""Windows 进程内存读取（雷电模拟器 dnplayer.exe 等）。"""

from __future__ import annotations

import ctypes
import struct
from ctypes import wintypes
from typing import Iterable

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)

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
        self._handle = kernel32.OpenProcess(
            PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid
        )
        if not self._handle:
            _raise_last_error(f"无法打开进程 PID={pid}")

    def close(self) -> None:
        if self._handle:
            kernel32.CloseHandle(self._handle)
            self._handle = None

    def __enter__(self) -> ProcessMemory:
        return self

    def __exit__(self, *_args) -> None:
        self.close()

    @classmethod
    def find_pid(cls, process_names: Iterable[str]) -> tuple[int, str]:
        names = {n.lower() for n in process_names}
        snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if snap == INVALID_HANDLE_VALUE:
            _raise_last_error("CreateToolhelp32Snapshot 失败")

        entry = PROCESSENTRY32()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32)
        try:
            if not kernel32.Process32First(snap, ctypes.byref(entry)):
                _raise_last_error("Process32First 失败")
            while True:
                exe = entry.szExeFile.decode("utf-8", errors="ignore").lower()
                if exe in names:
                    return int(entry.th32ProcessID), exe
                if not kernel32.Process32Next(snap, ctypes.byref(entry)):
                    break
        finally:
            kernel32.CloseHandle(snap)
        raise ProcessLookupError(f"未找到进程: {', '.join(process_names)}")

    @classmethod
    def auto_attach(cls, process_names: Iterable[str]) -> ProcessMemory:
        pid, name = cls.find_pid(process_names)
        return cls(pid, name)

    def list_modules(self) -> dict[str, int]:
        snap = kernel32.CreateToolhelp32Snapshot(
            TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, self.pid
        )
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
        return modules

    def get_module_base(self, module_name: str) -> int:
        modules = self.list_modules()
        key = module_name.lower()
        if key not in modules:
            # 模糊匹配（CE 模块名可能与枚举名略有差异）
            for name, base in modules.items():
                if key in name or name in key:
                    return base
            raise KeyError(f"模块未找到: {module_name}")
        return modules[key]

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
            _raise_last_error(f"读取内存失败 @ 0x{address:X}")
        return buf.raw

    def read_u32(self, address: int) -> int:
        return struct.unpack("<I", self.read_bytes(address, 4))[0]

    def read_u64(self, address: int) -> int:
        return struct.unpack("<Q", self.read_bytes(address, 8))[0]

    def read_i32(self, address: int) -> int:
        return struct.unpack("<i", self.read_bytes(address, 4))[0]

    def read_f32(self, address: int) -> float:
        return struct.unpack("<f", self.read_bytes(address, 4))[0]

    def read_pointer(self, address: int, pointer_size: int = 8) -> int:
        if pointer_size == 8:
            return self.read_u64(address)
        return self.read_u32(address)

    def resolve_chain(
        self,
        module_name: str,
        module_offset: int,
        offsets: tuple[int, ...] | list[int],
        pointer_size: int = 8,
    ) -> int:
        address = self.get_module_base(module_name) + module_offset
        if not offsets:
            return address
        for i, off in enumerate(offsets):
            if i < len(offsets) - 1:
                address = self.read_pointer(address + off, pointer_size)
                if address == 0:
                    raise ValueError(f"指针链断裂 @ offset index {i}")
            else:
                address = address + off
        return address


def attach_ldplayer() -> ProcessMemory:
    return ProcessMemory.auto_attach(
        (
            "dnplayer.exe",
            "ldplayer.exe",
            "ldboxheadless.exe",
            "ldvboxheadless.exe",
            "ld9boxheadless.exe",
        )
    )
