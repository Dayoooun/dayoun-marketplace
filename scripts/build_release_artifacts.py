from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Iterable
from contract_utils import canonical_digest

REPO_ROOT = Path(__file__).resolve().parents[1]
TARGETS = ("contracts", "business-plan-writer", "business-documents", "course-kit")
FIXED_TIME = (1980, 1, 1, 0, 0, 0)


class BuildError(ValueError):
    pass


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _files(root: Path) -> Iterable[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
        and path.name not in {".DS_Store", "Thumbs.db"}
    )


def _contract_files() -> list[tuple[Path, str]]:
    result: list[tuple[Path, str]] = []
    for subdir in ("schemas", "policies"):
        root = REPO_ROOT / "contracts" / subdir
        result.extend((path, f"_contracts/{subdir}/{path.relative_to(root).as_posix()}") for path in _files(root))
    return result


def collect_members(target: str) -> list[tuple[Path, str]]:
    if target == "contracts":
        root = REPO_ROOT / "contracts"
        members = [(path, path.relative_to(root).as_posix()) for path in _files(root)]
        members.append((REPO_ROOT / "LICENSE", "LICENSE"))
        return members
    if target == "business-plan-writer":
        root = REPO_ROOT / "plugins" / target
        members = [(path, path.relative_to(root).as_posix()) for path in _files(root)]
        if any("create-business-documents" in name for _, name in members):
            raise BuildError("business-plan-writer contains the separated documents skill")
        if any(name.startswith("tests/") or name.endswith("test_harness.py") for _, name in members):
            raise BuildError("business-plan-writer artifact contains test-owned files")
        members.extend(_contract_files())
        members.append((REPO_ROOT / "LICENSE", "LICENSE"))
        members.append((REPO_ROOT / "requirements.txt", "requirements.txt"))
        return members
    if target == "business-documents":
        root = REPO_ROOT / "plugins" / target
        members = [(path, path.relative_to(root).as_posix()) for path in _files(root)]
        members.extend(_contract_files())
        members.append((REPO_ROOT / "LICENSE", "LICENSE"))
        return members
    if target == "course-kit":
        root = REPO_ROOT / "course"
        if not (root / "manifest.json").is_file():
            raise BuildError("generated course is missing; run scripts/generate_course.py --clean")
        members = [(path, path.relative_to(root).as_posix()) for path in _files(root)]
        if any("internal" in Path(name).parts or "materials-backlog" in name for _, name in members):
            raise BuildError("course-kit contains internal material")
        members.append((REPO_ROOT / "LICENSE", "LICENSE"))
        members.append((REPO_ROOT / "requirements.txt", "requirements.txt"))
        return members
    raise BuildError(f"unsupported target: {target}")


def declared_version(target: str) -> str:
    if target == "contracts":
        path = REPO_ROOT / "contracts" / "manifest.json"
    elif target == "course-kit":
        path = REPO_ROOT / "course" / "manifest.json"
    else:
        path = REPO_ROOT / "plugins" / target / "plugin.json"
    try:
        return str(json.loads(path.read_text(encoding="utf-8"))["version"])
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        raise BuildError(f"cannot determine {target} source version: {exc}") from exc

def _rule_matches(path: str, rule: str) -> bool:
    normalized = rule.rstrip("/")
    return path == normalized or path.startswith(normalized + "/")


def validate_source_closure(source_reads: list[str], closure: dict[str, object]) -> None:
    for rule in closure.get("sourceRoots", []):
        if not any(_rule_matches(path, str(rule)) for path in source_reads):
            raise BuildError(f"required source was not read: {rule}")
    for rule in closure.get("forbiddenSourceRoots", []):
        if any(_rule_matches(path, str(rule)) for path in source_reads):
            raise BuildError(f"forbidden source was read: {rule}")



def build_target(
    target: str,
    version: str,
    output_dir: Path,
    closure: dict[str, object] | None = None,
) -> dict[str, object]:
    source_version = declared_version(target)
    if version != source_version:
        raise BuildError(
            f"{target} artifact version {version} does not match source version {source_version}"
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((REPO_ROOT / "release" / "manifests" / f"{target}.json").read_text(encoding="utf-8"))
    artifact_name = manifest["artifactPattern"].format(version=version)
    artifact_path = output_dir / artifact_name
    members = collect_members(target)
    closure = closure or json.loads(
        (REPO_ROOT / "release" / "manifests" / f"{target}.json").read_text(encoding="utf-8")
    )
    source_reads = sorted(
        source.relative_to(REPO_ROOT).as_posix()
        for source, _name in members
    )
    validate_source_closure(source_reads, closure)
    closure_digest = canonical_digest(closure)
    source_records = [
        {
            "source": source.relative_to(REPO_ROOT).as_posix(),
            "archivePath": name.replace("\\", "/"),
            "sha256": sha256_bytes(source.read_bytes()),
        }
        for source, name in sorted(members, key=lambda item: item[1])
    ]
    seen: set[str] = set()
    member_records: list[dict[str, str]] = []
    with zipfile.ZipFile(artifact_path, "w") as archive:
        for source, name in sorted(members, key=lambda item: item[1]):
            normalized = name.replace("\\", "/")
            if normalized in seen:
                raise BuildError(f"duplicate archive member: {normalized}")
            seen.add(normalized)
            data = source.read_bytes()
            info = zipfile.ZipInfo(normalized, FIXED_TIME)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
            member_records.append({"path": normalized, "sha256": sha256_bytes(data), "mode": "100644"})
    artifact_digest = sha256_bytes(artifact_path.read_bytes())
    member_manifest = {
        "schemaVersion": "1.0.0",
        "target": target,
        "version": version,
        "artifact": artifact_name,
        "artifactSha256": artifact_digest,
        "members": member_records,
        "closureDigest": closure_digest,
        "sourceReads": source_reads,
        "sourceRecords": source_records,
    }
    manifest_path = output_dir / f"{artifact_name}.members.json"
    manifest_path.write_text(json.dumps(member_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / f"{artifact_name}.sha256").write_text(f"{artifact_digest}  {artifact_name}\n", encoding="utf-8")
    access_path = output_dir / f"{artifact_name}.access.json"
    access_path.write_text(
        json.dumps(
            {
                "schemaVersion": "1.0.0",
                "target": target,
                "closureDigest": closure_digest,
                "sourceReads": source_reads,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return member_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic, target-scoped Dayoun artifacts")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--target", choices=TARGETS)
    group.add_argument("--all", action="store_true")
    parser.add_argument("--health-only", action="store_true")
    parser.add_argument("--version")
    parser.add_argument("--closure", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.all and not args.health_only:
        print("BLOCK: --all is health-only and cannot qualify a release", file=sys.stderr)
        return 2
    targets = TARGETS if args.all else (args.target,)
    try:
        closures = {}
        if args.closure:
            closure = json.loads(args.closure.read_text(encoding="utf-8"))
            if closure.get("target") != args.target:
                raise BuildError("closure target does not match selected artifact")
            closures[args.target] = closure
        results = [
            build_target(
                target,
                args.version or declared_version(target),
                args.output_dir,
                closures.get(target),
            )
            for target in targets
        ]
    except (OSError, json.JSONDecodeError, BuildError) as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"status": "PASS", "healthOnly": bool(args.all), "artifacts": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
