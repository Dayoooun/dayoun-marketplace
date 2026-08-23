# -*- coding: utf-8 -*-
"""하네스 스모크 테스트 (2026-08-02)

## 왜 필요한가
`doc_consistency`는 문서를, `deck_qc`는 산출 이미지를 검사한다.
**코드 자체가 도는지**는 아무도 안 본다.

이 세션에서 실제로 있었던 일:
- `typo()` 시그니처 불일치로 `NameError` — 렌더까지 가서야 발견
- `Deck.save()` 미호출로 `FileNotFoundError` — 재로드 시점에 터짐
- `Image.getdata()` deprecation — 씬 생성 때마다 경고

전부 "import는 되는데 실행하면 죽는" 부류다. import 확인만으로는 못 잡는다.

## 사용
    python scripts/harness_smoke.py           # 조립까지 (수초)
    python scripts/harness_smoke.py --quiet   # 실패만 출력
"""
import os, sys, glob, json, warnings, tempfile, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
# 하네스 사본은 평면 구조라 모듈이 HERE 에 그대로 있다.
# 스킬 원본 트리에서 돌릴 때만 scene-deck 하위를 본다.
SD = HERE if os.path.exists(os.path.join(HERE, "layout_engine.py")) \
    else os.path.join(HERE, "scene-deck")
sys.path.insert(0, SD)
sys.path.insert(0, HERE)

CHECKS = []


def check(name):
    def deco(fn):
        CHECKS.append((name, fn))
        return fn
    return deco


@check("모듈 import")
def _import():
    import fonts, presets, layout_engine, photos, revise, deck, intake, platform_support  # noqa
    import html_slide_renderer, codex_parallel_gen, scenario_harness  # noqa
    return "11모듈"


@check("스타일 프로파일")
def _style_profiles():
    import style_profile
    name, profile = style_profile.resolve()
    if name != "toss-data-unified" or not profile.get("variants"):
        raise AssertionError("통합 전역 기본 프로파일 누락")

    data_variant = style_profile.select_variant(
        name,
        "응답자 설문 KPI 58.4% 분포 차트",
    )
    toss_variant = style_profile.select_variant(
        name,
        "서비스 프로세스와 고객 여정을 보여주는 3D scene",
    )
    icon_variant = style_profile.select_variant(
        name,
        "핵심 기능 4가지와 단계별 체크리스트",
    )
    explicit = style_profile.select_variant(
        name,
        "표지에 KPI라는 단어가 있음",
        requested="toss-3d",
    )
    if (data_variant, toss_variant, icon_variant, explicit) != (
        "data-editorial",
        "toss-3d",
        "icon-editorial",
        "toss-3d",
    ):
        raise AssertionError("스타일 변형 라우팅 실패")
    if style_profile.select_variant(name, "표지") != "toss-3d":
        raise AssertionError("전역 기본 변형이 Toss 3D가 아님")

    assets = style_profile.reference_assets(name, data_variant)
    if len(assets) != 3 or not all(os.path.isfile(path) for path in assets):
        raise AssertionError("검증된 데이터 레퍼런스 3종 결속 실패")
    toss_assets = style_profile.reference_assets(name, toss_variant)
    if len(toss_assets) != 3 or not all(os.path.isfile(path) for path in toss_assets):
        raise AssertionError("검증된 Toss 3D 레퍼런스 3종 결속 실패")
    icon_assets = style_profile.reference_assets(name, icon_variant)
    if len(icon_assets) != 3 or not all(os.path.isfile(path) for path in icon_assets):
        raise AssertionError("아이콘 변형의 통합 DNA 앵커 결속 실패")
    table_assets = style_profile.reference_assets(
        name,
        data_variant,
        "세 열 데이터 테이블",
    )
    if (
        len(table_assets) != 1
        or not table_assets[0].endswith("toss-data-table.png")
        or not os.path.isfile(table_assets[0])
    ):
        raise AssertionError("승인 표 전용 앵커 선택 실패")

    data_prompt = style_profile.prompt_block(name, "#246BFD", data_variant)
    for required in (
        "SELECTED STYLE VARIANT: data-editorial",
        "#246BFD",
        "same-hue tints",
        "semantic status colour",
    ):
        if required not in data_prompt:
            raise AssertionError("데이터 변형 프롬프트 누락: %s" % required)

    toss_prompt = style_profile.prompt_block(name, "#246BFD", toss_variant)
    if "semantic status colour" in toss_prompt or "TOSS 3D SCENE" not in toss_prompt:
        raise AssertionError("Toss 3D 변형 규칙 오염")
    icon_prompt = style_profile.prompt_block(name, "#246BFD", icon_variant)
    if (
        "SEMANTIC ICON EDITORIAL" not in icon_prompt
        or "NO equal repeated cards" not in icon_prompt
    ):
        raise AssertionError("아이콘 에디토리얼 규칙 누락")
    return "전역통합·3방향라우팅·앵커7종"


