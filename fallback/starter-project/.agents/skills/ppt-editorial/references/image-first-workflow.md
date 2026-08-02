# Workflow

## Stage 1 — Intake and baseline judgment

Goal: understand what the deck is for without over-questioning.

Collect only the essentials:
- what the PPT is for
- who the audience is
- rough length or duration
- what materials already exist
- whether there are concrete identity anchors such as school, company, laboratory, research group, course, product line, or brand entity that should ground the deck

When giving example choices in the first intake round, use broad common examples.
Recommended examples:
- purpose: 발표 / 로드쇼 / 발표심사 / 제품 소개 / 교육 / 회고 / 방안 제안
- audience: 상사 / 고객 / 투자자 / 교수 / 동료 / 심사위원

Do not require the user to specify the desired overall tone in the first intake round.
If they volunteer it, you can use it.
If they do not, continue and surface style direction later in the dedicated style stage.

Then output a short baseline judgment:
- deck goal
- target audience
- recommended deck type
- recommended page range
- narrative spine
- usable identity anchors
- missing critical information

### Confirmation point 1 — 요구사항 확인
Stop and let the user confirm or correct the baseline judgment.

---

## Stage 1.25 — Pre-style content research and report basis

After `요구사항 확인` and before style-boundary alignment, create a content basis for the deck.

This stage should be the default rather than an exception.
Only compress it into extraction-only mode when the user has already provided a complete report, paper, project document, experiment record, full outline, or another complete narrative that is already strong enough to support page planning.

Use this stage to decide whether the work is:
- `정리하되 확장하지 않음` — when the user already provided strong report-like content
- `보강하여 보고서화 생성` — when the user only provided a topic, thin materials, partial materials, or scattered notes

Goal:
- create an upstream content basis before style work
- make later `표지 / 목차 페이지 / 본문 페이지` previews content-bearing rather than generic
- give `design_spec.md`, `slide_blueprint.md`, and `spec_lock.md` a grounded content source
- avoid empty topic shells, placeholder logic, and shallow page planning

Output:
- the default artifact is `content_report.md`
- write it as a small research-style report / report-like article rather than a short outline
- if the user already provided a complete narrative, compress the work into extraction and structuring instead of extra expansion
- show the user a synthesized judgment by default instead of dumping the full report immediately

The content report should include:
- source status and material status
- problem background / topic framing
- core problem or core objective
- narrative body with connected reasoning rather than only bullets
- section candidates and page-content candidates
- visualizable content candidates
- claim status and open questions

Rules:
- do not turn this stage into a long questionnaire
- at most give one lightweight supplement opening
- distinguish `user_provided`, `inferred`, and `needs_confirmation`
- do not invent precise data, experimental results, citations, rankings, or institutional conclusions without support
- even if the user says not to expand content, still run this stage as extraction/structuring rather than skipping the content basis entirely
- later previews should use this content basis rather than a fresh generic topic outline

---

## Stage 1.5 — Style-boundary alignment

After `요구사항 확인` and after any needed content-basis step, run one short style-boundary alignment step.

Ask only these 3 short questions in this stage:
1. `전체적으로 밝은 계열, 어두운 계열, 중간 계열 중 어느 쪽인가요?`
2. `이번 PPT는 일반 전문 노선으로 갈까요, 아니면 확연한 스타일리시 디자인 노선도 괜찮으신가요?`
3. `이번에 먼저 몇 가지 스타일 방향 프리뷰를 보고 싶으신가요?`

Show this helper note together with question 2:
`특별한 선호가 없으시면 기본값인 "일반 전문 노선"을 선택하시면 됩니다. 더 강한 디자인 감각을 원하실 때만 "확연한 스타일리시 노선"을 선택하세요.`

Show this helper note together with question 3:
`기본값은 3가지를 먼저 보는 것을 권장합니다. 빠르게 방향을 좁히고 싶다면 적게, 더 많은 방향을 보고 싶다면 늘릴 수 있습니다.`

Rules for this step:
- keep it short
- do not expand into a design questionnaire
- do not ask raw V1-V8 questions
- do not branch into subtype follow-up questions if the user allows the stylized route
- use the answers as boundary conditions for later style proposals rather than as a complete style definition
- if the user does not express a clear preference for question 2, default to `일반 전문 노선`
- if the user gives no clear answer on brightness, infer a middle brightness tendency unless the deck context strongly suggests otherwise
- if the user gives no clear answer on preview-count, default to `3` directions

