<!-- Logo -->
<p align="center">
  <a href="https://tashan.ac.cn" target="_blank" rel="noopener noreferrer">
    <img src="docs/assets/tashan.svg" alt="他山 Logo" width="280" />
  </a>
</p>

<!-- 标题 -->
<p align="center">
  <strong>他山公众号写作技能包</strong><br>
  <em>Tashan WeChat Publishing Skills</em>
</p>

<!-- 快速导航 -->
<p align="center">
  <a href="#项目简介">项目简介</a> •
  <a href="#包含的-skill">包含的 skill</a> •
  <a href="#快速开始">快速开始</a> •
  <a href="#如何更新">更新</a> •
  <a href="#生态位置">生态位置</a> •
  <a href="#贡献">贡献</a> •
  <a href="README.en.md">English</a>
</p>

<p align="center">
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT" /></a>
</p>

> **核心用法**：把已有手稿（word / md / txt）排版并导出为他山公众号微信 HTML——自动加内容摘要、完善引用规范、套用底部模板；**审稿为可选**。也支持从零写作与补全。

---

## 项目简介

他山围绕「跨学科交流 × AI for Science」持续对外输出内容。本项目是他山**内容生产 / 公众号宣发**环节的智能体工具层：把研究者或团队写好的手稿，稳定地转成符合「他山学科交叉」公众号排版与写作规范的成品，压掉从「写完」到「能发」之间的人工排版成本。

**核心思想**

- **手稿即输入**：核心用法是排版导出——给 word/md/txt，出微信 HTML，逐段保留原文措辞。
- **规范即真源**：排版、写作、配图规范以随附 `references/` 手册为准，全链路产出风格统一。
- **自包含分发**：每个 skill 自带 `references/`、`assets/`、`templates/`，复制目录即用，不依赖外部路径。

**适合场景与读者**

- 协会宣发 / 他山 AI 宣讲团：把科教稿、活动稿快速排成公众号 HTML
- 使用 Claude Code / Cursor 的智能体：clone 后即可调用整条链
- 需要复刻他山公众号统一风格的合作方

---

## 包含的 skill

共 **10 个**：公众号发文链路 + 抓取归档 + 通用团队协作 + 记忆召回。

| Skill | 目录 | 作用 |
|---|---|---|
| **wechat-article-writer** | [`skills/wechat-article-writer`](skills/wechat-article-writer/SKILL.md) | **入口**：把手稿排版导出为微信 HTML（核心）；也支持从零写作 |
| **document-pipeline** | [`skills/document-pipeline`](skills/document-pipeline/SKILL.md) | **引擎**：研究→草稿→逻辑自检→真实性校对→画图→（可选）审稿→引用规范→格式转换 |
| **article-proofreading** | [`skills/article-proofreading`](skills/article-proofreading/SKILL.md) | 审稿（可选）：AI 腔 / 标题 4 类错误 / 绝对表达 / 结构 / 结语 |
| **ai-image-generator** | [`skills/ai-image-generator`](skills/ai-image-generator/SKILL.md) | 配图能力层：模型选择、DashScope 调用、多视角、风格库、配图索引 |
| **article-image-angles** | [`skills/article-image-angles`](skills/article-image-angles/SKILL.md) | 配图多视角分析，给候选提示词 |
| **article-image-styles** | [`skills/article-image-styles`](skills/article-image-styles/SKILL.md) | 配图风格库管理（S01–S10 等） |
| **article-review-tracker** | [`skills/article-review-tracker`](skills/article-review-tracker/SKILL.md) | 审稿意见结构化追踪、逐条落实 |
| **wechat-article-crawler** | [`skills/wechat-article-crawler`](skills/wechat-article-crawler/SKILL.md) | 抓取/归档公众号文章（6 种方案 + 脚本），随附他山自有文章存档；发文链路的上游语料 |
| **team-collab** | [`skills/team-collab`](skills/team-collab/SKILL.md) | 通用团队异步协作 + 记忆层（「文件即消息」发帖/决策留痕、工作日志、会话归档/对话树）；也是记忆召回的**引擎 + 数据**（建对话树/向量库、`scripts/` 里的检索脚本）；**仓库无关**，可落地任意 git 项目 |
| **recall-memory** | [`skills/recall-memory`](skills/recall-memory/SKILL.md) | 记忆召回的**触发壳**：让 AI 在「上次那个脚本/网页/决定在哪个会话」时主动语义召回过去对话、并教它发散式读法；自己不带脚本，是 team-collab 检索引擎的一层薄前端 |

**调用链**

```
wechat-article-writer（入口：手稿→排版）
   └─转发→ document-pipeline（引擎）
              ├─（可选）article-proofreading（审稿）
              └─ ai-image-generator（配图）← article-image-angles / article-image-styles 增强
```

**上游**：`wechat-article-crawler` 抓取/归档公众号文章（含他山自有存档），为写作提供样本与语料。

