---
name: wiki-expand
description: Expand an inspiration into a draft knowledge card using AI
---

Trigger: trigger file with `action: expand`. Params: source (inspiration path), target_dir (01-项目 or 02-长期关注).

1. Read the inspiration source file (`00-灵感库/` + source) and its frontmatter (source type, tags).
2. Read `06-Wiki/hot.md` to get context from existing related concepts.
3. Using the Card template, expand the inspiration into a **draft card**:
   - Extract a core claim/thesis
   - Add supporting reasoning
   - Actively add `[[wikilinks]]` for concepts, entities, or related cards
   - Frontmatter: `type: card`, `source_ref: [<inspiration path>]`, `tags`, `created: YYYY-MM-DD`
   - **Do NOT set a `wiki` field** — the user reviews and manually triggers ingest later
4. Write the draft card to `<target_dir>/<slug>.md`.
5. Edit the original inspiration frontmatter: `status: carded` + `card_ref: <card path>`.
6. Append one line to `07-系统/pipeline-log.md` (`## [YYYY-MM-DD] expand | <inspiration first line> → <card path>`).
7. Report to user: draft card created, please review in Dashboard and trigger ingest.
