# dayoun marketplace

비개발자도 지원사업, 투자·IR, 사내 검토 등 여러 목적의 사업계획서를 공고·양식 분석부터 조사·설계·작성·검토·HWPX 제출본·발표 PPT까지 진행할 수 있게 만든 공개 플러그인입니다.

> 이 저장소는 Dayoun이 운영하는 비공식 오픈소스 marketplace입니다. OpenAI, Anthropic, Google 또는 각 제품사가 운영·인증하는 공식 marketplace가 아닙니다.

기본 스킬은 특정 기관이나 사업에 묶이지 않습니다. 부산대 수업에서는 현재 공식 공고와 평가표를 선택 설정으로 넣어 사용합니다. HWPX 반영은 원본 보존, 사용자 승인, 양식 검증이 확인된 경우에만 선택합니다. 누구나 무료로 설치하고 수정할 수 있도록 MIT 라이선스로 공개합니다.

## 1분 설치

설치할 프로그램에 맞는 한 줄을 고르면 됩니다.

| 사용하는 AI | 설치 방식 | 설치 후 보이는 버전 |
|---|---|---|
| Codex CLI | 터미널에서 marketplace 추가 | `business-plan-writer 0.12.1`, `business-documents 0.1.0` |
| Claude Code | Claude Code의 `/plugin` 명령 | `business-plan-writer 0.12.1`, `business-documents 0.1.0` |
| Antigravity | `course/starter-project` 폴더를 작업공간으로 열기 | `.agents/skills`의 일곱 사업계획서 스킬 |
| 일반 채팅형 AI | 자동 설치 없음 | [참가자 빠른 시작](course/06-participant-quick-start.md)의 질문·출력 형식만 사용 |

### AI에게 설치를 맡기기 — 가장 쉬운 방법

현재 사용 중인 코딩 AI에게 아래 문장을 그대로 붙여넣습니다.

```text
아래 GitHub 저장소를 확인해서 현재 환경에
business-plan-writer와 business-documents 플러그인을 설치해줘.
https://github.com/Dayoooun/dayoun-marketplace
설치 뒤 marketplace와 플러그인을 최신 상태로 업데이트하고 전체 테스트를 실행해줘.
기존 설정과 다른 플러그인은 삭제하거나 덮어쓰지 말고,
마지막에 설치 버전, enabled 상태, 테스트 결과를 요약해줘.
```

AI가 읽을 상세 설치 계약은 [`AGENTS.md`](AGENTS.md)에 있습니다. Claude Code는 [`CLAUDE.md`](CLAUDE.md)에서 같은 문서로 연결됩니다.

### Codex CLI — 복사해서 실행

PowerShell, Windows Terminal, macOS Terminal 중 하나를 열고 실행합니다.

```powershell
codex plugin marketplace add Dayoooun/dayoun-marketplace --ref main
codex plugin add business-plan-writer@dayoun
codex plugin add business-documents@dayoun
codex plugin list
```

마지막 명령에서 아래 두 항목이 `installed, enabled`이면 끝입니다.

```text
business-plan-writer@dayoun  0.12.1
business-documents@dayoun    0.1.0
```

`business-documents`가 필요 없다면 세 번째 줄만 생략할 수 있습니다.

### Claude Code — 네 줄로 설치

Claude Code를 연 뒤 대화 입력창에 한 줄씩 실행합니다.

```text
/plugin marketplace add Dayoooun/dayoun-marketplace
/plugin install business-plan-writer@dayoun
/plugin install business-documents@dayoun
/plugin list
```

목록에서 두 플러그인이 `enabled`이고 버전이 `0.12.1`, `0.1.0`이면 설치가 끝난 것입니다. 새 스킬이 바로 보이지 않으면 Claude Code를 한 번 다시 시작합니다.

터미널 명령을 선호하면 같은 작업을 다음처럼 실행할 수 있습니다.

```powershell
claude plugin marketplace add Dayoooun/dayoun-marketplace
claude plugin install business-plan-writer@dayoun
claude plugin install business-documents@dayoun
claude plugin list
```

### Antigravity — 설치 없는 수업용 시작

Antigravity에는 위 marketplace 명령을 사용하지 않습니다.

