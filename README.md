# dayoun marketplace

비개발자도 지원사업, 투자·IR, 사내 검토 등 여러 목적의 사업계획서를 공고·양식 분석부터 조사·설계·작성·검토·HWPX 제출본·발표 PPT까지 진행할 수 있게 만든 공개 플러그인입니다.

기본 스킬은 특정 기관이나 사업에 묶이지 않습니다. 부산대 수업에서는 현재 공식 공고와 평가표를 선택 설정으로 넣어 사용합니다. HWPX 반영은 원본 보존, 사용자 승인, 양식 검증이 확인된 경우에만 선택합니다. 누구나 무료로 설치하고 수정할 수 있도록 MIT 라이선스로 공개합니다.

## 가장 쉬운 시작

수업에서는 릴리스의 [`course/starter-project`](course/starter-project)를 작업 폴더로 여는 방법을 권장합니다. `course-src`와 일곱 핵심 스킬에서 자동 생성되며, Codex·Claude Code·Antigravity가 각자의 워크스페이스 경로에서 읽습니다. `business-documents`는 별도 설치하는 독립 플러그인이라 기본 강의 배포판에 들어가지 않습니다.

- Codex·Antigravity: `.agents/skills`
- Claude Code: `.claude/skills`

스킬을 읽을 수 있는 에이전트에서 다음처럼 자연어로 요청합니다.

```text
complete-business-plan 스킬을 사용해 공고문·평가지표·작성지침·양식을 먼저 분석하고,
회사·사업정보와 부족한 근거를 확인한 뒤 승인된 HWPX와 발표 PPT까지 10단계로 진행해줘.
```

공식 자료와 기존 사업정보를 확인한 뒤에도 고객·사용상황·문제가 비어 있을 때만 질문 하나를 합니다.

### Codex 마켓플레이스 설치

```powershell
codex plugin marketplace add Dayoooun/dayoun-marketplace --ref main
codex plugin add business-plan-writer@dayoun
```

### Claude Code 마켓플레이스 설치

Claude Code 안에서 다음 명령을 실행합니다.

```text
/plugin marketplace add Dayoooun/dayoun-marketplace
/plugin install business-plan-writer@dayoun
```

### 업데이트와 자동 업데이트

자동 업데이트는 GitHub에 공개된 새 버전만 가져옵니다. 로컬에서만 수정한 내용은 커밋·푸시되기 전까지 설치된 플러그인에 반영되지 않습니다.

Codex에서 마켓플레이스 스냅샷을 새로 받고 설치 버전을 확인합니다.

```powershell
codex plugin marketplace upgrade dayoun
codex plugin list
```

Claude Code에서 마켓플레이스와 플러그인을 갱신한 뒤 다시 시작합니다.

```powershell
claude plugin marketplace update dayoun
claude plugin update business-plan-writer@dayoun
```

자동 업데이트를 켜도 원리는 같습니다. 공개된 버전을 감지하면 갱신하고, 네트워크 오류나 버전 미공개 상태에서는 기존 설치본을 계속 사용합니다.

Antigravity와 일반 채팅형 AI를 포함한 차이는 [멀티 프로바이더 안내](course/07-multi-provider-guide.md)에서 확인할 수 있습니다. 설치 방법은 서로 다르지만 네 가지 기본 결과물은 같습니다.

## 두 시간에 만드는 네 가지

1. 공개 평가기준에서 가장 중요한 공백 1개와 확인 질문
2. 확인할 핵심 내용의 공식 출처 또는 기존 고객 근거, 기준일, 한계, 다음 확인
3. 제출 당시 생각과 새 근거를 비교한 유지·수정·보류 변화기록
4. 다음 공식 마감까지의 담당·기한·완료 증거와 1분 IR 핵심 메시지

내가 알고 있는 사업 정보와 외부 자료·고객 기록으로 확인할 내용을 분리합니다. 네 결과물은 같은 확인 내용을 사용합니다.

일반 채팅형 GPT, Gemini, Claude 등은 Yellow/Red 강의 fallback에서 [`course/06-participant-quick-start.md`](course/06-participant-quick-start.md)의 질문과 출력 형식만 연습합니다. core conformance·외부 베타 공식 프로바이더·marketplace 지원 표면에는 포함하지 않으며 파일 생성·추적·HWPX·PPT 자동화를 설치형 도구와 같다고 안내하지 않습니다.

## 공고에서 발표까지 이어지는 10단계

