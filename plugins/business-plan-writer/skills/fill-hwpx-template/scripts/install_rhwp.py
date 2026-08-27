#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rhwp CLI 설치·검사. HWPX→PDF 화면검수에 필요하다.

★ 왜 필요한가

`export_hwpx_pdf.py` 는 rhwp 가 없으면 BLOCK 한다. 화면검수 없는 HWPX 를
납품하지 않기 위해서다. 그런데 BLOCK 만 하고 설치 방법을 알려주지 않으면
사용자는 거기서 막힌다. 이 스크립트가 그 간극을 메운다.

★ 무결성 검증을 건너뛰지 않는 이유

바이너리를 인터넷에서 받아 실행하는 절차다. 릴리스에 첨부된
`SHA256SUMS.txt` 와 대조하지 않으면 받은 것이 게시된 것과 같은지 알 수 없다.
대조 실패는 경고가 아니라 BLOCK 이며, 받은 파일을 지운다.

★ 설치 위치

기본은 이 스킬 폴더의 `bin/` 이다. 시스템 경로를 건드리지 않고, 플러그인을
지우면 함께 사라진다. `--target` 으로 바꿀 수 있다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

REPO = "edwardkim/rhwp"
LATEST_API = f"https://api.github.com/repos/{REPO}/releases/latest"
SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TARGET = SKILL_ROOT / "bin"

# 릴리스 자산 이름 규칙: rhwp-<tag>-<platform>.<ext>
_PLATFORMS = {
    ("Darwin", "arm64"): ("macos-aarch64", "tar.gz"),
    ("Darwin", "x86_64"): ("macos-x86_64", "tar.gz"),
    ("Linux", "x86_64"): ("linux-x86_64", "tar.gz"),
    ("Windows", "AMD64"): ("windows-x86_64", "zip"),
    ("Windows", "x86_64"): ("windows-x86_64", "zip"),
}


