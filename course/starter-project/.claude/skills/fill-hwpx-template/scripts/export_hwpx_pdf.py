#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HWPX 를 PDF 로 내보내고 레이아웃 넘침을 게이트로 판정한다.

★ 왜 이 스크립트가 필요한가

`verify_hwpx_render.py` 는 렌더 receipt 를 검사하고 `render_pdf_pages.py` 는
PDF 를 페이지 PNG 로 쪼갠다. 그런데 **PDF 를 만드는 단계 자체가 없었다.**
그래서 SKILL.md 는 "한컴 한글에서 열어 `파일 → PDF로 저장하기`" 라는 수동
절차를 안내했고, 화면검수가 사람 손에 묶여 자동 게이트에서 빠졌다.

`rhwp export-pdf` 는 한컴 설치 없이 HWPX 를 직접 PDF 로 변환한다. 이 스크립트가
그 CLI 를 감싸 파이프라인의 빠진 고리를 채운다.

★ LAYOUT_OVERFLOW 를 게이트로 올린 이유 (2026-08-27 실측)

rhwp 는 문단이 단(column) 아래로 넘칠 때 stderr 에 `LAYOUT_OVERFLOW` 를
찍지만 종료코드는 0 이다. 실측: 데모 양식을 치환한 HWPX 가 구조검사
(`hwpx_placeholders validate`, `hwpx_source_integrity`)를 모두 PASS 하고도
렌더에서 넘침 43건이 났다. 원본은 2건이었다 — 치환이 레이아웃을 깨뜨렸는데
어떤 자동 검사도 잡지 못했다.

경고를 파싱해 receipt 에 남기고, 원본 대비 증가분을 BLOCK 조건으로 쓴다.
양식 자체가 원래 갖고 있던 넘침까지 실패로 만들면 쓸 수 없으므로
`--baseline` 으로 원본을 함께 주면 그 차이만 판정한다.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# platform_support 는 ppt-editorial 스킬에만 있다. 이 스킬은 독립 배포되므로
# 다른 스킬 파일을 import 하면 릴리스 ZIP 에서 깨진다. PATH 탐색은 표준
# shutil.which 로 하고, GUI 실행 시 PATH 에서 빠지는 Homebrew 경로만 보완한다.
_PATH_FALLBACKS = ("/opt/homebrew/bin", "/usr/local/bin")


def _which(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    for directory in _PATH_FALLBACKS:
        candidate = Path(directory) / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None

# rhwp 가 찍는 줄 예시:
#   LAYOUT_OVERFLOW: page=0, sec=0, col=0, para=27, type=FullParagraph, ...
#   LAYOUT_OVERFLOW_DRAW: section=0 pi=29 line=0 y=1636.9 ...
_OVERFLOW = re.compile(r"^LAYOUT_OVERFLOW(?:_DRAW)?:", re.MULTILINE)

# 이 스킬이 install_rhwp.py 로 설치하는 위치를 가장 먼저 본다. 그 다음이
# consulting-report 스킬이 bin/ 에 두는 경로다. PATH 와 RHWP_BIN 이 이 목록보다
# 우선한다 — 사용자가 명시한 경로를 번들 사본이 덮으면 안 된다.
_SKILL_BIN = Path(__file__).resolve().parent.parent / "bin"
_EXTRA_RHWP_PATHS = (
    str(_SKILL_BIN / "rhwp"),
    str(_SKILL_BIN / "rhwp.exe"),
    "~/.claude/skills/consulting-report/bin/rhwp",
    "~/.gjc/skills/consulting-report/bin/rhwp",
)


def find_rhwp(explicit: str | None = None) -> str:
    """rhwp 실행 파일 경로. 없으면 설치 안내와 함께 RuntimeError."""
    if explicit:
        candidate = Path(explicit).expanduser()
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
        raise RuntimeError(f"지정한 rhwp 를 찾을 수 없습니다: {explicit}")

    from_env = os.environ.get("RHWP_BIN")
    if from_env:
        return find_rhwp(from_env)

    found = _which("rhwp")
    if found:
        return found

    for raw in _EXTRA_RHWP_PATHS:
        candidate = Path(raw).expanduser()
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)

    raise RuntimeError(
        "rhwp 를 찾을 수 없습니다. HWPX→PDF 화면검수에 필요합니다.\n"
        "  설치: python scripts/install_rhwp.py install\n"
        "  또는 PATH 에 두거나 RHWP_BIN 환경변수로 경로를 지정하세요.\n"
        "  LibreOffice 는 HWPX 를 열지 못하므로 대체재가 아닙니다."
    )


