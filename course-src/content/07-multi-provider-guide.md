# Codex·Claude Code·Antigravity 공통 사용 안내

이 자료는 같은 일곱 개 범용 사업계획서 스킬 원본을 Codex, Claude Code, Antigravity에서 사용하도록 구성했습니다. 공고·양식 분석부터 승인된 HWPX와 발표자료까지 목표와 결과물은 같지만 설치 방법은 서로 다릅니다. 기본 스킬은 특정 지원사업에 묶이지 않으며, 수업에서는 제공된 공고와 평가표를 선택 자료로 넣어 사용합니다.

## 먼저 구분하기

| 환경 | 스킬 파일 사용 | 파일·명령 실행 | 권장 시작 방법 |
| --- | --- | --- | --- |
| Codex | 가능 | 가능 | dayoun 마켓플레이스 설치 또는 스타터 프로젝트 |
| Claude Code | 가능 | 가능 | Claude 마켓플레이스 설치 또는 스타터 프로젝트 |
| Antigravity | 가능 | 가능 | 스타터 프로젝트의 `.agents/skills` 사용 |
| 일반 채팅형 AI | 설치형 스킬은 사용하지 않음 | 보통 제한됨 | 참가자 빠른 시작의 공통 프롬프트 사용 |

일반 채팅형 AI는 Yellow/Red 강의 fallback에서 사고 순서와 출력 형식만 연습합니다. core conformance, 외부 베타의 공식 프로바이더 할당, marketplace 지원 표면에는 포함하지 않으며 프로젝트 생성·파일 추적·HWPX·PPT 자동화를 설치형 도구와 같다고 안내하지 않습니다.

## 가장 쉬운 수업용 방법

배포된 `dayoun-business-plan-course-kit`의 `starter-project`를 작업 폴더로 엽니다.

- Codex와 Antigravity는 `.agents/skills`를 읽습니다.
- Claude Code는 `.claude/skills`를 읽습니다.
- 두 폴더는 `plugins/business-plan-writer/skills`에서 자동 생성된 동일한 복사본입니다.
- `.dayoun/validators`와 `.dayoun/_contracts`도 같은 빌드에서 생성되며 범위·사실·승인 검증을 수행합니다.
- 수강생은 자연어로 “`complete-business-plan` 스킬을 사용해 DEMO 모드로 시작해줘”라고 요청합니다.

실무 전체 흐름은 “`complete-business-plan` 스킬을 사용해 공식 자료 분석부터 승인된 HWPX와 발표 PPT·대본·예상 Q&A까지 10단계로 진행해줘”라고 요청합니다.

## 제품별 설치

### Codex

```powershell
codex plugin marketplace add Dayoooun/dayoun-marketplace --ref main
codex plugin add business-plan-writer@dayoun
```

### Claude Code

Claude Code 안에서 실행합니다.

```text
/plugin marketplace add Dayoooun/dayoun-marketplace
/plugin install business-plan-writer@dayoun
```

설치 뒤 `/reload-plugins`를 실행하거나 Claude Code를 다시 시작합니다.

### Antigravity

수업에서는 스타터 프로젝트를 여는 방법을 권장합니다. Antigravity는 워크스페이스의 `.agents/skills/<skill-name>/SKILL.md`를 읽습니다.

플러그인 단위로 관리하려는 강사·운영자는 `plugins/business-plan-writer` 폴더를 워크스페이스의 `.agents/plugins/business-plan-writer`에 복사할 수 있습니다. 이 폴더의 루트 `plugin.json`과 `skills/`를 함께 유지합니다.

## 모든 에이전트에서 같은 완료 계약

어떤 에이전트 도구를 사용해도 기본 완료 결과는 다음 네 가지입니다.

1. `공백진단표`: 평가기준과 현재 내용 사이의 가장 중요한 공백 한 개
2. `조사기록`: 확인할 내용, 근거, 말할 수 없는 범위, 다음 확인
3. `멘토링변화기록`: 유지·수정·보류 결정과 이유
4. `실행카드`: 담당·기한·완료 증거·다음 행동과 1분 설명

위 네 가지는 120분 핵심 실습의 완료 결과입니다. 실무 전체 흐름에서는 텍스트 초안 검토와 사용자 승인 뒤에만 HWPX를 반영하고, 구조·한글 화면검사를 통과한 승인 내용을 발표용 PPTX·대본·예상 Q&A로 재구성합니다.

`.hwp`를 `.hwpx`로 저장하고 최종 페이지 배치를 확인하는 단계는 한글이 설치된 환경에서 진행합니다. Python 보조 스크립트는 이미 준비된 `.hwpx`의 구조 확인과 승인값 치환을 돕는 역할이며, 한글의 화면 검수를 대신하지 않습니다.

## 호환성 원칙

- 일곱 스킬의 원본은 `plugins/business-plan-writer/skills` 한 곳만 수정합니다.
- 제품별 매니페스트는 설치 위치만 연결하고 스킬 내용을 복제하지 않습니다.
- 스타터의 `.agents/skills`와 `.claude/skills`는 동기화 검사로 원본과 바이트 단위 일치를 확인합니다.
- 특정 제품의 호출 기호에 의존하지 않고 스킬 이름과 목표를 자연어로 요청합니다.
- 결과물의 ID, 표 제목, 안전 규칙은 프로바이더와 관계없이 같습니다.
