from __future__ import annotations

import json
import sys
from pathlib import Path

from ce_base_extractor.compare.sqlite_diff import diff_sqlite_files, diff_sqlite_many
from ce_base_extractor.export.batch_export import export_all
from ce_base_extractor.export.ct_export import result_to_ct
from ce_base_extractor.export.formatter import save_result
from ce_base_extractor.export.frida_script import save_frida_script
from ce_base_extractor.export.python_module import save_python_module
from ce_base_extractor.export.python_script import save_python_script
from ce_base_extractor.export.scc_export import save_scc_json
from ce_base_extractor.io.scc_import import import_scc_to_result
from ce_base_extractor.pipeline import extract, load_config
from ce_base_extractor.profiles.store import ProfileStore
from ce_base_extractor.verify.restart_verify import verify_restart_stability
from ce_base_extractor.watch.folder_watcher import FolderWatcher


def run_extract(args) -> int:
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

    if args.format == "all":
        out_dir = args.output or str(input_path.parent / f"{cfg.game_name}_export")
        files = export_all(
            result,
            out_dir,
            game_name=cfg.game_name,
            preset_id=cfg.preset,
            pointer_size=cfg.pointer_size,
            target_pid=cfg.target_pid,
        )
        print(f"完成: 导出 {len(files)} 个文件 → {out_dir}")
        return 0

    if args.format == "py":
        out = args.output or str(input_path.with_name(f"{cfg.game_name}_reader.py"))
        save_python_script(
            result,
            out,
            preset_id=cfg.preset,
            game_name=cfg.game_name,
            pointer_size=cfg.pointer_size,
            target_pid=cfg.target_pid,
        )
    elif args.format == "ct":
        out = args.output or str(input_path.with_suffix(".CT"))
        Path(out).write_text(result_to_ct(result, title=cfg.game_name), encoding="utf-8")
    elif args.format == "scc":
        out = args.output or str(input_path.with_name(f"{cfg.game_name}_scc.json"))
        save_scc_json(result, out, preset_id=cfg.preset)
    elif args.format == "frida":
        out = args.output or str(input_path.with_name(f"{cfg.game_name}_frida.js"))
        save_frida_script(result, out, game_name=cfg.game_name, preset_id=cfg.preset)
    elif args.format == "module":
        out = args.output or str(input_path.with_name(f"{cfg.game_name}_memory.py"))
        save_python_module(
            result,
            out,
            game_name=cfg.game_name,
            pointer_size=cfg.pointer_size,
            target_pid=cfg.target_pid,
        )
    else:
        out = args.output or str(input_path.with_suffix(f".bases.{args.format}"))
        save_result(result, out, fmt=args.format)

    print(f"完成: 原始 {result.total_raw} 条 → 输出 {len(result.chains)} 条 → {out}")
    return 0


def run_diff(args) -> int:
    ptrid = args.ptrid
    if len(args.files) == 2:
        diff = diff_sqlite_files(args.files[0], args.files[1], ptrid=ptrid)
        print(json.dumps(diff, ensure_ascii=False, indent=2))
    else:
        diff = diff_sqlite_many(args.files, ptrid=ptrid)
        print(json.dumps(diff, ensure_ascii=False, indent=2))
    return 0


def run_verify(args) -> int:
    store = ProfileStore()
    profile = store.load(args.profile)
    chains = profile.to_result().chains
    if not chains:
        print("配置中没有指针链", file=sys.stderr)
        return 1
    results = verify_restart_stability(
        chains,
        {},
        preset_id=profile.preset,
        pointer_size=profile.pointer_size,
        pid=args.pid or profile.target_pid,
        require_value_match=args.require_value_match,
    )
    ok = sum(1 for r in results if r.stable)
    for i, r in enumerate(results, 1):
        name = r.chain.export_name(i)
        if r.error:
            status = f"失败: {r.error}"
        elif r.stable:
            extra = ""
            if r.value_unchanged is False:
                extra = f" (可读, 数值变化 {r.before} → {r.after})"
            status = f"稳定 ✓{extra}"
        else:
            status = "不稳定"
        print(f"{name}: {status}")
    print(f"\n稳定 {ok}/{len(results)}")
    return 0 if ok == len(results) else 2


def run_watch(args) -> int:
    folder = Path(args.folder)
    folder.mkdir(parents=True, exist_ok=True)
    print(f"监视目录: {folder.resolve()}  (Ctrl+C 退出)")

    def on_new(path: Path) -> None:
        print(f"[新文件] {path.name}")
        if args.auto_extract:
            cfg = load_config(args.config)
            cfg.game_name = args.game
            try:
                result = extract(path, config=cfg)
                print(f"  提取: {len(result.chains)} 条稳定链")
            except Exception as exc:
                print(f"  提取失败: {exc}", file=sys.stderr)

    watcher = FolderWatcher(folder, on_new, interval=args.interval)
    watcher.start()
    try:
        while True:
            import time

            time.sleep(1)
    except KeyboardInterrupt:
        watcher.stop()
        print("\n已停止监视")
    return 0


def run_import_scc(args) -> int:
    result = import_scc_to_result(args.input)
    fmt = args.format
    out = args.output
    game = args.game

    if fmt == "py":
        path = out or str(Path(args.input).with_name(f"{game}_reader.py"))
        save_python_script(result, path, preset_id=args.preset, game_name=game)
    elif fmt == "all":
        out_dir = out or str(Path(args.input).parent / f"{game}_export")
        export_all(result, out_dir, game_name=game, preset_id=args.preset)
        print(f"导出到 {out_dir}")
        return 0
    else:
        path = out or str(Path(args.input).with_suffix(f".bases.{fmt}"))
        save_result(result, path, fmt=fmt)

    print(f"完成 → {path}")
    return 0