**记忆层配对（引擎 ↔ 触发壳）**：`team-collab`（**引擎 + 数据**：建对话树、建向量库、`scripts/` 里的 `build_memory_index.py`/`query_memory.py`/`memory_daemon.py`）↔ `recall-memory`（**触发壳 + 协议**：让 AI 在「回忆过去做过什么」时主动去检索，并教它发散式读法）。依赖单向——装 `recall-memory` 必须一起装 `team-collab`；`team-collab` 可独立用。

> 每个 skill **自包含**：`SKILL.md` 里的 `references/…`、`assets/…`、`templates/…` 都相对该 skill 目录解析，整目录复制/软链即可用。

---

## 快速开始

### 1. 克隆

```bash
git clone https://github.com/TashanGKD/tashan-wechat-skills.git
cd tashan-wechat-skills
```

### 2. 安装到智能体 skill 目录

```bash
# Claude Code · 项目级（推荐）
mkdir -p <你的项目>/.claude/skills && cp -R skills/* <你的项目>/.claude/skills/
# Claude Code · 全局：cp -R skills/* ~/.claude/skills/
# Cursor：       cp -R skills/* <你的项目>/.cursor/skills/
# 或一键：       bash scripts/install.sh <目标目录>   # 默认 ./.claude/skills，--force 覆盖同名
```

> ⚠️ skill 在会话启动时扫描，装好后需**新开一个会话**才能被发现调用。

### 3. 触发（核心用法）

把手稿交给智能体，说「**按他山公众号格式把这篇排版成 HTML**」或「帮我排版/转 HTML/导出 HTML」：

- 输入可为 word(.docx) / md / txt / 粘贴全文；`.docx` 会先抽取为 markdown。
- 自动：加栏目前缀、内容摘要框、章节 H2、关键词加粗、封面/配图、底部模板，并完善引用规范。
- **审稿为可选**：想复核时再说「审稿 / review 一下」触发 `article-proofreading`。

### 4. 配图需要 API key

`ai-image-generator` 直连阿里云 DashScope：`export DASHSCOPE_API_KEY=...`（或 `AI_GENERATION_API_KEY`）。不设则只有配图步骤跳过，写作/排版/HTML 不受影响。⛔ 勿把密钥写进 skill 或提交仓库，见 [SECURITY.md](SECURITY.md)。

---

## 代码结构

```
tashan-wechat-skills/
├── docs/
│   ├── assets/tashan.svg     # 统一 Logo
│   └── 使用与更新指南.md      # 面向智能体的详细用法
├── skills/                   # 10 个自包含 skill（SKILL.md + references/ + assets/ + templates/）
├── scripts/install.sh        # 安装到 skill 目录
├── manifest.yml              # skill 清单
├── CHANGELOG.md              # 版本变更（SemVer）
├── CONTRIBUTING.md           # 贡献 / 更新回流规范
├── SECURITY.md               # 密钥与安全策略
├── LICENSE                   # MIT
├── README.md                 # 中文说明（本文件）
└── README.en.md              # English
```

---

## 如何更新

```bash
cd tashan-wechat-skills && git pull
```

- **复制安装**：`git pull` 后重跑 `bash scripts/install.sh <目标> --force`（或重新 `cp -R`）。
- **软链安装**：`git pull` 即生效。
- 更新前看 [CHANGELOG.md](CHANGELOG.md)：SemVer，**MAJOR = 破坏性变更**，读迁移说明。
- 想改进：按 [CONTRIBUTING.md](CONTRIBUTING.md) 开分支 → conventional commit → PR，改动回流本仓库，避免各处副本漂移。

---

## 生态位置

本项目是他山（TashanGKD）开源生态中的**内容生产 / 宣发工具**层，与科研 skill 集、讨论平台并列。

| 仓库 | 定位 | 链接 |
|---|---|---|
| **tashan-wechat-skills** | 公众号写作 / 排版 skill（本仓库） | 当前 |
| tashan-research-skills | 学术科研 skill 集（文献/写作/图表/审稿） | [TashanGKD/tashan-research-skills](https://github.com/TashanGKD/tashan-research-skills) |
| Tashan-TopicLab | 多专家圆桌讨论平台 | [TashanGKD/Tashan-TopicLab](https://github.com/TashanGKD/Tashan-TopicLab) |
| 他山官网 | 协会主页 | [tashan.ac.cn](https://tashan.ac.cn) |

---

## 贡献

欢迎贡献！详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

- **skill 改进**：保持自包含（资源放各自 `references/`/`assets/`/`templates/`），不硬编码密钥。
- **文档贡献**：改进 README 或补充 `docs/`。

---

## 更新日志

版本变更见 [CHANGELOG.md](CHANGELOG.md)。

---

## 许可证

MIT License. See [LICENSE](LICENSE) for details.

出品：中国科学院大学他山学科交叉创新协会 · 他山 AI 宣讲团。
