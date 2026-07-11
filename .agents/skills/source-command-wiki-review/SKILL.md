---
name: "source-command-wiki-review"
description: "Process pending reviews from review.md"
---

# source-command-wiki-review

Use this skill when the user asks to run the migrated source command `wiki-review`.

## Command Template

Read 09-AI总结/review.md, find all [x]-checked pending items, and execute the selected action (CreatePage / Skip) for each.
Follow the Review Confirmation Workflow in the project's AGENTS.md.
After processing, update review.md: move items to done section, refresh counts.
