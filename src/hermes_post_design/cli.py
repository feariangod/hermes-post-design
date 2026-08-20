"""Command-line interface for Chiyi image generation and Hermes resource sync."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests

from hermes_post_design.chiyi_core import ChiyiClient
from hermes_post_design.chiyi_core.models import EditRequest, GenerateRequest, ImageSource
from hermes_post_design.sync import apply_sync, plan_sync, restore_backup


def _result_payload(result) -> dict:
    payload = {
        "success": result.success,
        "provider": result.provider,
        "model": result.model,
        "quality": result.quality,
        "requested_size": result.requested_size,
        "upstream_size": result.upstream_size,
        "modality": result.modality,
    }
    if result.artifact is not None:
        payload["artifact"] = {
            "path": str(result.artifact.path),
            "format": result.artifact.format,
            "width": result.artifact.width,
            "height": result.artifact.height,
            "sha256": result.artifact.sha256,
            "normalized": result.artifact.normalized,
        }
    if result.error is not None:
        payload["error"] = {
            "type": result.error.type,
            "message": result.error.message,
            "retryable": result.error.retryable,
            "request_id": result.error.request_id,
        }
    return payload


def _print(payload: dict, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return
    if payload.get("success"):
        artifact = payload.get("artifact", {})
        print(f"Saved: {artifact.get('path')}")
        print(f"Size: {artifact.get('width')}x{artifact.get('height')}")
    else:
        error = payload.get("error", {})
        print(f"Error [{error.get('type', 'error')}]: {error.get('message', 'Operation failed')}")


def _make_client(session) -> ChiyiClient:
    key = os.environ.get("CHIYI_IMAGE_API_KEY", "")
    if not key:
        raise RuntimeError("CHIYI_IMAGE_API_KEY is not configured")
    return ChiyiClient(api_key=key, session=session)


def _command_generate(args) -> int:
    try:
        with requests.Session() as session:
            result = _make_client(session).generate(
                GenerateRequest(args.prompt, args.output_dir, args.size)
            )
    except RuntimeError as exc:
        _print({"success": False, "error": {"type": "auth_required", "message": str(exc)}}, as_json=args.json)
        return 2
    payload = _result_payload(result)
    _print(payload, as_json=args.json)
    return 0 if result.success else 1


def _command_edit(args) -> int:
    references = tuple(ImageSource(value) for value in args.reference)
    request = EditRequest(
        prompt=args.prompt,
        output_dir=args.output_dir,
        primary_image=ImageSource(args.image, role="primary"),
        reference_images=references,
        size=args.size,
    )
    try:
        with requests.Session() as session:
            result = _make_client(session).edit(request)
    except RuntimeError as exc:
        _print({"success": False, "error": {"type": "auth_required", "message": str(exc)}}, as_json=args.json)
        return 2
    payload = _result_payload(result)
    _print(payload, as_json=args.json)
    return 0 if result.success else 1


def _command_doctor(args) -> int:
    home = args.hermes_home.expanduser().absolute()
    payload = {
        "success": True,
        "python": sys.version.split()[0],
        "hermes_home": str(home),
        "hermes_home_exists": home.is_dir(),
        "key": "present" if bool(os.environ.get("CHIYI_IMAGE_API_KEY")) else "missing",
        "sync": [entry.__dict__ for entry in plan_sync(home)],
    }
    _print(payload, as_json=args.json)
    return 0


def _command_sync(args) -> int:
    payload = apply_sync(args.hermes_home) if args.apply else {
        "changed": False,
        "dry_run": True,
        "entries": [entry.__dict__ for entry in plan_sync(args.hermes_home)],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2 if not args.json else None, sort_keys=True))
    return 0


def _command_restore(args) -> int:
    payload = restore_backup(args.hermes_home, args.backup)
    print(json.dumps(payload, ensure_ascii=False, indent=2 if not args.json else None, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hermes-post-design")
    sub = parser.add_subparsers(dest="command", required=True)

    generate = sub.add_parser("generate", help="Generate one image with Chiyi")
    generate.add_argument("prompt")
    generate.add_argument("--size", default="1024x1024")
    generate.add_argument("--output-dir", type=Path, default=Path.cwd())
    generate.add_argument("--json", action="store_true")
    generate.set_defaults(handler=_command_generate)

    edit = sub.add_parser("edit", help="Edit an image with optional references")
    edit.add_argument("prompt")
    edit.add_argument("--image", required=True)
    edit.add_argument("--reference", action="append", default=[])
    edit.add_argument("--size", default="1024x1024")
    edit.add_argument("--output-dir", type=Path, default=Path.cwd())
    edit.add_argument("--json", action="store_true")
    edit.set_defaults(handler=_command_edit)

    doctor = sub.add_parser("doctor", help="Inspect installation without secrets")
    doctor.add_argument("--hermes-home", type=Path, default=Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")))
    doctor.add_argument("--json", action="store_true")
    doctor.set_defaults(handler=_command_doctor)

    sync = sub.add_parser("sync", help="Preview or deploy Hermes plugin and skills")
    sync.add_argument("--hermes-home", type=Path, required=True)
    sync.add_argument("--apply", action="store_true", help="Apply changes; default is dry-run")
    sync.add_argument("--json", action="store_true")
    sync.set_defaults(handler=_command_sync)

    restore = sub.add_parser("restore", help="Restore a backup created by sync")
    restore.add_argument("--hermes-home", type=Path, required=True)
    restore.add_argument("--backup", type=Path, required=True)
    restore.add_argument("--json", action="store_true")
    restore.set_defaults(handler=_command_restore)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
