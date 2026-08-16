---
name: fill-hwpx-template
description: "승인된 내용을 원본 보존 작업용 HWPX에 반영하고, 사용자의 디자인 지시 또는 '알아서 보기 좋게' 요청에 맞춰 표·문단·시각자료·타이포·여백을 주도적으로 설계할 때 사용한다. HWP→HWPX 준비, 중괄호 치환, 의미 기반 시각자료 배치, 구조검사, PDF/PNG 화면검수까지 수행한다."
---

# HWPX 양식 안전하게 채우기

## 먼저 확인

- `.hwp`는 직접 처리하지 않는다. 한글에서 **다른 이름으로 저장 → HWPX**로 준비한다.
- 원본은 보존하고 `03. 사업계획서양식/작업용 HWPX`의 복사본만 사용한다.
- 사용자가 승인한 `placeholder-values.approved.json`만 기본 입력으로 사용한다.
- 중괄호 항목이 0개면 자동 입력 성공이 아니라 BLOCK이다.
- 구조검사와 실제 렌더 검사는 서로 다른 검사이며 둘 다 필요하다. 실제 렌더러가 만든 PDF·페이지별 PNG와 전체·100%·확대 검수 기록이 없으면 BLOCK이다.
- 공식 고정 구조·고정 문구와 사용자가 지정하지 않은 문단·글자·목록·표 스타일은 유지한다. 공식 지시, 사용자 지시, 디자인 결정표가 지정한 속성만 작업용 복사본에서 변경하고 변경 속성을 로그에 남긴다.
- 시각자료가 있으면 `references/visual-design-system.md`와 승인된 `앞 문단 / 뒤 문단 / 짧은 캡션` 명세를 먼저 확인한다.
- 원본의 섹션 순서, 공식 질문·제목·안내문, 최상위 표 topology, 고정 셀 텍스트를 source integrity receipt로 잠근다. 승인된 답변 셀·치환값·디자인 삽입영역 밖의 변경은 BLOCK이다.
- 장문 답변은 공식 서술형 요구가 없는 한 `o 핵심항목`과 `- 세부내용` 개조식이어야 한다. filler는 각 플레이스홀더 답변 셀의 글꼴·크기·자간 등 기준 글자 스타일을 별도로 복제한 뒤 `o` 문단에 1,200/-1,200 HWPUNIT, `-` 문단에 2,400/-1,200 HWPUNIT의 실제 내어쓰기 `paraPr`을 만들고 제목은 굵게, 세부내용은 일반 굵기로 연결한다.
- 공백·탭으로 들여쓰기를 흉내 내거나 장문 산문을 한 문단으로 넣으면 BLOCK이다. 공식 양식이 장문 서술형을 요구할 때만 근거를 기록하고 `--allow-prose-values`를 사용한다.
- 각 `- 세부내용` 주장 끝에는 보고서 안에서 출처·상태가 보이고 `근거목록.csv`로 연결되는 `[E001 | 기관·연도]`·`[U001 | 사용자 자료]`·`[H001 | 검증가설]`·`[P001 | 실행계획]` 표지가 있어야 한다. 장문 서술형 예외도 각 문단 끝에 표지가 없으면 BLOCK한다.
- 비어 있지 않은 플레이스홀더 값은 길이와 무관하게 기본적으로 주장 문단이다. 회사명·성명·날짜 같은 식별 라벨만 승인 JSON의 `_claim_free` 객체에 `"{회사명}": "회사명 식별값"`처럼 키와 사유를 명시해 제외한다.
- 주장 표지의 `|` 뒤 짧은 출처·상태는 `--evidence-registry 근거목록.csv`의 동일 ID `inline_citation`과 정확히 같아야 한다. E/U 행은 출처명·경로 또는 URL·확인일도 없으면 BLOCK한다.
- 주장 플레이스홀더는 한 개의 문단과 한 개의 텍스트 run을 단독 점유해야 한다. 뒤에 고정 문구가 붙거나 여러 run으로 쪼개졌으면 최종 문단 끝 표지를 보장할 수 없으므로 BLOCK한다.

## `알아서 보기 좋게` 실행 계약

이 요청을 받으면 색상 취향을 되묻는 것으로 시작하지 않는다. 에이전트가 원본 HWPX와
승인 문안을 분석해 디자인 권장안을 만들고, 사용자 지정이 없는 항목만 공통 기본값으로
채운다.

