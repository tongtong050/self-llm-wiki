---
name: wiki-query
description: Query the knowledge graph and synthesize a cited answer from wiki pages
---

## Step 1: Read hot.md
Read `06-Wiki/hot.md` for recent context.

## Step 2: Intent classification (REQUIRED — classify before ANY search)
| Intent | Definition | Action |
|---|---|---|
| `chitchat` | Greetings, casual talk | Reply directly. Skip all remaining steps. |
| `fact_lookup` | Specific fact, name, procedure | Search 1–3 most relevant pages via index.md |
| `summary` | "有哪些"/"总结"/"概述" | Read overview.md + index.md + 3–5 recent sources |
| `relationship` | "为什么"/"导致"/"影响"/"关联" | Search via index.md + expand by graph |
| `deep_analysis` | "综合分析"/"全面评估" | Broad search + graph + multi-round |

## Step 3: Search via index.md
Read `06-Wiki/index.md` FIRST. Only after reading index.md, use Grep to supplement. Do NOT start with Grep.

## Step 4: Retrieve matching pages
Read identified pages. Clip each at 3000 characters. If `relationship` or `deep_analysis`, expand by graph neighbors from `06-Wiki/graph/graph.json`.

## Step 5: Synthesize answer
Answer with `[[PageName]]` wikilink citations. Include `## 来源` section.

## Step 6: Offer to save (REQUIRED — NEVER SKIP)
End every query answer with:
"需要将此回答保存到 `06-Wiki/syntheses/` 吗？（回复 /save 或 保存）"

If user replies `/save` or "保存":
- Write answer to `06-Wiki/syntheses/<slug>.md`
- Add to index.md under `## Syntheses`
- Update log.md and hot.md