```text
1. 공고문·평가지표·작성지침·사업계획서 양식 분석
2. 회사·사업 현황·아이디어 분석
3. 부족한 근거와 확인 질문 도출
4. 시장·고객·경쟁·가격·규제 조사
5. 사업전략·실행계획·수익구조 설계
6. 평가지표와 양식에 맞춰 텍스트 초안 작성
7. 검토·수정·사용자 승인
8. 선택한 경우 승인 내용을 HWPX 양식에 반영
9. 선택한 HWPX 구조·화면검사
10. 선택한 PPT·대본·예상 Q&A 제작
```

| 구간 | 담당 스킬 | 다음 단계로 넘어가는 조건 |
|---|---|---|
| 전체 순서·공고 분석 | `complete-business-plan` | 자격·지원·일정·제출·평가·작성 제한이 원문 위치와 연결됨 |
| 원본·사업정보 정리 | `setup-business-plan-project` | 사실·미확인·가정·계획과 누락 자료가 구분됨 |
| 근거 조사 | `research-business-evidence` | 질문별 출처·기준일·단위·한계와 유지·수정·보류 판정이 있음 |
| 전략·텍스트 초안 | `draft-business-plan` | 공식 요구사항이 초안 장·절과 근거 위치에 연결됨 |
| 검토·승인 | `review-business-plan` | BLOCK이 없고 최종 문안과 공개 범위를 사용자가 승인함 |
| HWPX 반영·검사 | `fill-hwpx-template` + `review-business-plan` | 승인값만 반영되고 구조검사와 한글 화면검사가 통과함 |
| 발표자료 | `ppt-editorial` | 승인 원문과 수치가 일치하고 PDF/PPTX·대본·Q&A를 육안 검수함 |

조사 결과가 아이디어의 핵심 가정을 부정하면 앞 단계로 돌아가 사업정보와 전략을 고칩니다.
HWPX 안에서 초안을 쓰지 않으며, HWPX 페이지를 PPT로 그대로 변환하지도 않습니다.
승인된 텍스트를 발표 목적과 시간에 맞춰 압축·재구성해 PPTX를 만듭니다.

## 제공하는 7개 핵심 스킬

| 스킬 | 하는 일 |
| --- | --- |
| `complete-business-plan` | 공고·양식 분석부터 조사·설계·초안·승인·HWPX·발표자료까지 10단계 연결 |
| `setup-business-plan-project` | 원본을 보존하는 범용 폴더와 기본 작업표 생성 |
| `research-business-evidence` | 확인할 내용 하나를 공식 출처 또는 기존 고객 근거로 조사 |
| `draft-business-plan` | 목적·요구사항과 확인된 근거로 선택 항목 초안 작성 |
| `fill-hwpx-template` | 조건부 HWPX 중괄호 치환 또는 수동 매핑 |
| `review-business-plan` | 콘텐츠와 선택 HWPX 산출물을 분리해 검토 |
| `ppt-editorial` | 발표 덱 제작 — 자료 정리 후 씬 덱(텍스트는 코드 렌더) 또는 이미지 퍼스트 중 선택 |

## 독립 `business-documents` 플러그인

| 스킬 | 하는 일 |
| --- | --- |
| `create-business-documents` | 승인된 사실로 견적서·프로필·이력서·공문·안내문을 A4 HTML로 생성하고 사용자가 브라우저에서 PDF로 저장 |

이 스킬은 같은 marketplace에서 `business-documents@dayoun`으로 별도 설치·버전·릴리스합니다. `business-plan-writer` 10단계나 기본 강의 배포판에 포함되지 않으며 한 플러그인의 실패가 다른 플러그인의 릴리스를 막지 않습니다.

```text
create-business-documents 스킬로 이 품목표를 부가세 별도 견적서 HTML로 만들어줘.
공급자 정보 중 비어 있는 값은 만들지 말고 표시만 남겨줘.
```

## 모노레포와 계약 경계

| authored 원본 | generated·배포 표면 |
| --- | --- |
| `contracts/` | 각 ZIP의 immutable `_contracts/` snapshot |
| `plugins/business-plan-writer/` | `business-plan-writer` 독립 ZIP |
| `plugins/business-documents/` | `business-documents` 독립 ZIP |
| `course-src/` + writer의 일곱 스킬 | `course/`와 `business-plan-course-kit` ZIP |
| `tests/` | 공개 플러그인 ZIP에서 제외 |

runtime contract fetch, 저장소 상대경로 조회, 예전 이름 compatibility alias는 사용하지 않습니다. `course/`와 starter의 두 skill directory는 생성물이므로 직접 수정하지 않습니다.