1. GitHub 저장소를 ZIP으로 내려받거나 아래 명령으로 복제합니다.
2. 저장소 전체가 아니라 `course/starter-project` 폴더를 Antigravity 작업공간으로 엽니다.
3. Antigravity가 `.agents/skills`를 읽으면 설치가 끝납니다.

```powershell
git clone --depth 1 https://github.com/Dayoooun/dayoun-marketplace.git
cd dayoun-marketplace
```

작업공간 루트에 아래 경로가 보여야 합니다.

```text
course/starter-project/.agents/skills
```

### 설치 후에는 자연어로 지시합니다

스킬 이름이나 10단계를 외울 필요가 없습니다. 결과와 자료, 고정할 조건만 말하면
`complete-business-plan`이 필요한 스킬을 연결하고 작업을 리드합니다.

```text
이 공고와 우리 회사 자료를 보고 평가기준에 맞는 사업계획서를 처음부터 작성해줘.
빠진 근거는 조사하고, 내가 결정해야 할 것만 권장안과 함께 물어봐.
최종 문안이 승인되면 원본 양식을 보존한 HWPX를 전문적으로 디자인하고 검수해줘.
```

```text
이 HWPX를 분석해서 내용은 바꾸지 말고 평가자가 빨리 이해하도록 알아서 보기 좋게 다듬어줘.
브랜드 색은 #0057B8이고, 표·문단·시각자료의 잘림까지 PDF로 확인해줘.
```

에이전트는 지시를 고정 조건으로 기록하고, 이미 있는 자료를 먼저 읽고, 되돌릴 수 있는
분석·조사·디자인은 스스로 진행합니다. 고객·전략·최종 문안·공개범위처럼 결과를 바꾸는
결정만 권장안과 대안을 제시해 확인받습니다. `알아서`는 사실·실적을 만들어도 된다는
뜻이 아니며, 근거 안에서 정보구조와 디자인을 주도하라는 뜻입니다.

### 설치 확인용 첫 요청

설치한 AI에게 아래 요청을 보냅니다. 실제 회사 정보 없이도 스킬 인식 여부를 확인할 수 있습니다.

```text
complete-business-plan 스킬을 사용해줘.
아직 실제 사업계획서는 작성하지 말고,
QUICK 범위에서 필요한 입력자료와 진행 단계만 설명해줘.
확인되지 않은 회사 정보나 실적은 만들지 마.
```

문서 플러그인도 설치했다면 다음 요청으로 확인합니다.

```text
create-business-documents 스킬을 사용해줘.
견적서를 만들기 전에 필요한 공급자 정보와 품목 열만 알려줘.
비어 있는 값은 추측하지 마.
```

## 업데이트

### Codex

```powershell
codex plugin marketplace upgrade dayoun
codex plugin list
```

### Claude Code

```powershell
claude plugin marketplace update dayoun
claude plugin update business-plan-writer@dayoun
claude plugin update business-documents@dayoun
claude plugin list
```

업데이트 후 Claude Code를 다시 시작합니다. 자동 업데이트를 지원하는 호스트도 GitHub에 공개된 marketplace 버전을 기준으로 동작합니다. 로컬에서만 수정한 파일은 GitHub에 커밋·푸시되기 전까지 다른 사용자에게 배포되지 않습니다.

## 설치가 안 될 때

| 증상 | 확인할 것 | 해결 |
|---|---|---|
| `codex` 또는 `claude` 명령을 찾지 못함 | 해당 CLI가 설치되어 있는지 확인 | CLI를 먼저 설치하고 새 터미널에서 다시 실행 |
| marketplace가 이미 있다고 나옴 | 기존 `dayoun` 등록이 있음 | 새로 추가하지 말고 marketplace update/upgrade 실행 |
| 예전 버전이 계속 보임 | marketplace 캐시가 갱신되지 않음 | update/upgrade 후 프로그램 재시작 |
| Claude에서 스킬이 안 보임 | 플러그인이 disabled 상태인지 확인 | `/plugin list` 확인 후 install/update, 재시작 |
| Antigravity에서 스킬이 안 보임 | 연 폴더가 `starter-project`인지 확인 | `.agents/skills`가 바로 아래 보이도록 작업공간을 다시 열기 |
| PPT 생성에서 Python 패키지 오류 | 선택 PPT 기능의 추가 의존성 미설치 | 저장소에서 `python -m pip install -r requirements.txt` 실행 |
| 네트워크 없이 수업해야 함 | marketplace 접근 불가 | `course/starter-project`와 `course/offline-evidence-pack` 사용 |

