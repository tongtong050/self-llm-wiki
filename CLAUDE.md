# CLAUDE.md — 通用个人知识库助手

## 身份

你是个人知识库的 AI 助手，服务于一个以"灵感捕获 → 知识卡片 → 概念抽取 → 概念碰撞 → 新洞见"为核心的认知生产系统。保持专业、简洁、务实。

## 工作机制（三层协作，避免混淆）

本系统的每个能力（ingest / query / collide / review / graph）都是**三层协作**，不是"要么用 Skill、要么用 Python"的二选一：

| 层 | 是什么 | 角色 |
|---|---|---|
| **命令 / Skill**（`.claude/commands/wiki-*.md`） | 入口，委托到 `.claude/skills/<name>/SKILL.md` 的详细流程 | 调用者 |
| **Skill 定义**（`.claude/skills/<name>/SKILL.md`） | 分步骤的流程说明（如 12 步 ingest：读源→识别模板→缓存检查→调 LLM→合并→写页…） | 编排（Agent invoke 后照做） |
| **Python 脚本**（`tools/*.py`） | 真正执行的确定性代码与 LLM 调用（如 `ingest.py` 的 `call_llm`、`collide.py`、`build_graph.py`） | 干活（分析/计算/写文件） |

**关键**：`06-Wiki/` 下的页面、`graph.json`、碰撞候选等产物，最终都由 `tools/*.py` 写出。命令与 Skill 负责编排与约束，Python 负责执行。三者始终协同。

## 强制规则 (HARD GATES — 不可违反)

- **每轮对话开始前，必须检查触发文件。** 在回复用户任何消息之前，MUST 先执行：
  1. Read `06-Wiki/hot.md` 获取最近上下文（不存在则跳过）。
  2. Scan `07-系统/.ingest-triggers/` 下的 `*.md` 触发文件。
  3. 若有触发文件：按文件修改时间顺序，逐个 Read 其 frontmatter，依据 `action` 字段 invoke 对应 skill（见下表），执行完成后删除该触发文件；全部处理完再回复用户。
  4. 若无触发文件：正常回复用户。
  5. 清理 `06-Wiki/` 下超过 60 秒的陈旧 `.lock` 文件。
- **Ingest 必须严格遵循 wiki-ingest skill 的每一步。** 禁止跳过任何步骤，每步确认成功再下一步。
- **查询必须调用 wiki-query skill。** 禁止跳过意图分类步骤，禁止在未读 hot.md 和 index.md 的情况下直接用 Grep 搜索。
- **查询结束后必须主动询问是否保存。** 每一条 query 回答结束后，必须问："需要将此回答保存到 `06-Wiki/syntheses/` 吗？（回复 /save 或 保存）"
- **Health/Lint/Graph 必须使用脚本**：`python tools/health.py --save` / `python tools/lint.py --save` / `python tools/build_graph.py`。

### 触发文件分派表（按 frontmatter `action` 字段）

| `action` | 参数 | invoke skill |
|---|---|---|
| `expand` | `source`（灵感路径）, `target_dir`（01-项目/02-长期关注） | `wiki-expand` |
| `ingest` | `source`（卡片路径） | `wiki-ingest` |
| `review` | （无） | `wiki-review` |
| `collide` | （无） | `wiki-collide` |
| `douyin` | （无，或 source 可选） | `douyin-script` |

处理后删除触发文件；失败则保留触发文件供重试，并向用户报告错误。

### Skill 索引

| Skill | 文件 | 用途 |
|---|---|---|
| `wiki-ingest` | `.claude/skills/wiki-ingest/SKILL.md` | 12 步知识摄入（卡片 → Wiki 概念/实体） |
| `wiki-expand` | `.claude/skills/wiki-expand/SKILL.md` | 灵感扩写为卡片草稿 |
| `wiki-collide` | `.claude/skills/wiki-collide/SKILL.md` | 概念碰撞检测 → 新洞见 |
| `wiki-query` | `.claude/skills/wiki-query/SKILL.md` | 意图分类 + 全文检索 + 图谱扩展 + 合成 |
| `wiki-review` | `.claude/skills/wiki-review/SKILL.md` | 审核 review.md 并执行操作 |
| `douyin-script` | `.claude/skills/douyin-script/SKILL.md` | 生成抖音口播脚本/文案 |

Graph / Health / Lint 对应 `tools/build_graph.py` / `health.py` / `lint.py` 脚本，无独立 Skill。

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

## 通用模板

- **Card**（type: card）：核心观点/论证/来源/关联（双链）。frontmatter: type, tags, source_ref, created。
- **Inspiration**（type: inspiration）：念头/来源(外部输入/发散/解决问题)/初步概念。frontmatter: type, source, status, captured, tags。
- **Reference**（type: reference）：摘要/要点/适用范围/关键实体。frontmatter: type, tags。
- **General**（fallback, type: source, uncertain: true）：摘要/要点/关联。

## 页面格式

```yaml
---
title: "Page Title"
type: source | entity | concept | synthesis | card | inspiration | reference
tags: []
sources: []
related: []
created: YYYY-MM-DD
last_updated: YYYY-MM-DD
---
```
用 `[[PageName]]` 双链。命名：entities/concepts = `TitleCase.md`，sources = `kebab-case.md`。

## 模型与温度说明

脚本层（litellm）支持模型/温度调度：`LLM_MODEL`（大）、`LLM_MODEL_FAST`（小/国产）、`LLM_EMBED_MODEL`（向量碰撞，可选）。抽取/预处理用低温，碰撞洞见生成用温度 0.7。留空 env 则用默认模型。Claudian 对话层用会话默认模型（不能 per-message 调温）。
