---
name: wiki-collide
description: Run concept collision detection and generate cross-concept insights
---

Trigger: trigger file with `action: collide`.

1. Run `python tools/collide.py` (finds candidate concept pairs in the sweet spot [0.6, 0.75] by tags/sources/related overlap, writes `07-系统/.collision-candidates.json`).
2. Read `07-系统/.collision-candidates.json` for the `candidates` list.
3. For each candidate pair (a, b): Read both concept pages. Judge whether this collision genuinely yields a cross-concept insight (skip if not — don't force connections).
4. For valuable pairs: generate a "new insight" — a novel connection or question emerging from these two concepts colliding. Approach with a creative perspective (temperature 0.7 thinking).
5. Append valuable insights to `07-系统/review.md` in this format:
   ```
   - [ ] [collision] 「ConceptA」× 「ConceptB」（similarity 0.68）
          insight: <cross-concept connection>
          → check to create new inspiration in 00-灵感库 (re-enter the inspiration→expand→card pipeline)
   ```
6. Move processed candidate pairs into `.collision-candidates.json` `processed` list (incremental — don't regenerate insights for already-processed pairs).
7. Append one line to `07-系统/pipeline-log.md` (`## [YYYY-MM-DD] collide | N candidates → M insights`).

## Insight reflow convention
When the user checks a `[collision]` item in review.md and processes it through the Review Confirmation Workflow, the insight becomes a **new inspiration** (type: inspiration, status: pending) written to `00-灵感库/`, NOT a card directly — it should re-enter the full digestion pipeline (expand → card → ingest).
