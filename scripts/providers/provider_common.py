from __future__ import annotations

import hashlib
import os
import platform
import subprocess
import uuid
from datetime import datetime, timezone
import json
import shutil
from pathlib import Path
from typing import Any
import rfc8785

PROVIDERS = ("codex", "claude-code", "antigravity")
EXECUTABLE_NAMES = {
    "codex": ("codex",),
    "claude-code": ("claude",),
    "antigravity": ("antigravity",),
}


class ProviderEvidenceError(ValueError):
    pass


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()

def canonical_digest(value: Any) -> str:
    return sha256_bytes(rfc8785.dumps(value))


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProviderEvidenceError(f"cannot read provider evidence {path}: {exc}") from exc


def _launch_argv(executable: str, arguments: list[str]) -> list[str]:
    if os.name == "nt" and Path(executable).suffix.lower() in {".cmd", ".bat"}:
        return [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/s", "/c", executable, *arguments]
    return [executable, *arguments]


def resolve_real_executable(provider: str) -> str:
    if provider not in EXECUTABLE_NAMES:
        raise ProviderEvidenceError(f"unsupported provider: {provider}")
    for name in EXECUTABLE_NAMES[provider]:
        candidates = (f"{name}.exe", f"{name}.cmd", name) if os.name == "nt" else (name,)
        for candidate in candidates:
            resolved = shutil.which(candidate)
            if resolved:
                path = Path(resolved).resolve()
                if os.name != "nt" or path.suffix.lower() in {".exe", ".cmd", ".bat", ".com"}:
                    return str(path)
    raise ProviderEvidenceError(f"required real provider executable unavailable: {provider}")


def required_run_ids(matrix: dict[str, Any]) -> list[tuple[str, str]]:
    providers = matrix.get("providers")
    cases = matrix.get("cases")
    if providers != list(PROVIDERS) or not isinstance(cases, list) or len(cases) != 10:
        raise ProviderEvidenceError("matrix must declare the approved providers and ten cases")
    result = [(case["id"], provider) for case in cases for provider in providers]
    if matrix.get("expectedRunCount") != len(result):
        raise ProviderEvidenceError("matrix expectedRunCount mismatch")
    return result


def canonical_projection(payload: dict[str, Any]) -> dict[str, Any]:
    projection = {
        "cycle": payload["cycle"],
        "facts": payload["facts"],
        "evidenceRefs": [item["id"] for item in payload["evidence"]],
        "businessVerdicts": payload["businessVerdicts"],
        "contentSteps": payload["contentSteps"],
        "scope": payload["scope"],
        "outputs": payload["outputs"],
        "rendererMode": payload["rendererMode"],
    }
    if payload["scope"] == "SECTION":
        projection["sectionId"] = payload["sectionId"]
    return projection


def verify_evidence_record(
    record: dict[str, Any],
    *,
    expected_fixture: str,
    expected_provider: str,
    expected_projection: dict[str, Any],
    evidence_root: Path,
    expected_adapter: Path,
) -> None:
    if record.get("fixtureId") != expected_fixture or record.get("provider") != expected_provider:
        raise ProviderEvidenceError("run identity does not match fixture/provider assignment")
    if record.get("protocolVersion") != "dayoun-provider-run-v1":
        raise ProviderEvidenceError("provider protocol version mismatch")
    if record.get("timeout") or record.get("exitCode") != 0:
        raise ProviderEvidenceError("provider invocation did not complete successfully")
    executable = record.get("executable", "")
    if not Path(executable).is_absolute():
        raise ProviderEvidenceError("evidence must record an absolute real executable")
    executable_path = Path(executable)
    if not executable_path.is_file():
        raise ProviderEvidenceError("recorded real provider executable is unavailable")
    if sha256_bytes(executable_path.read_bytes()) != record.get("executableDigest"):
        raise ProviderEvidenceError("provider executable digest mismatch")
    raw_path = (evidence_root / record.get("rawOutputRef", "")).resolve()
    try:
        raw_path.relative_to(evidence_root.resolve())
    except ValueError as exc:
        raise ProviderEvidenceError("raw output escapes evidence root") from exc
    if not raw_path.is_file():
        raise ProviderEvidenceError("raw provider output is missing")
    if sha256_bytes(raw_path.read_bytes()) != record.get("rawOutputDigest"):
        raise ProviderEvidenceError("raw provider output digest mismatch")
    if record.get("normalizedProjection") != expected_projection:
        raise ProviderEvidenceError("provider changed or omitted canonical fields")
    approved = record.get("approvedTuple", {})
    if not approved.get("payloadDigest") or not approved.get("approvalEnvelopeDigest"):
        raise ProviderEvidenceError("provider evidence is not bound to approved inputs")
    if not record.get("provenanceId") or not record.get("adapterDigest"):
        raise ProviderEvidenceError("provider provenance is incomplete")
    if adapter_source_digest(expected_adapter) != record.get("adapterDigest"):
        raise ProviderEvidenceError("provider adapter source digest mismatch")
    unsigned = dict(record)
    provenance_id = unsigned.pop("provenanceId", None)
    if provenance_id != canonical_digest(unsigned):
        raise ProviderEvidenceError("provider provenance digest does not bind the complete run")
    try:
        started = datetime.fromisoformat(record["startedAt"])
        finished = datetime.fromisoformat(record["finishedAt"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ProviderEvidenceError("provider timestamps are invalid") from exc
    if finished < started:
        raise ProviderEvidenceError("provider finishedAt predates startedAt")


def executable_version(executable: str) -> str:
    try:
        result = subprocess.run(
            _launch_argv(executable, ["--version"]),
            capture_output=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ProviderEvidenceError(f"cannot capture executable version: {exc}") from exc
    text = (result.stdout or result.stderr).decode("utf-8", errors="replace").strip()
    if result.returncode != 0 or not text:
        raise ProviderEvidenceError("provider --version did not return a usable version")
    return text.splitlines()[0]


def adapter_source_digest(adapter_path: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(
        {
            adapter_path.resolve(),
            Path(__file__).resolve(),
            Path(__file__).resolve().with_name("runner_cli.py"),
        },
        key=lambda item: item.name,
    ):
        relative = path.name.encode("utf-8")
        data = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return "sha256:" + digest.hexdigest()


def workspace_digest(workspace: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in workspace.rglob("*") if item.is_file()):
        relative = path.relative_to(workspace).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        data = path.read_bytes()
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return "sha256:" + digest.hexdigest()


def record_real_run(
    *,
    provider: str,
    fixture_id: str,
    command: list[str],
    workspace: Path,
    normalized_output: Path,
    approved_tuple: dict[str, Any],
    adapter_path: Path,
    evidence_root: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    executable = resolve_real_executable(provider)
    if not command:
        raise ProviderEvidenceError("provider invocation is empty")
    requested_name = Path(command[0]).stem.lower()
    allowed_names = {Path(name).stem.lower() for name in EXECUTABLE_NAMES[provider]}
    if requested_name not in allowed_names and Path(command[0]).resolve() != Path(executable):
        raise ProviderEvidenceError("provider invocation does not use the approved real executable")
    launch_command = _launch_argv(executable, command[1:])
    workspace = workspace.resolve()
    normalized_output = normalized_output.resolve()
    if not workspace.is_dir():
        raise ProviderEvidenceError("provider workspace is missing")
    try:
        normalized_output.relative_to(workspace)
    except ValueError as exc:
        raise ProviderEvidenceError("normalized provider output must stay inside its workspace") from exc
    if normalized_output.exists():
        raise ProviderEvidenceError("normalized provider output must not predate the real invocation")
    version = executable_version(executable)
    before_workspace_digest = workspace_digest(workspace)
    started = datetime.now(timezone.utc)
    timed_out = False
    try:
        completed = subprocess.run(
            launch_command,
            cwd=workspace,
            env={**os.environ, "DAYOUN_PROVIDER": provider, "DAYOUN_FIXTURE_ID": fixture_id},
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        stdout = completed.stdout
        stderr = completed.stderr
        exit_code = completed.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = exc.stdout or b""
        stderr = exc.stderr or b""
        exit_code = -1
    finished = datetime.now(timezone.utc)
    run_id = f"{fixture_id}--{provider}--{uuid.uuid4().hex}"
    raw_dir = evidence_root / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"{run_id}.json"
    raw_record = {
        "stdout": stdout.decode("utf-8", errors="replace"),
        "stderr": stderr.decode("utf-8", errors="replace"),
    }
    raw_path.write_text(json.dumps(raw_record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if timed_out or exit_code != 0:
        raise ProviderEvidenceError(f"real provider failed: timeout={timed_out} exit={exit_code}")
    if not normalized_output.is_file():
        raise ProviderEvidenceError("real provider did not create the normalized output")
    if normalized_output.stat().st_mtime < started.timestamp() - 2:
        raise ProviderEvidenceError("normalized provider output predates the real invocation")
    projection = load_json(normalized_output)
    relative_raw = raw_path.relative_to(evidence_root).as_posix()
    record = {
        "schemaVersion": "1.0.0",
        "protocolVersion": "dayoun-provider-run-v1",
        "runId": run_id,
        "fixtureId": fixture_id,
        "provider": provider,
        "executable": executable,
        "executableDigest": sha256_bytes(Path(executable).read_bytes()),
        "executableVersion": version,
        "adapterDigest": adapter_source_digest(adapter_path),
        "installMethod": "public-provider-cli",
        "invocation": command,
        "startedAt": started.isoformat(),
        "finishedAt": finished.isoformat(),
        "exitCode": exit_code,
        "timeout": timed_out,
        "workspaceDigest": before_workspace_digest,
        "approvedTuple": approved_tuple,
        "rawOutputRef": relative_raw,
        "rawOutputDigest": sha256_bytes(raw_path.read_bytes()),
        "normalizedProjection": projection,
        "capabilities": ["canonical-conformance", "recorded-raw-output"],
        "os": platform.platform(),
    }
    record["provenanceId"] = canonical_digest(record)
    return record
