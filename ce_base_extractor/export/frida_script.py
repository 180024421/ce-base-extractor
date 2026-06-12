from __future__ import annotations

from pathlib import Path

from ce_base_extractor.filters.presets import get_preset
from ce_base_extractor.models import ExtractResult, PointerChain


def chains_to_frida_script(
    chains: list[PointerChain],
    game_name: str = "game",
    preset_id: str = "ldplayer",
) -> str:
    preset = get_preset(preset_id)
    process_names = list(preset.process_names) if preset else ["dnplayer.exe"]
    items = []
    for i, c in enumerate(chains, 1):
        name = c.export_name(i)
        offsets_js = ", ".join(f"0x{o:X}" for o in c.offsets)
        items.append(
            f'  {{ name: "{name}", module: "{c.module_name}", '
            f"base: 0x{c.module_offset:X}, offsets: [{offsets_js}], type: '{c.value_type}' }}"
        )
    chains_js = ",\n".join(items)
    proc_array = ", ".join(f'"{p}"' for p in process_names)

    return f"""// Frida 脚本 · {game_name} · 由 ce-base-extractor 生成
// frida -n dnplayer.exe -l {game_name}_frida.js

const PROCESS_NAMES = [{proc_array}];
const CHAINS = [
{chains_js}
];

function findModule(name) {{
  const m = Process.findModuleByName(name);
  if (m) return m;
  return Process.enumerateModules().find(mod => mod.name.indexOf(name) >= 0);
}}

function resolveChain(chain) {{
  const mod = findModule(chain.module);
  if (!mod) throw new Error('module not found: ' + chain.module);
  let addr = mod.base.add(chain.base);
  for (let i = 0; i < chain.offsets.length; i++) {{
    const off = chain.offsets[i];
    if (i < chain.offsets.length - 1) {{
      addr = addr.add(off).readPointer();
    }} else {{
      addr = addr.add(off);
    }}
  }}
  return addr;
}}

function readValue(addr, type) {{
  if (type === 'float') return addr.readFloat();
  if (type === 'double') return addr.readDouble();
  if (type === 'uint32') return addr.readU32();
  if (type === 'int64') return addr.readS64();
  return addr.readS32();
}}

CHAINS.forEach(chain => {{
  try {{
    const addr = resolveChain(chain);
    const val = readValue(addr, chain.type);
    console.log(chain.name + ': ' + val + ' @ ' + addr);
  }} catch (e) {{
    console.log(chain.name + ': ERROR ' + e);
  }}
}});
"""


def save_frida_script(
    result: ExtractResult,
    output: str | Path,
    game_name: str = "game",
    preset_id: str = "ldplayer",
) -> Path:
    path = Path(output)
    path.write_text(
        chains_to_frida_script(result.chains, game_name=game_name, preset_id=preset_id),
        encoding="utf-8",
    )
    return path
