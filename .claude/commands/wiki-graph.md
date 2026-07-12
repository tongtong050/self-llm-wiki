---
name: wiki-graph
description: Build the LLM Wiki knowledge graph
---

Run `python tools/build_graph.py` to build the knowledge graph with four-signal edge weights.
If $ARGUMENTS contains "--insights" or user says "分析知识图谱", also run `python tools/build_graph.py --insights` to generate insights report.
Outputs go to 06-Wiki/graph/graph.json, graph.html, and optionally graph-insights.md.
