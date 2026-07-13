# 认知生产台（Cognition Hub）— 个人知识库 Vault

通用个人知识库 vault，配合 cognition-hub Obsidian 插件与 Claude Code Agent 工作流，构成完整的认知生产管线。

## Features

- **5-Tab Dashboard**: 工作任务 / 故障报单 / 技术通知 / 数据汇总 / 知识库整理
- **Real Vault Data**: 从 Obsidian vault 中读取 `02-工作任务/`、`03-故障记录/`、`04-技术通知/` 等目录的 `.md` 文件
- **Task & Fault Management**: 新建任务/故障/通知模态框，模板化文件创建，一键状态变更
- **Lunar Calendar**: 农历日历 + 法定节假日 + 任务/故障/通知条目展示，支持跨月浏览
- **Fault Heatmap**: 12 个月滚动热力图，鼠标悬停显示故障详情
- **Wiki Integration**: ingest 触发文件机制，知识库健康检查，review 面板
- **Theme Support**: 完整暗色/亮色主题适配

## Directory Structure

插件自动创建并管理以下 vault 目录：

```
01-工作台/
02-工作任务/
03-故障记录/
04-技术通知/
05-技术资料/
06-模板/
07-日常工作记录/
08-日常随记/
09-AI总结/
  wiki/  graph/  .ingest-triggers/
```

---

## LLM Wiki 系统