1. 원본의 용지·여백·머리말·꼬리말·표·문단·글자 스타일을 inventory로 기록한다.
2. 각 답변의 평가 질문, 핵심 주장, 근거, 숫자, 순서를 읽고 시각화 필요성을 판정한다.
3. 문장만으로 충분하면 시각자료를 넣지 않는다. 판단이 빨라지는 항목만 표·비교·흐름·로드맵·KPI로 바꾼다.
4. `디자인 결정표`에 정보구조, 시각자료 종류, 삽입 위치, 크기, 타이포, 색상, 근거를 기록한다.
5. 사용자가 지정한 브랜드·폰트·색·톤·참고 이미지는 고정 조건으로 적용한다. 없을 때만 중립 기본값을 쓴다.
6. 승인 문안과 디자인 결정표를 작업용 복사본에 반영하고 새 버전으로 저장한다.
7. XML·ZIP·manifest·`secPr` 검사 뒤 PDF/PNG로 렌더해 100%와 확대 화면에서 잘림, 겹침, 빈 페이지, 과밀, 낮은 대비를 확인한다.
8. 결함이 있으면 사용자에게 위치를 찾아 달라고 하지 않고 원인을 고쳐 새 버전을 다시 검사한다.

진짜로 결정이 필요한 경우만 묻는다. 공식 양식이 여러 개라 대상이 불명확하거나,
사용자 디자인 지시가 서로 충돌하거나, 승인 문안·원본·렌더러가 없을 때는 권장안과
영향을 제시하고 확인받는다. 그 외에는 분석 보고서만 남기고 멈추지 말고 결과 HWPX와
검증 기록까지 만든다.
사용자의 `알아서·전문적으로·보기 좋게` 지시는 근거 범위 안 디자인 결정을 위임한
현재 요청의 승인으로 기록한다. 같은 디자인을 적용해도 되는지 다시 묻지 않는다.
문안·공개범위·제출 승인까지 대신하지 않으며, 위임 범위 밖의 중대한 변경만 확인받는다.

## 파이프라인 위치: 8단계 HWPX 반영 + 9단계 검사

이 스킬은 사업계획서를 새로 쓰는 도구가 아니다. `review-business-plan`에서
BLOCK이 없고 사용자가 승인한 문안만 최종 제출 양식의 작업용 복사본에 옮긴다.

**진입 조건**: 승인 대상 파일·버전·승인자·시각, 승인된 치환값 또는 위치표가 있다.

**완료 조건**: 새 HWPX와 변경 로그가 있고 미치환·빈 값이 없으며, 원본 고정 구조와
패키지 구조검사 PASS, 실제 렌더러가 만든 PDF·페이지별 PNG, 전체 페이지·100%·확대
육안검수 기록 PASS가 모두 있어야 한다. 시각자료가 있으면 의미상 위치, 중첩표 계층,
이미지 참조, 캡션, 원본 `secPr` 보존도 PASS해야 한다. 렌더러나 렌더 산출물이 없으면
완료가 아니라 BLOCK이다.

**다음 단계**: 승인된 사업계획서 원문과 HWPX 검증 기록을 `ppt-editorial`에 넘긴다.
PPT는 HWPX 페이지를 복사하지 않고 발표 목적에 맞게 내용을 다시 구성한다.

## 실행 방법

이 SKILL.md가 있는 폴더를 스킬 루트로 정하고 그 아래 `scripts/hwpx_placeholders.py`를 사용한다. 프로젝트 루트의 scripts로 해석하지 않는다.

Windows에서는 `python`, macOS/Linux에서는 `python3`를 사용한다.

### 1. 양식의 중괄호 항목 찾기

Windows:

```powershell
python "<이 SKILL.md가 있는 폴더>\scripts\hwpx_placeholders.py" scan "03. 사업계획서양식\작업용 HWPX\양식.hwpx" --map-out "03. 사업계획서양식\placeholder-values.draft.json"
```

macOS/Linux:

```bash
python3 "<이 SKILL.md가 있는 폴더>/scripts/hwpx_placeholders.py" scan "03. 사업계획서양식/작업용 HWPX/양식.hwpx" --map-out "03. 사업계획서양식/placeholder-values.draft.json"
```

찾은 항목이 0개면 실제 양식에 자동 입력 표시가 없는 것이다. 자동 치환을 중단하고 위치표를 만들어 사람이 반영한다.

### 2. 사용자 승인값으로 새 파일 만들기

```powershell
python "<이 SKILL.md가 있는 폴더>\scripts\hwpx_placeholders.py" fill "03. 사업계획서양식\작업용 HWPX\양식.hwpx" --values "03. 사업계획서양식\placeholder-values.approved.json" --evidence-registry "00. 시작하기\근거목록.csv" --output "07. 최종본\사업계획서_v01.hwpx"
```

macOS/Linux에서는 `python3`와 `/` 경로 구분자를 사용한다.

### 3. 구조 다시 검사하기

```powershell
python "<이 SKILL.md가 있는 폴더>\scripts\hwpx_placeholders.py" validate "07. 최종본\사업계획서_v01.hwpx"
```

4. 변경 로그에서 찾지 못한 항목, 빈 값, 미치환 중괄호가 없는지 확인한다.
5. 한글에서 결과 파일을 열어 표 너비·행 높이, 문단·자동 줄 바꿈, 번호 체계·목록 단계·들여쓰기, 글자 겹침, 페이지 넘김을 직접 확인한다. 시각자료는 실제 문맥 위치, 1열 2행 중첩표, 이미지 비율·해상도, 짧고 가운데 정렬된 캡션을 함께 확인한다.
6. 오류가 있으면 원본을 덮어쓰지 말고 승인값 또는 위치표를 고친 뒤 새 버전을 만든다.

