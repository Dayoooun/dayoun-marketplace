---
name: fill-hwpx-template
description: "한글 HWP 파일을 HWPX로 준비하도록 안내하고, HWPX 안의 정확한 중괄호 항목을 승인된 값으로 채운 새 파일과 변경 로그를 만든다. 사용자가 HWPX 양식 확인, 중괄호 치환, 사업계획서 양식 채우기, HWPX 구조검사를 요청할 때 사용한다."
---

# HWPX 양식 안전하게 채우기

## 먼저 확인

- `.hwp`는 직접 처리하지 않는다. 한글에서 **다른 이름으로 저장 → HWPX**로 준비한다.
- 원본은 보존하고 `03. 사업계획서양식/작업용 HWPX`의 복사본만 사용한다.
- 사용자가 승인한 `placeholder-values.approved.json`만 기본 입력으로 사용한다.
- 중괄호 항목이 0개면 자동 입력 성공이 아니라 BLOCK이다.
- 구조검사와 한글 화면 확인은 서로 다른 검사이며 둘 다 필요하다.
- 원본의 문단·글자·목록·표 스타일을 유지하고, 공백·탭·줄 바꿈으로 들여쓰기를 임의로 만들지 않는다.

## 파이프라인 위치: 8단계 HWPX 반영 + 9단계 검사

이 스킬은 사업계획서를 새로 쓰는 도구가 아니다. `review-business-plan`에서
BLOCK이 없고 사용자가 승인한 문안만 최종 제출 양식의 작업용 복사본에 옮긴다.

**진입 조건**: 승인 대상 파일·버전·승인자·시각, 승인된 치환값 또는 위치표가 있다.

**완료 조건**: 새 HWPX와 변경 로그가 있고, 미치환·빈 값이 없으며 구조검사와
한글 화면검사가 모두 통과해야 한다.

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
python "<이 SKILL.md가 있는 폴더>\scripts\hwpx_placeholders.py" fill "03. 사업계획서양식\작업용 HWPX\양식.hwpx" --values "03. 사업계획서양식\placeholder-values.approved.json" --output "07. 최종본\사업계획서_v01.hwpx"
```

macOS/Linux에서는 `python3`와 `/` 경로 구분자를 사용한다.

### 3. 구조 다시 검사하기

```powershell
python "<이 SKILL.md가 있는 폴더>\scripts\hwpx_placeholders.py" validate "07. 최종본\사업계획서_v01.hwpx"
```

4. 변경 로그에서 찾지 못한 항목, 빈 값, 미치환 중괄호가 없는지 확인한다.
5. 한글에서 결과 파일을 열어 표 너비·행 높이, 문단·자동 줄 바꿈, 번호 체계·목록 단계·들여쓰기, 글자 겹침, 페이지 넘김을 직접 확인한다.
6. 오류가 있으면 원본을 덮어쓰지 말고 승인값 또는 위치표를 고친 뒤 새 버전을 만든다.

HWP에서 HWPX로 저장하는 방법과 제한은 `references/hwp-to-hwpx.md`를 읽는다.
