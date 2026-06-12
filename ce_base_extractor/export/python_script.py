from __future__ import annotations

from pathlib import Path

from ce_base_extractor.filters.presets import EmulatorPreset, get_preset
from ce_base_extractor.models import ExtractResult, PointerChain

READER_EMBED = r'''
"""Windows 进程内存读取（内嵌，ce-base-extractor 生成）。"""
from __future__ import annotations
import ctypes, struct
from ctypes import wintypes

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
TH32CS_SNAPPROCESS = 0x00000002
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
        ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_char * 260)]

class MODULEENTRY32(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("th32ModuleID", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD), ("GlblcntUsage", wintypes.DWORD),
        ("ProccntUsage", wintypes.DWORD), ("modBaseAddr", ctypes.POINTER(ctypes.c_byte)),
        ("modBaseSize", wintypes.DWORD), ("hModule", wintypes.HMODULE),
        ("szModule", ctypes.c_char * 256), ("szExePath", ctypes.c_char * 260)]

class ProcessMemory:
    def __init__(self, pid: int, process_name: str):
        self.pid, self.process_name = pid, process_name
        self._handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
        if not self._handle:
            raise OSError(f"无法打开进程 PID={pid}")

    def close(self):
        if self._handle:
            kernel32.CloseHandle(self._handle)
            self._handle = None

    def __enter__(self): return self
    def __exit__(self, *_): self.close()

    @classmethod
    def list_matching(cls, process_names):
        names = {n.lower() for n in process_names}
        snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        entry = PROCESSENTRY32(); entry.dwSize = ctypes.sizeof(PROCESSENTRY32)
        found = []
        try:
            kernel32.Process32First(snap, ctypes.byref(entry))
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
    def auto_attach(cls, process_names, pid=None):
        if pid is not None:
            return cls(int(pid), "selected")
        matches = cls.list_matching(process_names)
        if not matches:
            raise ProcessLookupError(f"未找到进程: {process_names}")
        return cls(matches[0][0], matches[0][1])

    def list_modules(self):
        snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, self.pid)
        entry = MODULEENTRY32(); entry.dwSize = ctypes.sizeof(MODULEENTRY32)
        modules = {}
        try:
            kernel32.Module32First(snap, ctypes.byref(entry))
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
        ok = kernel32.ReadProcessMemory(self._handle, ctypes.c_void_p(address), buf, size, ctypes.byref(read))
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

    def resolve_chain(self, module_name: str, module_offset: int, offsets, pointer_size: int = 8) -> int:
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
'''


def _format_chain_dict(chain: PointerChain, index: int) -> str:
    name = chain.export_name(index)
    parts = [
        f'        "name": {name!r},',
        f'        "module": {chain.module_name!r},',
        f'        "module_offset": 0x{chain.module_offset:X},',
        f'        "offsets": {list(chain.offsets)!r},',
        f'        "type": {chain.value_type!r},',
        f'        "verified": {str(chain.verified)},',
    ]
    if chain.il2cpp_symbol:
        parts.append(f'        "il2cpp_symbol": {chain.il2cpp_symbol!r},')
    parts.append(f'        "score": {chain.score:.1f},')
    return "    {\n" + "\n".join(parts) + "\n    }"


