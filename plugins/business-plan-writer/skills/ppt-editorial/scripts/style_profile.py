#!/usr/bin/env python3
"""스타일 프로파일을 프롬프트 블록으로 해석한다.

왜 필요한가
-----------
`SKILL.md`의 스타일 설명만으로는 실행 경로가 디자인 DNA를 읽지 못했다.
프로파일을 기계가 읽는 단일 출처(`style_profiles.json`)로 옮기고, 잡 생성 시
슬라이드 역할에 맞는 변형과 기준 이미지를 항상 주입한다.

기본값 정책
-----------
프로파일을 지정하지 않으면 `defaultProfile`(`toss-data-unified`)을 쓴다.
개념·제품·프로세스는 Toss형 3D, 설문·KPI·통계는 데이터 에디토리얼로 고른다.
명시한 `styleVariant`가 자동 판정보다 우선한다. 브랜드색은 파라미터로 받는다.
"""

from __future__ import annotations

import argparse
import json
import re
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
def resolve_palette(name: str | None = None) -> tuple[str, dict]:
    """큐레이션된 팔레트를 확정한다. 미지정 기본값은 editorial-blue."""
    data = load_profiles()
    palettes = data.get("palettePresets", {})
    resolved = name or "editorial-blue"
    if resolved not in palettes:
        raise StyleProfileError(
            f"알 수 없는 palettePreset: {resolved!r}. 사용 가능: {sorted(palettes)}"
        )
    return resolved, palettes[resolved]



def _keyword_score(text: str, keywords: list[str]) -> int:
    """부정문에 등장한 시각어를 제외하고 역할어를 센다."""
    score = 0
    for keyword in keywords:
        needle = str(keyword).casefold()
        start = 0
        while True:
            position = text.find(needle, start)
            if position < 0:
                break
            prefix = text[max(0, position - 20):position].rstrip()
            if not re.search(r"(?:\bno|\bnot|\bwithout|금지|제외)\s*$", prefix):
                score += 1
                break
            start = position + len(needle)
    return score


def select_variant(
    name: str | None = None,
    prompt: str = "",
    requested: str | None = None,
) -> str | None:
    """통합 프로파일의 슬라이드 역할 변형을 고른다."""
    _, profile = resolve(name)
    variants = profile.get("variants")
    if not variants:
        if requested:
            raise StyleProfileError(
                f"{name!r} 프로파일은 styleVariant를 지원하지 않습니다."
            )
        return None
    if requested:
        if requested not in variants:
            raise StyleProfileError(
                f"알 수 없는 styleVariant: {requested!r}. "
                f"사용 가능: {sorted(variants)}"
            )
        return requested

    routing = profile.get("variantRouting", {})
    folded = prompt.casefold()
    data_score = _keyword_score(folded, routing.get("dataKeywords", []))
    icon_score = _keyword_score(folded, routing.get("iconKeywords", []))
    toss_score = _keyword_score(folded, routing.get("toss3dKeywords", []))
    if data_score >= max(icon_score, toss_score) and data_score > 0:
        return "data-editorial"
    if icon_score >= toss_score and icon_score > 0:
        return "icon-editorial"
    return routing.get("default") or next(iter(variants))


def variant_config(name: str | None = None, variant: str | None = None) -> dict:
    """프로파일 공통값 위에 선택 변형을 얹는다."""
    _, profile = resolve(name)
    if variant is None:
        return profile
    variants = profile.get("variants", {})
    if variant not in variants:
        raise StyleProfileError(
            f"알 수 없는 styleVariant: {variant!r}. 사용 가능: {sorted(variants)}"
        )
    return {**profile, **variants[variant]}


def _is_table_prompt(prompt: str) -> bool:
    folded = prompt.casefold()
    return (
        "테이블" in folded
        or re.search(
            r"(?<![가-힣])표(?=$|[\s·,.:()]|로|를|처럼|형식|형태)",
            folded,
        )
        is not None
    )


