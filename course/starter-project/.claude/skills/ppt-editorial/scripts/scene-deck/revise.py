# -*- coding: utf-8 -*-
"""수정 인터페이스 — 한 줄 명령으로 덱 수정 (2026-08-01 G004)

## 왜 필요한가
지금까지는 spec 파일을 열어 dict를 손으로 고쳐야 했다.
"3번 헤드라인 바꿔줘" 같은 요청이 파일 편집 → 재실행 → 확인의 3단계였다.

## 핵심 설계: 재생성 필요 여부 자동 판별 (철칙 E)
수정을 두 종류로 나눈다.

| 종류 | 예 | 처리 |
|---|---|---|
| **TEXT** — 코드만 다시 그림 | 헤드라인·서브·eyebrow·푸터·순서·구도·색 | 씬 재사용, 조립만 (수초) |
| **SCENE** — 씬 재생성 필요 | 씬 내용·모티프·라벨·도메인 변경 | 해당 장만 codex 재생성 |

전면 재생성은 절대 하지 않는다(철칙 E).
"""
import os, re, json, copy

# ── 수정 종류
TEXT_ONLY = {"head", "sub", "eyebrow", "lay", "foot", "palette", "family", "order"}
SCENE_REQ = {"scene", "motif", "label", "domain"}