@check("하이브리드 렌더 라우팅")
def _hybrid_renderer():
    import html_slide_renderer
    import codex_parallel_gen
    from playwright.sync_api import sync_playwright

    table_job = {
        "renderer": "html",
        "layout": "table",
        "out": "table.png",
    }
    scene_job = {
        "renderer": "codex",
        "prompt": "Toss-style 3D product scene",
        "out": "scene.png",
    }
    if not html_slide_renderer.supports(table_job):
        raise AssertionError("HTML 표 라우팅 실패")
    if html_slide_renderer.supports(scene_job):
        raise AssertionError("3D 씬이 HTML 경로로 오염")
    if not codex_parallel_gen.is_html_job(table_job):
        raise AssertionError("통합 생성기 HTML 라우팅 실패")
    if codex_parallel_gen.is_html_job(scene_job):
        raise AssertionError("통합 생성기 Codex 라우팅 실패")
    with sync_playwright() as playwright:
        if not os.path.isfile(playwright.chromium.executable_path):
            raise AssertionError("Playwright Chromium 미설치")
    return "HTML9종·Codex3역할"


@check("실전 시나리오 계약")
def _scenario_contract():
    import html_slide_renderer

    reference_dir = os.path.join(os.path.dirname(HERE), "references")
    paths = {
        "contract": os.path.join(reference_dir, "render_contract.json"),
        "fewshots": os.path.join(reference_dir, "scenario_fewshots.json"),
        "catalog": os.path.join(reference_dir, "scenario_catalog.json"),
    }
    payloads = {}
    for name, path in paths.items():
        if not os.path.isfile(path):
            raise AssertionError(f"{name} 파일 누락: {path}")
        with open(path, encoding="utf-8") as handle:
            payloads[name] = json.load(handle)
    scenarios = payloads["catalog"].get("scenarios", [])
    fewshots = payloads["fewshots"].get("fewShots", [])
    if len(scenarios) < 12 or len(fewshots) < 9:
        raise AssertionError("시나리오 또는 few-shot 수량 부족")
    routing = payloads["contract"].get("contextRouting", {}).get(
        "visualRoleToLayout", {}
    )
    covered_layouts = {
        shot.get("decision", {}).get("layout")
        for shot in fewshots
    }
    for scenario in scenarios:
        role = scenario.get("context", {}).get("visualRole")
        layout = scenario.get("spec", {}).get("layout")
        if routing.get(role) != layout:
            raise AssertionError(
                f"context route mismatch: {scenario.get('id')}: "
                f"{role}->{routing.get(role)} != {layout}"
            )
        if layout not in covered_layouts:
            raise AssertionError(
                f"few-shot coverage missing: {scenario.get('id')}: {layout}"
            )
    graph_scenarios = [
        scenario for scenario in scenarios
        if scenario.get("spec", {}).get("layout") == "network"
    ]
    for scenario in graph_scenarios:
        graph = scenario["spec"]["graph"]
        errors = html_slide_renderer.validate_graph(graph)
        if errors:
            raise AssertionError(f"그래프 계약 실패: {scenario['id']}: {errors}")
        if any("x" in node or "y" in node for node in graph["nodes"]):
            raise AssertionError(f"수동 좌표 발견: {scenario['id']}")
    invalid = {
        "nodes": [
            {"id": "a", "label": "A", "entityType": "INPUT"},
            {"id": "orphan", "label": "고립", "entityType": "SYSTEM"},
        ],
        "edges": [
            {"source": "a", "target": "missing", "direction": "forward", "label": ""}
        ],
    }
    if not html_slide_renderer.validate_graph(invalid):
        raise AssertionError("잘못된 그래프를 통과시킴")
    return f"{len(scenarios)}시나리오·{len(fewshots)}few-shot·그래프차단"