---

## Stage 2 — Style proposal

Once the request direction is confirmed:
- derive style vectors internally
- use the existing content basis as the source for preview content; if `content_report.md` exists, do not replace it with a fresh generic topic outline
- propose the user-requested number of style directions as lightweight proposal cards
- if the user gave no clear count, propose `3` directions by default
- generate previews for each direction
- place the proposal cards and preview images into the bundled `assets/preview_shell/index.html` shell
- do not create a replacement preview shell, a lookalike HTML page, or a fresh preview UI from scratch
- immediately attempt to open the local preview HTML for the user
- only fall back to giving the file path if the open action fails, and explain the blocker
- show the proposals together with their previews before asking for final selection

Each proposal must include:
- proposal name
- one-line positioning
- cover direction
- body-page visual grammar
- suitable scenarios
- risk note

Each proposal must also include exactly 3 previews:
- 표지 — checks first-impression and visual tone
- 목차 페이지 — checks structural capability
- 본문 페이지 — checks information-carrying capability

Those previews must be content-bearing enough to evaluate.
Do not treat empty shells, placeholder copy, or mostly blank UI scaffolds as acceptable preview outputs.
If `content_report.md` or another content basis summary exists, the preview set should draw from it directly: cover positioning from the thesis, TOC structure from the narrative chain, and body-page content from the section/page candidates rather than from generic placeholder topic logic.

## Stage 2.5 — Style refinement

If the user is not ready to confirm a final direction yet, enter a style refinement round before `스타일 확인`.

In each refinement round:
- let the user choose one current direction as the base direction
- before deriving more options from that base, run one short refinement-time style inversion pass on that base direction
- in that pass, read the chosen `표지 / 목차 페이지 / 본문 페이지` together with the original prompt and summarize what this direction actually became in the generated images
- surface which parts appear stable and suitable to inherit into the next round, and which parts may be one-off effects
- let the user say what they want adjusted on top of that now-clarified base
- derive another user-requested number of candidate directions from that base
- if the user gives no clear count for the refinement round, default to `3` derived directions
- regenerate the same `표지 / 목차 페이지 / 본문 페이지` preview set for each derived direction

During refinement, proactively give a few lightweight tweak prompts to help the user think, such as:
- `대비를 조금 더 높게`
- `색상을 더 선명하게`
- `더 절제되게`
- `더 고급스럽게`
- `정보감을 더 강하게`
- `화면을 더 가볍게`
- `텍스트 위주인지, 이미지 위주인지`

Do not turn these prompts into a rigid option list.
Use them as guidance cues so the user can react in natural language.

Repeat refinement rounds until the user is ready to confirm one final direction.

When presenting a refinement round result, explicitly remind the user that there are 2 valid next paths:
- `특정 방향을 기반으로 한 번 더 추진`
- `현재 방향 중 하나로 스타일 단계를 종료하고 이후 확정 및 생성 단계로 진입`
Do not phrase the result as if the only next step is immediate final selection.

### Confirmation point 2 — 스타일 확인
Stop and let the user choose, mix, or revise the style direction.

---

## Stage 2.75 — Style inversion confirmation

After `스타일 확인` and before writing any planning files, run one short `스타일 역검증 확인` stage.

In this stage:
- read the chosen `표지 / 목차 페이지 / 본문 페이지` as visual evidence rather than treating the original prompt text as the whole truth
- compare the actual images with the original generation prompt and identify what the model really produced
- extract stable repeated style facts such as brightness range, palette role usage, material feel, lighting/depth behavior, container grammar, edge treatment, decoration grammar, information density, text-image balance, and overall restraint level
- also extract theme-specific or scene-specific liked elements that may matter to the user, such as school emblems, campus buildings, company marks, laboratory context, domain imagery, clouds, devices, chart language, or other subject anchors
- distinguish between what appears consistently across the preview set and what only works as a one-off local flourish

When reporting the inversion result to the user:
- do not ask an open-ended style interview
- first present a short structured judgment in 3 groups:
  - `명확히 이어가야 할 것`
  - `효과는 좋지만 전체 적용 여부를 확인해야 할 것`
  - `현재 이미지에서만 우연히 성립한 것으로 고정하지 않을 것`
- then let the user confirm, remove, or promote items between those groups
- if the user gives no correction, keep the first group by default and do not automatically hard-lock the second group

