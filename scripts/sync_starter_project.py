#!/usr/bin/env python3
"""Keep the downloadable starter project aligned with create_project.py."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = (
    ROOT
    / "plugins"
    / "business-plan-writer"
    / "skills"
    / "setup-business-plan-project"
    / "scripts"
    / "create_project.py"
)
TARGET = ROOT / "fallback" / "starter-project"
GENERATED_DIRS = tuple(f"{index:02d}." for index in range(8))


def load_templates() -> dict[str, str]:
    spec = importlib.util.spec_from_file_location("create_project", GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {GENERATOR}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.TEMPLATES, module.render_template


def main() -> int:
    parser = argparse.ArgumentParser(description="스타터 프로젝트 템플릿 동기화")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    templates, render_template = load_templates()
    different: list[str] = []
    for relative, template in templates.items():
        expected = render_template(template, "교육", "unknown", "DEMO")
        target = TARGET / relative
        current = target.read_text(encoding="utf-8-sig") if target.is_file() else None
        if current != expected:
            different.append(relative)
            if args.write:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(expected, encoding="utf-8", newline="\n")
                print(f"SYNCED: {relative}")
            else:
                print(f"DIFFERENT: {relative}")
    expected_paths = {Path(relative).as_posix() for relative in templates}
    actual_paths = {
        path.relative_to(TARGET).as_posix()
        for path in TARGET.rglob("*")
        if path.is_file()
        and path.relative_to(TARGET).parts[0].startswith(GENERATED_DIRS)
    }
    unexpected = sorted(actual_paths - expected_paths)
    for relative in unexpected:
        print(f"UNEXPECTED_GENERATED_FILE: {relative}")
    if unexpected:
        print("Remove or relocate unexpected files manually after review.")
    if (different and not args.write) or unexpected:
        return 1
    print(f"STARTER_PROJECT_OK: {len(templates)} templates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