네 산출물은 별도 tag namespace를 씁니다: `contracts/v*`, `business-plan-writer/v*`, `business-documents/v*`, `course-kit/v*`. `python scripts/build_release_artifacts.py --all --health-only --output-dir dist/health`는 전체 건강검사이며 release qualification이 아닙니다. 각 `Promote ...` workflow는 `workflow_dispatch`에서 candidate commit을 먼저 검증하고, target closure·deterministic rebuild·public-artifact smoke·raw-bound 외부 증거·`release_dry_run.py --strict-evidence`·immutable last-verified rollback rehearsal이 모두 PASS한 뒤에만 namespaced tag와 GitHub Release를 생성합니다. Writer qualification은 exact-app digest를 재검증할 수 있는 `self-hosted/Windows/X64/dayoun-rc` runner에서만 실행합니다.

## 발표 덱 만들기 (`ppt-editorial`)

사업계획서를 다 쓰면 발표가 남습니다. 같은 내용을 16:9 슬라이드로 옮기는 스킬입니다.

### 먼저 자료를 정리합니다

바로 그리라고 시키면 다시 그리는 일만 반복됩니다. 네 가지를 먼저 채웁니다.

| 산출물 | 채우는 것 |
| --- | --- |
| `deck_brief.md` | 목적·청중·발표 상황·장수·출력 형식 |
| `content_report.md` | 주장마다 근거 상태 — 사용자 제공 / 출처 확인 / 추정 / **확인 필요** |
| `style_card.md` | 원하는 룩의 레퍼런스에서 뽑은 색·서체·금지 요소 |
| `slide_blueprint.md` | 장별 역할·핵심 메시지·들어갈 문구·사용할 이미지 |

`content_report.md`가 가장 중요합니다. 출처 없는 수치를 슬라이드에 넣으면
발표장 질의응답에서 무너집니다. **추정**과 **확인 필요**는 만들기 전에 되묻습니다.

### 두 가지 방식 중 고릅니다

| | **A. 씬 덱** (기본값) | **B. 이미지 퍼스트** |
| --- | --- | --- |
| AI가 그리는 것 | 배경 그림**만** | 슬라이드 **한 장 전체** |
| 글자 | **코드가 씁니다** — 한글이 안 깨집니다 | 그림 안에 그려집니다 |
| 문구 고치기 | 다시 조립만 — **몇 초** | 그 장을 다시 생성 |
| 결과물 | PDF + 재조립 가능한 PPTX(텍스트 직접 편집 불가) | 이미지 PPTX |
| 어울리는 곳 | 제안서·결과보고·IR·강의 | 콘셉트 제안·비주얼 우선 |

**고르는 기준 한 줄** — 자주 편집할 텍스트·표가 중심이면 **A**, 전달 pixels 자체가 최종 디자인이고 재생성을 감수할 수 있으면 **B**입니다.

두 방식 모두 같은 이미지 생성 엔진을 쓰지만 지원·완료 기준은 같습니다. 이미지 퍼스트도 한글 깨짐을 허용하지 않습니다. 생성 전 canonical payload·ordered deck briefs·stable `text_id`와 normalized region·relation geometry를 가진 visible-text manifest를 한 approval digest에 묶습니다. 렌더 직후 ordered PNG digest receipt를 고정하고, 전달 PPTX와 PDF pixels의 source artifact/page raster digest가 일치하는 OCR만 받아 label/value·evidence/claim 관계까지 검사합니다. 한 글자·수치·날짜·고유명사·clip·tofu·ambiguous region·stale OCR이 다르면 자동 BLOCK입니다.

### 레퍼런스는 역할을 나눠서 줍니다

이미지를 한 덩어리로 주면 안 됩니다. 쓰임이 다르면 처리도 다릅니다.

| 역할 | 예 | 처리 |
| --- | --- | --- |
| 스타일 | 원하는 느낌의 완성 덱 | 색·서체·리듬만 뽑아 씁니다 |
| 제품·공간 | 제품 사진, 매장 내부 | 모양을 그대로 유지해 그립니다 |
| 증거 | 스크린샷, 인증서, 표 | **다시 그리지 않고** 원본을 붙입니다 |

로고·인증서·글자 많은 표를 AI에게 다시 그리게 하면 반드시 깨집니다.

### 발표 덱을 만들기 전에 설치할 것

에이전트에게 **"발표 덱 전제조건 설치해줘"** 라고 하면 아래를 알아서 처리합니다.
직접 하려면 다음 두 줄입니다.

```bash
python -m pip install -r requirements.txt
npm i -g @openai/codex && codex login
```

| 필요한 것 | 왜 | 없으면 |
| --- | --- | --- |
| 파이썬 3.10 이상 | 전체 실행 | 동작 안 함 |
| `pillow` `pymupdf` `numpy` | 이미지 합성·PDF·검사 | 동작 안 함 |
| `python-pptx` | 수정 가능한 PPTX 저장 | PDF만 나옴 |
| `opencv-python` | 사진 자동 크롭 | 사진 슬라이드만 안 됨 |
| **codex CLI** | **배경 그림 생성** | **글자만 있는 덱은 그대로 됩니다** |

