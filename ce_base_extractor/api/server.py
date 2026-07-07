"""ce-base-extractor Headless JSON API。"""

from __future__ import annotations

import argparse
import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from ce_base_extractor.export.batch_export import export_all
from ce_base_extractor.export.context import load_export_context
from ce_base_extractor.filters.presets import get_preset
from ce_base_extractor.integrations.scc import scheduled_recheck_profile
from ce_base_extractor.logging_config import setup_logging
from ce_base_extractor.pipeline import extract, load_config
from ce_base_extractor.runtime.win_memory import ProcessMemory

_log = logging.getLogger(__name__)


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0") or 0)
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    return json.loads(raw.decode("utf-8"))


class ApiHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        _log.info("%s - %s", self.address_string(), fmt % args)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            return _json_response(self, 200, {"ok": True, "service": "ce-base-extractor"})
        if parsed.path == "/processes":
            qs = parse_qs(parsed.query)
            preset_id = (qs.get("preset") or ["ldplayer"])[0]
            preset = get_preset(preset_id)
            names = list(preset.process_names) if preset else ["dnplayer.exe"]
            try:
                procs = [
                    {"pid": p.pid, "name": p.name, "label": p.label}
                    for p in ProcessMemory.list_matching(names)
                ]
            except OSError as exc:
                return _json_response(self, 500, {"ok": False, "error": str(exc)})
            return _json_response(self, 200, {"preset": preset_id, "processes": procs})
        _json_response(self, 404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            body = _read_json(self)
        except json.JSONDecodeError as exc:
            return _json_response(self, 400, {"ok": False, "error": f"invalid json: {exc}"})

        if parsed.path == "/extract":
            input_path = body.get("input")
            if not input_path:
                return _json_response(self, 400, {"ok": False, "error": "input required"})
            cfg = load_config(body.get("config"))
            if body.get("game"):
                cfg.game_name = body["game"]
            if body.get("preset"):
                cfg.preset = body["preset"]
            result = extract(input_path, config=cfg, extra_files=body.get("cross"))
            payload = {
                "ok": True,
                "chains": len(result.chains),
                "modules": result.modules_seen,
                "source": result.source_file,
            }
            if body.get("export_dir"):
                snapshots, pkg = load_export_context(cfg.game_name)
                if not cfg.android_package and pkg:
                    cfg.android_package = pkg
                files = export_all(
                    result,
                    body["export_dir"],
                    game_name=cfg.game_name,
                    preset_id=cfg.preset,
                    pointer_size=cfg.pointer_size,
                    target_pid=cfg.target_pid,
                    android_package=cfg.android_package,
                    snapshots=snapshots,
                )
                payload["exported"] = [str(p) for p in files]
            return _json_response(self, 200, payload)

        if parsed.path == "/verify":
            profile = body.get("profile")
            if not profile:
                return _json_response(self, 400, {"ok": False, "error": "profile required"})
            recheck = scheduled_recheck_profile(
                profile,
                scc_path=body.get("scc"),
                pid=body.get("pid"),
                require_value_match=bool(body.get("require_value_match")),
            )
            return _json_response(
                self,
                200,
                {
                    "ok": recheck.ok,
                    "stable": recheck.stable,
                    "total": recheck.total,
                    "details": recheck.details,
                },
            )

        if parsed.path == "/load-bases":
            path = body.get("path")
            if not path:
                return _json_response(self, 400, {"ok": False, "error": "path required"})
            from ce_base_extractor.integrations.scc import list_chain_names, load_bases

            data = load_bases(path)
            return _json_response(
                self,
                200,
                {"ok": True, "names": list_chain_names(path), "chains": data.get("chains", [])},
            )

        _json_response(self, 404, {"ok": False, "error": "not found"})


def run_server(host: str = "127.0.0.1", port: int = 17860, *, json_logs: bool = False) -> None:
    setup_logging(json_logs=json_logs)
    server = ThreadingHTTPServer((host, port), ApiHandler)
    _log.info("ce-base-extractor API http://%s:%s", host, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        _log.info("API 已停止")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ce-base-extractor-api")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=17860)
    parser.add_argument("--json-logs", action="store_true")
    args = parser.parse_args(argv)
    run_server(args.host, args.port, json_logs=args.json_logs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
