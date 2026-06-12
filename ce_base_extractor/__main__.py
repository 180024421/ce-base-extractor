from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ce_base_extractor.gui.app import run_gui
from ce_base_extractor.models import ExtractConfig
from ce_base_extractor.pipeline import extract_and_save, load_config


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ce-base-extractor",
        description="从 CE 指针扫描 SQLite/PTR 结果中一键提取稳定基址（模拟器优化）",
    )
    p.add_argument("input", nargs="?", help="CE 导出的 .sqlite / .db / .PTR 文件")
    p.add_argument("-o", "--output", help="输出文件路径")
    p.add_argument("--format", choices=("txt", "json"), default="txt", help="输出格式")
    p.add_argument("--top", type=int, help="输出前 N 条")
    p.add_argument("--max-depth", type=int, help="最大偏移层级")
    p.add_argument("--max-offset", type=int, help="单级偏移上限（十进制）")
    p.add_argument("--ptrid", type=int, help="SQLite 中的 ptrid（默认取最新）")
    p.add_argument("--no-emulator", action="store_true", help="关闭模拟器模块优先策略")
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

    input_path = Path(args.input)
    output = args.output
    if not output:
        output = str(input_path.with_suffix(f".bases.{args.format}"))

    result = extract_and_save(input_path, output, fmt=args.format, config=cfg)
    print(f"完成: 原始 {result.total_raw} 条 → 输出 {len(result.chains)} 条 → {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
