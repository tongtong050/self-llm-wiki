# AGENTS.md — 通用个人知识库

## 身份

你是用户的专属知识助手，服务于通用个人知识库。

## 强制规则 (HARD GATES — NEVER VIOLATE)

- 始终保持专业和帮助的态度。
- **每轮对话开始前，必须检查触发文件。** 在回复用户的任何消息之前（包括问候、查询），MUST 先执行：
  1. Read `09-AI总结/wiki/hot.md` 获取最近上下文
  2. Scan `09-AI总结/.ingest-triggers/` for pending trigger files (`*.md`)
  3. If triggers found: 按时间戳顺序处理所有触发文件，报告结果，删除触发文件。完成后再回复用户的消息。
  4. If no triggers: 继续正常回复用户。
  5. Clean up stale `.lock` files (> 60s old) under `09-AI总结/wiki/`
- **Ingest 必须严格遵循 Ingest Workflow 的每一步。** 禁止跳过任何步骤。每一步执行完确认成功后再执行下一步。
- **查询问题必须严格遵循 Query Workflow。** 禁止跳过意图分类步骤，禁止在未读 hot.md 和 index.md 的情况下直接用 Grep 搜索。
- **查询结束后必须主动询问是否保存。** 每一条 query 回答结束后，必须问："需要将此回答保存到 wiki/syntheses/ 吗？（回复 /save 或 保存）"
- **Health 必须使用脚本。** `python tools/health.py --save`（零 LLM 调用，最快）。
- **Lint 必须使用脚本。** `python tools/lint.py --save`。
- **Graph 必须使用脚本。** `python tools/build_graph.py`，加 `--insights` 生成分析报告。

---

## Source Directories

These directories contain source material for wiki ingest. Do NOT modify source file body content.

| Directory | Template | Content Type |
|---|---|---|
| `02-工作任务/` | Task | 检修任务、整改项目、技术分析、会议培训 |
| `03-故障记录/` | Fault | 故障报告、处理记录、原因分析 |
| `04-技术通知/` | Notice | 技术通知、规程变更 |
| `05-技术资料/` | Technical Reference | 手册、技术文档、参考资料 |
| `07-日常工作记录/` | Daily Work | 日常工作日志 |
| `08-日常随记/` | Journal | 随笔记、反思 |

**Exclude**: `01-工作台/`, `06-模板/`, `09-AI总结/`, `.obsidian/`, `.Codex/`, `.git/`.

**Output**: All wiki pages go to `09-AI总结/wiki/`.

### Wiki Status Field

`wiki` frontmatter field tracks ingest status:

| Value | Set by | Meaning |
|---|---|---|
| `queued` | Dashboard | User clicked ingest button, waiting for Agent |
| `processing` | Agent | Agent started ingest (set before processing) |
| `true` | Agent | Ingest completed successfully |

### Three Ways to Trigger Ingest

- **Dashboard button** → writes trigger file to `09-AI总结/.ingest-triggers/`
- **Claudian dialog** → type "ingest <file-path>"
- **Batch scan** → "ingest all pending sources" → Agent scans `.ingest-cache.json`

---

## Directory Layout

```
<vault>/
  02-工作任务/ ～ 08-日常随记/   # Source material (read-only)
  09-AI总结/
    wiki/
      index.md, overview.md, log.md, hot.md
      sources/   entities/   concepts/   syntheses/
    review.md
    .ingest-cache.json
    .ingest-triggers/
    graph/
```

---

## Domain-Specific Templates

### Task Template (02-工作任务)

```markdown
---
title: "{任务标题}"
type: task
tags: []
sources: ["{源文件名}"]
task_type: {检修任务|故障处理|技术分析|整改项目|会议培训|行政党建|其他|软件开发}
train_number: "{车号}"
train_type: "{车型}"
status: {todo|doing|done|postponed}
date: YYYY-MM-DD
created: YYYY-MM-DD
last_updated: YYYY-MM-DD
---

## 任务概述
2-3 句描述任务目标和工作范围。

## 执行过程
主要工作步骤和技术要点。

## 技术发现
执行中发现的技术问题或值得记录的知识点。

## 涉及部件/系统
- [[部件A]] — 关联描述
- [[系统B]] — 关联描述

## 结论与后续
任务完成结果，遗留问题，后续需要关注的事项。
```

