"""Frida guest（Android 子进程）脚本骨架。"""

from __future__ import annotations

from pathlib import Path

from ce_base_extractor.models import ExtractResult


def result_to_frida_guest(result: ExtractResult, *, package: str = "com.example.game") -> str:
    lines = [
        "// ce-base-extractor Frida guest 骨架",
        f"// adb shell pm list packages | findstr game",
        f"// frida -U -f {package} -l this_file.js",
        "",
        "function readChain(moduleName, moduleOffset, offsets, type) {",
        "  const m = Process.findModuleByName(moduleName);",
        "  if (!m) throw new Error('module not found: ' + moduleName);",
        "  let addr = m.base.add(ptr(moduleOffset));",
        "  for (let i = 0; i < offsets.length - 1; i++) {",
        "    addr = addr.add(offsets[i]).readPointer();",
        "    if (addr.isNull()) throw new Error('null pointer');",
        "  }",
        "  if (offsets.length) addr = addr.add(offsets[offsets.length - 1]);",
        "  if (type === 'float') return addr.readFloat();",
        "  if (type === 'int64') return addr.readS64();",
        "  return addr.readS32();",
        "}",
        "",
    ]
    for i, c in enumerate(result.chains, 1):
        name = c.export_name(i)
        offs = ", ".join(f"0x{o:X}" for o in c.offsets)
        vtype = c.value_type or "int32"
        lines.append(
            f"// {name}: {c.module_name}+0x{c.module_offset:X} [{offs}]"
        )
        lines.append(
            f"const {name} = readChain('{c.module_name}', 0x{c.module_offset:X}, "
            f"[{offs}], '{vtype}');"
        )
        lines.append(f"console.log('{name}=', {name});")
        lines.append("")
    return "\n".join(lines)


def save_frida_guest_script(
    result: ExtractResult,
    output: str | Path,
    *,
    package: str = "com.example.game",
) -> Path:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(result_to_frida_guest(result, package=package), encoding="utf-8")
    return path