설치기가 다른 플러그인, 사용자 설정, 작업 파일을 자동으로 삭제해서는 안 됩니다. 인증이나 네트워크 문제는 기존 설치본을 유지한 채 BLOCK으로 보고해야 합니다.

## 가장 쉬운 사용 시작

수업에서는 [`course/starter-project`](course/starter-project)를 작업 폴더로 여는 방법을 권장합니다. `course-src`와 일곱 핵심 스킬에서 자동 생성되며, Codex·Claude Code·Antigravity가 각자의 워크스페이스 경로에서 읽습니다. `business-documents`는 별도 설치하는 독립 플러그인이라 기본 강의 배포판에 들어가지 않습니다.

스킬을 읽을 수 있는 에이전트에서 다음처럼 자연어로 요청합니다.

```text
complete-business-plan 스킬을 사용해 공고문·평가지표·작성지침·양식을 먼저 분석하고,
회사·사업정보와 부족한 근거를 확인한 뒤 승인된 HWPX와 발표 PPT까지 10단계로 진행해줘.
```

공식 자료와 기존 사업정보를 확인한 뒤에도 고객·사용상황·문제가 비어 있을 때만 질문 하나를 합니다. Antigravity와 일반 채팅형 AI를 포함한 차이는 [멀티 프로바이더 안내](course/07-multi-provider-guide.md)에서 확인할 수 있습니다.

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
| HWPX 반영·검사 | `fill-hwpx-template` + `review-business-plan` | 승인값과 위임된 디자인만 반영되고 원본 고정 구조 검사, 실제 PDF·페이지별 PNG, 전체·100%·확대 검수 기록이 모두 PASS |
| 발표자료 | `ppt-editorial` | 승인 원문과 수치가 일치하고 PDF/PPTX·대본·Q&A를 육안 검수함 |

조사 결과가 아이디어의 핵심 가정을 부정하면 앞 단계로 돌아가 사업정보와 전략을 고칩니다.
HWPX 안에서 초안을 쓰지 않으며, HWPX 페이지를 PPT로 그대로 변환하지도 않습니다.
승인된 텍스트를 발표 목적과 시간에 맞춰 압축·재구성해 PPTX를 만듭니다.

시각자료를 사용자가 직접 지정하지 않았더라도 `알아서·전문적으로·보기 좋게`라고 디자인을 위임하면 별도 디자인 승인을 다시 요구하지 않습니다. 에이전트가 근거가 있는 한 가지 권장안을 디자인 결정표에 기록해 작업용 복사본에 적용합니다. 문안·공개범위 승인과 공식 양식 불명확·사용자 지시 충돌만 REAL 확인 게이트로 유지합니다. 위임되지 않은 중대한 시각 선택은 권장안과 대안을 제시해 승인받습니다. HWPX에서는 의미상 위치에 배치하고 원본 고정 구조·중첩표·이미지 참조·쪽 설정과 실제 PDF/PNG 렌더를 재현 검증합니다.

## 제공하는 7개 핵심 스킬

| 스킬 | 하는 일 |
| --- | --- |
| `complete-business-plan` | 공고·양식 분석부터 조사·설계·초안·승인·HWPX·발표자료까지 10단계 연결 |
| `setup-business-plan-project` | 원본을 보존하는 범용 폴더와 기본 작업표 생성 |
| `research-business-evidence` | 확인할 내용 하나를 공식 출처 또는 기존 고객 근거로 조사 |
| `draft-business-plan` | 목적·요구사항과 확인된 근거로 선택 항목 초안 작성 |
| `fill-hwpx-template` | 조건부 HWPX 치환·수동 매핑, 의미상 시각자료 배치와 `secPr`·이미지 참조 검증 |
| `review-business-plan` | 콘텐츠와 선택 HWPX 산출물을 분리해 검토 |
| `ppt-editorial` | 씬 덱·이미지 퍼스트, FLOW·GENEALOGY·PROMPT 포함 정보 구도 7종, 대본·Q&A |

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