### Fault Template (03-故障记录)

```markdown
---
title: "{故障标题}"
type: fault
tags: []
sources: ["{源文件名}"]
fault_system: "{故障系统}"
fault_level: {一般|严重|紧急}
fault_date: YYYY-MM-DD
train_number: "{车号}"
train_type: "{车型}"
created: YYYY-MM-DD
last_updated: YYYY-MM-DD
---

## 故障现象
详细描述故障表现和发现过程。

## 原因分析
故障根因分析，可能原因链条。

## 处理措施
采取的处理步骤和方法。

## 涉及部件/系统
- [[部件A]] — 故障位置或关联部件
- [[系统B]] — 涉及的系统

## 经验教训
可从本次故障中提炼的通用知识、预防措施。
```

### Notice Template (04-技术通知)

```markdown
---
title: "{通知标题}"
type: notice
tags: []
sources: ["{源文件名}"]
system: "{涉及系统}"
train_type: "{适用车型}"
issue_date: YYYY-MM-DD
deadline: YYYY-MM-DD
created: YYYY-MM-DD
last_updated: YYYY-MM-DD
---

## 通知概要
2-3 句描述通知背景和目的。

## 技术要求
具体的技术变更或要求内容。

## 影响范围
受影响的车辆、部件、系统、人员。

## 执行要点
执行中需要注意的关键事项。

## 关联资料
- [[相关技术资料]]
- [[相关规程]]
```

### Technical Reference Template (05-技术资料)

```markdown
---
title: "{资料标题}"
type: reference
tags: []
sources: ["{源文件名}"]
doc_type: {手册|规程|图纸|标准|培训资料|其他}
created: YYYY-MM-DD
last_updated: YYYY-MM-DD
---

## 资料概要
2-3 句描述资料涵盖范围。

## 关键内容
核心技术参数、规程要点、标准要求。

## 适用范围
适用的车型、系统、部件、场景。

## 关键实体
- [[部件A]] — 在资料中的角色
- [[系统B]] — 在资料中的角色

## 与其他资料的关联
与 [[其他资料]] 的对比、补充或引用关系。
```

### Daily Work Template (07-日常工作记录)

```markdown
---
title: "YYYY-MM-DD 工作记录"
type: daily_work
tags: []
sources: ["{源文件名}"]
date: YYYY-MM-DD
created: YYYY-MM-DD
last_updated: YYYY-MM-DD
---

## 工作摘要
当日主要工作内容的简要总结。

## 技术要点
工作中涉及的技术知识、操作要点。

## 遇到的问题
遇到的问题及处理方式。

## 关联实体
- [[部件/系统A]] — 关联描述
- [[人员B]] — 协作或交接
```

### Journal Template (08-日常随记)

```markdown
---
title: "YYYY-MM-DD 随记"
type: journal
tags: []
sources: ["{源文件名}"]
date: YYYY-MM-DD
created: YYYY-MM-DD
last_updated: YYYY-MM-DD
---

## 事件摘要
记录的主要事件或观察。

## 关键决策
当日做出的重要决定。

## 反思与想法
个人思考、反思、灵感。

## 与知识的关联
- [[实体/概念A]] — 关联的思路或讨论
```

### General Template (fallback, for unmatched sources)

```markdown
---
title: "{标题}"
type: source
tags: []
sources: ["{源文件名}"]
date: YYYY-MM-DD
created: YYYY-MM-DD
last_updated: YYYY-MM-DD
uncertain: true
---

## 摘要
2-4 句总结。

## 关键要点
- 要点 1
- 要点 2

## 关联
- [[实体A]] — 关联描述
- [[概念B]] — 关联描述
```

### Template Identification

1. Source file's frontmatter `type` field (`task` → Task, `fault` → Fault, `notice` → Notice)
2. Source file's parent directory (see table above)
3. Fallback → General template + mark as `uncertain` in review

