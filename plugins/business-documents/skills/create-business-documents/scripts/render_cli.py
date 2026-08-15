from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import notice_render
import profile_render
import quote_render
from common import save_html


KINDS = ("quote", "profile", "official", "notice", "poster")
STYLE_MAP = {
    "quote": set(quote_render.STYLES),
    "profile": set(profile_render.STYLES),
    "official": {"official"},
    "notice": {"notice"},
    "poster": {"poster"},
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a sanitized A4 business document from JSON.")
    parser.add_argument("--kind", required=True, choices=KINDS)
    parser.add_argument("--style")
    parser.add_argument("--input", required=True, dest="input_path")
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args(argv)


def load_input(path_value: str) -> dict[str, Any]:
    path = Path(path_value).expanduser()
    if not path.is_file():
        raise ValueError(f"input file not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid JSON input: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError("JSON input must be an object")
    return payload


def resolve_style(kind: str, requested: Any) -> str:
    if kind == "quote":
        style = str(requested or "clean")
    elif kind == "profile":
        style = str(requested or "clean")
    else:
        style = str(requested or kind)
    if style not in STYLE_MAP[kind]:
        allowed = ", ".join(sorted(STYLE_MAP[kind]))
        raise ValueError(f"style '{style}' is invalid for kind '{kind}'; allowed: {allowed}")
    return style


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        data = load_input(args.input_path)
        style = resolve_style(args.kind, args.style or data.get("style"))
        if args.kind == "quote":
            html_text = quote_render.render(data, style)
        elif args.kind == "profile":
            html_text = profile_render.render(data, style)
        else:
            html_text = notice_render.render(data, args.kind)
        target = save_html(html_text, f"{args.kind}.html", args.output_dir)
    except (TypeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    print(f"Rendered {args.kind}: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
