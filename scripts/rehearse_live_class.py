#!/usr/bin/env python3
"""라이브 수업 시연을 독립 환경에서 그대로 재현하고 결과가 같은지 증명한다.

이 스크립트는 저장소 작업본을 참조하지 않는다. 공개 릴리스 ZIP 하나만 받아
임시 HOME·임시 작업폴더에서 시연 단계를 실행하고, 같은 입력이면 같은 결과가
나오는지 두 번 돌려 비교한다.

사용 예:
  python scripts/rehearse_live_class.py \
      --artifact dist/rehearsal/dayoun-business-plan-writer-0.12.5.zip \
      --demo-inputs "D:/.../강의시연용" \
      --template "D:/.../(양식) 성명_1R 사업계획서.hwpx" \
      --out release/evidence/rehearsal
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
# 버전을 하드코딩하면 릴리스마다 이 파일을 고쳐야 하고, 고치는 걸 잊으면
# 검증이 조용히 옛 버전을 통과시킨다. 소스 매니페스트를 단일 출처로 쓴다.
EXPECTED_VERSION = json.loads(
    (REPO_ROOT / "plugins" / "business-plan-writer" / "plugin.json").read_text(
        encoding="utf-8"
    )
)["version"]
EXPECTED_SKILLS = 7

# 시연에서 강사가 실제로 만드는 폴더/파일. 하나라도 빠지면 수업이 막힌다.
REQUIRED_PROJECT_PATHS = (
    "00. 시작하기/프로젝트상태.md",
    "00. 시작하기/계획프로필.json",
    "00. 시작하기/단계상태.json",
    "00. 시작하기/사용자협업상태.json",
    "01. 사업정보/사업정보표.md",
    "02. 목적 및 요구사항/목적과요구사항.md",
    "03. 사업계획서양식/작업용 HWPX",
    "03. 사업계획서양식/placeholder-values.draft.json",
    "03. 사업계획서양식/placeholder-values.approved.json",
    "04. 조사자료/방향결정.md",
    "04. 조사자료/독립조사/worker-01.md",
    "04. 조사자료/독립조사/worker-02.md",
    "04. 조사자료/독립조사/worker-03.md",
    "05. 작성초안/사업계획서초안.md",
    "06. 검토결과/문안승인.md",
    "07. 최종본/최종확인.md",
    "99. 원본백업/README.md",
)

# 방향결정.md 가 역질문 인터뷰 서식을 유지하는지 본다.
DIRECTION_TABLE_HEADERS = (
    "인터뷰 상태: NOT_STARTED",
    "다음 질문",
    "자료에서 확인한 내용",
    "모호한 지점",
    "사용자 결정",
    "근거 파일·위치",
    "권장안과 대안",
    "보류 항목과 영향",
)

# 인터뷰가 되묻는 결정 항목. 고정 질문지가 아니라 모호성 탐지 대상이다.
DIRECTION_DECISIONS = (
    "목표고객과 사용 상황",
    "해결할 문제",
    "첫 제품 또는 서비스",
    "첫 판매 방식",
    "조사 우선순위",
    "중단·변경 기준",
)

# worker 템플릿이 출처 확인 항목을 유지하는지 본다.
WORKER_FIELDS = (
    "조사 lane·질문",
    "독립 입력·검색 범위",
    "출처 기관·URL",
    "발표일·기준일·확인일",
    "수치·단위·적용 범위",
    "한계·말할 수 없는 것",
    "시간·사용량 제한",
    "미확인 질문",
)


class RehearsalError(RuntimeError):
    pass


def configure_utf8_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def normalize(text: str, project: Path) -> str:
    """실행마다 달라지는 임시 경로를 지운다. 내용이 같으면 digest 도 같아야 한다.

    JSON 출력은 ensure_ascii=False 라 한글은 그대로 남고 백슬래시만 이스케이프된다.
    그래서 raw 경로, JSON 이스케이프 경로, 슬래시 경로 세 형태를 모두 지운다.
    """
    resolved = str(project.resolve())
    for variant in (
        resolved.replace("\\", "\\\\"),
        resolved,
        resolved.replace("\\", "/"),
    ):
        text = text.replace(variant, "<PROJECT>")
    return text.strip()



def tree_digest(root: Path) -> tuple[str, list[dict[str, str]]]:
    """폴더 전체를 경로 정렬 후 한 개 digest 로 접는다. mtime 은 보지 않는다."""
    entries: list[dict[str, str]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        if path.is_dir():
            entries.append({"path": relative + "/", "digest": "dir"})
            continue
        entries.append({"path": relative, "digest": sha256_file(path)})
    payload = json.dumps(entries, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return sha256_bytes(payload), entries


def extract_artifact(archive: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive) as source:
        for name in source.namelist():
            if name.startswith("/") or ".." in Path(name).parts:
                raise RehearsalError(f"아카이브에 안전하지 않은 경로가 있습니다: {name}")
        source.extractall(destination)


def isolated_env(home: Path, plugin_root: Path) -> dict[str, str]:
    """저장소·사용자 설정을 못 보게 막은 환경변수."""
    env = {
        key: value
        for key, value in os.environ.items()
        if key in {"SystemRoot", "COMSPEC", "PATHEXT", "TEMP", "TMP", "windir"}
    }
    env["PATH"] = os.pathsep.join(
        [str(Path(sys.executable).parent), os.environ.get("SystemRoot", "") + r"\system32"]
    )
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    env["APPDATA"] = str(home / "AppData" / "Roaming")
    env["LOCALAPPDATA"] = str(home / "AppData" / "Local")
    env["PYTHONPATH"] = str(plugin_root)
    env["PYTHONHASHSEED"] = "0"
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["TZ"] = "UTC"
    env["LANG"] = "ko_KR.UTF-8"
    return env


def run(command: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )


def verify_artifact_shape(plugin_root: Path) -> dict[str, object]:
    manifest = json.loads((plugin_root / "plugin.json").read_text(encoding="utf-8"))
    version = manifest.get("version")
    if version != EXPECTED_VERSION:
        raise RehearsalError(f"릴리스 버전이 {EXPECTED_VERSION} 이 아닙니다: {version}")

    skills = sorted(path.name for path in (plugin_root / "skills").iterdir() if path.is_dir())
    if len(skills) != EXPECTED_SKILLS:
        raise RehearsalError(f"스킬이 {EXPECTED_SKILLS}개가 아닙니다: {skills}")

    validators = [
        "fact_validator.py",
        "structure_validator.py",
        "contract_validator.py",
        "aggregate_validators.py",
    ]
    missing = [name for name in validators if not (plugin_root / "validators" / name).is_file()]
    if missing:
        raise RehearsalError(f"독립 검증기가 빠졌습니다: {missing}")

    if not (plugin_root / "_contracts" / "schemas" / "canonical.schema.json").is_file():
        raise RehearsalError("계약 스냅샷이 아티팩트 안에서 해결되지 않습니다")

    return {"version": version, "skills": skills}


def step_lead_request(plugin_root: Path, workdir: Path, env: dict[str, str]) -> dict[str, object]:
    """수업 3단계: 설치 직후 첫 자연어 요청문이 같은 브리프를 만드는지."""
    script = plugin_root / "skills" / "complete-business-plan" / "scripts" / "lead_request.py"
    request = (
        "사업계획서를 작성하려고 해. "
        "현재 환경에 dayoun marketplace와 business-plan-writer를 설치·업데이트해줘. "
        "기존 설정과 작업 파일은 삭제하거나 덮어쓰지 마. "
        "전체 테스트 후 설치 버전, enabled 상태와 결과를 확인해줘. "
        "7개 기능과 HWPX·PPT 사용법을 설명하고 실제 작성은 아직 시작하지 마."
    )
    result = run(
        [sys.executable, str(script), "--request", request, "--mode", "REAL"],
        cwd=workdir,
        env=env,
    )
    if result.returncode != 0:
        raise RehearsalError(f"lead_request 실패: {result.stderr.strip()}")
    brief = json.loads(result.stdout)

    if brief.get("interactionMode") != "REAL":
        raise RehearsalError(f"라이브 수업은 REAL 이어야 합니다: {brief.get('interactionMode')}")
    gates = brief.get("approvalGates", {})
    if gates.get("contentApproval") is not True:
        raise RehearsalError("내용 승인 게이트가 꺼져 있습니다")
    if gates.get("publicationApproval") is not True:
        raise RehearsalError("최종 반영 승인 게이트가 꺼져 있습니다")

    return {"digest": sha256_bytes(result.stdout.encode("utf-8")), "brief": brief}


def step_create_project(plugin_root: Path, project: Path, env: dict[str, str]) -> dict[str, object]:
    """수업 4~6단계: 프로젝트 폴더 생성. 기본 모드가 REAL 이어야 한다."""
    script = (
        plugin_root
        / "skills"
        / "setup-business-plan-project"
        / "scripts"
        / "create_project.py"
    )
    result = run(
        [
            sys.executable,
            str(script),
            "--path",
            str(project),
            "--purpose",
            "지원사업",
            "--track",
            "모두의창업 일반기술트랙",
        ],
        cwd=project.parent,
        env=env,
    )
    if result.returncode != 0:
        raise RehearsalError(f"create_project 실패: {result.stderr.strip()}")

    missing = [item for item in REQUIRED_PROJECT_PATHS if not (project / item).exists()]
    if missing:
        raise RehearsalError(f"시연에 필요한 경로가 없습니다: {missing}")

    direction = (project / "04. 조사자료" / "방향결정.md").read_text(encoding="utf-8")
    absent = [header for header in DIRECTION_TABLE_HEADERS if header not in direction]
    if absent:
        raise RehearsalError(f"역질문 인터뷰 서식이 깨졌습니다: {absent}")
    undetected = [item for item in DIRECTION_DECISIONS if item not in direction]
    if undetected:
        raise RehearsalError(f"모호성 탐지 대상 항목이 빠졌습니다: {undetected}")
    if direction.count("모호함") < len(DIRECTION_DECISIONS):
        raise RehearsalError("결정 항목이 모호함으로 시작하지 않습니다")

    for index in (1, 2, 3):
        worker = (project / "04. 조사자료" / "독립조사" / f"worker-{index:02d}.md").read_text(
            encoding="utf-8"
        )
        gaps = [field for field in WORKER_FIELDS if field not in worker]
        if gaps:
            raise RehearsalError(f"worker-{index:02d} 에 출처 확인 항목이 없습니다: {gaps}")

    plan = json.loads(
        (project / "04. 조사자료" / "독립조사계획.json").read_text(encoding="utf-8")
    )
    if plan.get("direction_confirmed") is not False:
        raise RehearsalError("방향 확정 전에 조사가 열려 있습니다")
    if len(plan.get("lanes", [])) < 3:
        raise RehearsalError("독립 조사 lane 이 3개 미만입니다")

    # 라이브 수업은 강사가 참여자 답변·승인을 기록하므로 REAL 이어야 한다.
    # DEMO 는 무인 회귀검증 전용이다.
    stage_state = json.loads(
        (project / "00. 시작하기" / "단계상태.json").read_text(encoding="utf-8")
    )
    if stage_state.get("interactionMode") != "REAL":
        raise RehearsalError(
            f"단계상태 기본 모드가 REAL 이 아닙니다: {stage_state.get('interactionMode')}"
        )
    if len(stage_state.get("stages", [])) != 10:
        raise RehearsalError(f"단계가 10개가 아닙니다: {len(stage_state.get('stages', []))}")
    if stage_state.get("currentStage") != 1:
        raise RehearsalError("새 프로젝트가 1단계에서 시작하지 않습니다")
    started = [
        stage["name"]
        for stage in stage_state.get("stages", [])
        if stage.get("status") != "NOT_STARTED"
    ]
    if started:
        raise RehearsalError(f"생성 직후 이미 진행된 단계가 있습니다: {started}")

    collaboration = json.loads(
        (project / "00. 시작하기" / "사용자협업상태.json").read_text(encoding="utf-8")
    )
    if collaboration.get("interactionMode") != "REAL":
        raise RehearsalError("협업상태 기본 모드가 REAL 이 아닙니다")
    if collaboration.get("contentApproval", {}).get("status") != "NOT_APPROVED":
        raise RehearsalError("생성 직후 내용 승인이 이미 되어 있습니다")

    status_md = (project / "00. 시작하기" / "프로젝트상태.md").read_text(encoding="utf-8")
    if "자료 사용 모드: REAL" not in status_md:
        raise RehearsalError("프로젝트상태.md 에 REAL 이 기록되지 않았습니다")

    approved = json.loads(
        (project / "03. 사업계획서양식" / "placeholder-values.approved.json").read_text(
            encoding="utf-8"
        )
    )
    if approved.get("_approval", {}).get("status") != "NOT_APPROVED":
        raise RehearsalError(f"승인 파일이 미승인 상태가 아닙니다: {approved}")

    digest, entries = tree_digest(project)
    return {"digest": digest, "fileCount": len(entries), "stdout": result.stdout.strip()}


def step_stage_gate(plugin_root: Path, project: Path, env: dict[str, str]) -> dict[str, object]:
    """수업 7~9단계: 승인 전에는 다음 단계로 못 넘어가야 한다."""
    script = (
        plugin_root
        / "skills"
        / "setup-business-plan-project"
        / "scripts"
        / "advance_stage.py"
    )
    if not script.is_file():
        raise RehearsalError("advance_stage.py 가 아티팩트에 없습니다")

    # 1단계는 아직 안 끝났는데 7단계(승인)로 건너뛰려 하면 막혀야 한다.
    skipped = run(
        [sys.executable, str(script), "start", str(project), "7"],
        cwd=project,
        env=env,
    )
    if skipped.returncode == 0:
        raise RehearsalError("승인 단계로 건너뛰기가 차단되지 않았습니다")

    # 증거 없이 1단계를 PASS 로 닫으려 하면 막혀야 한다.
    no_evidence = run(
        [sys.executable, str(script), "complete", str(project), "1", "--status", "PASS"],
        cwd=project,
        env=env,
    )
    if no_evidence.returncode == 0:
        raise RehearsalError("증거 없는 단계 완료가 차단되지 않았습니다")

    # 정상 경로: 1단계 시작은 통과해야 한다.
    started = run(
        [sys.executable, str(script), "start", str(project), "1"],
        cwd=project,
        env=env,
    )
    if started.returncode != 0:
        raise RehearsalError(f"1단계 시작이 실패했습니다: {started.stderr.strip()}")

    checked = run([sys.executable, str(script), "check", str(project)], cwd=project, env=env)
    if checked.returncode != 0:
        raise RehearsalError(f"advance_stage check 실패: {checked.stderr.strip()}")

    payload = "\n".join(
        [
            f"skip:{skipped.returncode}:{normalize(skipped.stdout + skipped.stderr, project)}",
            f"noEvidence:{no_evidence.returncode}:{normalize(no_evidence.stdout + no_evidence.stderr, project)}",
            f"start:{started.returncode}:{normalize(started.stdout, project)}",
            f"check:{checked.returncode}:{normalize(checked.stdout, project)}",
        ]
    )
    return {
        "digest": sha256_bytes(payload.encode("utf-8")),
        "stdout": payload[:1200],
        "skipBlocked": skipped.returncode != 0,
        "evidenceRequired": no_evidence.returncode != 0,
    }


def step_demo_inputs(project: Path, demo_inputs: Path) -> dict[str, object]:
    """수업 6단계: 참여자가 올리는 입력자료가 그대로 들어오는지."""
    target = project / "01. 사업정보"
    copied: list[str] = []
    for name in ("01_회사소개.txt", "02_사업아이디어.txt"):
        matches = sorted(demo_inputs.rglob(name))
        if not matches:
            raise RehearsalError(f"시연 입력자료를 찾지 못했습니다: {name}")
        source = matches[0]
        shutil.copy2(source, target / name)
        copied.append(name)

    banned = ("가상", "더미", "dummy", "샘플입니다")
    hits: list[str] = []
    for name in copied:
        text = (target / name).read_text(encoding="utf-8")
        hits.extend(f"{name}:{word}" for word in banned if word in text)
    if hits:
        raise RehearsalError(f"입력자료에 금지 표현이 남아 있습니다: {hits}")

    digest, _ = tree_digest(target)
    return {"digest": digest, "copied": copied}


def step_hwpx_gate(
    plugin_root: Path, project: Path, template: Path, env: dict[str, str]
) -> dict[str, object]:
    """수업 10단계: 승인 없이는 HWPX 에 아무것도 못 쓰는지."""
    script = (
        plugin_root
        / "skills"
        / "fill-hwpx-template"
        / "scripts"
        / "hwpx_placeholders.py"
    )
    if not script.is_file():
        raise RehearsalError("hwpx_placeholders.py 가 아티팩트에 없습니다")

    workdir = project / "03. 사업계획서양식" / "작업용 HWPX"
    working_copy = workdir / template.name
    shutil.copy2(template, working_copy)

    scanned = run(
        [sys.executable, str(script), "scan", str(working_copy)],
        cwd=project,
        env=env,
    )
    if scanned.returncode != 0:
        raise RehearsalError(f"HWPX scan 실패: {scanned.stderr.strip()}")

    # 미승인 값 파일로 채우려 하면 막혀야 한다.
    unapproved = project / "03. 사업계획서양식" / "placeholder-values.approved.json"
    filled = run(
        [
            sys.executable,
            str(script),
            "fill",
            str(working_copy),
            "--values",
            str(unapproved),
            "--output",
            str(workdir / "미승인출력.hwpx"),
        ],
        cwd=project,
        env=env,
    )
    if filled.returncode == 0:
        raise RehearsalError("승인 없이 HWPX 치환이 통과했습니다")
    if (workdir / "미승인출력.hwpx").exists():
        raise RehearsalError("차단됐는데도 HWPX 파일이 생성됐습니다")

    # --allow-unapproved-values 는 0.12.4 에서 제거됐다. 남아 있으면 게이트가 뚫린다.
    help_text = run([sys.executable, str(script), "fill", "--help"], cwd=project, env=env)
    if "--allow-unapproved-values" in help_text.stdout:
        raise RehearsalError("미승인 우회 플래그가 아직 남아 있습니다")
    if "--canonical-receipt" not in help_text.stdout:
        raise RehearsalError("canonical receipt 결속 옵션이 없습니다")

    payload = "\n".join(
        [
            f"scan:{scanned.returncode}:{normalize(scanned.stdout, project)}",
            f"fillBlocked:{filled.returncode}:{normalize(filled.stdout + filled.stderr, project)}",
            f"flags:{'--allow-unapproved-values' in help_text.stdout}:"
            f"{'--canonical-receipt' in help_text.stdout}",
        ]
    )
    return {
        "returncode": filled.returncode,
        "digest": sha256_bytes(payload.encode("utf-8")),
        "output": payload[:2000],
    }


def step_citation_rendering(plugin_root: Path, env: dict[str, str]) -> dict[str, object]:
    """최종 문서에 외부 출처만 남고 내부 표지는 사라지는지.

    심사자가 보는 문서에 `(검증가설)`·`(사용자 제공자료)`가 찍히면
    사업자가 스스로 근거 없음을 선언한 것으로 읽힌다. 문장은 남고
    표지만 사라져야 한다.
    """
    module = (
        plugin_root
        / "skills"
        / "fill-hwpx-template"
        / "scripts"
        / "hwpx_placeholders.py"
    )
    probe = (
        "import sys, json;"
        f"sys.path.insert(0, {str(module.parent)!r});"
        "from hwpx_placeholders import render_claim_citations as r;"
        "cases=["
        "'- 부산 미역 생산량은 연간 약 11,000톤이다. [E001 | 부산광역시, 2026]',"
        "'- 대표자는 폐기 미역 소식을 접했다. [U001 | 사용자 제공자료, 2026]',"
        "'- 고객군은 아직 검증할 가설이다. [H001 | 검증가설]',"
        "'- 3개월 내 시제품을 만든다. [P001 | 실행계획]',"
        "'- 두 기관 자료를 함께 본다. [E001 | 해양수산부, 2025][E002 | 부산광역시, 2024]',"
        "'- 공개자료와 사용자 진술을 함께 쓴다. [E001 | 부산광역시, 2026][H001 | 검증가설]'"
        "];"
        "print(json.dumps([r(c) for c in cases], ensure_ascii=False))"
    )
    result = run([sys.executable, "-c", probe], cwd=plugin_root, env=env)
    if result.returncode != 0:
        raise RehearsalError(f"출처 표기 검사 실패: {result.stderr.strip()}")
    rendered = json.loads(result.stdout)

    expected = [
        "- 부산 미역 생산량은 연간 약 11,000톤이다. (부산광역시, 2026)",
        "- 대표자는 폐기 미역 소식을 접했다.",
        "- 고객군은 아직 검증할 가설이다.",
        "- 3개월 내 시제품을 만든다.",
        "- 두 기관 자료를 함께 본다. (해양수산부, 2025; 부산광역시, 2024)",
        "- 공개자료와 사용자 진술을 함께 쓴다. (부산광역시, 2026)",
    ]
    if rendered != expected:
        raise RehearsalError(
            "최종 출처 표기가 기대와 다릅니다.\n"
            + "\n".join(
                f"  got={got!r}\n  want={want!r}"
                for got, want in zip(rendered, expected)
                if got != want
            )
        )

    payload = json.dumps(rendered, ensure_ascii=False, sort_keys=True)
    return {"digest": sha256_bytes(payload.encode("utf-8")), "rendered": rendered}


def rehearse(archive: Path, demo_inputs: Path, template: Path, label: str) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix=f"dayoun-rehearsal-{label}-") as temp:
        base = Path(temp)
        home = base / "home"
        plugin_root = base / "plugin"
        workspace = base / "workspace"
        for path in (home, plugin_root, workspace):
            path.mkdir(parents=True, exist_ok=True)

        extract_artifact(archive, plugin_root)
        env = isolated_env(home, plugin_root)
        project = workspace / "모두의창업-사업계획서"

        shape = verify_artifact_shape(plugin_root)
        lead = step_lead_request(plugin_root, workspace, env)
        created = step_create_project(plugin_root, project, env)
        inputs = step_demo_inputs(project, demo_inputs)
        stage = step_stage_gate(plugin_root, project, env)
        hwpx = step_hwpx_gate(plugin_root, project, template, env)
        citations = step_citation_rendering(plugin_root, env)

        return {
            "label": label,
            "artifact": archive.name,
            "artifactDigest": sha256_file(archive),
            "shape": shape,
            "steps": {
                "leadRequest": lead["digest"],
                "createProject": created["digest"],
                "demoInputs": inputs["digest"],
                "stageGate": stage["digest"],
                "hwpxGate": hwpx["digest"],
                "citationRendering": citations["digest"],
            },
            "details": {
                "createdFiles": created["fileCount"],
                "createProjectStdout": normalize(created["stdout"], project),
                "stageStatus": stage["stdout"],
                "skipBlocked": stage["skipBlocked"],
                "evidenceRequired": stage["evidenceRequired"],
                "hwpxFillReturncode": hwpx["returncode"],
                "hwpxGateOutput": hwpx["output"],
                "copiedInputs": inputs["copied"],
                "renderedCitations": citations["rendered"],
            },
        }


def main() -> int:
    configure_utf8_output()
    parser = argparse.ArgumentParser(
        description="공개 릴리스만으로 라이브 수업 시연을 독립 재현하고 결과 동일성을 증명한다"
    )
    parser.add_argument("--artifact", type=Path, required=True, help="공개 릴리스 ZIP")
    parser.add_argument("--demo-inputs", type=Path, required=True, help="강의시연용 입력자료 폴더")
    parser.add_argument(
        "--template",
        type=Path,
        required=True,
        help="시연에 쓰는 HWPX 양식 파일",
    )
    parser.add_argument("--out", type=Path, help="영수증을 남길 폴더")
    args = parser.parse_args()

    if not args.artifact.is_file():
        print(f"BLOCK: 릴리스 ZIP 이 없습니다: {args.artifact}", file=sys.stderr)
        return 2
    if not args.demo_inputs.is_dir():
        print(f"BLOCK: 시연 입력자료 폴더가 없습니다: {args.demo_inputs}", file=sys.stderr)
        return 2
    if not args.template.is_file():
        print(f"BLOCK: HWPX 양식이 없습니다: {args.template}", file=sys.stderr)
        return 2

    try:
        first = rehearse(args.artifact, args.demo_inputs, args.template, "a")
        second = rehearse(args.artifact, args.demo_inputs, args.template, "b")
    except (RehearsalError, OSError, zipfile.BadZipFile, json.JSONDecodeError) as error:
        print(f"BLOCK: {error}", file=sys.stderr)
        return 1

    mismatched = [
        name
        for name in first["steps"]
        if first["steps"][name] != second["steps"][name]
    ]
    status = "PASS" if not mismatched else "BLOCK"

    receipt = {
        "status": status,
        "artifact": first["artifact"],
        "artifactDigest": first["artifactDigest"],
        "version": first["shape"]["version"],
        "skills": first["shape"]["skills"],
        "runA": first["steps"],
        "runB": second["steps"],
        "mismatchedSteps": mismatched,
        "details": first["details"],
    }

    if args.out is not None:
        args.out.mkdir(parents=True, exist_ok=True)
        target = args.out / "live-class-rehearsal.json"
        target.write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"RECEIPT: {target}")

    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
