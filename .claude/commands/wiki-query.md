---
name: wiki-query
description: Query the LLM Wiki and synthesize an answer
---

Take $ARGUMENTS as the user's question. Follow the Query Workflow in the project's CLAUDE.md exactly:
- Read hot.md, classify intent (chitchat/fact_lookup/summary/relationship/deep_analysis), route to retrieval strategy, retrieve relevant pages, expand by graph if needed, synthesize answer with [[wikilink]] citations, offer to save to 06-Wiki/syntheses/.
- If user replies `/save` or "保存", write the answer to 06-Wiki/syntheses/<slug>.md.
