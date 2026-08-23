# AGENTS.md — dayoun marketplace agent guide

이 문서는 이 저장소를 읽는 Codex, Claude Code, Antigravity와 기타 코딩 에이전트가 사람 대신 안전하게 설치·업데이트·검증하기 위한 실행 계약입니다.

## 목표

사용자가 “설치해”, “업데이트해”, “사업계획서 플러그인 연결해”라고 요청하면 다음 결과를 만듭니다.

- Codex 또는 Claude Code에서 `business-plan-writer@dayoun`을 사용할 수 있다.
- 사용자가 문서 플러그인도 요청하면 `business-documents@dayoun`을 사용할 수 있다.
- 설치 결과에 실제 버전과 enabled 상태가 남는다.
- 기존 플러그인, 사용자 설정, 작업 파일은 보존한다.
- 실패를 성공으로 보고하거나 확인되지 않은 명령을 만들지 않는다.

설치 성공 보고에서 멈추지 않습니다. 사용자가 자연어로 사업계획서·HWPX 결과를 요청하면
스킬 이름이나 명령을 되묻지 않고 `complete-business-plan`을 기본 진입점으로 사용합니다.
PPT·PPTX·파워포인트·슬라이드·발표자료·피치덱·IR 덱·제안서·강의자료의 생성·수정·
리디자인·PDF 변환·대본·예상 Q&A를 말하면 `ppt-editorial`을 즉시 적용합니다.
모든 PPT 제목·본문·캡션·대본·Q&A는 보호값 대조를 포함한 한국어 윤문을 반드시 거칩니다.
사용자의 명시적 지시를 고정 조건으로 기록하고, 되돌릴 수 있는 분석·조사·디자인은 직접
진행하며 결과를 바꾸는 결정만 권장안과 함께 확인받습니다. 특히 HWPX는
원본 보존, 의미 기반 시각자료, 실제 PDF/PNG 화면검수까지 리드합니다.

현재 공개 RC 버전:

| 플러그인 | 버전 | 용도 |
|---|---:|---|
| `business-plan-writer` | `0.12.10` | 전용 표지·휴식 화면과 기획 승인 후 2단 병렬제작을 갖춘 Full HD PPT 하네스 |
| `business-documents` | `0.1.0` | 견적서·회사소개서·이력서·공문·안내문 HTML |

stable `1.0`은 외부 프로바이더·화면검수·강의·베타 증거가 충족되기 전까지 설치 대상으로 안내하지 않습니다.

## 먼저 환경을 감지한다

터미널에서 아래 두 명령을 각각 실행할 수 있는지 확인합니다.

```powershell
codex --version
claude --version
```

판정:

1. `codex`만 있으면 Codex 절차를 사용합니다.
2. `claude`만 있으면 Claude Code 절차를 사용합니다.
3. 둘 다 있으면 사용자가 현재 사용하는 호스트를 우선하고, 모르면 둘 다 설치하지 말고 감지 결과를 설명합니다.
4. 둘 다 없으면 CLI 설치가 선행 조건이라고 보고하고 플러그인 설치를 BLOCK합니다.
5. Antigravity 작업공간이면 marketplace CLI를 흉내 내지 말고 아래 Antigravity 절차를 사용합니다.

절대로 전역 설정 디렉터리를 삭제하거나 초기화하지 않습니다. 격리 테스트가 필요하면 새 임시 설정 디렉터리를 만들고 그 안에서만 실행합니다.

## Codex 설치

정확히 다음 순서로 실행합니다.

```powershell
codex plugin marketplace add Dayoooun/dayoun-marketplace --ref main
codex plugin add business-plan-writer@dayoun
codex plugin add business-documents@dayoun
codex plugin list
```

`business-documents`가 요청되지 않았다면 해당 `plugin add` 줄만 생략할 수 있습니다.

성공 조건:

- marketplace 이름이 `dayoun`이다.
- `business-plan-writer@dayoun`이 `installed, enabled`다.
- writer 버전이 `0.12.10`이다.
- 요청한 경우 `business-documents@dayoun`이 `installed, enabled`이고 `0.1.0`이다.

marketplace가 이미 등록되어 있으면 추가 실패를 반복하지 않습니다. 다음 업데이트 명령으로 전환합니다.

```powershell
codex plugin marketplace upgrade dayoun
codex plugin list
```

## Claude Code 설치

Claude Code 대화 입력창에서는 다음 slash command를 한 줄씩 사용합니다.

```text
/plugin marketplace add Dayoooun/dayoun-marketplace
/plugin install business-plan-writer@dayoun
/plugin install business-documents@dayoun
/plugin list
```

터미널에서는 동일한 작업을 다음처럼 실행할 수 있습니다.

```powershell
claude plugin marketplace add Dayoooun/dayoun-marketplace
claude plugin install business-plan-writer@dayoun
claude plugin install business-documents@dayoun
claude plugin list
```

성공 조건:

- 두 플러그인의 scope가 의도한 사용자 또는 프로젝트 scope다.
- 상태가 enabled다.
- 버전이 각각 `0.12.10`, `0.1.0`이다.
- 설치 후 Claude Code 재시작이 필요하다고 안내한다.

이미 등록된 marketplace는 중복 추가하지 않고 업데이트합니다.

