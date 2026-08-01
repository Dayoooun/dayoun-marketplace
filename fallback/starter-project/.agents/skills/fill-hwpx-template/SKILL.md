---
name: fill-hwpx-template
description: "한글 HWP를 HWPX로 저장하도록 안내하고, HWPX의 중괄호 플레이스홀더를 스캔해 JSON 치환표를 만든 뒤 원본을 보존한 새 HWPX 파일과 변경 로그를 생성·검증한다. 사용자가 한글 양식, HWPX 치환, 사업계획서 양식 채우기, 중괄호 항목 자동 입력을 요청할 때 사용한다."
---

# HWPX 양식 채우기

## 안전 규칙

- .hwp 파일은 직접 처리하지 않는다. 한글에서 다른 이름으로 저장하여 .hwpx로 만든다.
- 원본과 같은 경로로 출력하지 않는다.
- 정확히 발견된 중괄호 항목만 치환한다.
- 미치환 항목과 구조검증 결과를 반드시 보고한다.
- 구조검증 통과는 한글에서의 육안검수를 대신하지 않는다.
- 플레이스홀더 0개는 자동치환 성공이 아니라 BLOCK이다.
- 콘텐츠 검토와 사용자 승인을 마친 placeholder-values.approved.json만 기본 입력으로 사용한다.

## 시작 모드

- ANNOTATED_TEMPLATE: 강사가 중괄호를 미리 넣은 교육용 HWPX를 자동 치환한다.
- MANUAL_MAPPING: 실제 양식에 중괄호가 없으면 template-field-map.csv와 수동 치환표까지만 만들고 DRY_RUN 또는 FALLBACK으로 종료한다.

## 절차

1. 이 SKILL.md가 있는 폴더를 스킬 루트로 정하고 그 아래 `scripts/hwpx_placeholders.py`를 사용한다. 프로젝트 루트의 scripts로 해석하지 않는다.
   - Windows에서는 `python`, macOS/Linux에서는 `python3`를 사용한다.
2. 작업용 HWPX를 스캔한다.

Windows 예시:

~~~powershell
python "<이 SKILL.md가 있는 폴더>\scripts\hwpx_placeholders.py" scan "03. 사업계획서양식\작업용 HWPX\양식.hwpx" --map-out "03. 사업계획서양식\placeholder-values.draft.json"
~~~

macOS/Linux 예시:

~~~bash
python3 "<이 SKILL.md가 있는 폴더>/scripts/hwpx_placeholders.py" scan "03. 사업계획서양식/작업용 HWPX/양식.hwpx" --map-out "03. 사업계획서양식/placeholder-values.draft.json"
~~~

3. 0개가 나오면 자동치환을 중단한다. 실제 양식이면 `--manual-mapping`으로 전환하고 template-field-map.csv를 작성한다.
4. draft 값을 작성하고 콘텐츠 검토와 사용자 승인을 거쳐 placeholder-values.approved.json을 만든다.
5. 승인된 값으로 새 파일을 생성한다.

~~~powershell
python "<이 SKILL.md가 있는 폴더>\scripts\hwpx_placeholders.py" fill "03. 사업계획서양식\작업용 HWPX\양식.hwpx" --values "03. 사업계획서양식\placeholder-values.approved.json" --output "05. 작성초안\사업계획서_고도화_v01.hwpx"
~~~

macOS/Linux에서는 같은 인자를 유지하고 `python3`와 `/` 경로 구분자를 사용한다.

6. 구조를 다시 검증한다.

~~~powershell
python "<이 SKILL.md가 있는 폴더>\scripts\hwpx_placeholders.py" validate "05. 작성초안\사업계획서_고도화_v01.hwpx"
~~~

7. replacement-log.csv와 남은 플레이스홀더를 확인한다.
8. 한글에서 표, 줄바꿈, 글자 겹침, 페이지 넘김을 육안 확인해야 FULL이다. 확인하지 못하면 DRY_RUN으로 기록한다.

HWP에서 HWPX로 저장하는 방법과 제한사항은 references/hwp-to-hwpx.md를 읽는다.
