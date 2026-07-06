# 首次落地实录：clone → 全局注册 → 在新（非 git）仓库建对话树+记忆库的问题清单（附原始证据）

> 来源：2026-07-07，一次真实落地过程。任务链：`git clone` tashan-wechat-skills → 把 `team-collab`/`recall-memory` **全局**注册进 `~/.claude/skills/` → 在 `/Users/boyuan/softmatter`（**不是 git 仓库**）建对话树 + 语义记忆库（`--person Boyuan`）。
> 环境：macOS（Darwin 25.3）· 系统 `python3` = `/usr/bin/python3` = **Python 3.9.6**（无 `python`、无 `py`）· 无 conda。
> 定位：性质同 [`retrieval-issues-and-divergent-protocol.md`](./retrieval-issues-and-divergent-protocol.md)（recall-memory 的问题实录），但覆盖**安装 / 建树 / 建库首次落地**这一段。每条都附**原始命令 + 输出**为证。**修复状态见下「修复状态」节**：#1–#5 均已在 macOS 上就地修并验证；仅剩两处**设计判断**留给维护者——#3 的 `long-id` 是否过度脱敏、#1 的「缺省是否改用 cwd 上溯替换安装路径反推」。
> 复现说明：除特别标注外，问题与操作系统无关（REPO 推导、脱敏计数、CLI 契约都是平台无关逻辑）。

## 摘要表

| # | 级别 | 问题 | 根因位置 | 一句话建议 |
|---|---|---|---|---|
| 1 | **P1** | 全局安装时 `build_session_tree.py` 把 REPO 误解析成用户 home，会往 `~/团队协作记录/` 写、marker 变 `boyuan` | `build_session_tree.py:24,29,32`（REPO 由**脚本安装路径**反推，无 `--repo`、无护栏） | 加 `--repo`；缺省用 **cwd 上溯**找项目根而非安装路径；REPO 落到 home/非项目时**拒绝并提示** |
| 2 | P2 | 建库脚本打印的检索提示是 **Windows-only**（`py -3.12 …`），mac/Linux 复制即 `command not found` | `build_memory_index.py`（末尾提示行，见 E5） | 按平台给命令，或直接打印 `sys.executable` |
| 3 | P2 | 每节点 `脱敏命中: N` 显示的是**「累计到此」的 running total**（对话10 头写 11277，文件里只有 21），因跨节点共享同一 `counts` | `build_session_tree.py:300` 一个 `counts` 传给每个节点的 `render()`；`render()` 用 `sum(counts)`（`make_transcript:99`） | `render()` 改用**本次增量** `sum(counts)-起始` 作每节点计数 |
| 4 | P3 | 首次在**无依赖机器**上建库需手动搭 venv：系统 `python3`(3.9.6) 无 `chromadb`，`python`/`py` 都不存在 | 依赖未随附；`ensure_vector_stack` 探测全失败时只报错不给 venv 步骤 | README/SKILL 增补 macOS/Linux 的 venv 建法；探测全失败时打印「建 venv」的具体命令 |
| 5 | P3 | `--person` 必填、无默认、对首次/单人建树无引导 | `build_session_tree.py:143` | 文档给「个人用就填你的 handle」示例；或缺省时交互提示而非直接退出 |

另有「部署/环境注意」若干（非脚本缺陷）见文末第二节。

---

## 修复状态（2026-07-07 · 5 项均已在 macOS 修并验证）

> 落地者在 macOS 上把 5 项都就地修了、逐项实测；只剩两处**设计判断**留维护者（文末各条注明）。改动 6 个文件。