Rules:
- trust the confirmed preview evidence more than the raw prompt wording when they differ
- only lock features that are either visually stable across the selected previews or explicitly confirmed by the user
- do not mistake rendering accidents, one-off decorations, typo-like artifacts, or isolated composition tricks for deck-level style facts
- use the confirmed inversion result to make the later planning files more concrete than the original prompt alone could support

## Stage 3 — Planning files

Do not enter this stage while style refinement is still active.
Do not enter this stage before `스타일 역검증 확인` is finished.
After the style is confirmed and the inversion result is confirmed, generate the 3 planning artifacts in this exact order:
1. `design_spec.md`
2. `slide_blueprint.md`
3. `spec_lock.md`

Then output a short pre-generation summary instead of dumping all files.

The summary should cover:
- project overview
- chosen style result
- deck-level continuity anchor
- page structure summary
- execution readiness

### Confirmation point 3 — 생성 전 확인
Stop and let the user confirm whether generation can start.

---

## Stage 4 — Generation

Only after the 3rd confirmation point may you proceed into downstream generation.

Before the first full generation pass, ask one short branch question:
- `최종 페이지는 이번에 슬라이드당 1장을 바로 검토하는 방식으로 할까요, 아니면 슬라이드당 여러 후보를 먼저 뽑아 선택하는 방식으로 할까요?`

Rules for this branch:
- keep it short and operational
- if the user wants the multi-candidate path, also ask how many candidates per slide they want
- if the user chooses the single-candidate path, skip the candidate-picker stage entirely
- if the user gives no clear preference, default to one final image per slide and go directly into review

Generation in this skill should stay image-first.
That means:
- when image generation is available, use an available image-generation toolchain from the environment such as a tool, MCP server, or skill to produce the page visuals
- do not silently fall back to a traditional element-by-element PPT workflow as the main rendering path when image generation is available
- do not skip image generation and directly assemble the final deck only from default PPT shapes, text boxes, layout primitives, custom-drawn vectors, SVG-like code, or programmatic page reconstruction unless the user explicitly asks for that approach
- if the confirmed direction depends on generated page visuals, actually generate those visuals and use them in the final deck
- do not hand-build substitute page art yourself with code just because it is easier or more controllable than calling the image-generation path
- do not silently switch to textless or background-only generated images just to avoid rendering text problems
- if you choose to keep PPT text editable while using generated visuals, that must still preserve the confirmed style direction and must not collapse into generic background art plus ordinary default slides
- treat generated page visuals as complete outputs by default, not as underlays for a second design pass
- post-generation overlays should default to zero
- do not treat generated images as mere background plates and then invent a second layer of titles, metrics, bullets, labels, callouts, captions, badges, or decorative elements on top unless those overlay contents were already defined by the confirmed content plan and are explicitly traceable to approved blueprint fields
- do not add self-authored editable copy just because the generated page looks sparse or because editable text feels safer
- do not add explanatory boxes, correction notes, patch text, or rescue text to compensate for weak generation output; fix the generation path instead
- when editable overlays are necessary, they should come from the approved slide content and should be used to realize the confirmed page, not to redesign it after the fact
- if image generation quality, text rendering limits, or tooling constraints force a tradeoff, tell the user explicitly before changing generation strategy

The final generation should remain faithful to the confirmed preview logic rather than drifting into a different production method.
Unless the user explicitly requests another presentation ratio, generate preview images and final page visuals in `16:9`.
Do not let the image-generation path default to a generic art ratio such as `3:2`.

If the user chose single-candidate generation:
- generate one final image per slide
- skip the candidate-picker stage
- move directly into the review HTML stage

If the user chose multi-candidate generation:
- generate the requested number of final candidates for each slide using the same approved page prompt for that slide
- keep the variation inside one approved page direction rather than treating the candidates as new style proposals
- assemble the bundled `assets/candidate_picker_shell/index.html`
- immediately attempt to open that local candidate-picker HTML for the user
- tell the user to finish the selection in the page and click `전체 번호 복사`
- tell the user concretely to return to the chat input, paste the copied codes, and send them
- wait for the returned selection codes before entering the review HTML stage
- once the codes arrive, map them to the selected page images and use that chosen set as the review input

