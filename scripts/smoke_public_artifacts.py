from __future__ import annotations

import argparse
import json
import sys
import tempfile
import zipfile
from pathlib import Path


class SmokeError(ValueError):
    pass


def one_archive(directory: Path) -> Path:
    archives = sorted(directory.glob("*.zip"))
    if len(archives) != 1:
        raise SmokeError(f"expected one archive, got {len(archives)}")
    return archives[0]


def smoke(
    directory: Path,
    target: str,
    *,
    ppt_modes: set[str] | None = None,
    require_approved_resolver: bool = False,
    require_extractor: bool = False,
) -> dict[str, object]:
    archive = one_archive(directory)
    with tempfile.TemporaryDirectory(prefix="dayoun-public-smoke-") as temp:
        root = Path(temp)
        with zipfile.ZipFile(archive) as source:
            names = source.namelist()
            if any(name.startswith("/") or ".." in Path(name).parts for name in names):
                raise SmokeError("archive contains unsafe paths")
            source.extractall(root)
        if target == "business-plan-writer":
            skills = [path for path in (root / "skills").iterdir() if path.is_dir()]
            if len(skills) != 7:
                raise SmokeError(f"writer artifact must contain seven skills, got {len(skills)}")
            if (root / "skills" / "create-business-documents").exists():
                raise SmokeError("writer artifact contains separated documents skill")
            if not (root / "_contracts" / "schemas" / "canonical.schema.json").is_file():
                raise SmokeError("writer artifact cannot resolve embedded contracts")
            if any(path.name == "test_harness.py" for path in root.rglob("*")):
                raise SmokeError("writer artifact contains test-owned harness")
            required_validators = (
                root / "validators" / "fact_validator.py",
                root / "validators" / "structure_validator.py",
                root / "validators" / "contract_validator.py",
                root / "validators" / "aggregate_validators.py",
            )
            if not all(path.is_file() for path in required_validators):
                raise SmokeError("writer artifact is missing independent validators")
            ppt_root = root / "skills" / "ppt-editorial"
            skill_text = (ppt_root / "SKILL.md").read_text(encoding="utf-8")
            if ppt_modes and not all(mode in skill_text for mode in ppt_modes):
                raise SmokeError("writer artifact does not expose every requested PPT mode")
            if require_approved_resolver:
                resolver = ppt_root / "scripts" / "approved_inputs.py"
                assembler = ppt_root / "scripts" / "assemble_pptx.py"
                if not resolver.is_file() or "--approval-digest" not in assembler.read_text(encoding="utf-8"):
                    raise SmokeError("writer artifact does not enforce approved digest resolution")
            if require_extractor:
                required_ocr = (
                    ppt_root / "scripts" / "ocr" / "map_ocr_regions.py",
                    ppt_root / "scripts" / "ocr" / "validate_visible_text.py",
                )
                if not all(path.is_file() for path in required_ocr):
                    raise SmokeError("writer artifact is missing OCR mapping or validation")
        elif target == "business-documents":
            if not (root / "skills" / "create-business-documents" / "scripts" / "render_cli.py").is_file():
                raise SmokeError("documents renderer is missing")
            if not (root / "_contracts" / "schemas" / "canonical.schema.json").is_file():
                raise SmokeError("documents artifact cannot resolve embedded contracts")
        elif target == "course-kit":
            if not (root / "manifest.json").is_file() or not (root / "starter-project").is_dir():
                raise SmokeError("course artifact is incomplete")
            starter_runtime = root / "starter-project" / ".dayoun"
            if not (starter_runtime / "validators" / "contract_validator.py").is_file():
                raise SmokeError("course starter is missing generated independent validators")
            if not (starter_runtime / "_contracts" / "schemas" / "canonical.schema.json").is_file():
                raise SmokeError("course starter cannot resolve its generated contract snapshot")
            if any("internal" in path.parts or "materials-backlog" in path.name for path in root.rglob("*")):
                raise SmokeError("course artifact leaks internal material")
        elif target == "contracts":
            if not (root / "schemas" / "canonical.schema.json").is_file():
                raise SmokeError("contracts artifact is incomplete")
        else:
            raise SmokeError(f"unsupported target: {target}")
    return {"status": "PASS", "target": target, "archive": archive.name}


def main() -> int:
    parser = argparse.ArgumentParser(description="Install-free smoke for a public Dayoun artifact")
    parser.add_argument("artifacts", type=Path)
    parser.add_argument("--target", required=True)
    parser.add_argument("--clean-home", action="store_true")
    parser.add_argument("--hide-repository-root", action="store_true")
    parser.add_argument("--ppt-modes")
    parser.add_argument("--require-approved-resolver", action="store_true")
    parser.add_argument("--require-extractor", action="store_true")
    args = parser.parse_args()
    if not args.clean_home or not args.hide_repository_root:
        print("BLOCK: public smoke must use a clean home with repository root hidden", file=sys.stderr)
        return 2
    try:
        result = smoke(
            args.artifacts,
            args.target,
            ppt_modes=set(args.ppt_modes.split(",")) if args.ppt_modes else None,
            require_approved_resolver=args.require_approved_resolver,
            require_extractor=args.require_extractor,
        )
    except (OSError, zipfile.BadZipFile, SmokeError) as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