- **#1 ✅ 已修+验证** — `build_session_tree.py` 加 `--repo`（显式项目根、覆盖安装路径反推；全局安装也能建任意仓库），并透传给 `verify_tree.py`；未传 `--repo` 时保留**护栏**（REPO 把 `~/.claude` 包在内=全局误判 → 拒绝并指路）。实测：全局安装**无** `--repo` `--list` → 拒绝（exit 1、未建 `~/团队协作记录`）；全局 `--repo /…/softmatter --list` → 列 182（exit 0）；`--repo` 子集建树 → `verify ✓ 全过`（证明透传到 verify）。回归：护栏对成功路径字节零影响（冻结源 261==261）。**留维护者**：是否把「缺省」也从安装路径反推改成 cwd 上溯（首次建树时 `团队协作记录/` 尚不存在、`resolve_repo` 会落回安装路径，故缺省未改）。
- **#2 ✅ 已修+验证** — `build_memory_index.py` 检索提示改按平台。实测：重建索引打印 `检索：python3 …`。
- **#3 ✅ 已修+验证** — `make_transcript_claudecode.py` `render()` 改用**本次 render 的命中增量**作每节点 `脱敏命中`，不再跨节点累计。实测（25 会话子集）各节点头部 `59 0 0 5 81 21 3 7 0 0 0 0`（**非单调** → 确为每节点；旧版会一路涨到总数 381），40 个干净节点 header==文件内标记数。**留维护者**：`long-id`（旧总报告占大头）是否把 uuid/hash 当 PII 过度脱敏——属规则判断，放宽有漏真 PII 风险，未改。
- **#4 ✅ 已修+验证** — `recall-memory/SKILL.md` 增 macOS/Linux venv 说明 + 「首次搭建」③；`_vector_env.py` 两处「无依赖」失败提示加入可粘贴的 ③ venv 命令。实测：系统 `python3`（无依赖）运行打印含 venv recipe 的新提示。
- **#5 ✅ 已修+验证** — `--person` 加 `help`（举例 `Boyuan`）+ 非法值报错带示例。实测：`--person 'bad name!'` → `只用字母/数字/下划线/连字符/中文，如 Boyuan / XX78`；`--help` 显示引导。（未加交互式 prompt：非交互场景是 footgun。）

---

## 一、脚本/工具层问题（每条附原始证据）

### 1.1 【P1】全局安装时 REPO 被误解析到用户 home 目录

**场景**：用户要求把 `team-collab` **全局**注册（`~/.claude/skills/team-collab`，软链到 clone）。README 与 SKILL.md 都把全局安装列为可选项，SKILL.md 还称本 skill「仓库无关，放进任意 `.claude/skills/` 即可用」。

**问题**：`build_session_tree.py` 的目标仓库**不是**由 cwd 或参数决定，而是由**脚本自身的安装路径**反推：

```
build_session_tree.py:24  HERE = os.path.dirname(os.path.abspath(__file__))
build_session_tree.py:29  REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
build_session_tree.py:32  REPO_MARKER = os.path.basename(REPO)   # 自动取当前仓库目录名，不写死项目
```

它假定安装在 `<repo>/.claude/skills/team-collab/scripts/`（四级 `..` 正好回到 `<repo>`）。**全局安装**时四级 `..` 从 `~/.claude/skills/team-collab/scripts` 回到的是**用户 home**。且**没有 `--repo` 参数**可覆盖（CLI 只有下列 flag）：

原始证据（实测两种安装位置各自解析出的 REPO）：
```
# 全局安装那份（~/.claude/skills/team-collab）：
REPO   = /Users/boyuan
MARKER = boyuan
# 项目级安装那份（softmatter/.claude/skills/team-collab）：
REPO   = /Users/boyuan/softmatter
MARKER = softmatter
```
```
# 所有 CLI flag（无 --repo）：
add_argument("--person")  add_argument("--src")  add_argument("--manifest")
add_argument("--out")     add_argument("--list") add_argument("--keep-stubs")
add_argument("--adapters")add_argument("--with-subagents")  add_argument("--if-stale")
# 脚本内 "--repo" 出现次数：0
```