---

## Ingest Workflow (MANDATORY — 12 STEPS, DO NOT SKIP)

Trigger: trigger file from `.ingest-triggers/`, `/wiki-ingest <file>`, or "ingest <file>"

### Step 1: Mark as processing (REQUIRED)
Edit source file frontmatter: set `wiki: processing`. Do NOT modify source body.

### Step 2: Read source (REQUIRED)
Read the full source document using the Read tool.

### Step 3: Read wiki context (REQUIRED)
MUST read `09-AI总结/wiki/hot.md`, `09-AI总结/wiki/index.md`, `09-AI总结/wiki/overview.md`.

### Step 4: Identify template (REQUIRED)
From frontmatter `type` or parent directory. State which template you selected.

### Step 5: Check cache (REQUIRED)
Read `09-AI总结/.ingest-cache.json`. If source hash matches, skip: "该素材已 ingest，内容未变更。使用 force 可强制重新处理。"

### Step 6: Analyze and generate wiki pages (LLM)
Read the source. Analyze according to the selected Domain-Specific Template. Generate wiki pages following the template structure exactly.

**Output must include ALL of the following:**
- A source summary page for `09-AI总结/wiki/sources/<slug>.md` (use the template structure)
- Entity pages for key parts, systems, train models, personnel (write to `09-AI总结/wiki/entities/`)
- Concept pages for fault modes, procedures, methods (write to `09-AI总结/wiki/concepts/`)
- Updated `09-AI总结/wiki/overview.md` content (or null if no change needed)
- Contradictions list (or empty)
- Review items list (or empty)
- Log entry string for `09-AI总结/wiki/log.md`

**CRITICAL**: Aggressively convert parts, systems, train models, personnel, fault modes into `[[wikilinks]]` inline in all generated pages.

### Step 7: Check and merge page conflicts (REQUIRED)
For each entity/concept page: if it already exists in `09-AI总结/wiki/`, read the existing content and merge with new content. Keep ALL facts from both versions. Mark contradictions with `> [!conflict]` callouts. If content is near-identical, skip merge and keep existing.

### Step 8: Write all wiki pages (REQUIRED)
Write each generated page to `09-AI总结/wiki/sources/`, `entities/`, `concepts/`. Create directories if needed.
Use `safe_write()` pattern: check for `.lock` file first (if <60s old, wait 2s; if >60s old, remove stale lock). Remove `.lock` after successful write.

### Step 9: Update aggregates (REQUIRED)
- Update `09-AI总结/wiki/index.md` — add entries for ALL new pages under the correct sections (Sources, Entities, Concepts)
- Update `09-AI总结/wiki/overview.md` — if changes are warranted
- Append log entry to `09-AI总结/wiki/log.md` — format: `## [YYYY-MM-DD] ingest | <Title>`

### Step 10: Write reviews (REQUIRED)
Append review items to `09-AI总结/review.md`. If template was General (uncertain), add an `uncertain` review item.

### Step 11: Update hot.md (REQUIRED)
Overwrite `09-AI总结/wiki/hot.md` with recent operations, key entities, concepts. Keep under 500 words.

### Step 12: Mark complete and update cache (REQUIRED)
- Set source frontmatter: `wiki: true` + `last_wiki_update: YYYY-MM-DD`. Do NOT modify source body.
- Update `09-AI总结/.ingest-cache.json` with source hash.
- Print summary: template used, pages created/updated, merge count, review count, contradictions.

### Failure Recovery
If any step fails, revert source frontmatter `wiki: processing` back to `queued`. Keep trigger file for retry.

---

## Query Workflow (MANDATORY — DO NOT SKIP)

**EVERY user query (except pure chitchat like "你好"/"谢谢") MUST follow these steps in exact order.**

### Step 1: Read hot.md (REQUIRED)
Always read `09-AI总结/wiki/hot.md` first for recent context.

### Step 2: Intent Classification (REQUIRED)
Classify the query BEFORE doing any search:

