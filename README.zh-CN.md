# 他山公众号写作技能包（tashan-wechat-skills）

[English README](README.md)

面向智能体（Claude Code / Cursor 等）的**他山公众号发文链路** skill 集合：从写稿、逻辑自检、真实性校对、配图规划与生成、审稿、引用规范，到微信 HTML 排版，一条龙。产出符合中国科学院大学他山学科交叉创新协会公众号「他山学科交叉」的排版与写作规范。

> 每个 skill 都是**自包含**的：它需要的 `references/`（排版/写作/配图真源）、`assets/`（底部模板图）、`templates/`（模板）都在自己的目录里，复制走即可用，不依赖外部路径。

---

## 包含的 skill（7 个）

| Skill | 目录 | 作用 |
|---|---|---|
| **wechat-article-writer** | [`skills/wechat-article-writer`](skills/wechat-article-writer/SKILL.md) | **入口**：写公众号文章。触发后转发 document-pipeline，产出微信 HTML |
| **document-pipeline** | [`skills/document-pipeline`](skills/document-pipeline/SKILL.md) | **引擎**：研究→草稿→逻辑自检→真实性校对→画图→审稿→引用规范→格式转换 |
| **article-proofreading** | [`skills/article-proofreading`](skills/article-proofreading/SKILL.md) | 审稿：AI 腔 / 标题 4 类错误 / 绝对表达 / 结构层次 / 结语完整性 |
| **ai-image-generator** | [`skills/ai-image-generator`](skills/ai-image-generator/SKILL.md) | 配图能力层：模型选择、DashScope 调用、多视角、风格库、配图索引 |
| **article-image-angles** | [`skills/article-image-angles`](skills/article-image-angles/SKILL.md) | 配图多视角分析，给候选提示词 |
| **article-image-styles** | [`skills/article-image-styles`](skills/article-image-styles/SKILL.md) | 配图风格库管理（S01–S10 等） |
| **article-review-tracker** | [`skills/article-review-tracker`](skills/article-review-tracker/SKILL.md) | 审稿意见结构化追踪、逐条落实 |

**调用链**：

```
wechat-article-writer（入口）
   └─转发→ document-pipeline（引擎）
              ├─调用→ article-proofreading（审稿）
              └─调用→ ai-image-generator（配图）← article-image-angles / article-image-styles 增强
                       article-review-tracker（用户给审稿意见时）
```

---

## 快速使用（其他智能体 git 到本地后）

### 1. 克隆

```bash
git clone https://github.com/TashanGKD/tashan-wechat-skills.git
cd tashan-wechat-skills
```

### 2. 安装到你的智能体 skill 目录

因为每个 skill 自包含，**把整个 skill 目录复制过去即可**。

**Claude Code**（放到项目级或全局）：

```bash
# 项目级：仅当前项目可用（推荐，跟着项目走）
mkdir -p <你的项目>/.claude/skills
cp -R skills/* <你的项目>/.claude/skills/

# 或全局：所有项目可用
cp -R skills/* ~/.claude/skills/
```

**Cursor**：

```bash
mkdir -p <你的项目>/.cursor/skills
cp -R skills/* <你的项目>/.cursor/skills/
```

也可以用脚本一键安装（默认装到当前目录的 `.claude/skills/`，不覆盖已存在的同名 skill）：

```bash
bash scripts/install.sh                       # → ./.claude/skills/
bash scripts/install.sh ~/.claude/skills      # 指定目标
bash scripts/install.sh <目标> --force        # 允许覆盖同名
```

> ⚠️ **新会话才生效**：skill 在智能体会话启动时扫描一次。装好后需**新开一个会话**才能被发现和调用。

### 3. 触发

新会话里，自然语言即可触发入口 skill：

- 「写一篇公众号文章」「帮我把这篇写完」「补全这篇文章」→ `wechat-article-writer`
- 「审稿」「review 一下」→ `article-proofreading`
- 「生成配图」「画一张信息图」→ `ai-image-generator`

### 4. 路径约定（重要）

SKILL.md 里出现的 `references/…`、`assets/…`、`templates/…`，**都相对该 skill 自己的目录**（SKILL.md 所在目录）解析。所以整目录复制走就能自洽，不要拆散。

### 5. 配图需要 API key

`ai-image-generator` 直连阿里云 DashScope 生成配图，需要环境变量（否则只有配图这一步跑不了，写作/审稿/HTML 转换不受影响）：

```bash
export DASHSCOPE_API_KEY=...        # 首选
# 或 export AI_GENERATION_API_KEY=...
```

⛔ 切勿把密钥写进 skill 或提交到仓库。见 [SECURITY.md](SECURITY.md)。

---

## 如何更新

本仓库是**单一真源**，更新只走 git：

```bash
cd tashan-wechat-skills
git pull                    # 拉取最新
```

- 若你之前是**复制**到 `.claude/skills/`：`git pull` 后重新执行第 2 步（或 `scripts/install.sh <目标> --force`）覆盖旧版。
- 若你之前是**软链**（`ln -s`）到 skill 目录：`git pull` 即自动生效，无需再复制。
- 每次更新前先看 [CHANGELOG.md](CHANGELOG.md)：版本号遵循 [SemVer](https://semver.org/lang/zh-CN/)，**MAJOR 版本含破坏性变更**，务必读迁移说明。

**想改进并贡献回来**：见 [CONTRIBUTING.md](CONTRIBUTING.md)（开分支 → conventional commit → PR）。不要在自己的副本里改了就算，改动请回流到本仓库，避免各处副本漂移。

---

## 仓库结构

```text
.
├── skills/                  # 7 个 skill，每个自包含（SKILL.md + references/ + assets/ + templates/）
├── docs/                    # 使用与更新指南
├── scripts/install.sh       # 一键安装到 skill 目录
├── manifest.yml             # skill 清单
├── CHANGELOG.md             # 版本变更记录（SemVer）
├── CONTRIBUTING.md          # 贡献 / 更新回流规范
├── SECURITY.md              # 密钥与安全策略
├── LICENSE                  # MIT
├── README.md / README.zh-CN.md
```

---

## 出品与支持

- 出品：中国科学院大学他山学科交叉创新协会 · 他山 AI 宣讲团
- 官网：tashan.ac.cn ｜ 跨学科交流平台（内测）：world.tashan.chat

许可证：[MIT](LICENSE)。排版/写作规范文档（`references/`）为协会公众号实践沉淀，随 skill 一并发布，供复刻他山排版风格使用。
