---
name: wiki-collide
description: Run concept collision detection and generate insights
---

Follow the Collide Workflow in the project's CLAUDE.md:
- Run `python tools/collide.py` to find candidate concept pairs in the sweet spot.
- Read `07-系统/.collision-candidates.json`, judge each pair for genuine cross-concept insight value, and write valuable insights to `07-系统/review.md` as `[collision]` items.
- Mark processed pairs incrementally. Append a line to `07-系统/pipeline-log.md`.
