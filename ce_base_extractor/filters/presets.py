from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmulatorPreset:
    id: str
    label: str
    process_names: tuple[str, ...]
    host_module_patterns: tuple[str, ...]
    preferred_modules: tuple[str, ...]
    score_bonus_modules: tuple[str, ...]


PRESETS: dict[str, EmulatorPreset] = {
    "ldplayer": EmulatorPreset(
        id="ldplayer",
        label="雷电模拟器",
        process_names=(
            "dnplayer.exe",
            "ldplayer.exe",
            "ldboxheadless.exe",
            "ldvboxheadless.exe",
            "ld9boxheadless.exe",
        ),
        host_module_patterns=("dnplayer", "ldplayer", "ldbox", "ldvbox"),
        preferred_modules=(
            "libil2cpp.so",
            "libunity.so",
            "libmain.so",
            "libgame.so",
        ),
        score_bonus_modules=("libil2cpp.so", "libunity.so"),
    ),
    "mumu": EmulatorPreset(
        id="mumu",
        label="MuMu 模拟器",
        process_names=("nemuplayer.exe", "nemuheadless.exe", "mumunxdevice.exe"),
        host_module_patterns=("nemu", "mumu"),
        preferred_modules=("libil2cpp.so", "libunity.so", "libmain.so"),
        score_bonus_modules=("libil2cpp.so",),
    ),
    "nox": EmulatorPreset(
        id="nox",
        label="夜神模拟器",
        process_names=("nox.exe", "noxvmhandle.exe", "noxplayer.exe"),
        host_module_patterns=("nox",),
        preferred_modules=("libil2cpp.so", "libunity.so"),
        score_bonus_modules=("libil2cpp.so",),
    ),
    "bluestacks": EmulatorPreset(
        id="bluestacks",
        label="蓝叠模拟器",
        process_names=("hd-player.exe", "hd-agent.exe", "bluestacks.exe"),
        host_module_patterns=("hd-player", "bluestacks"),
        preferred_modules=("libil2cpp.so", "libunity.so"),
        score_bonus_modules=("libil2cpp.so",),
    ),
    "xiaoyao": EmulatorPreset(
        id="xiaoyao",
        label="逍遥模拟器",
        process_names=("memu.exe", "memuheadless.exe", "microvirt.exe"),
        host_module_patterns=("memu", "microvirt", "xiaoyao"),
        preferred_modules=("libil2cpp.so", "libunity.so", "libmain.so"),
        score_bonus_modules=("libil2cpp.so",),
    ),
    "huawei": EmulatorPreset(
        id="huawei",
        label="华为移动引擎",
        process_names=("hwemu.exe", "hwandroid.exe", "hvmheadless.exe"),
        host_module_patterns=("hwemu", "hwandroid", "hvm"),
        preferred_modules=("libil2cpp.so", "libunity.so"),
        score_bonus_modules=("libil2cpp.so",),
    ),
    "ldplayer9": EmulatorPreset(
        id="ldplayer9",
        label="雷电 9 多开",
        process_names=(
            "dnplayer.exe",
            "ld9boxheadless.exe",
            "ldboxheadless.exe",
            "ldvboxheadless.exe",
        ),
        host_module_patterns=("dnplayer", "ldbox", "ld9box", "ldvbox"),
        preferred_modules=("libil2cpp.so", "libunity.so", "libmain.so"),
        score_bonus_modules=("libil2cpp.so", "libunity.so"),
    ),
}


DEFAULT_PRESET = "ldplayer"


def get_preset(preset_id: str | None) -> EmulatorPreset | None:
    if not preset_id:
        return PRESETS.get(DEFAULT_PRESET)
    return PRESETS.get(preset_id)
