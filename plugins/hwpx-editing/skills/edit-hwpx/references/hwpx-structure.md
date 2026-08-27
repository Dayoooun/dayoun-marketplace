# HWPX 구조 레퍼런스 — 그림·표 배치

> 근거: 한컴 공식 OWPML 모델 소스(`github.com/hancom-io/hwpx-owpml-model`, Apache-2.0) +
> 실무 문서 43개 / `<hp:pic>` 276개 전수 실측 (2026-08-27).
> 추측 아님. 각 항목에 확인 방법을 붙였다.

## 1. 파일 구조

HWPX 는 ZIP 이다. 핵심 4개만 알면 된다.

| 경로 | 역할 | 건드릴 때 주의 |
|---|---|---|
| `Contents/section0.xml` | 본문 전체(문단·표·그림) | 실제 편집 대상 |
| `Contents/content.hpf` | 매니페스트(BinData 목록) | **파일 지우면 여기 항목도 지워야 한다** |
| `Contents/header.xml` | paraPr/charPr/borderFill 정의 | ID 참조만 하고 수정하지 않는다 |
| `BinData/*` | 이미지 실물 | 텍스트 치환과 무관 — 따로 갈아야 한다 |
| `mimetype` | 무압축(STORED) 첫 엔트리 | repack 시 순서·압축방식 지키지 않으면 안 열린다 |

```python
with zipfile.ZipFile(out, "w") as zf:
    zf.write(os.path.join(wd, "mimetype"), "mimetype", zipfile.ZIP_STORED)  # ★ 반드시 첫째, 무압축
    for r, _, fs in os.walk(wd):
        for f in fs:
            if f == "mimetype": continue
            zf.write(os.path.join(r, f), os.path.relpath(os.path.join(r, f), wd), zipfile.ZIP_DEFLATED)
```

### 매니페스트 유령 항목 = 그림이 새까맣게 렌더된다

`BinData/imageN.png` 를 지우고 `content.hpf` 의 `<opf:item>` 을 남기면 한글이 **없는 파일을 참조**해
그림 영역을 통째로 검게 그린다. 사진 9장이 전부 검은 사각형으로 나온 사고의 원인이 이거였다.

```python
# ✗ [^/]* 는 href="BinData/..." 의 슬래시에서 끊겨 매칭 실패 → 유령 항목이 남는다
re.sub(r'<opf:item id="%s"[^/]*/>' % iid, '', manifest)
# ✓
re.sub(r'<opf:item id="%s"[^>]*/>' % iid, '', manifest)
```

검증: `ids = re.findall(r'<opf:item id="\w+" href="(BinData/[^"]+)"', manifest)` →
전부 `zipfile.namelist()` 에 있어야 한다.

---

## 2. 그림 배치 — 좌표가 두 개인데 하나만 쓰인다

`<hp:pic>` 안에 좌표계가 둘 있다. **역할이 완전히 다르다.**

| 요소 | OWPML 클래스 | 역할 | 렌더 영향 |
|---|---|---|---|
| `<hp:offset x y>` | `CASCOffset` (**ASC = As-Character**) | 글자처럼 배치일 때의 오프셋. 기본값 (0,0) | `treatAsChar=1` 일 때만 |
| `<hp:pos vertOffset horzOffset>` | `CPos` | 부동 배치의 앵커 기준 좌표 | `treatAsChar=0` 일 때 **유일한 결정자** |

근거 — 공식 소스 `OWPML/Class/Para/poffset.cpp:84`:
```cpp
CASCOffset::CASCOffset() : CExtObject(ID_PARA_ASCOffset), m_uX(0), m_uY(0) {}
```
`PictureType.cpp:89` 에서 `<hp:pic>` 의 자식으로 등록된다:
```cpp
OWPML_PARALIST_ADD_REDIRECT_FUNC(offset, CASCOffset, ID_PARA_ASCOffset)
```

### 실측 검증 (276개 pic)

| treatAsChar | 의미 | pos 값 | 일치율 |
|---|---|---|---|
| `1` | 글자처럼 취급(인라인) | vertOffset=0, horzOffset=0 | 101/104 = **97%** |
| `0` | 부동(자유 배치) | pos 에 실제 좌표 | 105/172 = 61% |

