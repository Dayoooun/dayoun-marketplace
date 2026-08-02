# deck_brief.md

Use this template to normalize a user's PPT request.

```yaml
deck_id: short-kebab-name
title: ""
purpose: proposal|report|lecture|pitch|briefing|redesign|other
audience: ""
delivery_context: ""
language: ko|en|mixed
slide_count: 10
duration_minutes:
output:
  primary: image-pptx
  secondary: png
must_include:
  - ""
must_avoid:
  - ""
source_materials:
  - path: ""
    role: content|style_reference|product_reference|evidence|logo
assumptions:
  - ""
open_questions:
  - ""
```

Rules:
- Keep it short enough to review quickly.
- Mark assumptions instead of blocking the workflow with too many questions.
- Do not put secrets, API keys, or private credentials in this file.
