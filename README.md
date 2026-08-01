# dayoun marketplace

비개발자와 초기 창업자가 제출한 사업계획을 근거와 활동 기록으로 고도화하도록 만든 공개 교육용 플러그인입니다.

제출본 보존, 평가 공백 진단, 주장 검증, 멘토링 변화기록, 다음 공식 마감 실행카드를 같은 순서로 안내합니다. HWPX 반영은 수정 허용과 양식 검증이 확인된 경우에만 선택합니다. 누구나 무료로 설치하고 수정할 수 있도록 MIT 라이선스로 공개합니다.

## 가장 쉬운 시작

수업에서는 [`fallback/starter-project`](fallback/starter-project)를 내려받아 작업 폴더로 여는 방법을 권장합니다. 같은 여섯 스킬을 Codex·Claude Code·Antigravity가 각자의 워크스페이스 경로에서 읽습니다.

- Codex·Antigravity: `.agents/skills`
- Claude Code: `.claude/skills`

스킬을 읽을 수 있는 에이전트에서 다음처럼 자연어로 요청합니다.

```text
complete-modoo-plan 스킬을 사용해 제출본을 보존하고 평가 공백 하나부터 안내해줘.
```

자료가 거의 없으면 파일을 만들기 전에 고객과 사용상황을 묻는 질문 하나부터 시작합니다.

### Codex 마켓플레이스 설치

```powershell
codex plugin marketplace add Dayoooun/dayoun-marketplace --ref main
codex plugin add modoo-startup-plan@dayoun
```

### Claude Code 마켓플레이스 설치

Claude Code 안에서 다음 명령을 실행합니다.

```text
/plugin marketplace add Dayoooun/dayoun-marketplace
/plugin install modoo-startup-plan@dayoun
```

Antigravity와 일반 채팅형 AI를 포함한 차이는 [멀티 프로바이더 안내](course/07-multi-provider-guide.md)에서 확인할 수 있습니다. 설치 방법은 서로 다르지만 네 가지 기본 결과물은 같습니다.

## 두 시간에 만드는 네 가지

1. 공개 평가기준에서 가장 중요한 공백 1개와 확인 질문
2. 주장 `C001`의 공식 출처 또는 기존 고객 근거, 기준일, 한계, 다음 검증
3. 제출 당시 생각과 새 근거를 비교한 유지·수정·보류 변화기록
4. 다음 공식 마감까지의 담당·기한·완료 증거와 1분 IR 핵심 메시지

회사 내부 입력은 `F001` 계열, 이번에 외부·고객 근거로 검증할 핵심 주장은 `C001`로 분리합니다. 네 결과물은 같은 C001을 사용합니다.

일반 채팅형 GPT, Gemini, Claude 등을 쓰는 참가자도 [`course/06-participant-quick-start.md`](course/06-participant-quick-start.md)의 같은 질문과 출력 형식으로 공통 경로를 완주할 수 있습니다. 다만 파일 생성·추적·HWPX 자동화는 에이전트 도구와 같은 기능이라고 안내하지 않습니다.

## 제공하는 6개 스킬

| 스킬 | 하는 일 |
| --- | --- |
| `complete-modoo-plan` | 공백·근거·변화·다음 행동의 전체 순서 안내 |
| `setup-startup-plan-project` | 원본을 보존하는 폴더와 네 가지 기본 작업표 생성 |
| `research-startup-evidence` | 주장 하나를 공식 출처 또는 기존 고객 근거로 검증 |
| `draft-modoo-plan` | 평가기준과 검증된 근거로 선택 항목 초안 작성 |
| `fill-hwpx-template` | 조건부 HWPX 중괄호 치환 또는 수동 매핑 |
| `review-modoo-plan` | 콘텐츠와 선택 HWPX 산출물을 분리해 검토 |

## 수업에서 사용하는 기본 폴더

```text
00. 시작하기
01. 회사내용
02. 공고문 및 평가지표
03. 사업계획서양식
04. 시장조사 리서치
05. 작성초안
06. 검토결과
07. 최종본
99. 원본백업
```

`setup-startup-plan-project` 스킬이 프로그램프로필과 위 폴더·작업표를 자동으로 만듭니다. `--force`를 사용해도 사용자 수정 파일은 덮어쓰지 않습니다.

## HWPX 선택 트랙 전 확인

- 운영기관이 제출 이후 수정 또는 보완본 제출을 허용했는지 먼저 확인합니다.
- 원본이 `.hwp`라면 한컴오피스에서 먼저 `.hwpx`로 다른 이름 저장합니다.
- 원본 문서는 그대로 보관하고 복사본만 치환합니다.
- 일반 양식에 중괄호가 0개이면 자동치환을 중단하고 `template-field-map.csv`로 수동 매핑합니다.
- 콘텐츠 검토와 사용자 승인이 끝난 값만 HWPX에 반영합니다.
- 자동 검사는 문서 구조와 미치환 항목을 확인합니다. 실제 페이지 배치와 글자 넘침은 한컴오피스에서 마지막으로 확인합니다.
- 데모 파일은 실습용이며 실제 제출 양식이 아닙니다. 출처는 [`PROVENANCE.md`](plugins/modoo-startup-plan/assets/demo/PROVENANCE.md)에 기록했습니다.

## 직접 내려받아 설치

저장소를 내려받거나 ZIP으로 압축 해제한 뒤 저장소 루트에서 실행합니다.

```powershell
codex plugin marketplace add .
codex plugin add modoo-startup-plan@dayoun
```

## 교육 자료

- [웹에서 전체 과정 보기](https://lecture-assistant-dayooouns-projects.vercel.app/courses/practice/12-modoo-startup-plan)
- [2시간 커리큘럼](course/02-curriculum-draft.md)
- [수업 전 체크리스트](course/03-preclass-checklist.md)
- [강사 운영 가이드](course/04-instructor-guide.md)
- [참가자 한 장 빠른 시작](course/06-participant-quick-start.md)
- [Codex·Claude Code·Antigravity 공통 사용 안내](course/07-multi-provider-guide.md)
- [설치 없는 스타터 프로젝트](fallback/starter-project)
- [완성 예시](fallback/completed-project)
- [인터넷 장애용 오프라인 근거팩](fallback/offline-evidence-pack)

## 안전 원칙

- 회사 사실, 외부 근거, 가정, 향후 계획을 구분합니다.
- 출처 없는 수치와 확인되지 않은 실적을 만들지 않습니다.
- 개인정보와 영업비밀이 포함된 자료는 공개 저장소에 올리지 않습니다.
- 외부 MCP나 별도 API 키 없이도 핵심 실습을 완주할 수 있게 구성했습니다.

## 버전

현재 공개 버전은 `0.4.0`입니다. 같은 스킬 원본을 Codex·Claude Code·Antigravity에서 사용하며, 일반 채팅형 AI에는 동일한 사고 순서와 출력 형식의 프롬프트 경로를 제공합니다.

## 기여와 문의

오류 제보와 개선 제안은 GitHub Issues로 남겨주세요. 변경 제안은 [CONTRIBUTING.md](CONTRIBUTING.md)를 참고해 주세요. 보안 문제는 [SECURITY.md](SECURITY.md)의 비공개 제보 절차를 이용해 주세요.

## 라이선스

[MIT License](LICENSE)
