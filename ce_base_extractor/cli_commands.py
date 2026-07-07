from __future__ import annotations

import json
import sys
from pathlib import Path

from ce_base_extractor.compare.sqlite_diff import diff_sqlite_files, diff_sqlite_many
from ce_base_extractor.export.batch_export import export_all
from ce_base_extractor.export.context import load_export_context
from ce_base_extractor.export.ct_export import result_to_ct
from ce_base_extractor.export.formatter import save_result
from ce_base_extractor.export.frida_script import save_frida_script
from ce_base_extractor.export.lua_script import save_lua_script
from ce_base_extractor.export.python_module import save_python_module
from ce_base_extractor.export.python_script import save_python_script
from ce_base_extractor.export.scc_export import save_scc_json
from ce_base_extractor.io.scc_import import import_scc_to_result
from ce_base_extractor.pipeline import extract, load_config
from ce_base_extractor.profiles.migrate import compare_profiles
from ce_base_extractor.profiles.store import GameProfile, ProfileStore
from ce_base_extractor.verify.restart_verify import verify_restart_stability
from ce_base_extractor.watch.folder_watcher import FolderWatcher
from ce_base_extractor.watch.incremental_cross import IncrementalCrossValidator


def run_list_processes(args) -> int:
    from ce_base_extractor.filters.presets import get_preset
    from ce_base_extractor.runtime.win_memory import ProcessMemory

    preset = get_preset(args.preset)
    names = list(preset.process_names) if preset else ["dnplayer.exe"]
    try:
        processes = ProcessMemory.list_matching(names)
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if not processes:
        print(f"未找到匹配进程: {', '.join(names)}")
        return 1
    for proc in processes:
        print(proc.label)
    return 0


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
    if getattr(args, "no_live_probe", False):
        cfg.live_probe = False
    if getattr(args, "android_package", None):
        cfg.android_package = args.android_package

    input_path = Path(args.input)
    result = extract(input_path, config=cfg, extra_files=args.cross)

    if args.format == "all":
        out_dir = args.output or str(input_path.parent / f"{cfg.game_name}_export")
        snapshots, pkg = load_export_context(cfg.game_name)
        if not cfg.android_package and pkg:
            cfg.android_package = pkg
        files = export_all(
            result,
            out_dir,
            game_name=cfg.game_name,
            preset_id=cfg.preset,
            pointer_size=cfg.pointer_size,
            target_pid=cfg.target_pid,
            android_package=cfg.android_package,
            snapshots=snapshots,
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
    elif args.format == "lua":
        out = args.output or str(input_path.with_name(f"{cfg.game_name}_reader.lua"))
        save_lua_script(result, out)
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
    fuzzy = not getattr(args, "no_fuzzy", False)
    cfg = load_config(getattr(args, "config", None))
    fuzzy_step = cfg.fuzzy_last_offset_step
    if len(args.files) == 2:
        diff = diff_sqlite_files(
            args.files[0],
            args.files[1],
            ptrid=ptrid,
            fuzzy=fuzzy,
            fuzzy_last_offset_step=fuzzy_step,
            sqlite_threshold=cfg.cross_validate_sqlite_threshold,
            force_sqlite_backend=cfg.cross_validate_force_sqlite,
        )
        print(json.dumps(diff, ensure_ascii=False, indent=2))
    else:
        diff = diff_sqlite_many(
            args.files,
            ptrid=ptrid,
            fuzzy=fuzzy,
            fuzzy_last_offset_step=fuzzy_step,
            sqlite_threshold=cfg.cross_validate_sqlite_threshold,
            force_sqlite_backend=cfg.cross_validate_force_sqlite,
        )
        print(json.dumps(diff, ensure_ascii=False, indent=2))
    return 0


def run_verify(args) -> int:
    store = ProfileStore()
    try:
        profile = store.load(args.profile)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    chains = profile.to_result().chains
    if not chains:
        print("配置中没有指针链", file=sys.stderr)
        return 1
    before = profile.snapshot_values()
    results = verify_restart_stability(
        chains,
        before,
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
    cfg = load_config(args.config)
    print(f"监视目录: {folder.resolve()}  (Ctrl+C 退出)")
    incremental = IncrementalCrossValidator(
        min_occurrences=max(cfg.cross_validate_min, 2),
        ptrid=args.ptrid,
        fuzzy=cfg.cross_validate_fuzzy,
        fuzzy_last_offset_step=cfg.fuzzy_last_offset_step,
        module_ids=None,
        sqlite_threshold=cfg.cross_validate_sqlite_threshold,
        force_sqlite_backend=cfg.cross_validate_force_sqlite,
    )
    export_dir = Path(getattr(args, "export_dir", None) or folder / f"{args.game}_auto_export")

    def on_error(path: Path, exc: Exception) -> None:
        print(f"  [错误] {path.name}: {exc}", file=sys.stderr)

    def _auto_export_result(result, source: Path) -> None:
        snapshots, pkg = load_export_context(cfg.game_name)
        if not cfg.android_package and pkg:
            cfg.android_package = pkg
        files = export_all(
            result,
            export_dir,
            game_name=cfg.game_name,
            preset_id=cfg.preset,
            pointer_size=cfg.pointer_size,
            target_pid=cfg.target_pid,
            android_package=cfg.android_package,
            snapshots=snapshots,
        )
        store = ProfileStore()
        profile = GameProfile.from_result(
            result,
            cfg.game_name,
            preset=cfg.preset,
            pointer_size=cfg.pointer_size,
            target_pid=cfg.target_pid,
            android_package=cfg.android_package,
        )
        store.save(profile)
        print(f"  已导出 {len(files)} 个文件 → {export_dir}，Profile 已更新")

    def on_new(path: Path) -> None:
        print(f"[新文件] {path.name}")
        if args.auto_extract:
            cfg.game_name = args.game
            try:
                if getattr(args, "incremental_cross", False):
                    info = incremental.add_file(path)
                    print(
                        f"  增量交叉: +{info['new_unique_keys']} 键, 稳定 {info['stable_keys']} 条"
                    )
                    stable, meta = incremental.ranked_stable_chains(cfg)
                    if stable:
                        from ce_base_extractor.models import ExtractResult

                        result = ExtractResult(
                            chains=stable,
                            total_raw=meta.get("unique_keys", len(stable)),
                            total_after_filter=len(stable),
                            modules_seen=sorted({c.module_name for c in stable}),
                            source_file=str(path),
                            cross_validate_meta=meta,
                        )
                        print(f"  当前稳定链(打分后): {len(result.chains)} 条")
                        if not getattr(args, "no_export_on_stable", False):
                            _auto_export_result(result, path)
                else:
                    result = extract(path, config=cfg)
                    print(f"  提取: {len(result.chains)} 条稳定链")
                    _auto_export_result(result, path)
            except Exception as exc:
                print(f"  提取失败: {exc}", file=sys.stderr)

    watcher = FolderWatcher(folder, on_new, interval=args.interval, on_error=on_error)
    watcher.start()
    try:
        while True:
            import time

            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        watcher.stop()
        incremental.close()
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


def run_profile_migrate(args) -> int:
    store = ProfileStore()
    old = store.load(args.profile)
    if args.compare_with:
        new = store.load_version(args.profile, args.compare_with)
    elif args.input:
        from ce_base_extractor.models import ExtractConfig
        from ce_base_extractor.pipeline import extract

        cfg = ExtractConfig(game_name=args.profile, preset=old.preset, live_probe=False)
        result = extract(args.input, config=cfg)
        new = GameProfile.from_result(result, args.profile, preset=old.preset)
    else:
        print("请提供 input SQLite 或 --compare-with 历史版本", file=sys.stderr)
        return 1

    report = compare_profiles(old, new)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    if args.save:
        store.save(new)
        print(f"已保存新版本 → {args.profile}")
    return 0


def run_scc_recheck(args) -> int:
    from ce_base_extractor.integrations.scc import scheduled_recheck_profile

    result = scheduled_recheck_profile(
        args.profile,
        scc_path=args.scc,
        pid=args.pid,
        require_value_match=getattr(args, "require_value_match", False),
    )
    for item in result.details:
        status = "稳定" if item["stable"] else f"失败: {item.get('error', '')}"
        print(f"{item['name']}: {status}")
    print(f"\n稳定 {result.stable}/{result.total}")
    return 0 if result.ok else 2