codex CLI는 **Claude Code에서 써도 따로 설치해야 합니다.** 배경 그림을 만드는
이미지 생성 엔진을 이 CLI로 부르기 때문입니다. 설치돼 있지 않으면
스킬이 시작할 때 설치 명령을 알려주고 멈춥니다.

그림 없이 글자만으로 덱을 만들 거라면 codex 없이도 끝까지 됩니다.

### 만들고 나서 확인할 것

- 자동 검사는 여백과 화면 비율을 봅니다.
- 오른쪽 3분의 1을 확대해 글자가 잘렸는지 **눈으로** 봅니다.
- 슬라이드의 모든 수치를 원본 파일과 대조합니다.

색은 업종에 맞춰 아홉 가지가 준비돼 있습니다 — 복지·유통·의료·제조·식음료 등.

## 수업에서 사용하는 기본 폴더

```text
00. 시작하기
01. 사업정보
02. 목적 및 요구사항
03. 사업계획서양식
04. 조사자료
05. 작성초안
06. 검토결과
07. 최종본
08. 발표덱
99. 원본백업
```

`setup-business-plan-project` 스킬이 계획프로필과 위 폴더·작업표를 자동으로 만듭니다. `--force`를 사용해도 사용자 수정 파일은 덮어쓰지 않습니다.

## HWPX 선택 트랙 전 확인

- 운영기관이 제출 이후 수정 또는 보완본 제출을 허용했는지 먼저 확인합니다.
- 원본이 `.hwp`라면 한컴오피스에서 먼저 `.hwpx`로 다른 이름 저장합니다.
- 원본 문서는 그대로 보관하고 복사본만 치환합니다.
- 일반 양식에 중괄호가 0개이면 자동치환을 중단하고 `template-field-map.csv`로 수동 매핑합니다.
- 콘텐츠 검토와 사용자 승인이 끝난 값만 HWPX에 반영합니다.
- 자동 검사는 문서 구조와 미치환 항목을 확인합니다. 실제 페이지 배치와 글자 넘침은 한컴오피스에서 마지막으로 확인합니다.
- 데모 파일은 실습용이며 실제 제출 양식이 아닙니다. 출처는 [`PROVENANCE.md`](../../../plugins/business-plan-writer/assets/demo/PROVENANCE.md)에 기록했습니다.

## 직접 내려받아 설치

저장소를 내려받거나 ZIP으로 압축 해제한 뒤 저장소 루트에서 실행합니다.

```powershell
codex plugin marketplace add .
codex plugin add business-plan-writer@dayoun
```

## 교육 자료

- [웹에서 전체 과정 보기](https://lecture-assistant-dayooouns-projects.vercel.app/courses/practice/12-modoo-startup-plan)
- [2시간 커리큘럼](course/02-curriculum-draft.md)
- [수업 전 체크리스트](course/03-preclass-checklist.md)
- [강사 운영 가이드](course/04-instructor-guide.md)
- [참가자 한 장 빠른 시작](course/06-participant-quick-start.md)
- [Codex·Claude Code·Antigravity 공통 사용 안내](course/07-multi-provider-guide.md)
- [설치 없는 스타터 프로젝트](course/starter-project)
- [완성 예시](course/completed-project)
- [인터넷 장애용 오프라인 근거팩](course/offline-evidence-pack)

## 안전 원칙

- 회사 사실, 외부 근거, 가정, 향후 계획을 구분합니다.
- 출처 없는 수치와 확인되지 않은 실적을 만들지 않습니다.
- 개인정보와 영업비밀이 포함된 자료는 공개 저장소에 올리지 않습니다.
- 외부 MCP나 별도 API 키 없이도 핵심 실습을 완주할 수 있게 구성했습니다.

## 버전

현재 공개된 `business-plan-writer`는 `0.9.0`, 새 독립 `business-documents`는 `0.1.0` 개발선입니다. `1.0`은 10개 fixture × 3개 실제 프로바이더, 선택 문서의 자동·외부 화면검수, N≥10 강의 검증, 10명 외부 베타, 중대 결함 0건을 모두 만족하기 전에는 태그하지 않습니다.

## 기여와 문의

오류 제보와 개선 제안은 GitHub Issues로 남겨주세요. 변경 제안은 [CONTRIBUTING.md](CONTRIBUTING.md)를 참고해 주세요. 보안 문제는 [SECURITY.md](SECURITY.md)의 비공개 제보 절차를 이용해 주세요.

## 라이선스

[MIT License](LICENSE)
