from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ce_base_extractor.export.ct_export import result_to_ct
from ce_base_extractor.export.formatter import save_result
from ce_base_extractor.export.python_script import save_python_script
from ce_base_extractor.export.scc_export import save_scc_json
from ce_base_extractor.gui.app import run_gui
from ce_base_extractor.pipeline import extract, load_config


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ce-base-extractor",
        description="CE 指针扫描 → 稳定基址 → Python 读取脚本（雷电优化）",
    )
    p.add_argument("input", nargs="?", help="CE 导出的 .sqlite / .db / .PTR")
    p.add_argument("-o", "--output", help="输出路径")
    p.add_argument("--format", choices=("txt", "json", "py", "ct", "scc"), default="txt")
    p.add_argument("--top", type=int)
    p.add_argument("--max-depth", type=int)
    p.add_argument("--max-offset", type=int)
    p.add_argument("--ptrid", type=int)
    p.add_argument("--preset", default="ldplayer")
    p.add_argument("--game", default="game")
    p.add_argument("--cross", nargs="+")
    p.add_argument("--whitelist", nargs="+")
    p.add_argument("--end-offset", type=lambda x: int(x, 0))
    p.add_argument("--pointer-size", type=int, choices=(4, 8))
    p.add_argument("--pid", type=int, help="目标模拟器 PID")
    p.add_argument("--il2cpp-map", help="Il2Cpp 映射 json/cs 路径")
    p.add_argument("--no-emulator", action="store_true")
    p.add_argument("--gui", action="store_true")
    p.add_argument("--config")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.gui or not args.input:
        run_gui()
        return 0

    cfg = load_config(args.config)
    if args.top is not None:
        cfg.top_n = args.top
    if args.max_depth is not None:
        cfg.max_depth = args.max_depth
    if args.max_offset is not None:
        cfg.max_single_offset = args.max_offset
    if args.ptrid is not None:
        cfg.ptrid = args.ptrid
    if args.no_emulator:
        cfg.emulator_mode = False
    cfg.preset = args.preset
    cfg.game_name = args.game
    if args.whitelist:
        cfg.module_whitelist = args.whitelist
    if args.end_offset is not None:
        cfg.required_end_offset = args.end_offset
    if args.pointer_size is not None:
        cfg.pointer_size = args.pointer_size
    if args.pid is not None:
        cfg.target_pid = args.pid
    if args.il2cpp_map:
        cfg.il2cpp_map_path = args.il2cpp_map

    input_path = Path(args.input)
    result = extract(input_path, config=cfg, extra_files=args.cross)

    if args.format == "py":
        out = args.output or str(input_path.with_name(f"{cfg.game_name}_reader.py"))
        save_python_script(
            result, out, preset_id=cfg.preset, game_name=cfg.game_name,
            pointer_size=cfg.pointer_size, target_pid=cfg.target_pid,
        )
    elif args.format == "ct":
        out = args.output or str(input_path.with_suffix(".CT"))
        Path(out).write_text(result_to_ct(result, title=cfg.game_name), encoding="utf-8")
    elif args.format == "scc":
        out = args.output or str(input_path.with_name(f"{cfg.game_name}_bases_scc.json"))
        save_scc_json(result, out, preset_id=cfg.preset)
    else:
        out = args.output or str(input_path.with_suffix(f".bases.{args.format}"))
        save_result(result, out, fmt=args.format)

    print(f"完成: 原始 {result.total_raw} 条 → 输出 {len(result.chains)} 条 → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
