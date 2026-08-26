# -*- coding: utf-8 -*-
"""문서-코드 정합 검사 (2026-08-01)

## 왜 필요한가
한 세션에서 문서 모순을 **6건** 수작업으로 찾았다. 전부 같은 원인이다 —
같은 사실을 여러 공개 문서에 적어두고 코드를 고칠 때 일부만 갱신했다.

발견된 모순:
1. README §2·§4가 격리된 `scene_prompts.py`를 쓰라고 안내
2. README §3 "구도 4종" vs §9 "구도 7종" vs 실제 10종
3. README §4 그리드 규격이 구버전 수치(112px)
4. README §1 표가 초기 표기 `(L/W/S/C)`
5. CLAUDE.md 헤드라인 112px + PPTX 누락
6. CLAUDE.md "구도 10종"이라 써놓고 나열은 4종

**코드에서 실제 값을 읽어 문서와 대조**하면 자동으로 잡힌다.

## 사용
    python scripts/doc_consistency.py

## pre-commit 훅
    printf '#!/bin/sh\\npython scripts/doc_consistency.py || exit 1\\n' \\
      > .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
FLAT_HARNESS = os.path.exists(os.path.join(HERE, "layout_engine.py"))
SKILL_DIR = os.path.dirname(HERE)
SD = HERE if FLAT_HARNESS else os.path.join(HERE, "scene-deck")
sys.path.insert(0, SD)

DOCS = {
    "README.md": os.path.join(SD, "README.md"),
}
if not FLAT_HARNESS:
    DOCS["SKILL.md"] = os.path.join(SKILL_DIR, "SKILL.md")

# 문서에 남아 있으면 안 되는 구버전 패턴
STALE = [
    (r"구도 [1-9]종",        "구도 개수"),
    (r"\(L/W/S/C\)",         "구도 나열(구버전 4종)"),
    # 헤드라인 크기는 STALE로 잡지 않는다 — 실측값과 대조하는 규칙(4)이 담당.
    # 정규식으로 잡으면 정상값 115px까지 오탐한다(실측).
    (r"scene_prompts",       "격리된 모듈"),
    (r"jobs_v3",             "구버전 산출물명"),
    (r"15~25분",             "정정된 성능 수치"),
    (r"(?<!\d)4배(?!\w)",    "정정된 성능 배수"),
]


def code_facts():
    """코드에서 실제 값을 읽는다"""
    import layout_engine as LE
    import presets, fonts, photos, deck, revise
    return {
        "구도_개수": len(LE.LAY),
        "구도_코드": sorted(LE.LAY),
        "도메인_개수": len(presets.PRESETS),
        "헤드라인_px": fonts.TYPE_SCALE["headline"],
        "표지_px": fonts.TYPE_SCALE["display"],
        "사진_모드": len(photos.ARRANGE),
        "revise_패턴": len(revise.PATTERNS),
        "Deck_메서드": [m for m in ("cover", "agenda", "closing", "slide",
                                   "photos", "generate", "build", "pdf",
                                   "pptx", "revise", "load")
                       if hasattr(deck.Deck, m)],
    }


def check():
    f = code_facts()
    problems = []

    for name, path in DOCS.items():
        if not os.path.exists(path):
            # 저장소 사본·메모리는 환경에 따라 없을 수 있다
            if name.startswith("repo/") or name == "memory":
                continue
            problems.append((name, "-", "파일 없음"))
            continue

        # ★ 인수인계 메모리는 "이런 실수를 했다"는 이력을 담는다.
        #   'scene_prompts를 쓰라고 안내했다', '4배라고 보고했다가 정정' 같은
        #   서술을 현재 주장으로 오인하면 전부 오탐이다(실측 11건).
        #   현재 사용법을 적는 부분(스모크 항목 수)만 검사 8에서 본다.
        if name == "memory":
            continue
        text = open(path, encoding="utf-8").read()

        # PPT 섹션만 보는 문서
        if name == "CLAUDE.md":
            i = text.find("Auto-Trigger: PPT")
            text = text[i:i + 3000] if i > 0 else text

        # 1) 구버전 패턴
        for pat, why in STALE:
            for m in re.finditer(pat, text):
                ln = text[:m.start()].count("\n") + 1
                problems.append((name, "%d행" % ln, "%s: '%s'" % (why, m.group())))

        # 2) 구도 개수 주장 vs 실제
        for m in re.finditer(r"구도\s*(\d+)\s*종", text):
            if int(m.group(1)) != f["구도_개수"]:
                problems.append((name, "%d행" % (text[:m.start()].count("\n") + 1),
                                 "구도 %s종 주장 ≠ 실제 %d종" % (m.group(1), f["구도_개수"])))

        # 3) 구도 개수를 언급했다면 전 코드가 나열돼야 함
        if re.search(r"구도\s*\d+\s*종", text):
            # 단일 문자 코드(L/S/W/C/A/F/T)는 일반 단어에 묻히므로
            # 백틱·괄호·굵게 표시 안에 있을 때만 '나열됨'으로 본다.
            def listed(c):
                # 단일 문자 코드(L/S/W/C/A/F/T)는 일반 단어에 묻히므로
                # 백틱·괄호·굵게 표시 안에 있을 때만 인정한다.
                if len(c) == 1:
                    return re.search(r"[`*(\s]%s[`*)\s(,·/]" % c, text) is not None
                # ★ 다중 문자도 경계를 봐야 한다. `c in text`면
                #   AGENDAX가 AGENDA를 포함해 통과한다(실측: selftest가 놓쳤다).
                return re.search(r"(?<![A-Za-z])%s(?![A-Za-z])" % c, text) is not None
            missing = [c for c in f["구도_코드"] if not listed(c)]
            if missing:
                problems.append((name, "-", "구도 나열 누락: %s" % ", ".join(missing)))

        # 4) 헤드라인 px 주장 vs 실제
        for m in re.finditer(r"헤드라인\s*\*{0,2}(\d+)px", text):
            if int(m.group(1)) != f["헤드라인_px"]:
                problems.append((name, "%d행" % (text[:m.start()].count("\n") + 1),
                                 "헤드라인 %spx 주장 ≠ 실제 %dpx" % (m.group(1), f["헤드라인_px"])))

        # 5) 도메인 개수
        # "도메인 9종" 뿐 아니라 프리셋 절의 "9종: `it` `food` ..." 형태도 대조한다.
        # 실측: README는 후자만 쓰는데 정규식이 전자만 봐서 검사에 안 걸렸다.
        dom_pats = [r"도메인\s*(?:프리셋\s*)?(\d+)\s*종",
                    r"^(\d+)\s*종:\s*`"]
        for dp in dom_pats:
            for m in re.finditer(dp, text, re.M):
                if int(m.group(1)) != f["도메인_개수"]:
                    problems.append((name, "%d행" % (text[:m.start()].count("\n") + 1),
                                     "도메인 %s종 주장 ≠ 실제 %d종" % (m.group(1), f["도메인_개수"])))

    # 6) README의 자연어 명령 표 — 적어둔 명령이 실제로 파싱되는지
    #    실측: 파서를 고친 뒤 문서만 남고 코드가 어긋나면 사용자가 오답을 배운다.
    rd = DOCS.get("README.md")
    if rd and os.path.exists(rd):
        import json as _json
        text = open(rd, encoding="utf-8").read()
        i = text.find("### 지원하는 자연어 명령")
        if i >= 0:
            import revise as _rv
            spec = {"domain": "it", "foot": "x", "slides": [
                {"lay": "L", "eyebrow": "A", "scene": "s%02d" % k,
                 "head": ["h%d" % k], "sub": ["s"]} for k in range(1, 6)]}
            for row in text[i:i + 1200].split("\n"):
                if not row.startswith("| `"):
                    continue
                cell = row.split("|")[1]
                for cmd in re.findall(r"`([^`]+)`", cell):
                    d = _rv.Deck(_json.loads(_json.dumps(spec)))
                    if _rv.apply_command(d, cmd) is None:
                        problems.append(("README.md", "명령표",
                                         "문서에 적힌 명령이 파싱 안 됨: '%s'" % cmd))

    # 7) 문서의 파이썬 예제 — Deck 메서드와 키워드 인자가 실제로 존재하는지
    #    실측: SKILL.md 예제를 그대로 실행해 검증한 적은 있으나 자동 검사는 없었다.
    #    메서드 이름이 바뀌면 문서 예제가 조용히 죽는다.
    import ast as _ast
    import inspect as _insp
    import deck as _deck
    import revise as _rev
    for name in ("SKILL.md", "README.md", "repo/README.md"):
        path = DOCS.get(name)
        if not path or not os.path.exists(path):
            continue
        body = open(path, encoding="utf-8").read()
        for block in re.findall(r"```python\n(.*?)\n```", body, re.S):
            import textwrap as _tw
            try:
                tree = _ast.parse(_tw.dedent(block))
            except SyntaxError:
                # 설명용 부분 코드(들여쓴 조각, 생략 기호 포함)는 검사 대상이 아니다.
                continue
            for node in _ast.walk(tree):
                if not isinstance(node, _ast.Call):
                    continue
                fn = node.func
                if not isinstance(fn, _ast.Attribute):
                    continue
                # ★ Deck 호출만 골라낸다. Call이면 무조건 Deck으로 보면
                #   np.array(...).astype() 같은 것까지 잡는다(실측 오탐 2건).
                base = fn.value
                if isinstance(base, _ast.Name):
                    is_deck = base.id in ("d", "Deck")
                elif isinstance(base, _ast.Call):
                    f2 = base.func
                    is_deck = (isinstance(f2, _ast.Name) and f2.id == "Deck") or \
                              (isinstance(f2, _ast.Attribute)
                               and isinstance(f2.value, _ast.Name) and f2.value.id == "Deck")
                else:
                    is_deck = False
                if not is_deck:
                    continue
                # 같은 블록이 revise.Deck을 import했으면 그쪽 클래스로 본다.
                # deck.Deck과 revise.Deck은 이름만 같고 API가 다르다(실측 오탐 3건).
                cls = _rev.Deck if "from revise import" in block else _deck.Deck
                meth = getattr(cls, fn.attr, None)
                if meth is None:
                    problems.append((name, "예제", "%s.%s 없음"
                                     % (cls.__module__.split(".")[-1], fn.attr)))
                    continue
                try:
                    params = set(_insp.signature(meth).parameters)
                except (TypeError, ValueError):
                    continue
                for kw in node.keywords:
                    if kw.arg and kw.arg not in params:
                        problems.append((name, "예제",
                                         "Deck.%s(%s=) 인자 없음" % (fn.attr, kw.arg)))

    # 8) 스모크 항목 수 — 문서가 "N항목"이라 주장하면 실제 CHECKS 수와 대조
    try:
        import importlib.util as _ilu
        sp = _ilu.spec_from_file_location(
            "_hs", os.path.join(HERE, "harness_smoke.py"))
        hs = _ilu.module_from_spec(sp)
        sp.loader.exec_module(hs)
        n_checks = len(hs.CHECKS)
        f["스모크_항목"] = n_checks
        for name, path in DOCS.items():
            if not path or not os.path.exists(path):
                continue
            body = open(path, encoding="utf-8").read()
            for m in re.finditer(r"(?:스모크|smoke)[^\n]{0,40}?(\d+)\s*항목", body):
                if int(m.group(1)) != n_checks:
                    problems.append((name, "%d행" % (body[:m.start()].count("\n") + 1),
                                     "스모크 %s항목 주장 ≠ 실제 %d항목"
                                     % (m.group(1), n_checks)))
            for m in re.finditer(r"(?:전|총)?\s*(\d+)\s*항목을?\s*(?:수초|확인)", body):
                if int(m.group(1)) != n_checks:
                    problems.append((name, "%d행" % (body[:m.start()].count("\n") + 1),
                                     "%s항목 주장 ≠ 실제 %d항목" % (m.group(1), n_checks)))
    except Exception:
        pass

    return f, problems


def selftest():
    """7개 검사가 실제로 문제를 잡는지 — 문서에 결함을 주입해 확인한다.

    ★ 검사기가 커지면 '통과'가 검사를 안 해서인지 문제가 없어서인지 알 수 없다.
      각 검사마다 걸려야 할 문자열을 넣고 잡히는지 본다.
    """
    import shutil

    # ★ 백업을 문서 옆에 예측 가능한 이름으로 둔다.
    #   tempfile.mktemp()는 임시 폴더에 흩어져 중단 시 복구 지점을 못 찾는다.
    #   시작할 때 이전 실행이 남긴 백업이 있으면 먼저 복구한다.
    SUF = ".selftest-bak"

    def _recover():
        n = 0
        for _, p in DOCS.items():
            b = p + SUF
            if p and os.path.exists(b):
                shutil.copy(b, p)
                os.remove(b)
                n += 1
        if n:
            print("  [복구] 이전 실행이 남긴 백업 %d개에서 원복" % n)

    _recover()

    CASES = [
        ("1 구버전패턴", "README.md", "구도 10종", "scene_prompts 를 쓴다"),
        ("2 구도개수",   "README.md", "## 8. 구도 10종", "## 8. 구도 5종"),
        ("4 헤드라인px", "README.md", "헤드라인", "헤드라인 999px"),
        ("5 도메인개수", "README.md", "9종: `it`", "3종: `it`"),
        ("6 명령표",     "README.md", "`1번 씬 다시`", "`1번 씬 갈아엎어`"),
        ("7 예제API",    "SKILL.md",  "d.generate(APPROVAL_DIGEST, APPROVAL_STORE)", "d.nosuchmethod()"),
        # 검사 3 — 구도 코드 하나를 전부 지우면 잡혀야 한다.
        #   ★ 한 곳만 바꾸면 다른 등장 지점이 매칭돼 통과한다(실측).
        #      CLOSING은 README에 한 번만 나오므로 이걸 쓴다.
        # 구도 코드는 문서에 여러 번 나오므로 전부 바꿔야 '누락'이 된다.
        ("3 구도나열",   "README.md", "CLOSING", "CLOSINGX", True),
        # 검사 8 — 스모크 항목 수 주장이 실제와 다르면 잡혀야 한다
        ("8 스모크항목", "SKILL.md",  "7항목 수초 검증", "9항목 수초 검증"),
    ]
    ok = 0
    for case in CASES:
        label, doc, find, repl = case[:4]
        replace_all = len(case) > 4 and case[4]
        path = DOCS.get(doc)
        if not path or not os.path.exists(path):
            print("  %-14s SKIP (%s 없음)" % (label, doc))
            continue
        bak = path + SUF
        shutil.copy(path, bak)
        try:
            body = open(path, encoding="utf-8").read()
            if find not in body:
                print("  %-14s SKIP (주입 지점 없음)" % label)
                continue
            open(path, "w", encoding="utf-8").write(
                body.replace(find, repl) if replace_all
                else body.replace(find, repl, 1))
            _, probs = check()
            hit = len(probs) > 0
            print("  %-14s %s" % (label, "검출 OK" if hit else "★놓침"))
            ok += 1 if hit else 0
        finally:
            shutil.copy(bak, path)
            os.remove(bak)

    _, probs = check()
    clean = not probs
    print("\n  원복 후 모순: %d건 %s" % (len(probs), "OK" if clean else "★"))
    print("  검출 %d/%d" % (ok, len(CASES)))
    return ok == len(CASES) and clean


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        print("=== 검사기 자체 회귀 (문제 주입) ===")
        sys.exit(0 if selftest() else 1)

    facts, probs = check()
    print("=== 코드 실측 ===")
    for k, v in facts.items():
        print("  %-12s %s" % (k, v if not isinstance(v, list) else " ".join(map(str, v))))
    print("\n=== 문서 정합 ===")
    if probs:
        for doc, loc, msg in probs:
            print("  ★ %-11s %-7s %s" % (doc, loc, msg))
        print("\n  모순 %d건 — 문서를 코드에 맞춰 갱신하라" % len(probs))
        sys.exit(1)
    checked = [n for n, p in DOCS.items() if os.path.exists(p)]
    print("  모순 0건 — %s 전건 정합" % " / ".join(checked))
