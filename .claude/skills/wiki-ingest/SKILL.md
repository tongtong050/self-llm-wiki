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

## Step 6: Analyze and generate (LLM via ingest.py)
Run `python tools/ingest.py --source <source_path>` to perform the LLM analysis and generate ALL wiki pages. `ingest.py` handles the full generation pipeline:
- Source summary page → `06-Wiki/sources/<中文标题>.md`（**用中文标题作为文件名**，保留中文字符，仅将空格和非法文件名字符替换为连字符）
- Concept pages → `06-Wiki/concepts/<中文概念名>.md`
- Entity pages → `06-Wiki/entities/<中文实体名>.md`
- Overview update content (or null)
- Contradictions list (or empty)
- Review items list (or empty)
- Log entry string

**CRITICAL: aggressively convert concepts/entities/persons/works/tools into `[[wikilinks]]` inline.
CRITICAL: page filenames MUST use Chinese titles (e.g. `人工智能聚类.md`, NOT pinyin like `ai-zhi-neng-ju-lei.md`).** `ingest.py` has a `safe_name()` sanitizer that preserves CJK characters.

## Step 7: Check and merge page conflicts
For each entity/concept page: if it already exists, Read existing + new content, merge keeping ALL facts from both. Mark contradictions with `> [!conflict]`. If near-identical, skip.
(Note: `ingest.py` handles step 7 merge detection automatically via difflib comparison.)

## Steps 8-12: handled automatically by ingest.py
The script handles writing pages (with locks), updating aggregates (index/overview/log), writing reviews, updating hot.md, marking the source complete (`wiki: true`), and updating the cache. After running `ingest.py`, read its printed summary to confirm results (template used, pages created/updated, merge count, review count, contradictions).

**Do NOT manually re-execute steps 8-12** — `ingest.py` already performed them.

## Failure recovery
If any step fails, revert source frontmatter `wiki: processing` back to `queued`. Keep trigger file for retry.