def reference_assets(
    name: str | None = None,
    variant: str | None = None,
    prompt: str = "",
) -> list[str]:
    """프로파일과 정보 형식에 결속된 시각 앵커를 절대경로로 돌려준다."""
    profile = variant_config(name, variant)
    asset_key = (
        "tableReferenceAssets"
        if _is_table_prompt(prompt) and profile.get("tableReferenceAssets")
        else "referenceAssets"
    )
    assets = []
    for raw_path in profile.get(asset_key, []):
        path = (SKILL_ROOT / raw_path).resolve()
        if not path.is_file():
            raise StyleProfileError(f"스타일 레퍼런스를 찾을 수 없습니다: {path}")
        assets.append(str(path))
    return assets


def accent_block(
    accent: str | None,
    allow_status: bool = False,
    allow_tints: bool = False,
) -> str:
    """강조색 강제 문구.

    프로파일이 블루 계열 레퍼런스를 쓰더라도 브랜드색을 이겨야 한다.
    색을 안 주면 하네스가 임의로 고르지 않고 명시적으로 중립을 요구한다.
    """
    status_exception = (
        " A small semantic status colour is allowed only for an actual warning, "
        "gap or negative finding."
        if allow_status
        else ""
    )
    colour_scope = (
        f"{accent} or lighter same-hue tints derived from it"
        if accent and allow_tints
        else accent
    )
    if accent:
        return (
            f"★★ ACCENT COLOUR — USE {colour_scope}:\n"
            f"Every highlight, key number, active pill, icon accent and rule "
            f"emphasis must use {colour_scope}. Do NOT substitute a generic blue or "
            f"any other decorative hue, even if the style reference uses one."
            f"{status_exception}"
        )
    return (
        "★★ ACCENT COLOUR — NOT SUPPLIED:\n"
        "Use a single restrained neutral accent (dark ink grey). Do NOT invent "
        "a brand colour and do NOT default to generic tech blue."
        f"{status_exception}"
    )


def prompt_block(
    name: str | None = None,
    accent: str | None = None,
    variant: str | None = None,
) -> str:
    """잡 프롬프트에 붙일 스타일 강제 블록."""
    _, profile = resolve(name)
    config = variant_config(name, variant)
    blocks = [profile.get("promptBlock", "").strip()]
    data = load_profiles()
    default_profile = data.get("profiles", {}).get(data.get("defaultProfile"), {})
    anti_slop = (
        profile.get("antiSlopPrompt")
        or default_profile.get("antiSlopPrompt")
        or ""
    ).strip()
    if anti_slop:
        blocks.append(anti_slop)
    headline = (
        profile.get("headlinePrompt")
        or default_profile.get("headlinePrompt")
        or ""
    ).strip()
    if headline:
        blocks.append(headline)
    if variant:
        blocks.append(config.get("promptBlock", "").strip())
    blocks = [block for block in blocks if block]
    if not blocks:
        raise StyleProfileError(f"{name} 프로파일에 promptBlock 이 없습니다.")
    variant_receipt = (
        f"★★ SELECTED STYLE VARIANT: {variant}\n"
        if variant
        else ""
    )
    return (
        variant_receipt
        + "\n\n".join(blocks)
        + "\n\n"
        + accent_block(
            accent,
            allow_status=bool(config.get("allowSemanticStatusColors")),
            allow_tints=bool(config.get("allowAccentTints")),
        )
    )


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description="스타일 프로파일 조회")
    parser.add_argument("--profile", help="프로파일 이름 (생략 시 기본값)")
    parser.add_argument("--accent", help="브랜드 강조색 (예: #0B5FFF)")
    parser.add_argument("--variant", help="통합 프로파일 변형 (toss-3d|data-editorial)")
    parser.add_argument("--prompt", default="", help="자동 변형 판정용 슬라이드 프롬프트")
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
        variant = select_variant(args.profile, args.prompt, args.variant)
        print(f"PROFILE: {name} — {profile.get('label')}")
        if variant:
            print(f"VARIANT: {variant}")
        print()
        print(prompt_block(args.profile, args.accent, variant))
        return 0
    except StyleProfileError as error:
        print(f"BLOCK: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
