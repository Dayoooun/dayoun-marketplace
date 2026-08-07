# -*- coding: utf-8 -*-
"""ppt-editorial 하네스의 Windows/macOS 공통 실행 지원.

폰트 탐색, CLI 위치 확인, 프로세스 트리 종료를 한곳에 모은다. 호출부가
운영체제별 절대 경로나 taskkill 명령을 직접 알지 않게 하는 것이 목적이다.
"""
from __future__ import annotations

import functools
import os
import ntpath
import posixpath
import platform
import shutil
import signal
import subprocess
from typing import Iterable

_FONT_EXTS = {".ttf", ".otf", ".ttc"}


def system_name() -> str:
    return platform.system() or ("Windows" if os.name == "nt" else "Unknown")


def font_dirs(system: str | None = None, home: str | None = None,
              existing_only: bool = True) -> list[str]:
    """운영체제별 폰트 디렉터리 목록을 반환한다.

    ``system``과 ``home``은 macOS 경로 규칙을 다른 OS에서도 테스트하기 위한
    주입 지점이다. ``PPT_EDITORIAL_FONT_DIRS``로 사용자 폰트 위치를 추가할 수 있다.
    """
    sys_name = system or system_name()
    pathmod = ntpath if sys_name == "Windows" else posixpath
    user_home = home or os.path.expanduser("~")
    dirs: list[str] = []
    if system is None:
        dirs.extend(p for p in os.environ.get("PPT_EDITORIAL_FONT_DIRS", "").split(os.pathsep) if p)

    if sys_name == "Windows":
        windir = os.environ.get("WINDIR", r"C:\Windows")
        local = os.environ.get("LOCALAPPDATA", pathmod.join(user_home, "AppData", "Local"))
        dirs.extend([
            pathmod.join(windir, "Fonts"),
            pathmod.join(local, "Microsoft", "Windows", "Fonts"),
        ])
    elif sys_name == "Darwin":
        dirs.extend([
            pathmod.join(user_home, "Library", "Fonts"),
            "/Library/Fonts",
            "/System/Library/Fonts",
            "/System/Library/Fonts/Supplemental",
        ])
    else:
        dirs.extend([
            pathmod.join(user_home, ".local", "share", "fonts"),
            pathmod.join(user_home, ".fonts"),
            "/usr/local/share/fonts",
            "/usr/share/fonts",
        ])

    seen: set[str] = set()
    result: list[str] = []
    for item in dirs:
        expanded = item if system is not None else os.path.expanduser(item)
        path = pathmod.normpath(expanded)
        key = pathmod.normcase(path)
        if key in seen or (existing_only and not os.path.isdir(path)):
            continue
        seen.add(key)
        result.append(path)
    return result


@functools.lru_cache(maxsize=1)
def _font_index() -> dict[str, str]:
    index: dict[str, str] = {}
    for root in font_dirs():
        for current, _, files in os.walk(root):
            for name in files:
                if os.path.splitext(name)[1].lower() in _FONT_EXTS:
                    index.setdefault(name.casefold(), os.path.join(current, name))
    return index


def find_font(names: Iterable[str] | str) -> str | None:
    """후보 파일명을 순서대로 찾아 첫 경로를 반환한다."""
    candidates = [names] if isinstance(names, str) else list(names)
    explicit = os.environ.get("PPT_EDITORIAL_FONT")
    if explicit and os.path.isfile(os.path.expanduser(explicit)):
        return os.path.abspath(os.path.expanduser(explicit))
    index = _font_index()
    for name in candidates:
        if not name:
            continue
        expanded = os.path.abspath(os.path.expanduser(name))
        if os.path.isfile(expanded):
            return expanded
        found = index.get(os.path.basename(name).casefold())
        if found:
            return found
    return None


def default_font(bold: bool = False, serif: bool = False) -> str:
    """한글을 렌더할 수 있는 기본 폰트를 운영체제와 무관하게 선택한다."""
    if serif:
        preferred = [
            "NotoSerifKR-VF.ttf", "NotoSerifCJK-Regular.ttc",
            "RIDIBatang.otf", "AppleMyungjo.ttf", "NanumMyeongjo.ttf",
            "batang.ttc", "Times New Roman.ttf", "DejaVuSerif.ttf",
            "LiberationSerif-Regular.ttf",
        ]
    elif bold:
        preferred = [
            "Pretendard-Bold.otf", "NotoSansKR-Bold.ttf",
            "NotoSansCJK-Bold.ttc", "AppleSDGothicNeo.ttc",
            "malgunbd.ttf", "Arial Unicode.ttf", "Arial Bold.ttf",
            "DejaVuSans-Bold.ttf",
        ]
    else:
        preferred = [
            "Pretendard-Regular.otf", "NotoSansKR-Regular.ttf",
            "NotoSansCJK-Regular.ttc", "AppleSDGothicNeo.ttc",
            "AppleGothic.ttf", "malgun.ttf", "Arial Unicode.ttf",
            "Arial.ttf", "DejaVuSans.ttf",
        ]
    found = find_font(preferred)
    if found:
        return found
    raise RuntimeError(
        "사용 가능한 글꼴을 찾지 못했습니다. Pretendard 또는 Noto Sans KR을 설치하거나 "
        "PPT_EDITORIAL_FONT 환경변수에 폰트 경로를 지정하세요."
    )


def resolve_executable(name: str) -> str | None:
    """PATH와 macOS GUI 셸의 대표 설치 위치에서 실행 파일을 찾는다."""
    found = shutil.which(name)
    if found:
        return found
    if system_name() != "Darwin":
        return None
    home = os.path.expanduser("~")
    candidates = [
        f"/opt/homebrew/bin/{name}",
        f"/usr/local/bin/{name}",
        os.path.join(home, ".npm-global", "bin", name),
        os.path.join(home, ".local", "bin", name),
        os.path.join(home, "Library", "pnpm", name),
    ]
    return next((p for p in candidates if os.path.isfile(p) and os.access(p, os.X_OK)), None)


def process_group_kwargs(system: str | None = None) -> dict:
    """Popen이 자식까지 종료할 수 있는 독립 프로세스 그룹을 만들게 한다."""
    if (system or system_name()) == "Windows":
        flag = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        return {"creationflags": flag} if flag else {}
    return {"start_new_session": True}


def terminate_process_tree(proc: subprocess.Popen | None, wait_seconds: float = 3.0) -> None:
    """Windows는 taskkill, macOS/Linux는 프로세스 그룹 신호로 전체 트리를 끝낸다."""
    if proc is None or proc.poll() is not None:
        return
    if system_name() == "Windows":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait(timeout=wait_seconds)
    except (ProcessLookupError, PermissionError, subprocess.TimeoutExpired):
        if proc.poll() is None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                proc.kill()