本插件与 **LLM Wiki Agent** 深度集成，构成一个完整的 AI 驱动知识管理系统。Wiki 系统基于 [Andrej Karpathy 的 LLM Wiki 模式](https://github.com/karpathy/llm-wiki) 构建，借鉴了 [claude-obsidian](https://github.com/AgriciDaniel/claude-obsidian) 的 Agent Skill 架构和 [llm_wiki](https://github.com/ekadetov/llm-wiki) 的桌面端设计。

### 核心能力

| 能力 | 描述 |
|------|------|
| **Ingest 知识摄入** | 从素材目录（02-08）中读取文档，提取实体（部件/系统/人员）、概念（故障模式/检修方法），生成结构化 wiki 页面 |
| **Query 知识查询** | 意图分类 + 全文检索 + 知识图谱扩展，多轮对话式问答，支持 `/save` 保存结果 |
| **Graph 知识图谱** | 自动构建知识图谱：wikilink 提取 + 语义推理 + 四信号权重计算 + Louvain 社区检测，产出交互式 HTML 可视化 |
| **Review 审核系统** | 文件驱动的人机协作：Agent 标注不确定性 → 用户审核 → Agent 执行，闭环管理 |
| **Health 健康检查** | 零 LLM 调用的结构完整性检查：空文件检测、索引同步、日志覆盖 |

### 架构概览

```
Dashboard 插件（Obsidian UI）
  │  ingest 按钮 / health 按钮 / review 面板
  │  写入触发文件到 09-AI总结/.ingest-triggers/
  ▼
Claudian Agent（Claude Code 交互式会话）
  │  读取触发文件 → 执行工作流
  │  Ingest: 12 步 Agent Skill（分析→生成→合并→写入→索引→日志）
  │  Query: 6 步检索流程（意图分类→index→图谱扩展→合成→/save）
  │  Graph: 脚本执行（wikilink 提取→语义推理→四信号权重→社区检测）
  │  Health/Lint: 脚本执行（确定性检查/LLM 语义分析）
  ▼
Vault 文件系统（09-AI总结/）
  wiki/（index/overview/log/hot + sources/entities/concepts/syntheses）
  review.md  .ingest-cache.json  graph/
```

### Ingest 工作流

从素材到知识页面的完整管线，Agent 严格遵循 12 步流程：

```
1. 标记状态 (wiki: processing)
2. 读取源文件
3. 读取 wiki 上下文 (hot.md + index.md + overview.md)
4. 识别 Domain 模板（Task/Fault/Notice/Reference/DailyWork/Journal）
5. 缓存检查（跳过未变更文件）
6. LLM 分析生成 wiki 页面（源摘要 + 实体页 + 概念页 + [[wikilinks]]）
7. 页面冲突检测与合并（保留所有事实，标记 [!conflict]）
8. 写入所有页面（文件级锁保护）
9. 更新聚合文件（index.md + overview.md + log.md）
10. 写入 review 项（待审核标记）
11. 更新 hot.md 上下文缓存
12. 标记完成 (wiki: true) + 更新缓存
```

### Domain-Specific 模板

系统提供 6 个领域的定制化模板，根据素材 frontmatter `type` 或所在目录自动选择：

| 目录 | 模板 | 提取重点 |
|------|------|---------|
| `02-工作任务/` | Task | 任务目标、执行过程、技术发现、涉及部件 |
| `03-故障记录/` | Fault | 故障现象、原因分析、处理措施、经验教训 |
| `04-技术通知/` | Notice | 通知概要、技术要求、影响范围、执行要点 |
| `05-技术资料/` | Technical Reference | 资料概要、关键参数、适用范围、关联资料 |
| `07-日常工作记录/` | Daily Work | 工作摘要、技术要点、问题记录、关联实体 |
| `08-日常随记/` | Journal | 事件摘要、关键决策、反思与灵感 |

### Query 查询工作流

```
用户问题 → 意图分类（chitchat/fact_lookup/summary/relationship/deep_analysis）
  → 读取 index.md 检索相关页面
  → 图谱邻居扩展（relationship/deep_analysis 模式）
  → LLM 合成答案（[[wikilink]] 引用）
  → 主动询问 /save（保存到 wiki/syntheses/）
```

### 知识图谱

两阶段构建 + 四信号权重 + 社区检测：

- **Pass 1**: wikilink 提取（确定性，EXTRACTED 边，confidence=1.0）
- **Pass 2**: LLM 语义推理（可选，INFERRED 边，带 confidence 评分）
- **Pass 3**: 四信号权重计算（零 token）：
  - 直接 wikilink (3.0) + 来源重叠 Jaccard (4.0) + Adamic-Adar (1.5) + 类型亲缘矩阵 (1.0)
- **社区检测**: Louvain 算法（NetworkX）
- **输出**: `graph.json` + 自包含 `graph.html`（vis.js 交互式可视化）+ 可选 `graph-insights.md` 洞察报告

### Review 审核系统

文件驱动的人机协作机制，零额外 token：

| Review 类型 | 触发条件 |
|-------------|---------|
| `contradiction` | 新素材与已有 wiki 内容冲突 |
| `duplicate` | 新实体/概念与已有页面高度相似 |
| `missing-page` | 重要概念被多次引用但缺少专属页面 |
| `suggestion` | LLM 建议的后续研究方向 |
| `uncertain` | 素材无 frontmatter，分类不确定 |

用户在 Obsidian 中编辑 `09-AI总结/review.md` 勾选操作选项，Dashboard 自动检测变更并写入触发文件，Agent 下次会话时自动消费。

### 触发文件机制

Dashboard 按钮点击 → 写入 `09-AI总结/.ingest-triggers/` → Agent SessionStart 自动扫描处理：

| 触发类型 | 触发文件前缀 | Agent 动作 |
|---------|-------------|-----------|
| Ingest | `ingest-*.md` | 执行 12 步 Ingest Workflow |
| Health | `health-*.md` | 运行 `python tools/health.py --save` |
| Review | `review-*.md` | 执行 Review Confirmation Workflow |

触发文件处理后自动删除。失败则保留文件供重试。

### Wiki 状态字段

素材文件的 `wiki` frontmatter 字段追踪 ingest 状态：

| 值 | 写入者 | 含义 |
|----|-------|------|
| `queued` | Dashboard | 用户点击了 ingest 按钮 |
| `processing` | Agent | Agent 正在执行 ingest |
| `true` | Agent | Ingest 成功完成 |
| （不存在） | — | 从未被 ingest |

---

## 使用指南

### Wiki 知识库使用

1. **触发 Ingest**: 在 Dashboard 的任务/故障/通知列表中点击 🧠 Ingest 按钮，或在 Claudian 对话框输入 `ingest <文件路径>`
2. **批量导入**: 在 Claudian 中说 "ingest all pending sources"，Agent 自动扫描未处理文件
3. **查询知识**: 直接在 Claudian 中提问（如 "制动缸漏风的原因有哪些"），Agent 自动检索 wiki 并合成答案
4. **保存答案**: 查询结束后回复 `/save`，答案归档到 `wiki/syntheses/`
5. **审核 Review**: 在 Obsidian 中打开 `09-AI总结/review.md`，勾选操作选项，Dashboard 自动触发
6. **构建图谱**: 在 Claudian 中说 "build the knowledge graph"
7. **健康检查**: Dashboard "知识库整理" Tab → 点击"运行健康检查"

### 环境依赖

- **Obsidian** ≥ 1.8.0
- **Claudian 插件**（Claude Code 交互式会话）
- **Claude Code CLI**（Agent 执行环境）
- **Python 3.10+**（脚本工具） + `litellm` / `networkx`
- **模型配置**：在系统环境变量中设置 `LLM_MODEL` 和 `LLM_MODEL_FAST`（不设则 Agent 使用 Claudian 订阅的默认模型）

### 素材准备

将以下类型文件放入对应目录即可被 Agent 识别：

- `02-工作任务/`: 检修任务、技术分析、整改项目（建议 `type: task` frontmatter）
- `03-故障记录/`: 故障报告、处理记录（建议 `type: fault` frontmatter）
- `04-技术通知/`: 技术通知、规程变更（建议 `type: notice` frontmatter）
- `05-技术资料/`: 手册、技术文档（建议 `type: reference` frontmatter）
- `07-日常工作记录/`: 日常记录（建议 `type: daily_work` frontmatter）
- `08-日常随记/`: 随笔记（建议 `type: journal` frontmatter）

无 frontmatter 的文件也会被处理，系统自动识别分类并在 review 中标注为 `uncertain` 供确认。

---

## Technical Stack

| 组件 | 技术 |
|------|------|
| Dashboard 插件 | TypeScript + Obsidian Plugin API |
| Agent 工作流 | Claude Code Agent Skills (CLAUDE.md) |
| Python 工具链 | litellm + NetworkX + vis.js |
| 知识图谱 | Louvain 社区检测 + 四信号权重模型 |
| 交互模式 | 文件驱动触发 + 交互式会话 |

## License

MIT
