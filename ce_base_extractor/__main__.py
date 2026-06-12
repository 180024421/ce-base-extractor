from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ce_base_extractor.export.ct_export import result_to_ct
from ce_base_extractor.export.formatter import save_result
from ce_base_extractor.export.python_script import save_python_script
from ce_base_extractor.gui.app import run_gui
from ce_base_extractor.pipeline import extract, load_config


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ce-base-extractor",
        description="从 CE 指针扫描结果提取稳定基址并生成 Python 读取脚本（雷电模拟器优化）",
    )
    p.add_argument("input", nargs="?", help="CE 导出的 .sqlite / .db / .PTR 文件")
    p.add_argument("-o", "--output", help="输出文件路径")
    p.add_argument(
        "--format",
        choices=("txt", "json", "py", "ct"),
        default="txt",
        help="输出格式",
    )
    p.add_argument("--top", type=int, help="输出前 N 条")
    p.add_argument("--max-depth", type=int, help="最大偏移层级")
    p.add_argument("--max-offset", type=int, help="单级偏移上限（十进制）")
    p.add_argument("--ptrid", type=int, help="SQLite ptrid（默认最新）")
    p.add_argument("--preset", default="ldplayer", help="模拟器预设: ldplayer/mumu/nox/bluestacks")
    p.add_argument("--game", default="game", help="游戏名称（Python 脚本用）")
    p.add_argument("--cross", nargs="+", help="交叉验证附加 SQLite 文件")
    p.add_argument("--whitelist", nargs="+", help="模块白名单（支持通配符）")
    p.add_argument("--end-offset", type=lambda x: int(x, 0), help="要求末级偏移（支持 0x 前缀）")
    p.add_argument("--no-emulator", action="store_true", help="关闭模拟器优先策略")
    p.add_argument("--gui", action="store_true", help="启动图形界面")
    p.add_argument("--config", help="自定义配置文件路径")
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

    input_path = Path(args.input)
    result = extract(input_path, config=cfg, extra_files=args.cross)

    if args.format == "py":
        out = args.output or str(input_path.with_name(f"{cfg.game_name}_reader.py"))
        save_python_script(result, out, preset_id=cfg.preset, game_name=cfg.game_name)
    elif args.format == "ct":
        out = args.output or str(input_path.with_suffix(".CT"))
        Path(out).write_text(result_to_ct(result, title=cfg.game_name), encoding="utf-8")
    else:
        out = args.output or str(input_path.with_suffix(f".bases.{args.format}"))
        save_result(result, out, fmt=args.format)

    print(f"完成: 原始 {result.total_raw} 条 → 输出 {len(result.chains)} 条 → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
