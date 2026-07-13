---
name: wiki-ingest
description: Ingest a knowledge card into the LLM Wiki — extract concepts, entities, and cross-links
---

Trigger: trigger file with `action: ingest`, `/wiki-ingest <file>`, or "ingest <file>". source = card path (01-项目/02-长期关注, type: card).

## Step 1: Mark as processing
Edit source card frontmatter: set `wiki: processing`. Do NOT modify body.

## Step 2: Read source
Read the full source card.

## Step 3: Read wiki context
Read `06-Wiki/hot.md`, `06-Wiki/index.md`, `06-Wiki/overview.md`.

## Step 4: Identify template
From frontmatter `type` or parent directory: card → Card, inspiration → Inspiration, reference → Reference, else General. State which template.

## Step 5: Check cache
Read `07-系统/.ingest-cache.json`. If source hash unchanged, skip: "该素材已 ingest，内容未变更。force 可强制重跑".

## Step 6: Analyze and generate (LLM)
Analyze per template. Generate ALL of:
- Source summary page → `06-Wiki/sources/<slug>.md`
- Concept pages → `06-Wiki/concepts/`
- Entity pages → `06-Wiki/entities/`
- Overview update content (or null)
- Contradictions list (or empty)
- Review items list (or empty)
- Log entry string

**CRITICAL: Aggressively convert concepts/entities/persons/works/tools into `[[wikilinks]]` inline.**

## Step 7: Check and merge page conflicts
For each entity/concept page: if it already exists, Read existing + new content, merge keeping ALL facts from both. Mark contradictions with `> [!conflict]`. If near-identical, skip.

## Step 8: Write all wiki pages (with locks)
Write each page to `06-Wiki/{sources,entities,concepts}/`. Use safe_write: check `.lock` first (<60s wait 2s, >60s delete stale lock). Remove `.lock` after write.

## Step 9: Update aggregates
- Update `06-Wiki/index.md`: add entries for all new pages under Sources/Entities/Concepts
- Update `06-Wiki/overview.md`: if changes warranted
- Append to `06-Wiki/log.md`: format `## [YYYY-MM-DD] ingest | <Title>`

## Step 10: Write reviews
Append review items to `07-系统/review.md`. If General template used, add `uncertain` review item.

## Step 11: Update hot.md
Overwrite `06-Wiki/hot.md` (recent operations, key entities/concepts, <500 words).

## Step 12: Mark complete and update cache
- Set source frontmatter: `wiki: true` + `last_wiki_update: YYYY-MM-DD`. Do NOT modify body.
- Update `07-系统/.ingest-cache.json` with source hash.
- Append one line to `07-系统/pipeline-log.md`.
- Print summary: template used, pages created/updated, merge count, review count, contradictions.

## Failure recovery
If any step fails, revert source frontmatter `wiki: processing` back to `queued`. Keep trigger file for retry.