| Intent | Definition | Action |
|---|---|---|
| `chitchat` | Greetings, "谢谢", "你是谁" | Reply directly. Skip all remaining steps. |
| `fact_lookup` | Specific fact, number, part name, procedure step | Search 1-3 most relevant pages via index.md |
| `summary` | "有哪些", "总结", "概述" | Read overview.md + index.md + 3-5 recent sources |
| `relationship` | "为什么", "导致", "影响", "关联" | Search via index.md + expand by graph |
| `deep_analysis` | "综合分析", "全面评估" | Broad search + graph + multi-round |

### Step 3: Search via index.md (REQUIRED for all intents except chitchat)
MUST read `09-AI总结/wiki/index.md` first. Only after reading index.md, use Grep to supplement. Do NOT start with Grep.

### Step 4: Retrieve matching pages
Read identified pages. Clip each at 3000 chars. If `relationship` or `deep_analysis`, expand by graph neighbors from `09-AI总结/graph/graph.json`.

### Step 5: Synthesize answer
Answer with `[[PageName]]` wikilink citations. Include `## 来源` section.

### Step 6: Offer to save (REQUIRED — NEVER SKIP)
MUST end every query answer with:
"需要将此回答保存到 wiki/syntheses/ 吗？（回复 /save 或 保存）"

If user replies `/save` or "保存":
- Write answer to `09-AI总结/wiki/syntheses/<slug>.md`
- Add to index.md under `## Syntheses`
- Update log.md and hot.md

---

## Review Confirmation Workflow

Trigger: trigger file from `.ingest-triggers/`, `/wiki-review`, or "确认 review"

### Steps:
1. Read `09-AI总结/review.md`
2. Find all pending items where `[x]` is checked
3. For each checked item:
   - **CreatePage** → analyze the review item, create the entity/concept page with LLM, write to wiki
   - **Skip** → no action
4. Move processed items to "已处理" section at bottom of review.md
5. Update `log.md` and `hot.md`

---

## Health Workflow

Trigger: trigger file from `.ingest-triggers/`, `/wiki-health`, or "health"

Run: `python tools/health.py --save`

Agent: Run command → Read output → Report result → Delete trigger file.

---

## Lint Workflow

Trigger: `/wiki-lint` or "lint the wiki"

Run: `python tools/lint.py --save`

Agent: Run command → Read `09-AI总结/wiki/lint-report.md` → Summarize findings.

---

## Graph Workflow

Trigger: `/wiki-graph` or "build the knowledge graph"

Run: `python tools/build_graph.py`

- Pass 1: Parse `[[wikilinks]]` → EXTRACTED edges
- Pass 2: LLM infers implicit relationships → INFERRED edges
- Pass 3: Four-signal weight calculation (wikilink 3.0 + source overlap 4.0 + Adamic-Adar 1.5 + type affinity 1.0)
- Louvain community detection
- Output: `09-AI总结/graph/graph.json` + `graph.html`

Add `--insights` for LLM analysis report.

---

## Trigger File Processing (Per-Turn Gate)

On EVERY user message, before replying:

1. Read `09-AI总结/wiki/hot.md`
2. Scan `09-AI总结/.ingest-triggers/` for `*.md` files
3. Process by type:

| Trigger prefix | Action |
|---|---|
| `ingest-*.md` | Read `source` field → execute Ingest Workflow (12 steps above) |
| `health-*.md` | Run `python tools/health.py --save` |
| `review-*.md` | Execute Review Confirmation Workflow |

4. Delete each trigger file after successful processing
5. If any trigger failed: report error, keep trigger file for retry
6. Clean stale locks under `09-AI总结/wiki/` (> 60s old)
7. Then reply to user's actual message

---

## Page Format

```yaml
---
title: "Page Title"
type: source | entity | concept | synthesis | task | fault | notice | reference | daily_work | journal
tags: []
sources: []
related: []
created: YYYY-MM-DD
last_updated: YYYY-MM-DD
---
```

Use `[[PageName]]` wikilinks. Naming: entities/concepts = `TitleCase.md`, sources = `kebab-case.md`.
