from __future__ import annotations

import re

# 模拟器宿主进程（CE 附加时常作为主模块出现）
EMULATOR_HOST_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"dnplayer\.exe",
        r"ldplayer",
        r"ldbox",
        r"ldvbox",
        r"nox",
        r"mumu",
        r"nemu",
        r"hd-player",
        r"bluestacks",
        r"memu",
        r"androidprocess",
        r"vboxheadless",
    )
]

# Android 游戏本体模块（模拟器内 CE 扫描时的高价值模块）
ANDROID_GAME_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"libil2cpp\.so",
        r"libunity\.so",
        r"libmain\.so",
        r"libue4\.so",
        r"libgame\.so",
        r"libnative\.so",
        r"libcocos",
        r"libpgl\.so",
        r"classes\.dex",
        r"libboot\.so",
        r"global-metadata\.dat",
    )
]

# 应降权或排除的系统模块
SYSTEM_DEPRIORITIZE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"ntdll\.dll",
        r"kernel32\.dll",
        r"kernelbase\.dll",
        r"ucrtbase\.dll",
        r"msvcrt\.dll",
        r"user32\.dll",
        r"gdi32\.dll",
        r"advapi32\.dll",
        r"libc\.so",
        r"libdl\.so",
        r"libm\.so",
        r"linker",
        r"libart\.so",
        r"libandroid_runtime\.so",
    )
]

# 动态/随机模块名（ASLR 临时映射）
RANDOM_MODULE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"^[0-9a-f]{8,}\.dll$",
        r"^tmp",
        r"^temp",
        r"\.tmp$",
        r"^\d+\.so$",
    )
]


def _matches(patterns: list[re.Pattern[str]], name: str) -> bool:
    return any(p.search(name) for p in patterns)


def module_tier(module_name: str, emulator_mode: bool) -> int:
    """
    模块优先级分层，数字越大越好。
    3 = Android 游戏模块
    2 = 模拟器宿主
    1 = 普通模块
    0 = 系统模块
    -1 = 随机/垃圾模块
    """
    if _matches(RANDOM_MODULE_PATTERNS, module_name):
        return -1
    if _matches(SYSTEM_DEPRIORITIZE_PATTERNS, module_name):
        return 0
    if emulator_mode and _matches(ANDROID_GAME_PATTERNS, module_name):
        return 3
    if emulator_mode and _matches(EMULATOR_HOST_PATTERNS, module_name):
        return 2
    return 1