def configure_utf8_output() -> None:
    """Windows 콘솔 기본 코드페이지(cp949)에서 한글 출력이 죽는 것을 막는다."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")


def platform_key() -> tuple[str, str]:
    machine = platform.machine()
    # macOS 는 arm64, Linux 는 aarch64 로 같은 CPU 를 다르게 부른다.
    if machine == "aarch64":
        machine = "arm64"
    return platform.system(), machine


def asset_for(tag: str) -> tuple[str, str]:
    """이 플랫폼의 (자산 이름, 확장자). 지원하지 않으면 RuntimeError."""
    key = platform_key()
    entry = _PLATFORMS.get(key)
    if entry is None:
        raise RuntimeError(
            f"지원하지 않는 플랫폼입니다: {key[0]}/{key[1]}\n"
            f"  https://github.com/{REPO}/releases 에서 직접 받아 PATH 에 두거나\n"
            "  RHWP_BIN 환경변수로 경로를 지정하세요."
        )
    suffix, extension = entry
    return f"rhwp-{tag}-{suffix}.{extension}", extension


def fetch(url: str, timeout: float = 120.0) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "dayoun-marketplace"})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return response.read()


def latest_tag() -> str:
    payload = json.loads(fetch(LATEST_API).decode("utf-8"))
    tag = payload.get("tag_name")
    if not tag:
        raise RuntimeError("최신 릴리스 태그를 확인하지 못했습니다")
    return str(tag)


def expected_digest(tag: str, asset: str) -> str:
    """SHA256SUMS.txt 에서 이 자산의 digest 를 찾는다."""
    url = f"https://github.com/{REPO}/releases/download/{tag}/SHA256SUMS.txt"
    for line in fetch(url).decode("utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == asset:
            return parts[0]
    raise RuntimeError(f"SHA256SUMS.txt 에 {asset} 항목이 없습니다")


def install(target: Path, tag: str | None = None) -> Path:
    """rhwp 를 target/ 에 설치하고 실행 파일 경로를 반환한다."""
    resolved_tag = tag or latest_tag()
    asset, extension = asset_for(resolved_tag)
    url = f"https://github.com/{REPO}/releases/download/{resolved_tag}/{asset}"

    with tempfile.TemporaryDirectory(prefix="rhwp-") as directory:
        scratch = Path(directory)
        archive = scratch / asset
        archive.write_bytes(fetch(url, timeout=600.0))

        actual = hashlib.sha256(archive.read_bytes()).hexdigest()
        wanted = expected_digest(resolved_tag, asset)
        if actual != wanted:
            archive.unlink(missing_ok=True)
            raise RuntimeError(
                "다운로드 무결성 검증 실패 — 받은 파일을 지웠습니다.\n"
                f"  기대: {wanted}\n  실제: {actual}"
            )

        extracted = scratch / "unpacked"
        extracted.mkdir()
        if extension == "zip":
            with zipfile.ZipFile(archive) as bundle:
                bundle.extractall(extracted)
        else:
            with tarfile.open(archive) as bundle:
                bundle.extractall(extracted)

        binary_name = "rhwp.exe" if platform_key()[0] == "Windows" else "rhwp"
        found = next(
            (path for path in extracted.rglob(binary_name) if path.is_file()), None
        )
        if found is None:
            raise RuntimeError(f"압축 안에 {binary_name} 이 없습니다")

        target.mkdir(parents=True, exist_ok=True)
        destination = target / binary_name
        shutil.copy2(found, destination)
        destination.chmod(destination.stat().st_mode | 0o111)

        # macOS 는 인터넷에서 받은 파일에 quarantine 속성을 붙여 실행을 막는다.
        if platform_key()[0] == "Darwin":
            subprocess.run(
                ["xattr", "-d", "com.apple.quarantine", str(destination)],
                capture_output=True,
                check=False,
            )
        return destination


def probe(binary: Path | str) -> str | None:
    """실제로 실행해 버전을 얻는다. 파일 존재만으로는 동작을 보장하지 못한다."""
    try:
        result = subprocess.run(
            [str(binary), "-V"], capture_output=True, text=True, timeout=60
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    output = (result.stdout or result.stderr).strip()
    return output.split()[-1] if output else None


def main() -> int:
    configure_utf8_output()
    parser = argparse.ArgumentParser(description="Install or check the rhwp CLI")
    parser.add_argument(
        "command", choices=("check", "install"), help="check: 설치 여부만 확인"
    )
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--tag", help="설치할 릴리스 태그 (기본: 최신)")
    parser.add_argument("--json", action="store_true", help="결과를 JSON 으로 출력")
    args = parser.parse_args()

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from export_hwpx_pdf import find_rhwp  # noqa: PLC0415

    try:
        existing = find_rhwp()
    except RuntimeError:
        existing = None

    if existing and args.command == "check":
        version = probe(existing)
        report = {"status": "PASS" if version else "BLOCK", "path": existing, "version": version}
        print(json.dumps(report, ensure_ascii=False, indent=2) if args.json
              else f"rhwp {version or '실행 불가'}: {existing}")
        return 0 if version else 2

    if existing and args.command == "install":
        version = probe(existing)
        if version:
            print(f"이미 설치돼 있습니다: rhwp {version} ({existing})")
            return 0

    if args.command == "check":
        print(
            "BLOCK: rhwp 가 없습니다. HWPX→PDF 화면검수에 필요합니다.\n"
            f"  설치: python {Path(__file__).name} install",
            file=sys.stderr,
        )
        return 2

    try:
        installed = install(args.target.expanduser().resolve(), args.tag)
    except (RuntimeError, urllib.error.URLError, OSError) as error:
        print(f"BLOCK: rhwp 설치 실패: {error}", file=sys.stderr)
        return 1

    version = probe(installed)
    if not version:
        print(f"BLOCK: 설치한 rhwp 를 실행할 수 없습니다: {installed}", file=sys.stderr)
        return 1

    report = {"status": "PASS", "path": str(installed), "version": version}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"설치 완료: rhwp {version}\n  {installed}")
        print(f"  export_hwpx_pdf.py 가 이 경로를 자동으로 찾습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
