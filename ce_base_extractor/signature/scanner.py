"""在进程可读内存中扫描 AOB 特征码。"""

from __future__ import annotations

import ctypes
from collections.abc import Callable
from ctypes import wintypes
from dataclasses import dataclass

from ce_base_extractor.runtime.win_memory import ProcessMemory
from ce_base_extractor.signature import find_pattern_in_buffer, parse_pattern

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100
PAGE_EXECUTE_READ = 0x20
PAGE_EXECUTE_READWRITE = 0x40
PAGE_EXECUTE_WRITECOPY = 0x80
PAGE_READONLY = 0x02
PAGE_READWRITE = 0x04
PAGE_WRITECOPY = 0x08
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wintypes.DWORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wintypes.DWORD),
        ("Protect", wintypes.DWORD),
        ("Type", wintypes.DWORD),
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


def _is_readable(protect: int) -> bool:
    if protect & PAGE_GUARD:
        return False
    readable = {
        PAGE_READONLY,
        PAGE_READWRITE,
        PAGE_WRITECOPY,
        PAGE_EXECUTE_READ,
        PAGE_EXECUTE_READWRITE,
        PAGE_EXECUTE_WRITECOPY,
    }
    return (protect & 0xFF) in readable


@dataclass
class MemoryRegion:
    start: int
    size: int
    label: str = ""


@dataclass
class ModuleRange:
    name: str
    base: int
    size: int


ProgressCb = Callable[[float, str], None]


def list_modules_detailed(mem: ProcessMemory) -> list[ModuleRange]:
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, mem.pid)
    if snap == INVALID_HANDLE_VALUE:
        return []
    entry = MODULEENTRY32()
    entry.dwSize = ctypes.sizeof(MODULEENTRY32)
    out: list[ModuleRange] = []
    try:
        if not kernel32.Module32First(snap, ctypes.byref(entry)):
            return []
        while True:
            name = entry.szModule.decode("utf-8", errors="ignore")
            base = ctypes.cast(entry.modBaseAddr, ctypes.c_void_p).value or 0
            size = int(entry.modBaseSize)
            if base and size > 0:
                out.append(ModuleRange(name=name, base=int(base), size=size))
            if not kernel32.Module32Next(snap, ctypes.byref(entry)):
                break
    finally:
        kernel32.CloseHandle(snap)
    return out


def list_readable_regions(
    mem: ProcessMemory,
    *,
    max_region: int = 48 * 1024 * 1024,
    module_filter: str | None = None,
    region_mode: str = "all",
) -> list[MemoryRegion]:
    """列举可读区域。

    region_mode:
      - all: 全部可读
      - modules: 仅模块映像（可再加 module_filter）
      - heap: 排除模块映像（匿名/堆倾向）
    """
    mode = (region_mode or "all").strip().lower()
    all_modules = list_modules_detailed(mem)
    module_ranges: list[ModuleRange] = []
    if module_filter:
        needle = module_filter.strip().lower()
        for m in all_modules:
            if needle in m.name.lower():
                module_ranges.append(m)
        if not module_ranges:
            raise KeyError(f"未找到模块: {module_filter}")
    elif mode == "modules":
        module_ranges = list(all_modules)

    regions: list[MemoryRegion] = []
    address = 0
    mbi = MEMORY_BASIC_INFORMATION()
    while True:
        got = kernel32.VirtualQueryEx(
            mem._handle,
            ctypes.c_void_p(address),
            ctypes.byref(mbi),
            ctypes.sizeof(mbi),
        )
        if not got:
            break
        base = int(mbi.BaseAddress or 0)
        size = int(mbi.RegionSize or 0)
        if size <= 0:
            break
        if mbi.State == MEM_COMMIT and _is_readable(int(mbi.Protect)) and size <= max_region:
            if mode == "modules" or module_filter:
                for mr in module_ranges:
                    start = max(base, mr.base)
                    end = min(base + size, mr.base + mr.size)
                    if end > start:
                        regions.append(MemoryRegion(start=start, size=end - start, label=mr.name))
            elif mode == "heap":
                # 跳过与任意模块重叠的区域
                overlaps = False
                for mr in all_modules:
                    start = max(base, mr.base)
                    end = min(base + size, mr.base + mr.size)
                    if end > start:
                        overlaps = True
                        break
                if not overlaps:
                    regions.append(MemoryRegion(start=base, size=size, label="heap"))
            else:
                regions.append(MemoryRegion(start=base, size=size))
        next_addr = base + size
        if next_addr <= address:
            break
        address = next_addr
        if address >= 0x7FFFFFFFFFFF:
            break
    return regions


def scan_process(
    mem: ProcessMemory,
    pattern_text: str,
    *,
    max_hits: int = 64,
    chunk_size: int = 1024 * 1024,
    max_region: int = 48 * 1024 * 1024,
    module_filter: str | None = None,
    region_mode: str = "all",
    stop_when_unique: bool = False,
    progress: ProgressCb | None = None,
    cancel: Callable[[], bool] | None = None,
) -> list[int]:
    pattern, mask = parse_pattern(pattern_text)
    if not any(mask):
        raise ValueError("特征码没有固定字节，无法扫描")
    regions = list_readable_regions(
        mem,
        max_region=max_region,
        module_filter=module_filter,
        region_mode=region_mode,
    )
    total = sum(r.size for r in regions) or 1
    done = 0
    hits: list[int] = []
    plen = len(pattern)
    for region in regions:
        if cancel and cancel():
            break
        if len(hits) >= max_hits:
            break
        if stop_when_unique and len(hits) == 1:
            break
        offset = 0
        overlap = max(plen - 1, 0)
        while offset < region.size and len(hits) < max_hits:
            if cancel and cancel():
                break
            if stop_when_unique and len(hits) == 1:
                break
            to_read = min(chunk_size, region.size - offset)
            if to_read < plen:
                break
            addr = region.start + offset
            try:
                buf = mem.read_bytes(addr, to_read)
            except OSError:
                break
            found = find_pattern_in_buffer(
                buf,
                pattern,
                mask,
                base_address=addr,
                max_hits=max_hits - len(hits),
            )
            hits.extend(found)
            advance = to_read - overlap if to_read > overlap else to_read
            offset += advance
            done += advance
            if progress:
                progress(min(1.0, done / total), region.label or f"0x{region.start:X}")
    if progress:
        progress(1.0, "完成")
    return hits


def count_pattern_hits(
    mem: ProcessMemory,
    pattern_text: str,
    *,
    max_hits: int = 8,
    module_filter: str | None = None,
    region_mode: str = "all",
) -> int:
    return len(
        scan_process(
            mem,
            pattern_text,
            max_hits=max_hits,
            module_filter=module_filter,
            region_mode=region_mode,
        )
    )
