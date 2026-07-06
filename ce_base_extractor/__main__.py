from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ce_base_extractor.cli_commands import (
    run_diff,
    run_extract,
    run_import_scc,
    run_profile_migrate,
    run_scc_recheck,
    run_verify,
    run_watch,
)
from ce_base_extractor.gui.app import run_gui

WATCH_DEFAULT = str(Path.home() / "Documents" / "ce-exports")


def _add_extract_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("input", help="CE 导出的 .sqlite / .db / .PTR")
    p.add_argument("-o", "--output", help="输出路径或目录（all 格式时为目录）")
    p.add_argument(
        "--format",
        choices=("txt", "json", "py", "ct", "scc", "frida", "lua", "module", "all"),
        default="txt",
    )
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
    p.add_argument("--pid", type=int)
    p.add_argument("--il2cpp-map")
    p.add_argument("--no-emulator", action="store_true")
    p.add_argument("--no-live-probe", action="store_true")
    p.add_argument("--config")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ce-base-extractor",
        description="CE 指针扫描 → 稳定基址 → Python 读取脚本（雷电优化）",
    )
    sub = p.add_subparsers(dest="command")

    extract_p = sub.add_parser("extract", help="从 SQLite/PTR 提取基址")
    _add_extract_args(extract_p)

    diff_p = sub.add_parser("diff", help="对比 2～N 份 SQLite 扫描结果")
    diff_p.add_argument("files", nargs="+", help="SQLite 文件路径")
    diff_p.add_argument("--ptrid", type=int)

    verify_p = sub.add_parser("verify", help="重启后验证已保存的游戏配置")
    verify_p.add_argument("--profile", required=True, help="游戏配置名")
    verify_p.add_argument("--pid", type=int)
    verify_p.add_argument(
        "--require-value-match",
        action="store_true",
        help="除可读外还要求数值与上次记录一致",
    )

    watch_p = sub.add_parser("watch", help="监视 CE 导出目录")
    watch_p.add_argument("folder", nargs="?", default=WATCH_DEFAULT)
    watch_p.add_argument("--interval", type=float, default=2.0)
    watch_p.add_argument("--auto-extract", action="store_true")
    watch_p.add_argument("--incremental-cross", action="store_true")
    watch_p.add_argument("--ptrid", type=int)
    watch_p.add_argument("--game", default="game")
    watch_p.add_argument("--config")

    mig_p = sub.add_parser("profile-migrate", help="对比或迁移游戏 Profile")
    mig_p.add_argument("--profile", required=True)
    mig_p.add_argument("input", nargs="?", help="新 SQLite（与当前 profile 对比）")
    mig_p.add_argument("--compare-with", help="历史版本 ID")
    mig_p.add_argument("--save", action="store_true")

    recheck_p = sub.add_parser("scc-recheck", help="SCC/Profile 定时复检")
    recheck_p.add_argument("--profile", required=True)
    recheck_p.add_argument("--scc")
    recheck_p.add_argument("--pid", type=int)
    recheck_p.add_argument("--require-value-match", action="store_true")

    imp_p = sub.add_parser("import-scc", help="从 SCC JSON 导入并导出")
    imp_p.add_argument("input", help="SCC JSON 路径")
    imp_p.add_argument("-o", "--output")
    imp_p.add_argument(
        "--format",
        choices=("txt", "json", "py", "all"),
        default="py",
    )
    imp_p.add_argument("--preset", default="ldplayer")
    imp_p.add_argument("--game", default="game")

    return p


def _build_legacy_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ce-base-extractor")
    p.add_argument("input", nargs="?")
    p.add_argument("--gui", action="store_true")
    _add_extract_args(p)
    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    if getattr(sys, "frozen", False) and not argv:
        run_gui()
        return 0
    if not argv or argv == ["--gui"] or (len(argv) == 1 and argv[0] == "--gui"):
        run_gui()
        return 0

    subcommands = {
        "extract",
        "diff",
        "verify",
        "watch",
        "import-scc",
        "profile-migrate",
        "scc-recheck",
    }
    if argv[0] in subcommands:
        args = build_parser().parse_args(argv)
        if args.command == "extract":
            return run_extract(args)
        if args.command == "diff":
            return run_diff(args)
        if args.command == "verify":
            return run_verify(args)
        if args.command == "watch":
            return run_watch(args)
        if args.command == "profile-migrate":
            return run_profile_migrate(args)
        if args.command == "scc-recheck":
            return run_scc_recheck(args)
        return run_import_scc(args)

    legacy = _build_legacy_parser()
    args = legacy.parse_args(argv)
    if args.gui or not args.input:
        run_gui()
        return 0
    return run_extract(args)


if __name__ == "__main__":
    sys.exit(main())
