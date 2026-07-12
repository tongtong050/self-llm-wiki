---
name: wiki-ingest
description: Ingest a source document into the LLM Wiki
---

Read the source file specified in $ARGUMENTS. Follow the Ingest Workflow in the project's CLAUDE.md:
- Read source, identify template, check cache, call LLM, check page conflicts, write pages, update aggregates, write reviews, update hot.md, mark source ingested, update cache.
- Do NOT modify source file body content — only add wiki: true frontmatter field.