def chains_to_python_script(
    chains: list[PointerChain],
    preset: EmulatorPreset | None = None,
    game_name: str = "game",
    pointer_size: int = 8,
    target_pid: int | None = None,
    embed_reader: bool = True,
) -> str:
    preset = preset or get_preset("ldplayer")
    assert preset is not None
    process_names = repr(list(preset.process_names))
    chain_blocks = ",\n".join(_format_chain_dict(c, i) for i, c in enumerate(chains, 1))
    pid_line = f"TARGET_PID = {target_pid}" if target_pid else "TARGET_PID = None"
    reader_block = READER_EMBED if embed_reader else "# from ce_base_extractor.runtime.win_memory import ProcessMemory\n"
    attach_line = "ProcessMemory.auto_attach(PROCESS_NAMES, pid=TARGET_PID)"

    return f'''# -*- coding: utf-8 -*-
"""
自动生成内存读取脚本
游戏: {game_name}
模拟器: {preset.label}
"""
from __future__ import annotations
import argparse
import sys

{reader_block}

PROCESS_NAMES = {process_names}
POINTER_SIZE = {pointer_size}
{pid_line}

CHAINS = [
{chain_blocks}
]

READERS = {{
    "int32": lambda mem, addr: mem.read_i32(addr),
    "uint32": lambda mem, addr: mem.read_u32(addr),
    "int64": lambda mem, addr: mem.read_i64(addr),
    "uint64": lambda mem, addr: mem.read_u64(addr),
    "float": lambda mem, addr: mem.read_f32(addr),
    "double": lambda mem, addr: mem.read_f64(addr),
    "bytes16": lambda mem, addr: mem.read_bytes(addr, 16),
}}


def read_chain(mem: "ProcessMemory", chain: dict):
    addr = mem.resolve_chain(
        chain["module"], chain["module_offset"], chain["offsets"], pointer_size=POINTER_SIZE
    )
    reader = READERS.get(chain.get("type", "int32"))
    if reader is None:
        raise ValueError(f"不支持的类型: {{chain.get('type')}}")
    return reader(mem, addr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="读取 CE 基址数据")
    parser.add_argument("--chain", help="只读取指定字段名")
    parser.add_argument("--pid", type=int, help="指定模拟器进程 PID（多开时用）")
    parser.add_argument("--list-processes", action="store_true", help="列出匹配的模拟器进程")
    parser.add_argument("--list-modules", action="store_true", help="列出模块")
    args = parser.parse_args(argv)

    if args.list_processes:
        for pid, name in ProcessMemory.list_matching(PROCESS_NAMES):
            print(f"PID={{pid}}  {{name}}")
        return 0

    pid = args.pid if args.pid is not None else TARGET_PID
    try:
        mem = {attach_line}
    except (ProcessLookupError, OSError) as exc:
        print(f"附加失败: {{exc}}", file=sys.stderr)
        print("提示: python {game_name}_reader.py --list-processes", file=sys.stderr)
        return 1

    with mem:
        if args.list_modules:
            for name, base in sorted(mem.list_modules().items()):
                print(f"{{name}} @ 0x{{base:X}}")
            return 0

        targets = CHAINS
        if args.chain:
            targets = [c for c in CHAINS if c["name"] == args.chain]
            if not targets:
                print(f"未找到: {{args.chain}}", file=sys.stderr)
                return 1

        for chain in targets:
            try:
                value = read_chain(mem, chain)
                sym = chain.get("il2cpp_symbol", "")
                extra = f"  [{{sym}}]" if sym else ""
                print(f"{{chain['name']}}: {{value}}{{extra}}")
            except Exception as exc:
                print(f"{{chain['name']}}: 失败 - {{exc}}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def result_to_python_script(
    result: ExtractResult,
    preset_id: str = "ldplayer",
    game_name: str = "game",
    pointer_size: int = 8,
    target_pid: int | None = None,
) -> str:
    preset = get_preset(preset_id)
    return chains_to_python_script(
        result.chains,
        preset=preset,
        game_name=game_name,
        pointer_size=pointer_size,
        target_pid=target_pid,
    )


def save_python_script(
    result: ExtractResult,
    output: str | Path,
    preset_id: str = "ldplayer",
    game_name: str = "game",
    pointer_size: int = 8,
    target_pid: int | None = None,
) -> Path:
    path = Path(output)
    path.write_text(
        result_to_python_script(
            result,
            preset_id=preset_id,
            game_name=game_name,
            pointer_size=pointer_size,
            target_pid=target_pid,
        ),
        encoding="utf-8",
    )
    return path