씬 덱의 정보 구도는 `TABLE`, `EXAMPLE`, `MATRIX`, `BAR`, `FLOW`, `GENEALOGY`, `PROMPT` 7종입니다. 복잡한 순서는 FLOW, 개념 계보는 GENEALOGY, 복사용 요청문은 PROMPT로 렌더합니다. 긴 표는 footer와 겹치기 전에 나누고 투사용 본문 크기를 고정할 수 있습니다. 생성 장면의 모든 화면·카드·버튼·연결선은 상하좌우 18%를 비운 중앙 64% 안에 들어와야 합니다.

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
`00. 시작하기/단계상태.json`과 `advance_stage.py`가 10단계를 순서대로 강제합니다. 앞 단계가 PASS 또는 선택 단계의 NOT_REQUESTED가 아니면 다음 단계가 BLOCK되고, PASS에는 프로젝트 내부의 실제 evidence 파일이 필요합니다. 업로드·강의시연·고객 원본 폴더는 읽기 전용으로 두고 그 안에 파일이나 폴더를 만들지 않습니다.
검증·강의시연은 `DEMO`, 실제 신청서는 `REAL`로 시작합니다. REAL 모드에서는 질문 확인, 전략 선택, 문안 승인, HWPX/PPT 선택을 사용자와 함께 결정하고 `사용자협업상태.json`에 사용자 원문을 기록해야만 다음 gate가 열립니다. 에이전트가 스스로 답을 만들어 승인으로 대체할 수 없습니다.
DEMO/PARTIAL은 승인·선택을 합성하지 않으므로 7단계를 BLOCK으로 기록하고 8~10단계로 진행하지 않습니다. evidence는 해당 단계 산출 폴더의 새 파일만 허용하며 디렉터리, 다른 단계 파일, 재사용 파일은 거부합니다.

## HWPX 선택 트랙 전 확인

- 운영기관이 제출 이후 수정 또는 보완본 제출을 허용했는지 먼저 확인합니다.
- 원본이 `.hwp`라면 한컴오피스에서 먼저 `.hwpx`로 다른 이름 저장합니다.
- 원본 문서는 그대로 보관하고 복사본만 치환합니다.
- 일반 양식에 중괄호가 0개이면 자동치환을 중단하고 `template-field-map.csv`로 수동 매핑합니다.
- 콘텐츠 검토와 사용자 승인이 끝난 값만 HWPX에 반영합니다.
- 시각자료는 승인된 `앞 문단 / 뒤 문단` 사이에 놓고 답변 셀 마지막 일괄 배치를 금지합니다.
- 한글 호환 구조는 `tc → subList → p → run → tbl`의 1열 2행 중첩표입니다.
- 캡션은 `그림 N. 핵심 그림명`으로 짧게 쓰고 가운데 정렬합니다.
- 이미지 `binaryItemIDRef`, `Contents/content.hpf`, 실제 `BinData` 파일이 일치해야 합니다.
- 원본과 결과의 `secPr` canonical digest를 비교해 쪽 크기와 여백을 보존합니다.
- 자동 검사는 문서 구조·미치환 항목·시각자료 위치·중첩표·이미지 참조·쪽 설정을 확인합니다. 실제 문맥 위치·비율·페이지 배치는 한컴오피스에서 마지막으로 확인합니다.
- 데모 파일은 실습용이며 실제 제출 양식이 아닙니다. 출처는 [`PROVENANCE.md`](plugins/business-plan-writer/assets/demo/PROVENANCE.md)에 기록했습니다.

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

현재 `main` marketplace의 공개 RC는 `business-plan-writer 0.12.1`, `business-documents 0.1.0`입니다. Codex와 Claude Code의 원격 설치를 실제 검증했습니다. stable `1.0`은 10개 fixture × 3개 실제 프로바이더, 선택 문서의 자동·외부 화면검수, N≥10 강의 검증, 10명 외부 베타, 중대 결함 0건을 모두 만족하기 전에는 태그하지 않습니다.

## 기여와 문의

오류 제보와 개선 제안은 GitHub Issues로 남겨주세요. 변경 제안은 [CONTRIBUTING.md](CONTRIBUTING.md)를 참고해 주세요. 보안 문제는 [SECURITY.md](SECURITY.md)의 비공개 제보 절차를 이용해 주세요.

## 라이선스

[MIT License](LICENSE)
