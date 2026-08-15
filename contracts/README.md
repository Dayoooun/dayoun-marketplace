# Dayoun contracts

`contracts/`가 네 산출물의 authored single source입니다. 각 공개 ZIP은 필요한 schema와 policy를 `_contracts/`에 복사하며 runtime fetch나 저장소 상대경로 조회를 하지 않습니다.

## Canonical payload

`schemas/canonical.schema.json`은 사실·근거·요구사항·결정·사업 판정·범위·선택 산출물을 분리합니다. `contentSteps`는 `policies/scope-steps.json`에서 선택 범위에 필요한 단계만 `PASS`로 기록하고 근거 ID를 가져야 합니다. 범위 밖 단계는 포함한다면 `NOT_REVIEWED`, 선택하지 않은 HWPX·PPT는 validation record에서 `NOT_REQUESTED`입니다.

- `QUICK`: 공백진단, 근거기록, 변화기록, 실행카드
- `SECTION`: 공식 요구, 사업 사실, 근거 조사, 선택 절 초안·검토·승인
- `FULL`: 일곱 core content skill
- HWPX와 PPT는 독립 boolean입니다. PPT를 선택할 때만 `scene-deck` 또는 `image-first`를 고릅니다.

## Approval tuple

`approval-envelope.schema.json`은 RFC 8785 JCS + SHA-256으로 canonical payload, ordered deck briefs, visible-text manifest, renderer/normalizer/mapper versions를 묶습니다. Renderer와 validator는 loose 입력 경로 대신 content-addressed store의 approval digest를 받습니다. tuple 구성요소가 바뀌면 `STALE_APPROVAL`입니다.

Image-first의 manifest는 각 표시 문구의 stable `textId`, occurrence, normalized region과 label/value·evidence/claim 관계를 고정합니다. 전달 PPTX와 PDF pixels의 OCR evidence는 `ocr-evidence.schema.json`을 따릅니다.

## Independent validation

Writer 공개 ZIP의 `validators/`에는 fact, structure, contract 세 검증자와 strict aggregator가 있습니다. 세 검증자는 같은 payload digest를 독립 판정하고 선택 산출물의 automation·external visual 결과와 함께 집계됩니다. 하나라도 BLOCK이면 PASS가 아니며 두 번째 실패는 `REJECTED`입니다. 사람이나 다른 검증자가 실패를 덮을 수 없습니다.

## Release evidence

`policies/release-gates.json`은 실제 provider 30회, N≥10 강의, ITT 외부 베타 10명, C1–C6, exact Windows visual baseline을 고정합니다. 로컬 자동 테스트는 이 외부 증거를 대신하지 않습니다.