렌더 실험: `<hp:offset y>` 를 -13053 / -20000 / -25000 / -30000 / -35089 / -40000 / 0 / 5000 / -100000
9종으로 바꿔 렌더 → **md5 전부 동일**(픽셀 무변화). QuickLook 캐시 리셋 후에도 동일.
반대로 `hp:pos.vertOffset` 을 1000~2500 스윕하면 매번 렌더가 달라진다.

> **결론: 부동 개체(서명·직인) 위치를 옮기려면 `hp:pos` 를 고쳐라. `hp:offset` 은 아무리 만져도 안 움직인다.**

### `vertRelTo` — 기준점이 무엇인가

`vertRelTo="PARA"` 는 **앵커 문단**을 기준으로 삼는다. 그래서 앵커 문단이 다르면
같은 vertOffset 이라도 전혀 다른 위치에 그려진다. 양식이 다르면 값을 이식하면 안 되는 이유다.

---

## 3. 크기 — curSz / orgSz 는 별개다

| 요소 | 의미 | 수정 |
|---|---|---|
| `<hp:curSz>` | 문서에 표시되는 크기 | **여기만 조정한다** |
| `<hp:orgSz>` | 원본 기준 크기 (예: 485040x159960) | **절대 건드리지 않는다** |

`orgSz` 에 픽셀값(예: 18810)을 넣으면 배율이 **26배**로 튀어 그림이 페이지를 덮는다.

**`curSz` 비율 = 원본 이미지 비율** 이 실무 규칙이다(28건 중 27건 일치).
도너의 `curSz` 를 통째로 복사하면 서명이 눌리거나 늘어난다 — 이미지마다 가로세로비가 다르기 때문.

```python
cw = int(도너_curSz_width)          # 폭은 유지
ch = int(round(cw * img_h / img_w)) # 높이만 새 이미지 비율로 재계산
```

---

## 4. 셀 좌표는 표마다 리셋된다

`<hp:cellAddr colAddr rowAddr>` 은 **표(`<hp:tbl>`)마다 0부터 다시 시작**한다.
문서에 `c1 r0` 이 여러 개 존재하므로 좌표로 셀을 찍으면 첫 번째 표가 걸린다.

교차 도너 빌드에서 "컨설턴트 칸에 업체명이, 수행구분 칸에 사업자번호가" 들어간 사고의 원인.

**해법: 좌표 대신 도너의 기존 값을 지문으로 삼아 치환한다.**
```python
x = x.replace("<hp:t>%s</hp:t>" % esc(old_value), "<hp:t>%s</hp:t>" % esc(new_value), 1)
```

---

## 5. linesegarray — 레이아웃 캐시

`<hp:linesegarray>` 는 한글이 계산해둔 줄 위치 캐시다. 텍스트 길이를 바꾸면 옛 캐시가
글자를 겹쳐 그리므로 **바꾼 셀에서는 제거**해야 한글이 재계산한다.

단 **문서 전체에서 지우지 않는다.** 부동 개체는 앵커 문단의 lineseg 를 기준으로 삼는 경우가 있어
기준을 잃을 수 있다.

```python
def strip_lineseg_in_cell(x, cell_start, cell_end):
    inner = x[cell_start:cell_end]
    return re.sub(r'<hp:linesegarray>.*?</hp:linesegarray>', '', inner, flags=re.S)
```

문서에 따라 linesegarray 가 **애초에 0개**인 경우가 있다(저장기가 캐시를 생략).
"사라졌다"고 판단하기 전에 원본에 있었는지부터 확인하라.

---

## 6. 멀티라인 텍스트 = 문단 여러 개

HWPX 에서 줄바꿈은 `\n` 이 아니라 **별도 `<hp:p>`** 다.

```python
def paras(lines, ppr, cpr):
    out = []
    for ln in lines:
        t = ('<hp:t>%s</hp:t>' % esc(ln)) if ln.strip() else '<hp:t/>'
        out.append('<hp:p id="%d" paraPrIDRef="%s" styleIDRef="0" pageBreak="0" '
                   'columnBreak="0" merged="0"><hp:run charPrIDRef="%s">%s</hp:run></hp:p>'
                   % (random.randint(10**8, 2**31-1), ppr, cpr, t))
    return "".join(out)
```