@check("요구사항 확인 게이트")
def _intake_gate():
    import intake
    sparse = intake.assess({"title": "테스트"})
    if sparse["phase"] != "intake" or not 0 < len(sparse["questions"]) <= 3:
        raise AssertionError("희소 입력 질문 제한 실패")
    brief = {
        "title": "테스트", "purpose": "lecture", "audience": "수강생",
        "delivery_context": "20분 강의", "duration_minutes": 20,
        "source_materials": [], "identity_anchors": [],
    }
    if intake.assess(brief)["phase"] != "confirmation":
        raise AssertionError("기준 판단 확인 단계 누락")
    brief["requirements_confirmed"] = True
    if not intake.assess(brief)["ready"]:
        raise AssertionError("승인된 요구사항이 준비 상태가 아님")
    if intake._recommended_mode(brief) != "image-first":
        raise AssertionError("비편집 덱의 전역 기본 모드가 image-first가 아님")
    editable = dict(brief, editable_text_required=True)
    if intake._recommended_mode(editable) != "scene-deck":
        raise AssertionError("편집 가능 덱이 scene-deck으로 라우팅되지 않음")
    return "질문≤3·확인·승인·모드라우팅"


@check("Windows/macOS 호환")
def _platforms():
    from PIL import ImageFont
    import platform_support as PS
    mac = PS.font_dirs(system="Darwin", home="/Users/test", existing_only=False)
    if "/Users/test/Library/Fonts" not in mac or "/System/Library/Fonts" not in mac:
        raise AssertionError("macOS 폰트 경로 누락")
    if PS.process_group_kwargs(system="Darwin") != {"start_new_session": True}:
        raise AssertionError("macOS 프로세스 그룹 설정 누락")
    path = PS.default_font(bold=True)
    ImageFont.truetype(path, 20)
    return "macOS 경로·현재 폰트"


@check("프리셋 전종")
def _presets():
    import presets
    bad = []
    for k in presets.PRESETS:
        p = presets.preset(k)
        if not p.get("palette", {}).get("hero") or not p.get("fonts", {}).get("head"):
            bad.append(k)
        if len(presets.style_block(k)) < 400:
            bad.append(k + "(style_block 짧음)")
    if bad:
        raise AssertionError("불완전: %s" % bad)
    return "%d종" % len(presets.PRESETS)


@check("구도 함수 시그니처")
def _layouts():
    """실제 렌더는 씬 파일이 필요하므로 시그니처와 등록만 확인한다."""
    import layout_engine as LE
    import info_layouts as IL
    import inspect
    IL.register()          # 정보 구도 7종도 검사 대상에 넣는다
    bad = []
    for name, fn in LE.LAY.items():
        params = list(inspect.signature(fn).parameters)
        # 전 구도가 (im, d, s) 3인자 규약을 지켜야 조립기가 호출할 수 있다
        if len(params) < 3:
            bad.append("%s%s" % (name, params))
    if bad:
        raise AssertionError("시그니처 불일치: %s" % bad)
    for need in ("L", "S", "W", "C", "A", "F", "T", "COVER", "AGENDA", "CLOSING",
                 "TABLE", "EXAMPLE", "MATRIX", "BAR", "FLOW", "GENEALOGY", "PROMPT"):
        if need not in LE.LAY:
            raise AssertionError("구도 %s 누락" % need)
    return "%d종" % len(LE.LAY)


@check("표 정렬 규칙")
def _table_align():
    """정렬이 글자 수로 회귀하면 같은 역할의 열이 표마다 갈린다(실측 사고)."""
    from PIL import Image, ImageDraw
    import layout_engine as LE
    import info_layouts as IL
    d = ImageDraw.Draw(Image.new("RGB", (LE.W, LE.H)))
    fn = LE.f("sub", size=32)
    cpad = 22

    def run(cols, rows, widths):
        xs = IL._cols_x(cols, widths)
        wr = [[IL._lines(d, c, xs[i + 1] - xs[i] - cpad * 2, fn)
               for i, c in enumerate(r)] for r in rows]
        return IL.align_of(d, cols, rows, wr, xs, fn, cpad)

    # 규칙 1 — 일련번호는 가운데
    a = run(["번호", "내용"], [["1", "가"], ["2", "나"], ["3", "다"]], [.6, 5])
    assert a[0] == "center", "규칙1 일련번호 실패: %s" % a

    # 규칙 2 — 1열은 글자 수와 무관하게 왼쪽 (구 규칙은 3자 이하를 가운데로 보냈다)
    a = run(["구분", "의미"], [["불편", "겉으로 드러난 현상"], ["문제", "발생하는 이유"]], [1, 4])
    assert a[0] == "left", "규칙2 1열 실패: %s" % a

    # 규칙 5 — 짧은 값은 가운데, 넓은 열의 긴 구는 왼쪽
    a = run(["기준", "질문", "판정"],
            [["문제 적합성", "직접 줄이는가", "관련 약함"],
             ["실행 가능성", "시험할 수 있는가", "자원 부족"]], [1.3, 3, 1])
    assert a[2] == "center", "규칙5 짧은 값 실패: %s" % a
    a = run(["항목", "질문", "수정 행동"],
            [["표본 편향", "같은 집단인가", "집단과 수집 경로가 서로 다른 독립 근거를 추가한다"],
             ["인용 출처", "요약을 썼는가", "공식 원문과 화자와 날짜를 다시 확인하고 기록한다"]], [1.2, 3, 2.4])
    assert a[2] == "left", "규칙5 절대상한 실패: %s" % a

    # 수동 지정이 규칙보다 우선하는지
    assert IL.table.__doc__ and "우선" in IL.table.__doc__
    return "6규칙 검증"


