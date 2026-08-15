# deck_brief.md

Use this template to normalize a user's PPT request.

```json
{
  "deck_id": "short-kebab-name",
  "title": "",
  "purpose": "",
  "audience": "",
  "delivery_context": "",
  "language": "ko",
  "slide_count": null,
  "duration_minutes": null,
  "mode": "auto",
  "editable_text_required": false,
  "flattened_pptx_accepted": false,
  "requirements_confirmed": false,
  "output": {
    "primary": "pptx",
    "secondary": "pdf"
  },
  "must_include": [],
  "must_avoid": [],
  "identity_anchors": null,
  "source_materials": null,
  "assumptions": [],
  "open_questions": []
}
```

Rules:
- Keep it short enough to review quickly.
- Ask only missing essentials, at most three questions in one round.
- Before confirmation, show purpose, audience, recommended mode/page range, narrative spine, identity anchors, and assumptions.
- Set `requirements_confirmed: true` only after the user confirms or corrects that baseline.
- Any later requirement correction invalidates the earlier confirmation.
- Mark assumptions instead of blocking the workflow with too many questions.
- An empty `source_materials` or `identity_anchors` list is valid only when the user explicitly said there are none.
- Do not put secrets, API keys, or private credentials in this file.
- `purpose` choices: `proposal`, `report`, `lecture`, `pitch`, `briefing`, `redesign`, `other`.
- `mode` choices: `auto`, `scene-deck`, `image-first`.
- `source_materials` roles: `content`, `style_reference`, `product_reference`, `evidence`, `logo`.
