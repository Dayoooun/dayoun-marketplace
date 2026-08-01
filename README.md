# dayoun marketplace

비개발자와 초기 창업자가 Codex로 사업계획서 작성 과정을 한 바퀴 실습할 수 있도록 만든 공개 교육용 플러그인입니다.

회사자료 정리부터 공고·평가기준 확인, 시장조사, 초안 작성, 팩트체크, HWPX 양식 치환까지 단계별로 안내합니다. 누구나 무료로 설치하고 수정할 수 있도록 MIT 라이선스로 공개합니다.

## 가장 쉬운 설치

PowerShell 또는 터미널에서 아래 두 줄을 실행합니다.

```powershell
codex plugin marketplace add Dayoooun/dayoun-marketplace --ref main
codex plugin add modoo-startup-plan@dayoun
```

설치가 끝나면 Codex를 새로 시작하고 다음과 같이 요청합니다.

```text
$complete-modoo-plan 내 사업계획서 작업을 처음부터 안내해줘.
```

## 제공하는 6개 스킬

| 스킬 | 하는 일 |
| --- | --- |
| `complete-modoo-plan` | 전체 작성 순서를 처음부터 끝까지 안내 |
| `setup-startup-plan-project` | 회사자료·공고문·양식·리서치 폴더와 작업표 생성 |
| `research-startup-evidence` | 공식 출처 중심으로 시장 근거 조사 |
| `draft-modoo-plan` | 평가기준에 맞춰 사업계획서 초안 작성 |
| `fill-hwpx-template` | HWPX 중괄호 항목 검색·치환·구조검증 |
| `review-modoo-plan` | 사실·출처·평가기준·미완성 항목 최종 점검 |

## 수업에서 사용하는 기본 폴더

```text
01. 회사내용
02. 공고문 및 평가지표
03. 사업계획서양식
04. 시장조사 리서치
```

`setup-startup-plan-project` 스킬이 위 폴더와 필요한 작업표를 자동으로 만듭니다. 기존 파일은 덮어쓰지 않습니다.

## HWPX 실습 전 확인

- 원본이 `.hwp`라면 한컴오피스에서 먼저 `.hwpx`로 다른 이름 저장합니다.
- 원본 문서는 그대로 보관하고 복사본만 치환합니다.
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

## 안전 원칙

- 회사 사실, 외부 근거, 가정, 향후 계획을 구분합니다.
- 출처 없는 수치와 확인되지 않은 실적을 만들지 않습니다.
- 개인정보와 영업비밀이 포함된 자료는 공개 저장소에 올리지 않습니다.
- 외부 MCP나 별도 API 키 없이도 핵심 실습을 완주할 수 있게 구성했습니다.

## 기여와 문의

오류 제보와 개선 제안은 GitHub Issues로 남겨주세요. 변경 제안은 [CONTRIBUTING.md](CONTRIBUTING.md)를 참고해 주세요. 보안 문제는 [SECURITY.md](SECURITY.md)의 비공개 제보 절차를 이용해 주세요.

## 라이선스

[MIT License](LICENSE)