class Deck:
    """덱 스펙 + 수정 API

    d = Deck.load("spec.json")
    d.head(3, "새 헤드라인")          # 3번 슬라이드 헤드라인
    d.lay(2, "W")                     # 2번을 W 구도로
    d.palette("navy")                 # 전체 강조색
    d.move(5, 2)                      # 5번을 2번 자리로
    d.scene(4, "저울 비교")            # 씬 교체 (재생성 대상으로 표시)
    print(d.plan())                   # 무엇이 재생성되는지 미리보기
    d.save()
    """

    def __init__(self, spec, path=None):
        self.spec = spec
        self.path = path
        self.dirty_scenes = set()      # 재생성 필요한 sid
        self.log = []

    # ── 로드/저장
    @classmethod
    def load(cls, path):
        return cls(json.load(open(path, encoding="utf-8")), path)

    def save(self, path=None):
        p = path or self.path
        json.dump(self.spec, open(p, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        return p

    # ── 내부
    def _ensure_ids(self):
        """모든 슬라이드에 고정 ID(_sid) 부여. 최초 1회.
        순서를 바꿔도 '3번'이 계속 같은 슬라이드를 가리키게 하는 앵커."""
        for i, s in enumerate(self.spec["slides"], 1):
            s.setdefault("_sid", i)

    def _slide(self, n):
        """슬라이드 번호 → dict.
        ★ 고정 ID 기준이다. move()로 순서를 바꿔도 'n번'은 계속 같은 슬라이드를 가리킨다.
        (순서 기준으로 하면 move 뒤 명령이 엉뚱한 장에 적용되는 버그가 난다 — 실측 확인)"""
        self._ensure_ids()
        for s in self.spec["slides"]:
            if s.get("_sid") == n:
                return s
        raise IndexError("슬라이드 %d 없음 (1~%d)" % (n, len(self.spec["slides"])))

    def _rec(self, kind, n, what):
        self.log.append((kind, n, what))

    # ══════ TEXT 수정 (재생성 불필요) ══════
    def head(self, n, *lines):
        """헤드라인 교체. d.head(3, "첫 줄", "둘째 줄")"""
        self._slide(n)["head"] = list(lines)
        self._rec("TEXT", n, "헤드라인")
        return self

    def sub(self, n, *lines):
        """서브 텍스트 교체"""
        self._slide(n)["sub"] = list(lines)
        self._rec("TEXT", n, "서브")
        return self

    def eyebrow(self, n, text):
        """상단 영문 라벨 교체"""
        self._slide(n)["eyebrow"] = text
        self._rec("TEXT", n, "eyebrow")
        return self

    def lay(self, n, code):
        """구도 변경. L/S/W/C/A/F/T"""
        code = code.upper()
        if code not in "LSWCAFT" or len(code) != 1:
            raise ValueError("구도는 L/S/W/C/A/F/T 중 하나")
        self._slide(n)["lay"] = code
        self._rec("TEXT", n, "구도→%s" % code)
        return self

    def move(self, frm, to):
        """슬라이드 순서 이동. frm은 고정 ID, to는 목표 위치(1-based)"""
        self._ensure_ids()
        sl = self.spec["slides"]
        idx = next(i for i, s in enumerate(sl) if s.get("_sid") == frm)
        item = sl.pop(idx)
        sl.insert(max(0, to - 1), item)
        self._rec("TEXT", frm, "순서 %d→%d위치" % (frm, to))
        return self

    def palette(self, name_or_rgb):
        """전체 강조색 변경. 프리셋 키('food') 또는 (r,g,b)"""
        self.spec["palette"] = name_or_rgb
        self._rec("TEXT", 0, "팔레트→%s" % (name_or_rgb,))
        return self

    def family(self, name):
        """폰트 패밀리 변경 (pretendard/paperlogy/serif_ridi ...)"""
        self.spec["family"] = name
        self._rec("TEXT", 0, "폰트→%s" % name)
        return self

    def foot(self, text):
        """하단 회사명 변경"""
        self.spec["foot"] = text
        self._rec("TEXT", 0, "푸터")
        return self

    # ══════ SCENE 수정 (해당 장만 재생성) ══════
    def scene(self, n, body=None, ratio=None):
        """씬 수정 → 해당 슬라이드만 재생성 대상.

        body를 주면 내용을 교체하고, 생략하면 기존 프롬프트로 다시 뽑는다
        ("1번 씬 다시" — 프롬프트는 좋은데 결과가 마음에 안 들 때).
        """
        s = self._slide(n)
        if body is not None:
            s["scene_body"] = body
        if ratio:
            s["scene_ratio"] = ratio
        sid = s.get("scene") or "s%02d" % n
        s["scene"] = sid
        self.dirty_scenes.add(sid)
        self._rec("SCENE", n, "씬 교체" if body is not None else "씬 재생성")
        return self

    def label(self, n, *labels):
        """씬 안 라벨 교체 → 재생성 필요"""
        s = self._slide(n)
        s["scene_labels"] = list(labels)
        self.dirty_scenes.add(s.get("scene") or "s%02d" % n)
        self._rec("SCENE", n, "라벨 %d개" % len(labels))
        return self

    def domain(self, name):
        """도메인 변경 → 전 씬 재생성 (팔레트/모티프가 통째로 바뀜)"""
        self.spec["domain"] = name
        for s in self.spec["slides"]:
            self.dirty_scenes.add(s.get("scene"))
        self._rec("SCENE", 0, "도메인→%s (전장 재생성)" % name)
        return self

    # ══════ 계획 미리보기 ══════
    def plan(self):
        """무엇이 재생성되고 무엇이 조립만인지 요약"""
        txt = [x for x in self.log if x[0] == "TEXT"]
        scn = [x for x in self.log if x[0] == "SCENE"]
        out = ["=== 수정 계획 ==="]
        if txt:
            out.append("[조립만, 재생성 없음] %d건" % len(txt))
            for _, n, w in txt:
                out.append("   %s %s" % (("전체" if n == 0 else "%d번" % n), w))
        if scn:
            out.append("[씬 재생성] %d장: %s" % (len(self.dirty_scenes),
                                             ", ".join(sorted(self.dirty_scenes))))
            for _, n, w in scn:
                out.append("   %s %s" % (("전체" if n == 0 else "%d번" % n), w))
        if not self.log:
            out.append("변경 없음")
        est = len(self.dirty_scenes) * 90 + (5 if txt else 0)
        out.append("예상 소요: 약 %d초" % est)
        return "\n".join(out)

    def dirty_jobs(self, style_fn, base_dir="scenes"):
        """재생성이 필요한 씬만 jobs 리스트로 반환"""
        jobs = []
        for i, s in enumerate(self.spec["slides"], 1):
            sid = s.get("scene")
            if sid not in self.dirty_scenes:
                continue
            jobs.append({
                "label": sid,
                "refs": [],
                "out": os.path.join(base_dir, "%s.png" % sid),
                "prompt": style_fn(self.spec.get("domain")) + s.get("scene_body", ""),
            })
        return jobs


# ══════════════════════════════════════════════════════════
# 자연어 명령 파서 — "3번 헤드라인을 ... 로"
# ══════════════════════════════════════════════════════════
PATTERNS = [
    (r"(\d+)\s*번.*?(?:헤드라인|제목|타이틀)\s*(?:을|를)?\s*[\"'「]?(.+?)[\"'」]?\s*(?:로|으로)?$",
     lambda d, m: d.head(int(m.group(1)), *[x.strip() for x in m.group(2).split("/")])),
    (r"(\d+)\s*번.*?(?:서브|부제|설명)\s*(?:을|를)?\s*[\"'「]?(.+?)[\"'」]?\s*(?:로|으로)?$",
     lambda d, m: d.sub(int(m.group(1)), *[x.strip() for x in m.group(2).split("/")])),
    (r"(\d+)\s*번.*?([LSWCAFT])\s*구도",
     lambda d, m: d.lay(int(m.group(1)), m.group(2))),
    # "2번 구도를 W로" — 구도가 코드 앞에 오는 어순. 실측: 이 형태가 더 자연스러운데 안 먹혔다.
    (r"(\d+)\s*번.*?구도\s*(?:을|를)?\s*([LSWCAFT])\s*(?:로|으로)?",
     lambda d, m: d.lay(int(m.group(1)), m.group(2))),
    # "1번 씬 다시" / "3번 씬 재생성" — 씬 재생성은 핵심 기능인데 자연어 경로가 없었다.
    (r"(\d+)\s*번.*?씬\s*(?:을|를)?\s*(?:다시|재생성|새로|바꿔|교체)",
     lambda d, m: d.scene(int(m.group(1)))),
    (r"(\d+)\s*번.*?(\d+)\s*번.*?(?:으?로)?\s*(?:이동|옮)",
     lambda d, m: d.move(int(m.group(1)), int(m.group(2)))),
    (r"(?:색|팔레트|컬러)\s*(?:을|를)?\s*(\S+?)\s*(?:로|으로)",
     lambda d, m: d.palette(m.group(1))),
    (r"(?:폰트|서체)\s*(?:을|를)?\s*(\S+?)\s*(?:로|으로)",
     lambda d, m: d.family(m.group(1))),
]


def apply_command(deck, text):
    """자연어 한 줄을 덱 수정으로 변환. 매칭 실패 시 None 반환"""
    t = text.strip()
    for pat, fn in PATTERNS:
        m = re.search(pat, t)
        if m:
            fn(deck, m)
            return deck.log[-1]
    return None


if __name__ == "__main__":
    demo = {"domain": "it", "foot": "샘플",
            "slides": [{"lay": "L", "eyebrow": "A", "scene": "s1",
                        "head": ["원래 제목"], "sub": ["원래 서브"]} for _ in range(5)]}
    d = Deck(demo)
    for cmd in ["3번 헤드라인을 새로운 제목/두번째 줄 로",
                "2번을 W 구도로",
                "색을 navy로",
                "5번을 2번으로 이동"]:
        r = apply_command(d, cmd)
        print("  %-32s → %s" % (cmd, r))
    print()
    print(d.plan())