def export_pdf(
    hwpx: Path,
    output: Path,
    *,
    rhwp: str,
    backend: str = "svg",
    timeout: float = 600.0,
) -> dict:
    """HWPX → PDF. rhwp 의 JSON 매니페스트와 넘침 경고 수를 함께 반환한다."""
    if not hwpx.is_file():
        raise FileNotFoundError(f"HWPX 를 찾을 수 없습니다: {hwpx}")
    output.parent.mkdir(parents=True, exist_ok=True)

    completed = subprocess.run(
        [rhwp, "export-pdf", str(hwpx), "-o", str(output), "--backend", backend, "--json"],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    # rhwp 는 진단을 stderr 로, 매니페스트를 stdout 으로 낸다.
    diagnostics = completed.stderr or ""
    if completed.returncode != 0:
        raise RuntimeError(
            f"rhwp export-pdf 실패 (exit {completed.returncode}): {diagnostics.strip()[:400]}"
        )
    if not output.is_file():
        raise RuntimeError("rhwp 가 PDF 를 만들지 않았습니다")

    manifest: dict = {}
    for line in (completed.stdout or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("{"):
            try:
                manifest = json.loads(stripped)
            except json.JSONDecodeError:
                continue
    return {
        "manifest": manifest,
        "overflowCount": len(_OVERFLOW.findall(diagnostics)),
        "diagnostics": diagnostics,
    }


def configure_utf8_output() -> None:
    """Windows 콘솔 기본 코드페이지(cp949)에서 한글 출력이 죽는 것을 막는다."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")


def main() -> int:
    configure_utf8_output()
    parser = argparse.ArgumentParser(
        description="Export HWPX to PDF and gate on layout overflow"
    )
    parser.add_argument("hwpx", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--baseline",
        type=Path,
        help="원본 HWPX. 양식이 원래 갖고 있던 넘침을 빼고 증가분만 판정한다",
    )
    parser.add_argument("--rhwp", help="rhwp 실행 파일 경로 (기본: PATH·RHWP_BIN)")
    parser.add_argument("--backend", default="svg", choices=("svg", "direct"))
    parser.add_argument(
        "--allow-overflow",
        type=int,
        default=0,
        help="허용할 넘침 증가분. 기본 0 — 치환이 레이아웃을 깨면 BLOCK",
    )
    parser.add_argument("--report", type=Path, help="판정 결과 JSON 저장 경로")
    args = parser.parse_args()

    try:
        rhwp = find_rhwp(args.rhwp)
        result = export_pdf(
            args.hwpx.resolve(), args.output.resolve(), rhwp=rhwp, backend=args.backend
        )
    except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired) as error:
        print(f"BLOCK: {error}", file=sys.stderr)
        return 1

    overflow = result["overflowCount"]
    baseline = None
    if args.baseline:
        try:
            with _temporary_pdf(args.output) as scratch:
                baseline = export_pdf(
                    args.baseline.resolve(), scratch, rhwp=rhwp, backend=args.backend
                )["overflowCount"]
        except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired) as error:
            print(f"BLOCK: baseline 변환 실패: {error}", file=sys.stderr)
            return 1

    added = overflow if baseline is None else overflow - baseline
    blocked = added > args.allow_overflow
    report = {
        "schemaVersion": "1.0.0",
        "status": "BLOCK" if blocked else "PASS",
        "hwpx": str(args.hwpx),
        "pdf": str(args.output),
        "renderer": {"name": "rhwp", "version": _rhwp_version(rhwp)},
        "pageCount": result["manifest"].get("pageCount"),
        "layoutOverflow": {
            "count": overflow,
            "baseline": baseline,
            "added": added,
            "allowed": args.allow_overflow,
        },
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if blocked:
        print(
            f"BLOCK: 레이아웃 넘침이 {added}건 늘었습니다. 치환값이 칸을 넘쳤는지 "
            "확인하세요. 짧은 칸에 개조식 2줄이 들어가면 셀이 터집니다.",
            file=sys.stderr,
        )
        return 2
    return 0


def _rhwp_version(rhwp: str) -> str:
    try:
        out = subprocess.run([rhwp, "-V"], capture_output=True, text=True, timeout=30)
        return (out.stdout or out.stderr).strip().split()[-1]
    except Exception:  # noqa: BLE001
        return "unknown"


class _temporary_pdf:
    """baseline 변환용 임시 PDF 경로. 산출물 옆에 만들고 지운다."""

    def __init__(self, sibling: Path) -> None:
        self._path = sibling.parent / f".baseline-{sibling.name}"

    def __enter__(self) -> Path:
        return self._path

    def __exit__(self, *_exc: object) -> None:
        shutil.rmtree(self._path, ignore_errors=True)
        if self._path.exists():
            self._path.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