**后果**：若直接用全局那份建树，会以「home 目录」为项目、marker=`boyuan` 去跨项目扫会话，并把 `团队协作记录/` 写进 `~/`。这与「仓库无关、全局可用」的文档承诺**直接矛盾**——对脚本这一半不成立。（本次是靠先读源码发现，改为在目标仓库里**另装一份项目级软链**才建对，代价是同一 skill 现存两份安装。）

**建议**（择一或组合）：
1. 增加 `--repo <path>` 显式指定；
2. 缺省不再用安装路径，而是**从 cwd 向上找项目根**（`_vector_env.resolve_repo` 已经是这套逻辑，可复用/对齐）；
3. **护栏**：解析出的 REPO 等于用户 home 或不含项目标志（无 `.git`/`团队协作记录/`/`CONTRIBUTING.md`）时，**拒绝执行并打印指引**，而不是静默往 home 写。

### 1.2 【P2】建库脚本打印的检索提示是 Windows-only，在 mac/Linux 复制即失败

**场景**：`build_memory_index.py` 跑完，末尾打印「下一步怎么检索」的提示。

**问题**：提示写死 Windows 的 `py -3.12` 启动器，macOS/Linux 上没有 `py`，用户照抄即 `command not found`。

原始证据（本次 mac 上的建库输出，`index.log:164`）：
```
检索：py -3.12 .claude/skills/team-collab/scripts/query_memory.py "<问题>" --person Boyuan
```

**建议**：提示行按平台选命令（Windows→`py -3.12` / 其它→`python3` 或已探测到的解释器），或直接回显 `sys.executable`。SKILL/README 里同类 `python3` 示例也应对 mac「`python3` 可用、`python` 不存在」的情况说明。

### 1.3 【P2】每节点 `脱敏命中: N` 是「累计到此」的 running total（非本节点计数）—— ✅ 已修

**场景**：建树给每个 `段.md` 头部写「脱敏命中: N 处」，建库结束再打印总报告。用户会据此判断「本节点挡了多少 PII」。

**问题（真因，已据源码确认）**：`build_session_tree.py:300` 建**一个** `counts={}`，遍历节点时把**同一个** `counts` 传给每个节点的 `render()`（`:331`）；而 `render()` 用 `sum(counts.values())` 当本节点头部计数（`make_transcript_claudecode.py:99`）。于是每个节点头部显示的是**渲染到该节点时的累计命中**、而非它自身——越靠后数字越大，最后一个≈全库总数。

> ⚠️ **更正**：本文早先猜测是「render 前全文命中、render 后截断丢弃」，**经查源码不成立**——`render()` 把 `tool_use`/`tool_result` 连同脱敏一起 emit 进 `段.md`（`make_transcript:96,98`），并未丢弃。真因是**跨节点共享 `counts`**。

原始证据（同一个节点：build 总数 / 该节点 header 声称 / 该节点 `段.md` 实际标记）：
```
# 建库总报告：
── 脱敏报告 ── 共 13250 处
   long-id: 10646   email: 1935   wechat-id: 349
   cred-kv: 156     cn-phone: 78  api-key: 69   jwt: 17

# 节点「对话10（2ca014c5）」段.md 头部声称：
> 处理: 仅格式转换 + 脱敏，无 AI 提炼 | 脱敏命中: 11277 处

# 同一个 段.md 里实际存在的 [已脱敏:*] 标记：
count: 21
     21 已脱敏:email          # long-id 标记数 = 0
```
即：11277 是「渲染到 对话10 时的累计」（该节点靠后），并非它自身；它自己的 `段.md` 只有 21 处（全 email）。

**修复**：`render()` 进入时记 `_red_start = sum(counts)`，末尾用 `sum(counts) - _red_start` 作本节点头部计数与返回值；共享 `counts` 仍供总报告累计。**实测**（25 会话子集）各节点头部 `59 0 0 5 81 21 3 7 0 0 0 0`（非单调递增 → 确为每节点；旧版会一路涨到总数），40 个「干净」节点 header==文件内标记数（其余 6 个仅因该会话正文里含 `脱敏命中`/`已脱敏` 字样而差 1~10，是测量假象）。

