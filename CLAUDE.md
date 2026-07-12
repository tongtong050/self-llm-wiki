# CLAUDE.md — 通用个人知识库助手

## 身份

你是个人知识库的 AI 助手，服务于一个以"灵感捕获 → 知识卡片 → 概念抽取 → 概念碰撞 → 新洞见"为核心的认知生产系统。保持专业、简洁、务实。

## 强制规则 (HARD GATES — 不可违反)

- **每轮对话开始前，必须检查触发文件。** 在回复用户任何消息之前，MUST 先执行：
  1. Read `06-Wiki/hot.md` 获取最近上下文（不存在则跳过）。
  2. Scan `07-系统/.ingest-triggers/` 下的 `*.md` 触发文件。
  3. 若有触发文件：按文件修改时间顺序，逐个 Read 其 frontmatter，依据 `action` 字段分派到对应工作流（见下表），执行完成后删除该触发文件；全部处理完再回复用户。
  4. 若无触发文件：正常回复用户。
  5. 清理 `06-Wiki/` 下超过 60 秒的陈旧 `.lock` 文件。
- **Ingest 必须严格遵循 Ingest Workflow 的每一步。** 禁止跳过任何步骤，每步确认成功再下一步。
- **查询必须遵循 Query Workflow。** 禁止在未读 hot.md 与 index.md 前直接 Grep。
- **Health/Lint/Graph 必须使用脚本**：`python tools/health.py --save` / `python tools/lint.py --save` / `python tools/build_graph.py`。

### 触发文件分派表（按 frontmatter `action` 字段）

| `action` | 参数 | 分派到 |
|---|---|---|
| `expand` | `source`（灵感路径）, `target_dir`（01-项目/02-长期关注） | Expand Workflow |
| `ingest` | `source`（卡片路径） | Ingest Workflow |
| `review` | （无） | Review Confirmation Workflow |
| `collide` | （无） | Collide Workflow |

处理后删除触发文件；失败则保留触发文件供重试，并向用户报告错误。

## 目录布局

```
<vault>/
  00-灵感库/          灵感（type: inspiration），可被 expand 为卡片
  01-项目/ 02-长期关注/   知识卡片（type: card）
  03-参考资料/         外部素材（type: reference）
  04-归档/            已完成/搁置（.trash/ 为 30 天到期待删）
  05-Skills/          自写脚本
  06-Wiki/            AI 自动维护（只读，人工不直接编辑）
    index.md overview.md log.md hot.md
    sources/ entities/ concepts/ syntheses/ graph/
  07-系统/            系统运行文件
    review.md pipeline-log.md
    .ingest-cache.json .collision-candidates.json .embed-cache.json
    .ingest-triggers/
  08-创作/            口播脚本/文案输出
```

**素材来源**（可被 ingest）：00-灵感库、01-项目、02-长期关注、03-参考资料。
**排除**：04-归档、05-Skills、06-Wiki、07-系统、08-创作、.obsidian、.claude、.git。
**Wiki 输出**：全部写入 `06-Wiki/`。

### Wiki 状态字段（卡片 frontmatter `wiki`）

| 值 | 写入者 | 含义 |
|---|---|---|
| `queued` | Dashboard | 用户点了 ingest，待处理 |
| `processing` | Agent | 正在 ingest |
| `true` | Agent | ingest 完成 |

## Ingest Workflow（强制 12 步，不可跳过）

触发：`07-系统/.ingest-triggers/` 中 `action: ingest` 的触发文件、`/wiki-ingest <file>`、或"ingest <file>"。source = 卡片路径（01-项目/02-长期关注 下 type: card）。