`paraPrIDRef`/`charPrIDRef` 는 **교체 대상 셀의 기존 문단에서 승계**한다. 하드코딩하면 서식이 깨진다.

---

## 7. 빌드 후 필수 검증

```python
import xml.etree.ElementTree as ET
ET.fromstring(section_xml)              # ① XML 유효성

ids = re.findall(r'<opf:item id="\w+" href="(BinData/[^"]+)"', manifest)
assert all(i in z.namelist() for i in ids)   # ② 매니페스트 유령 항목 0건

t = re.sub(r'<[^>]+>', '', section_xml)
assert not re.findall(r'\{[가-힣 ]+\}', t)   # ③ 미치환 placeholder 0건
```

교차 도너 빌드라면 추가로:
- 도너 업체명·대표자·사업자번호·주소가 텍스트에 남았는지 grep
- `binaryItemIDRef` 에 도너 이미지 ID 잔존 여부
- 렌더 육안 확인 (macOS: QuickLook 으로 GUI 없이 1페이지 렌더 가능)

---

## 10. ★ `treatAsChar` — 표와 그림에 각각 규칙이 있다

**그림이 틀어지거나 표가 잘리거나 사진이 셀을 벗어나면 전부 이 값 문제다.**

### 표

| 표 | treatAsChar | 이유 |
|---|---|---|
| 제목 배너 | `1` | 부동이면 서명 좌표계가 어긋난다 |
| 헤더(컨설턴트·수진기업) | `1` | 대표자 서명이 이 표 위에 얹힌다 |
| 업체정보 | `1` | 헤더와 같은 흐름 |
| **본문 서술(2행1열)** | **`0`** | **길어서 페이지를 넘겨야 한다. `1`이면 잘린다** |
| **증빙자료 표** | **`0`** | **사진이 많아 여러 장을 넘어간다** |

### 그림

| 그림 | treatAsChar | 이유 |
|---|---|---|
| **표 안 사진** | **`1`** | **부동(`0`)이면 셀을 벗어나 표가 깨진다** |
| 서명·직인 | `0` | 앵커 문단 기준 자유 배치가 필요하다 |

### 실측 (2026-08-27)

- 본문 서술 표(2x1): 2회차 10건 **전부 `0`**
- 증빙자료 표: 정상본 6/8이 `0`
- 표 안 사진: 정상본 **9/9 전부 `1`** — 예외 없음
- 사진을 부동으로 두면 셀 밖으로 나가 표가 깨진다(사용자 확인)

### 사진 크기·정렬

- **정렬은 `hp:pic` 이 아니라 담긴 문단의 `paraPr` 이 결정한다.**
  중앙정렬하려면 `header.xml` 에서 `horizontal="CENTER"` 인 paraPr id 를 찾아
  문단의 `paraPrIDRef` 를 그 값으로 바꾼다(실측: paraPr 20 = CENTER).

### 사진 크기 — 셀을 꽉 채우지 않는다

셀 실제 크기(예: 23814x18142)보다 작게 잡아 여백을 남긴다. 꽉 채우면 표가 다음 장으로 밀린다.

| 상한 | 값 | 적용 |
|---|---|---|
| 가로 | **12329** | 세로로 긴 문서(견적서·통장 등) |
| 세로 | **16441** | 대부분의 스캔 문서 |
| 정사각 예외 | **16860** | 원본이 정사각(1600x1600)인 현장 사진 |

```python
if w == h:
    cw = ch = 16860                       # 정사각은 셀을 꽉 채워도 안 넘친다
else:
    scale = min(12329 / w, 16441 / h)     # 둘 중 먼저 걸리는 쪽
    cw, ch = int(w * scale), int(h * scale)   # ★ round 아님. 한글은 내림
```

`round()` 를 쓰면 1 HWPUNIT 어긋나 한글 원본과 값이 달라진다(실측: 14건 중 4건 불일치).

```python
# 표 앵커 정규화
for m in re.finditer(r'<hp:tbl\b[^>]*rowCnt="(\d+)"[^>]*colCnt="(\d+)"[^>]*>', xml):
    rows, cols = int(m.group(1)), int(m.group(2))
    head = "".join(re.findall(r'<hp:t>([^<]{1,14})</hp:t>', xml[m.start():m.start()+2500]))[:16]
    want = "0" if ((rows == 2 and cols == 1) or "증빙자료" in head) else "1"
    # … seg 의 첫 hp:pos 를 want 로 치환

# 표 안 사진은 무조건 글자처럼
new_pic = re.sub(r'(<hp:pos\b[^>]*?)treatAsChar="\d"', r'\1treatAsChar="1"', pic, count=1)
```

