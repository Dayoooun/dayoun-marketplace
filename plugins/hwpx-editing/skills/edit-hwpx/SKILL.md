---
name: edit-hwpx
description: HWPX(한글) 문서를 XML 수준에서 편집합니다. 부동 개체(서명·직인) 배치, 이미지 교체, 표 셀 수정, 다른 문서를 도너로 삼은 교차 빌드, 빌드 후 무결성 검증을 다룹니다. 'hwpx', '한글 문서', '서명 위치', '직인', '그림이 검게 나옴', '표 셀 편집', '도너' 키워드에 사용합니다.
---

# HWPX XML 편집

HWPX 는 ZIP + XML 이라 파이썬 표준 라이브러리만으로 편집할 수 있습니다. 다만 한글 고유의
좌표계·캐시·매니페스트 규칙을 모르면 **열리기는 하는데 화면이 깨진** 문서가 나옵니다.

이 스킬은 한컴 공식 OWPML 모델 소스(`github.com/hancom-io/hwpx-owpml-model`, Apache-2.0)와
실무 문서 43개 / `<hp:pic>` 276개 전수 실측으로 확인한 규칙만 담았습니다.

상세는 **`references/hwpx-structure.md`** 를 읽으세요. 아래는 가장 자주 사고가 나는 4가지입니다.

## 0. 그림이 틀어지거나 표가 잘리면 — **`treatAsChar`** 를 보세요

표와 그림에 각각 규칙이 있습니다. 하나로 통일하면 안 됩니다.

**표**

| 표 | 값 |
|---|---|
| 제목·헤더·업체정보 | `1` (글자처럼) — 부동이면 서명이 엉뚱한 칸으로 |
| **본문 서술(2행1열)·증빙자료** | **`0` (부동)** — 길어서 페이지를 넘겨야 함 |

**그림**

| 그림 | 값 |
|---|---|
| **표 안 사진** | **`1`** — 부동이면 셀을 벗어나 표가 깨집니다 |
| 서명·직인 | `0` — 앵커 문단 기준 자유 배치 |

실측: 표 안 사진은 정상본 9/9 전부 `1`.

부동 서명·직인은 **앵커 문단이 제목 문단(idx 0)** 이어야 합니다.
`treatAsChar=0` 이고 표 밖에 있어도 앵커가 표 안 문단이면 그 셀을 밀어내 표가 늘어납니다(§11).

 상세는 `references/hwpx-structure.md` §10.

사진 정렬은 `hp:pic` 이 아니라 **담긴 문단의 `paraPr`** 이 결정합니다.
표 앵커를 바꾸면 **서명 좌표를 다시 잡아야 합니다.**

## 1. 그림 위치는 `hp:pos` 가 결정합니다

`<hp:pic>` 안에 좌표계가 둘 있는데 역할이 다릅니다.

| 요소 | OWPML 클래스 | 언제 쓰이나 |
|---|---|---|
| `<hp:offset x y>` | `CASCOffset` (**ASC = As-Character**) | `treatAsChar="1"` (글자처럼 배치)일 때만 |
| `<hp:pos vertOffset horzOffset>` | `CPos` | `treatAsChar="0"` (부동)일 때 **유일한 결정자** |

부동 개체에서 `hp:offset` 을 아무리 고쳐도 화면은 안 움직입니다.
(검증: offset y 를 9종으로 바꿔 렌더 → md5 전부 동일)

`vertRelTo="PARA"` 는 앵커 문단이 기준입니다. **양식이 다르면 좌표를 이식하지 마세요.**
앵커 문단이 다르면 같은 값이 다른 위치를 가리킵니다.

## 2. `orgSz` 는 건드리지 않습니다

- `<hp:curSz>` = 표시 크기 → 여기만 조정
- `<hp:orgSz>` = 원본 기준 크기(예: `485040x159960`) → **수정 금지**

`orgSz` 에 픽셀값을 넣으면 배율이 26배로 튀어 그림이 페이지를 덮습니다.

이미지를 교체할 때는 **폭은 유지하고 높이만 새 이미지 비율로 재계산**합니다.

```python
cw = 기존_curSz_width
ch = round(cw * new_img_h / new_img_w)
```

## 3. 셀 좌표는 표마다 리셋됩니다

`<hp:cellAddr colAddr rowAddr>` 은 `<hp:tbl>` 마다 0부터 다시 시작합니다.
문서에 `c1 r0` 이 여러 개라 좌표로 찍으면 첫 번째 표가 걸립니다.

**좌표 대신 기존 값을 지문으로 삼아 치환하세요.**

```python
x = x.replace("<hp:t>%s</hp:t>" % esc(old), "<hp:t>%s</hp:t>" % esc(new), 1)
```

## 4. BinData 는 텍스트 치환과 무관합니다

다른 문서를 도너로 삼아 빌드할 때 **텍스트만 바꾸면 사진·서명이 도너 것으로 남습니다.**
이미지를 지웠다면 `Contents/content.hpf` 의 `<opf:item>` 도 반드시 함께 지웁니다.

매니페스트에 파일 없는 항목이 남으면 한글이 **그림 영역을 통째로 검게** 그립니다.

```python
# ✗ [^/]* 는 href="BinData/..." 의 슬래시에서 끊깁니다
re.sub(r'<opf:item id="%s"[^/]*/>' % iid, '', manifest)
# ✓
re.sub(r'<opf:item id="%s"[^>]*/>' % iid, '', manifest)
```

## 빌드 후 검증

```bash
python3 scripts/hwpx_verify.py <파일.hwpx> [--donor <도너.hwpx>]
```

`--donor` 를 주면 도너 업체 정보·이미지가 잔존하는지까지 검사합니다.

검사 항목: XML 유효성 / 매니페스트 유령 항목 / 미치환 placeholder / mimetype 압축방식 /
부동 개체 pos 누락 / orgSz 이상값 / curSz 비율 불일치 / 도너 잔존.

## PDF 변환

**rhwp CLI** (Rust, MIT, ★3.7k) 로 한글 없이 변환합니다. macOS aarch64 네이티브 바이너리 제공.

```bash
rhwp export-pdf input.hwpx -o output.pdf --profile print
```

- **CLI 를 쓰세요.** `rhwp-python` 바인딩은 같은 코어지만 `<hp:checkBtn>` 을 안 그립니다
- 다운로드 후 `xattr -dr com.apple.quarantine` 필수 — 안 하면 실행이 무한 대기합니다
- 상류 코어가 stdout 으로 진단 로그를 쏟습니다 → `grep -vE "DEBUG_TAB_POS|LAYOUT_OVERFLOW"`

CUPS 가상 프린터(SIP 차단)·LibreOffice(`.hwpx` 필터 없음)는 검증 후 배제했습니다.
상세는 `references/hwpx-to-pdf.md`.

## 하지 않는 것

- `.hwp`(구 바이너리 포맷) 편집. 이 스킬은 `.hwpx`(OWPML) 전용입니다.