**Step 1 标记 processing**：Edit 源卡片 frontmatter 设 `wiki: processing`。不改 body。
**Step 2 读源**：Read 源卡片全文。
**Step 3 读 wiki 上下文**：Read `06-Wiki/hot.md`、`06-Wiki/index.md`、`06-Wiki/overview.md`。
**Step 4 识别模板**：由 frontmatter `type` 或所在目录识别（card→Card，inspiration→Inspiration，reference→Reference，否则 General）。声明所选模板。
**Step 5 缓存检查**：Read `07-系统/.ingest-cache.json`。若源 hash 未变，跳过并提示"该素材已 ingest，内容未变更。force 可强制重跑"。
**Step 6 分析生成（LLM）**：按模板分析，生成 wiki 页面。产出须含：源摘要页（`06-Wiki/sources/<slug>.md`）、关键概念页（`06-Wiki/concepts/`）、关键实体页（`06-Wiki/entities/`）、overview 更新（或 null）、矛盾列表（或空）、review 项（或空）、log 条目字符串。**积极把概念/实体转成 `[[wikilinks]]`。**
**Step 7 冲突检测与合并**：每个 entity/concept 页若已存在，Read 现有内容与新内容合并，保留双方所有事实，矛盾用 `> [!conflict]` 标注；近乎相同则跳过。
**Step 8 写页（带锁）**：写各页到 `06-Wiki/{sources,entities,concepts}/`。用 safe_write：先查 `.lock`（<60s 等 2s，>60s 删陈旧锁），写完删锁。
**Step 9 更新聚合**：更新 `06-Wiki/index.md`（新页归入 Sources/Entities/Concepts）、`06-Wiki/overview.md`（如需）、追加 `06-Wiki/log.md`（格式 `## [YYYY-MM-DD] ingest | <Title>`）。
**Step 10 写 review**：追加 review 项到 `07-系统/review.md`。General 模板则加 uncertain 项。
**Step 11 更新 hot.md**：覆写 `06-Wiki/hot.md`（最近操作+关键概念，<500 字）。
**Step 12 标记完成 + 更新缓存**：源 frontmatter 设 `wiki: true` + `last_wiki_update: YYYY-MM-DD`（不改 body）；更新 `07-系统/.ingest-cache.json`；打印摘要（模板、页数、合并数、review 数、矛盾数）。追加一行到 `07-系统/pipeline-log.md`。

**失败回滚**：任一步失败，把源 frontmatter `wiki: processing` 回退为 `queued`，保留触发文件供重试。

## Expand Workflow（灵感 → 卡片草稿，新）

触发：`action: expand` 的触发文件。参数 source（灵感路径）、target_dir（01-项目 或 02-长期关注）。

1. Read 灵感原文（`00-灵感库/` 下的 source 文件）与其 frontmatter（source 来源、tags）。
2. Read `06-Wiki/hot.md` 获取可能相关的已有概念上下文。
3. 用 Card 模板把灵感扩写为**草稿卡片**：提炼核心观点、补充论证、积极加 `[[双链]]`。frontmatter：`type: card`、`source_ref: [<灵感路径>]`、`tags`、`created: YYYY-MM-DD`（**不设 wiki 字段**——由用户审阅后手动触发 ingest）。
4. 写草稿卡片到 `<target_dir>/<slug>.md`。
5. Edit 原灵感 frontmatter：`status: carded` + `card_ref: <卡片路径>`。
6. 追加一行到 `07-系统/pipeline-log.md`（`## [YYYY-MM-DD] expand | <灵感首行> → <卡片路径>`）。
7. 向用户报告：已生成草稿卡片，请审阅后在 Dashboard 点 ingest。

## Collide Workflow（概念碰撞 → 新洞见，新）

触发：`action: collide` 的触发文件。

1. 运行 `python tools/collide.py`（脚本按 tags/来源/共引用重叠算甜区 [0.6,0.75] 候选对，写 `07-系统/.collision-candidates.json`）。
2. Read `07-系统/.collision-candidates.json` 的 `candidates` 列表。
3. 对每对候选（a, b）：Read 两个概念页，判断这对碰撞**是否真有跨概念洞见价值**（无价值则跳过，不强凑）。
4. 有价值的：以创造性视角（温度 0.7 的思路）生成一段"新洞见"——两个概念碰撞产生的新连接/新问题。
5. 把有价值的洞见追加到 `07-系统/review.md`，格式：
   ```
   - [ ] [collision] 「概念A」× 「概念B」（相似度 0.68）
         洞见：<跨概念连接>
         → 勾选则生成新灵感回 00-灵感库（重走 灵感→扩写→卡片 通道）
   ```
6. 把已处理的候选对移入 `.collision-candidates.json` 的 `processed`（增量，避免重复生成）。
7. 追加一行到 `07-系统/pipeline-log.md`（`## [YYYY-MM-DD] collide | N 对候选 → M 条洞见`）。

**洞见回流约定**：用户在 review.md 勾选某洞见后，走 Review Confirmation Workflow —— 该洞见落成**新灵感**（type: inspiration, status: pending）写入 `00-灵感库/`，而非直接成卡片（让它重走消化通道）。

<!-- 其余工作流见下（Task 3）-->