### 4. 원본 고정 구조 검사

원본의 플레이스홀더가 아닌 문단, 섹션 순서, 최상위 표 topology, `secPr`을 결과와
대조한다. 승인된 기존 답변 문단을 바꾸는 작업이면
`editable-zones.approved.json`의 `editableParagraphExact` 배열에 원본 문단 전체를
정확히 기록한다. 각 anchor는 원본에서 정확히 한 번만 일치해야 하며, 짧은 공통 단어,
부분 문자열, 중복 문단은 BLOCK이다. `사업명: {사업명}`처럼 플레이스홀더가 있는 문단도
플레이스홀더 바깥의 `사업명:` 고정 문구는 자동 보존한다.

```powershell
python "<이 SKILL.md가 있는 폴더>\scripts\hwpx_source_integrity.py" "07. 최종본\사업계획서_v01.hwpx" --source "03. 사업계획서양식\원본.hwpx" --editable-spec "03. 사업계획서양식\editable-zones.approved.json" --output "06. 검토결과\hwpx-source-integrity.json"
```

editable spec이 필요 없는 빈 양식은 `--editable-spec`만 생략한다. macOS/Linux에서는
`python3`와 `/` 경로를 사용한다. 결과가 BLOCK이면 HWPX를 완료로 표시하지 않는다.

### 5. 시각자료 구조와 위치 검사

시각자료는 답변 셀 마지막에 일괄 배치하지 않는다. 승인 명세의 설명 문단 직후,
다음 항목 직전에 `tc → subList → p → run → tbl` 계층의 1열 2행 중첩표로
삽입한다. 위 행은 이미지, 아래 행은 `그림 N. 핵심 그림명` 캡션이다.

현재 결과 설정을 먼저 확인한다.

```powershell
python "<이 SKILL.md가 있는 폴더>\scripts\hwpx_visuals.py" inspect "07. 최종본\사업계획서_v01.hwpx"
```

승인된 위치 명세와 원본 HWPX를 기준으로 재현 검증한다.

```powershell
python "<이 SKILL.md가 있는 폴더>\scripts\hwpx_visuals.py" validate "07. 최종본\사업계획서_v01.hwpx" --source "03. 사업계획서양식\원본.hwpx" --spec "03. 사업계획서양식\visual-placement.approved.json"
```

macOS/Linux에서는 `python3`와 `/` 경로 구분자를 사용한다. 검사는 다음을 모두
fail-closed로 확인한다.

- `앞 문단 / 뒤 문단` 사이의 의미상 위치
- `tc → subList → p → run → tbl` 계층과 1열 2행 구조
- `<img binaryItemIDRef>`·`Contents/content.hpf`·실제 `BinData` member 일치
- 짧은 캡션, 가운데 정렬, 행 높이, 배경
- 원본과 결과의 `secPr` canonical digest 일치
- `--source`는 필수다. 원본 없이 `secPrPreserved`를 PASS로 만들 수 없다.
- manifest ID와 ZIP member가 중복되거나 href가 절대경로·역슬래시·`.`·`..` segment를 포함하거나 이미지가 `BinData/` 밖을 가리키면 BLOCK
- 시각표 후보 수와 승인 명세 수가 정확히 같고 캡션도 중복되지 않음

### 6. 실제 렌더와 확대 검수

지원되는 실제 렌더러로 결과 HWPX를 PDF로 내보내고 모든 페이지를 PNG로 렌더한다.
렌더러 이름·버전, HWPX/PDF/PNG digest, 페이지 크기, 전체 페이지·100%·확대 검수 결과를
`render-qa.json`에 기록한다. 각 페이지는 `clipping`, `overlap`, `blankPage`,
`lowContrast`, `orphanParagraph`, `captionSplit`이 모두 `false`이고
`zoomReviewed=true`여야 한다.

```powershell
python "<이 SKILL.md가 있는 폴더>\scripts\verify_hwpx_render.py" "07. 최종본\사업계획서_v01.hwpx" --receipt "06. 검토결과\render-qa.json" --output "06. 검토결과\render-qa-verified.json"
```

PDF·페이지 PNG·렌더러 버전·확대 검수 중 하나라도 없거나 digest가 바뀌면 BLOCK이다.

1R 실측값과 다른 양식의 비례 조정 규칙은 `references/visual-design-system.md`를
따른다. 1R 수치를 다른 양식에 강제로 덮어쓰거나 시각자료 때문에 쪽 여백을 바꾸지 않는다.

HWP에서 HWPX로 저장하는 방법과 제한은 `references/hwp-to-hwpx.md`, 시각자료 배치·디자인·검증 기준은 `references/visual-design-system.md`를 읽는다.