**留维护者（未改）**：`long-id`（旧总报告占 10646）是否把 session uuid / git sha / 参数 hash 当 PII 过度脱敏——属**规则**判断，放宽有漏真 PII 风险，未动。

### 1.4 【P3】首次在无依赖机器上建库要手动搭 venv，脚本探测全失败时不给建法

**场景**：`build_memory_index.py` 需要 `chromadb`+`sentence-transformers`；`ensure_vector_stack` 会按 `TC_VECTOR_PYTHON`→`python3`→`python`→`py` 顺序探测带依赖的解释器。

**问题**：全新 mac 上**没有任何候选带依赖**，系统 `python3` 是 3.9.6 且无 chromadb，`python`/`py` 不存在——探测必然全失败，只能报错。本次是我手动建了独立 venv（`~/.venvs/tc-vector`）并用它跑。

原始证据：
```
which python3: /usr/bin/python3
which python:  python not found
Python 3.9.6
ModuleNotFoundError: No module named 'chromadb'
```

**建议**：README/SKILL 增补 macOS/Linux 的一步式 venv 建法（`python3 -m venv … && pip install chromadb sentence-transformers`，再 `export TC_VECTOR_PYTHON=…`）；`ensure_vector_stack` 探测全失败时，除现有报错外**直接打印这段建 venv 的命令**，而不是让用户自己想。

### 1.5 【P3】`--person` 必填、无默认、对首次/单人建树零引导

**场景**：任何建树命令都要 `--person`；用户没有既有身份、也不知道该填什么。

**问题**：`--person` `required=True`、无默认、文档未对「单人/首次」给建议，导致要么卡住、要么像本次一样由执行者**擅自代填**（本次填了 `Boyuan`，用户事后认可，但当时是无确认的假设）。

原始证据：
```
build_session_tree.py:143    ap.add_argument("--person", required=True)
```

**建议**：文档明确「个人自用就填你自己的 handle（如账号名）」并给例；或缺省时**交互式提示**而非直接 `SystemExit`。

---

## 二、部署 / 环境注意（非脚本缺陷，但影响落地，值得写进文档）

- **目标仓库非 git 时，skill 的另一半是「哑」的**。本次 `softmatter` 不是 git 仓库：
  ```
  $ git -C /Users/boyuan/softmatter rev-parse --show-toplevel
  fatal: not a git repository (or any of the parent directories): .git
  ```
  对话树 + 记忆库是**纯本地产物**、正常生成；但**协作发帖、格式/PII 的 git-hook gate、记忆的 git 同步全部不激活**。尤其：保护人写 `研究历程.md`/`动机日志.md` 的 `check_pii` 是 git hook——非 git 仓库里它**不生效**，笔记若日后填入 PII 无自动拦截。建议文档显式区分「仅建树+建库不需要 git」与「协作那半需要 `git init` + bootstrap」。
- **因 1.1 现同一 skill 装了两份**：全局一份（供发现 / SKILL 指引 / 协作），项目级一份（脚本真正用的）。文档应点明「**任何跑脚本的操作必须用项目级安装那份**」。
- **软链单点依赖**：全局 `team-collab`、项目级 `team-collab`、全局 `recall-memory` 三条软链都指向同一个 clone（`~/tashan-wechat-skills`）。`git pull` 能一次更新全部；但该 clone 一旦删/移，三处同时失效。采用软链安装时值得在文档提示这点。

---

*本文第一节报问题、第二节记环境注意；「修复状态」节记本次已在 macOS 就地修并验证的 5 项（仅剩两处设计判断留维护者）。其余按仓库 `CONTRIBUTING.md` 开分支 + conventional commit + PR。*