**주의**: 표 앵커를 바꾸면 좌표계가 달라지므로 **서명 좌표를 다시 잡아야 한다.**
추측하지 말고 여러 값으로 렌더해 비교한다(§8).

### 검증

`hwpx_verify.py` 가 표·그림 규칙을 각각 FAIL 로 잡는다.


## 9. 폰 스크린샷 증빙은 검은 여백을 잘라낸다

아이폰 스크린샷을 그대로 표 셀에 넣으면 상하 검은 띠가 **최대 47%** 를 먹는다.
표 셀 높이는 고정이라 그만큼 실제 증빙 내용이 작아져 판독이 어려워진다.

실측 (신디필라테스 증빙 9장):

| 파일 | 원본 | 내용 영역 | 낭비 |
|---|---|---|---|
| 사업자등록증 | 739x1600 | 53% | **47%** |
| 전자세금계산서 | 739x1600 | 59% | 41% |
| 통장사본(공급자) | 739x1600 | 87% | 13% |
| 거래명세서 | 739x1600 | 92% | 8% |

```python
def autocrop_dark(im, thresh=90):
    """상하 검은 여백 제거. 좌우는 문서 폭이 꽉 차 있어 건드리지 않는다."""
    w, h = im.size
    px = im.convert("RGB").load()
    def bright(y):
        xs = list(range(0, w, max(1, w // 40)))
        return sum(sum(px[x, y]) / 3 for x in xs) / len(xs)
    limit = int(h * 0.45)          # 본문을 먹지 않도록 상한
    top = 0
    while top < limit and bright(top) < thresh: top += 1
    bot = h - 1
    while bot > h - 1 - limit and bright(bot) < thresh: bot -= 1
    return im if (top == 0 and bot == h - 1) else im.crop((0, top, w, bot + 1))
```

**임계값 90 인 이유**: 순수 검정은 밝기 29 지만 사진앱 UI 바(페이지 인디케이터)가
**50~55** 로 검은 배경 사이에 끼어 있다. 임계 50 으로 두면 UI 바에서 크롭이 멈춰
검은 띠가 그대로 남는다. 문서 본문은 흰 배경이라 230 이상이므로 90 이 안전한 경계다.

**45% 상한이 필요한 이유**: 상한 없이 "가장 밝은 행 기준으로 바깥으로 훑기" 방식을 쓰면
본문까지 잘린다(실측: 사업자등록증 1336px → 180px, 본견적서까지 훼손).

## 8. macOS 에서 한글 native 렌더 (GUI 없음)

한컴 맥 버전은 AppleScript 사전도 CLI 도 없다(윈도우 COM 전용). 대신 한컴이 설치한
**QuickLook 프리뷰 확장**을 API 로 직접 호출하면 창 하나 안 띄우고 한글 native 렌더를 얻는다.

```python
import objc, Quartz
from Foundation import NSURL, NSRunLoop, NSDate
objc.loadBundle("QuickLookThumbnailing", globals(),
    bundle_path="/System/Library/Frameworks/QuickLookThumbnailing.framework")
objc.registerMetaDataForSelector(
    b"QLThumbnailGenerator", b"generateBestRepresentationForRequest:completionHandler:",
    {"arguments": {3: {"callable": {"retval": {"type": b"v"},
        "arguments": {0: {"type": b"^v"}, 1: {"type": b"@"}, 2: {"type": b"@"}}}}}})
req = globals()["QLThumbnailGenerationRequest"].alloc(). \
    initWithFileAtURL_size_scale_representationTypes_(NSURL.fileURLWithPath_(path), (1240.0, 1754.0), 1.0, 15)
```

- `representationTypes=15`(전체 허용) 필수. `qlmanage -t` CLI 는 타임아웃난다.
- 파일은 홈 디렉터리 아래에 둬야 한다(샌드박스). `/tmp` 는 거부될 수 있다.
- **1페이지만** 나온다. 다중 페이지 PDF 는 여전히 윈도우 한글 COM 이 필요하다.