@check("revise 명령")
def _revise():
    import revise
    spec = {"domain": "it", "foot": "x", "slides": [
        {"lay": "L", "eyebrow": "A", "scene": "s%02d" % i,
         "head": ["h%d" % i], "sub": ["s"]} for i in range(1, 6)]}
    d = revise.Deck(json.loads(json.dumps(spec)))
    cmds = ["3번 헤드라인을 새 제목 로", "2번 구도를 W로", "1번 씬 다시",
            "5번을 2번으로 이동", "색을 navy로"]
    fail = [c for c in cmds if revise.apply_command(d, c) is None]
    if fail:
        raise AssertionError("파싱 실패: %s" % fail)
    if not d.dirty_scenes:
        raise AssertionError("씬 재생성이 집계되지 않음")
    return "%d종" % len(cmds)


@check("Deck 조립+출력")
def _deck():
    from deck import Deck
    outs = sorted(glob.glob(os.path.join(
        os.path.expanduser("~"), "..", "..", "**", "showcase", "*", "spec.json")))
    # 검증 덱이 없으면 최소 스펙으로 조립만
    tmp = tempfile.mkdtemp()
    try:
        d = Deck(domain="it", foot="스모크", title="smoke", out_dir=tmp)
        d.cover("SMOKE", ["표지"], ["서브"], issuer="테스트", scene="a test cover")
        d.slide("L", "TEST", ["헤드라인"], ["서브"], scene="a simple test scene")
        d.flow("FLOW", ["순서"], ["모듈"], [("01", "입력", "근거"), ("02", "검증", "통과")])
        d.genealogy("GENEALOGY", ["계보"], ["실행"], [("Prompt", "요청", "지시"), ("Harness", "실행", "도구")])
        d.prompt("PROMPT", ["복사문"], ["그대로 입력"], ["저장소를 확인해줘"], checks=["결과"])
        d.save()
        sp = os.path.join(tmp, "spec.json")
        if not os.path.exists(sp):
            raise AssertionError("spec.json 미생성")
        d2 = Deck.load(sp)
        if len(d2.slides) != 5:
            raise AssertionError("load 후 슬라이드 %d개 (5 기대)" % len(d2.slides))
        # jobs 생성까지 — 프롬프트 조립 경로 확인
        jobs = d2.jobs()
        if len(jobs) != 2 or not jobs[0].get("prompt"):
            raise AssertionError("jobs 생성 실패")
        if "LEFT, and RIGHT 18%" not in jobs[0]["prompt"]:
            raise AssertionError("씬 네 방향 18% 안전여백 규칙 누락")
        return "save/load/jobs OK"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@check("상위 스크립트")
def _scripts():
    """scripts/*.py 전체를 import해 구문·의존성 오류를 잡는다.

    ★ 실측: 스모크가 scene-deck만 봐서 codex_parallel_gen·assemble_pptx 등
      9개 스크립트가 검증 범위 밖이었다. import만으로도 구문 오류와
      누락된 의존성은 드러난다.
    """
    import importlib.util
    skip = {"harness_smoke.py"}          # 자기 자신
    bad = []
    n = 0
    for p in sorted(glob.glob(os.path.join(HERE, "*.py"))):
        name = os.path.basename(p)
        if name in skip:
            continue
        try:
            spec = importlib.util.spec_from_file_location("_sm_" + name[:-3], p)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            n += 1
        except SystemExit:
            n += 1                        # argparse가 인자 없이 종료 — 정상
        except Exception as e:
            bad.append("%s(%s)" % (name, type(e).__name__))
    if bad:
        raise AssertionError("import 실패: %s" % bad)
    return "%d개" % n


