---
name: wiki-review
description: Process pending review items from review.md
---

Trigger: trigger file with `action: review`, `/wiki-review`, or "确认 review".

1. Read `07-系统/review.md`.
2. Find all `[x]` checked items.
3. Process each checked item by type:
   - `collision` type → turn the insight into a **new inspiration** (type: inspiration, status: pending) written to `00-灵感库/` — it re-enters the expand→card→ingest pipeline.
   - Other types (missing-page / duplicate / suggestion / uncertain) → create or merge wiki pages as appropriate.
   - Unchecked items → skip.
4. Move processed items to the `## 已处理` section at the bottom of review.md.
5. Update `06-Wiki/log.md` and `06-Wiki/hot.md`.