```powershell
claude plugin marketplace update dayoun
claude plugin update business-plan-writer@dayoun
claude plugin update business-documents@dayoun
claude plugin list
```

## Antigravity 설치

Antigravity는 이 저장소의 marketplace 명령 지원 대상으로 가장하지 않습니다.

1. 저장소를 내려받습니다.
2. `course/starter-project`를 Antigravity 작업공간 루트로 엽니다.
3. 작업공간의 `.agents/skills`가 보이는지 확인합니다.
4. `complete-business-plan` 스킬을 지정한 읽기 전용 QUICK 요청으로 인식 여부를 확인합니다.

저장소 복제 명령:

```powershell
git clone --depth 1 https://github.com/Dayoooun/dayoun-marketplace.git
```

Antigravity GUI가 비동기로 열렸다는 사실만으로 설치 성공을 주장하지 않습니다. 실제 작업공간에서 스킬을 읽고 결과 파일을 만들 수 있어야 실행 증거가 됩니다.

## 설치 후 smoke test

실제 회사 정보를 쓰지 않고 다음 요청을 실행합니다.

```text
complete-business-plan 스킬을 사용해줘.
QUICK 범위에서 필요한 입력자료와 단계만 설명하고 실제 문서는 만들지 마.
확인되지 않은 사실이나 실적은 만들지 마.
```

문서 플러그인 smoke test:

```text
create-business-documents 스킬을 사용해줘.
견적서를 만들기 전에 필수 공급자 정보와 품목 열만 알려줘.
빈 값은 추측하지 마.
```

성공 조건은 스킬 이름을 인식하고 해당 스킬의 입력 계약을 설명하는 것입니다. 일반적인 사업계획서 조언만 반환하면 설치 성공으로 간주하지 않습니다.

## 사용자 요청을 스킬로 연결한다

| 사용자 의도 | 우선 스킬 |
|---|---|
| 처음부터 전체 사업계획서 | `complete-business-plan` |
| 작업 폴더·입력자료 준비 | `setup-business-plan-project` |
| 초안 작성 | `draft-business-plan` |
| 기존 초안 검토 | `review-business-plan` |
| 승인된 HWPX 반영 | `fill-hwpx-template` |
| 제출 전 완료 검사 | `validate-business-plan` |
| 발표 PPT | `ppt-editorial` |
| 견적서·회사소개서·공문 | `create-business-documents` |

HWPX와 PPT는 독립 선택 산출물입니다. PPT를 만들기 위해 HWPX를 먼저 만들도록 강제하지 않습니다.

PPT 렌더 전 bundled Pretendard 1.3.9의 bundle·사용자 범위 설치를 검사하고 없을 때만
`install_bundled_fonts.py install`을 실행합니다.
제품·원료·기기·인물 씬은 `cutout`, 환경·공간 장면은 `canvas`로 명시합니다.
`.safe.json`과 조립 크롭을 분리하고 실제 alpha·가짜 체크무늬·전경 bbox·슬롯 점유율·
텍스트/크롬 충돌을 검증한 placement receipt가 없으면 PPT를 완료로 보고하지 않습니다.

## 안전 규칙

- 회사 사실, 외부 근거, 가정, 향후 계획을 구분합니다.
- 확인되지 않은 수치·날짜·실적·고객명을 만들지 않습니다.
- 사용자 승인이 필요한 canonical payload와 문서 내용을 임의 승인하지 않습니다.
- 원본 HWP/HWPX를 덮어쓰지 않습니다.
- 개인정보·영업비밀을 공개 저장소나 설치 로그에 남기지 않습니다.
- 설치 실패, 인증 실패, 네트워크 실패를 PASS로 바꾸지 않습니다.
- 다른 marketplace, 플러그인, 설정, 작업 파일을 삭제하지 않습니다.
- stable `1.0`이 공개됐다고 추정하지 않습니다. marketplace manifest의 실제 버전을 읽습니다.

## 이 저장소를 개발할 때

authoritative source와 generated output을 섞지 않습니다.

| authoritative source | generated·배포 표면 |
|---|---|
| `contracts/` | 각 release ZIP의 `_contracts/` |
| `plugins/business-plan-writer/` | writer marketplace와 ZIP |
| `plugins/business-documents/` | documents marketplace와 ZIP |
| `course-src/`와 writer skills | `course/`와 starter-project |

`course/`와 `course/starter-project`의 스킬 복사본을 직접 수정하지 않습니다. 원본을 수정한 뒤 다음 명령으로 재생성·검증합니다.

```powershell
python scripts/generate_course.py
python scripts/generate_course.py --check
python scripts/check_generated.py --forbid-internal
python scripts/validate_contracts.py contracts
python -m unittest discover -s tests -v
```

## 실패 보고 형식

설치 또는 업데이트가 실패하면 다음 네 줄을 남깁니다.

```text
상태: BLOCK
실패 단계: <실행한 단계>
실제 명령/오류: <토큰과 개인정보를 제거한 출력>
다음 조치: <사용자가 실행할 하나의 구체적 조치>
```

경고를 숨기거나, 버전을 확인하지 않고 “설치 완료”라고 말하거나, 일반 채팅형 AI를 설치형 플러그인과 같은 기능으로 안내하지 않습니다.
