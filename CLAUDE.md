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

<!-- 工作流章节见下（Task 2/3 追加）-->