Before writing per-slide generation prompts, extract the confirmed direction into one explicit deck-level continuity anchor.
Every slide prompt must inherit that anchor first, then add only page-role and content-specific variation.
Do not write slide prompts as independent style descriptions.
If one slide would naturally become darker, brighter, flatter, glossier, or more atmospheric than the rest, explicitly test that change against the allowed variation range before keeping it.

Prompt assembly metadata isolation:
- maintain slide IDs, candidate codes, filenames, and generation batch labels in a separate mapping table or local variables
- do not concatenate those identifiers into the text prompt sent to the image model
- do not format per-slide prompt bodies with production headers; use a separate executor-side label for logs and filenames
- the prompt body should contain only the approved audience-facing slide content, page role, visual direction, continuity anchor, layout intent, and any visible labels that should actually appear in the slide
- after generation, reconnect outputs to slide IDs through filenames or the external mapping table, not through text embedded in the image prompt

### Confirmation point 4 — 초안 검토 및 수정
Do not jump directly from first-pass page generation to final delivery.
After the first full set of page visuals exists, enter a dedicated review-and-retouch loop.

---

## Stage 5 — Review and retouch

After the first full set of page visuals is ready:
- assemble the review page from the bundled `assets/review_shell/index.html` shell
- do not create a replacement review shell, a lookalike HTML page, or a fresh review UI from scratch
- immediately attempt to open that local review HTML for the user
- treat that HTML as the main review surface instead of using the live PPT as the collaboration surface by default
- only fall back to a file path when the open action fails, and explain the blocker

When you present the review stage to the user, explicitly tell them:
- if the current result is satisfactory, they can say it is approved and the review stage can end
- if the current result is not satisfactory, they should use the review page's `현재 페이지 결과 복사` or `전체 페이지 결과 복사` button
- after clicking copy, they should return to the chat input box, paste the copied JSON into the input field, and send it
- do not merely say `paste the JSON`; tell them concretely how to do it in one short sentence

In the review HTML:
- show every generated slide image
- keep page order visible
- support per-page review comments
- when the environment supports it, prefer visual annotations such as brush marks, boxes, arrows, or highlighted regions in addition to text comments
- preserve enough context that the agent can understand both the page and the marked region together
- copy lightweight `review-shell-v2` JSON with normalized coordinate markup for notes, rectangles, and pen strokes
- do not include base64 images, data URLs, or full annotated preview images in the copied review JSON

When the user pastes `review-shell-v2` feedback:
- save the pasted JSON to a local file such as `review_feedback.json`
- run `python scripts/render_review_markup.py review_feedback.json --images <generated-page-image-directory> --out <marked-review-directory>`
- use the rendered marked images plus separate page comments and note comments as the reference for retouching or regenerating pages
- do not bake textual comments into the marked image by default; pass text feedback separately alongside the marked image when calling the image edit/regeneration model
- do not skip the local marked-image restoration step and rely only on raw coordinate text when visual markup is present
- if source images cannot be found automatically, create an image-map JSON from page IDs to local image paths and rerun the same script with `--image-map`

When the user gives review feedback, classify it before acting:
- `전체 페이지 재생성` → use when the user wants broader changes to composition, hierarchy, page concept, style intensity, or overall mood
- `부분 이미지 편집` → use when the user wants targeted changes to a specific region, background element, rendered text area, spacing, emphasis object, or small visual detail
- `콘텐츠/블루프린트 이슈` → use when the user is actually changing approved content, narrative structure, or page intent rather than only changing the rendered page

Execution rules:
- prefer an available image-editing path from the environment for local image edits
- prefer full-page regeneration for broad or structural dissatisfaction instead of forcing many small edits
- do not solve review feedback by adding unapproved PPT overlays
- do not treat the PPT file itself as the fast-turnaround retouch surface unless the user explicitly asks for that workflow
- if the requested revision would change approved content rather than only visuals, surface that explicitly before editing
- after each retouch round, update the review HTML, open it again, and repeat the same instruction about approving or copying JSON back into the chat input
- repeat the review-and-retouch round until the user confirms that the pages are ready for final delivery
- do not export the final PPT before that approval
- once the user approves the reviewed pages, export the final PPT and immediately attempt to open it for them

## Important rules

- Do not write the planning files before the style direction is confirmed.
- Do not turn the interaction into a parameter form.
- Do not ask for repeated approval inside a stage.
- Keep the first confirmation quick, the second heavy, the third short, and the final review stage iterative.
