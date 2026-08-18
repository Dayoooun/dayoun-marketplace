#!/usr/bin/env python3
"""스타일 프로파일을 프롬프트 블록으로 해석한다.

왜 필요한가
-----------
SKILL.md 의 "모던 플랫 (Toss/Naver flat)" 프로파일은 산문 설명이라 실행 경로가
읽지 못했다. 그래서 사용자가 매번 토스 룩을 원해도 슬라이드마다 다른 룩이
나왔다. 프로파일을 기계가 읽는 단일 출처(`style_profiles.json`)로 옮기고,
잡 생성 시 프롬프트에 항상 주입한다.

기본값 정책
-----------
프로파일을 지정하지 않으면 `defaultProfile`(modern-flat)을 쓴다.
"절대 고정 금지"는 강조색·서체를 하네스가 임의로 **가정**하지 말라는 뜻이지,
룩 자체를 매번 무작위로 흔들라는 뜻이 아니다. 기본 프로파일은 고정하고,
브랜드색은 파라미터로 받아 프롬프트에서 강제한다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
PROFILES_PATH = SKILL_ROOT / "style_profiles.json"


class StyleProfileError(ValueError):
    pass


def load_profiles() -> dict:
    try:
        return json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise StyleProfileError(
            f"스타일 프로파일 정의를 찾을 수 없습니다: {PROFILES_PATH}"
        ) from error
    except json.JSONDecodeError as error:
        raise StyleProfileError(f"스타일 프로파일 JSON 오류: {error}") from error


def resolve(name: str | None = None) -> tuple[str, dict]:
    """프로파일 이름을 확정한다. 지정이 없으면 기본값."""
    data = load_profiles()
    profiles = data.get("profiles", {})
    resolved = name or data.get("defaultProfile")
    if resolved not in profiles:
        raise StyleProfileError(
            f"알 수 없는 스타일 프로파일: {resolved!r}. "
            f"사용 가능: {sorted(profiles)}"
        )
    return resolved, profiles[resolved]


def accent_block(accent: str | None) -> str:
    """강조색 강제 문구.

    프로파일이 블루 계열 레퍼런스를 쓰더라도 브랜드색을 이겨야 한다.
    색을 안 주면 하네스가 임의로 고르지 않고 명시적으로 중립을 요구한다.
    """
    if accent:
        return (
            f"★★ ACCENT COLOUR — USE EXACTLY {accent}:\n"
            f"Every highlight, key number, active pill, icon accent and rule "
            f"emphasis must use {accent}. Do NOT substitute a generic blue or "
            f"any other hue, even if the style reference uses one."
        )
    return (
        "★★ ACCENT COLOUR — NOT SUPPLIED:\n"
        "Use a single restrained neutral accent (dark ink grey). Do NOT invent "
        "a brand colour and do NOT default to generic tech blue."
    )


def prompt_block(name: str | None = None, accent: str | None = None) -> str:
    """잡 프롬프트에 붙일 스타일 강제 블록."""
    _, profile = resolve(name)
    block = profile.get("promptBlock", "").strip()
    if not block:
        raise StyleProfileError(f"{name} 프로파일에 promptBlock 이 없습니다.")
    return block + "\n\n" + accent_block(accent)


def main() -> int:
    parser = argparse.ArgumentParser(description="스타일 프로파일 조회")
    parser.add_argument("--profile", help="프로파일 이름 (생략 시 기본값)")
    parser.add_argument("--accent", help="브랜드 강조색 (예: #0B5FFF)")
    parser.add_argument("--list", action="store_true", help="사용 가능한 프로파일")
    args = parser.parse_args()

    try:
        if args.list:
            data = load_profiles()
            print(f"기본값: {data.get('defaultProfile')}")
            for key, value in data.get("profiles", {}).items():
                mark = " (기본)" if key == data.get("defaultProfile") else ""
                print(f"  {key}{mark}: {value.get('label')}")
                print(f"      {value.get('summary')}")
            return 0

        name, profile = resolve(args.profile)
        print(f"PROFILE: {name} — {profile.get('label')}")
        print()
        print(prompt_block(args.profile, args.accent))
        return 0
    except StyleProfileError as error:
        print(f"BLOCK: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