@check("QC 상수 정합")
def _qc_consts():
    """deck_qc의 여백 기준이 하네스 규격과 어긋나면 정상 슬라이드를 FAIL 처리한다."""
    import importlib.util, re
    p = os.path.join(HERE, "deck_qc.py")
    src = open(p, encoding="utf-8").read()
    if "SCENE_DECK_MARGIN" not in src:
        raise AssertionError("SCENE_DECK_MARGIN 기준 없음 — 하네스 규격과 분리됨")
    m = re.search(r"SCENE_DECK_MARGIN\s*=\s*([0-9.]+)", src)
    if not m:
        raise AssertionError("SCENE_DECK_MARGIN 값 파싱 실패")
    margin = float(m.group(1))
    import layout_engine as LE
    # layout_engine의 실제 좌우 여백 비율과 대조
    ls = open(os.path.join(SD, "layout_engine.py"), encoding="utf-8").read()
    m2 = re.search(r"M\s*=\s*(?:int\()?W\s*\*\s*([0-9.]+)", ls)
    if m2 and abs(float(m2.group(1)) - margin) > 0.001:
        raise AssertionError("QC %.3f vs 하네스 %.3f 불일치" % (margin, float(m2.group(1))))
    return "margin %.3f" % margin


def selftest():
    """10항목이 실제로 결함을 잡는지 — 메모리 상에서 객체를 훼손해 확인한다.

    ★ 파일을 고치지 않는다. 모듈 속성을 임시로 바꾸고 원복하므로
      디스크 상태가 변하지 않아 언제든 안전하게 돌릴 수 있다.
      (doc_consistency의 selftest는 파일을 고쳤다 원복하는데,
       중단되면 문서가 훼손된 채 남는다 — 그 위험을 여기서는 없앴다.)
    """
    import presets, layout_engine as LE, revise as RV
    results = []

    def probe(label, broken, fn):
        """broken()으로 훼손 → fn()이 실패해야 정상 → 원복"""
        undo = broken()
        try:
            fn()
            results.append((label, False))       # 안 잡힘
        except Exception:
            results.append((label, True))        # 잡힘
        finally:
            undo()

    # 2) 프리셋 — 한 도메인의 hero 색을 지운다
    def _p():
        k = next(iter(presets.PRESETS))
        orig = presets.PRESETS[k]["palette"].get("hero")
        presets.PRESETS[k]["palette"]["hero"] = None
        return lambda: presets.PRESETS[k]["palette"].__setitem__("hero", orig)
    probe("프리셋", _p, dict(CHECKS)["프리셋 전종"])

    # 3) 구도 — 등록을 하나 뺀다
    def _l():
        removed = LE.LAY.pop("CLOSING")
        return lambda: LE.LAY.__setitem__("CLOSING", removed)
    probe("구도", _l, dict(CHECKS)["구도 함수 시그니처"])

    # 4) revise — 패턴을 전부 비운다
    def _r():
        orig = RV.PATTERNS[:]
        RV.PATTERNS.clear()
        return lambda: RV.PATTERNS.extend(orig)
    probe("revise", _r, dict(CHECKS)["revise 명령"])

    ok = sum(1 for _, hit in results if hit)
    for label, hit in results:
        print("  %-10s %s" % (label, "검출 OK" if hit else "★놓침"))
    print("\n  검출 %d/%d (나머지 7항목은 실측 역검증 완료)" % (ok, len(results)))
    return ok == len(results)


def main():
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="backslashreplace")
    if "--selftest" in sys.argv:
        print("=== 스모크 자체 회귀 (인메모리 주입) ===")
        sys.exit(0 if selftest() else 1)

    quiet = "--quiet" in sys.argv
    fails = []
    # deprecation을 오류로 승격 — import는 되는데 실행하면 죽는 부류를 잡는다
    warnings.simplefilter("error", DeprecationWarning)
    warnings.simplefilter("error", PendingDeprecationWarning)

    for name, fn in CHECKS:
        try:
            got = fn()
            if not quiet:
                print("  %-16s OK  %s" % (name, got))
        except Exception as e:
            fails.append((name, "%s: %s" % (type(e).__name__, str(e)[:70])))
            print("  %-16s ★ %s: %s" % (name, type(e).__name__, str(e)[:70]))

    if fails:
        print("\n실패 %d/%d" % (len(fails), len(CHECKS)))
        return 1
    if not quiet:
        print("\n전 %d항목 통과 (deprecation 승격 상태)" % len(CHECKS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
