# 认知生产台（Cognition Hub）— 个人知识库 Vault

通用个人知识库 vault，配合 [cognition-hub](https://github.com/) Obsidian 插件与 Claude Code Agent 工作流，构成完整的**灵感捕获 → 知识卡片 → AI 概念抽取 → 概念碰撞 → 新洞见**认知生产管线。

## 目录结构

```
<vault>/
  00-灵感库/             灵感暂存区（type: inspiration）
  01-项目/               项目卡片（type: card，有截止日）
  02-长期关注/           长期维护卡片（type: card，无截止日）
  03-参考资料/           外部素材 / flomo 碎片（type: reference）
  04-归档/               已完成或搁置（.trash/ 为 30 天到期待删）
  05-Skills/             自写脚本资产
  06-Wiki/               AI 自动维护的概念库（只读）
    index.md overview.md log.md hot.md
    sources/ entities/ concepts/ syntheses/ graph/
  07-系统/               系统运行文件
    review.md pipeline-log.md
    .ingest-cache.json .collision-candidates.json
    .ingest-triggers/
  08-创作/               抖音口播脚本 / 文案输出
```

## 工作机制（三层协作）

本系统的每个能力（ingest / query / collide / review / graph）都是三层协作：

| 层               | 位置                             | 角色                                  |
| ---------------- | -------------------------------- | ------------------------------------- |
| **命令 / Skill** | `.claude/commands/wiki-*.md`     | 入口（`/wiki-ingest` 等，或触发文件） |
| **Skill 定义**   | `.claude/skills/<name>/SKILL.md` | 分步骤流程说明（如 12 步 ingest）     |
| **Python 脚本**  | `tools/*.py`                     | 执行计算与 LLM 调用                   |

## Agent 工作流

| 工作流          | Skill           | 说明                                        |
| --------------- | --------------- | ------------------------------------------- |
| **Expand**      | `wiki-expand`   | 灵感 → 卡片草稿                             |
| **Ingest**      | `wiki-ingest`   | 12 步知识摄入（卡片 → wiki 概念/实体/来源） |
| **Collide**     | `wiki-collide`  | 概念碰撞检测 → 新洞见                       |
| **Query**       | `wiki-query`    | 意图分类 + 检索 + 图谱扩展合成              |
| **Review**      | `wiki-review`   | 审核 review.md 并执行操作                   |
| **Graph**       | —               | `python tools/build_graph.py`               |
| **Health/Lint** | —               | `python tools/health.py` / `lint.py`        |
| **Douyin**      | `douyin-script` | 生成抖音口播脚本 / 文案                     |

## 触发文件机制

Dashboard 按钮 → 写触发文件到 `07-系统/.ingest-triggers/` → Agent 每轮对话自动扫描 → invoke 对应 Skill → 处理后删除触发文件。

| `action`  | 参数                   | Skill         |
| --------- | ---------------------- | ------------- |
| `expand`  | `source`, `target_dir` | wiki-expand   |
| `ingest`  | `source`               | wiki-ingest   |
| `review`  | —                      | wiki-review   |
| `collide` | —                      | wiki-collide  |
| `douyin`  | —                      | douyin-script |

## Python 工具链

```bash
pip install litellm networkx pyyaml
```

| 脚本                   | 用途                                                  |
| ---------------------- | ----------------------------------------------------- |
| `tools/ingest.py`      | 12 步 LLM 知识摄入（分析 → 生成 → 合并 → 写入）       |
| `tools/collide.py`     | 概念碰撞检测（轻量 tags/来源/共引用档，可选向量增强） |
| `tools/build_graph.py` | 知识图谱构建 + Louvain 社区检测                       |
| `tools/query.py`       | 意图分类 + 检索 + LLM 合成                            |
| `tools/index_gen.py`   | 生成 00-灵感库/ 与 06-Wiki/ 的 index.md               |
| `tools/rss_pull.py`    | RSS 源拉取（需要 feedparser）                         |
| `tools/flomo_scan.py`  | 碎片素材扫描骨架                                      |

模型通过环境变量配置（全部可选，默认模型已内置 `anthropic/` 前缀）：

| 变量              | 默认值                               | 用途                 |
| ----------------- | ------------------------------------ | -------------------- |
| `LLM_MODEL`       | `anthropic/claude-3-5-sonnet-latest` | 重任务               |
| `LLM_MODEL_FAST`  | `anthropic/claude-3-5-haiku-latest`  | 分类 / 推理          |
| `LLM_EMBED_MODEL` | —                                    | 向量碰撞增强（可选） |

测试：`python -m pytest tools/tests/ -v`

## 使用指南

1. **捕获灵感** — Dashboard "快速捕获" 或直接在 `00-灵感库/` 建 `.md`（type: inspiration）
2. **扩写为卡片** — Dashboard 点 🤖 扩写 → Agent 生成草稿卡片到 `01-项目/` 或 `02-长期关注/`
3. **审阅并 ingest** — 审阅草稿 → 管线 Tab 点 "标记 queued" → 点 ingest → Agent 12 步摄入
4. **查询知识** — 在 Claudian 中直接提问，Agent 检索 wiki 合成答案
5. **概念碰撞** — 管线 Tab 点碰撞检测 → Agent 生成洞见到 review.md → 勾选回流为新灵感
6. **审核 Review** — 卡片入库时自动生成待审核项，在管线 Tab 处理

## 环境依赖

- [Obsidian](https://obsidian.md/) ≥ 1.8.0
- [cognition-hub](https://github.com/) Obsidian 插件
- [Claudian](https://github.com/bengbu/obsidian-claudian) 插件（Claude Code 交互式会话）
- Python 3.10+（可选，Agent 依赖 Python 工具链）

## License

MIT
