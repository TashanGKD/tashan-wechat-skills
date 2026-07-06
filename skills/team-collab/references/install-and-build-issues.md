# 首次落地实录：clone → 全局注册 → 在新（非 git）仓库建对话树+记忆库的问题清单（附原始证据）

> 来源：2026-07-07，一次真实落地过程。任务链：`git clone` tashan-wechat-skills → 把 `team-collab`/`recall-memory` **全局**注册进 `~/.claude/skills/` → 在 `/Users/boyuan/softmatter`（**不是 git 仓库**）建对话树 + 语义记忆库（`--person Boyuan`）。
> 环境：macOS（Darwin 25.3）· 系统 `python3` = `/usr/bin/python3` = **Python 3.9.6**（无 `python`、无 `py`）· 无 conda。
> 定位：性质同 [`retrieval-issues-and-divergent-protocol.md`](./retrieval-issues-and-divergent-protocol.md)（recall-memory 的问题实录），但覆盖**安装 / 建树 / 建库首次落地**这一段。每条都附**原始命令 + 输出**为证。**修复状态见下「修复状态」节**：#1(护栏) / #2 / #4 已在 macOS 上就地修并验证（本次落地时顺手修的、且都能在 mac 验证）；#3 / #5 / #1 的完整重设计留给读到本文的维护者。
> 复现说明：除特别标注外，问题与操作系统无关（REPO 推导、脱敏计数、CLI 契约都是平台无关逻辑）。

## 摘要表

| # | 级别 | 问题 | 根因位置 | 一句话建议 |
|---|---|---|---|---|
| 1 | **P1** | 全局安装时 `build_session_tree.py` 把 REPO 误解析成用户 home，会往 `~/团队协作记录/` 写、marker 变 `boyuan` | `build_session_tree.py:24,29,32`（REPO 由**脚本安装路径**反推，无 `--repo`、无护栏） | 加 `--repo`；缺省用 **cwd 上溯**找项目根而非安装路径；REPO 落到 home/非项目时**拒绝并提示** |
| 2 | P2 | 建库脚本打印的检索提示是 **Windows-only**（`py -3.12 …`），mac/Linux 复制即 `command not found` | `build_memory_index.py`（末尾提示行，见 E5） | 按平台给命令，或直接打印 `sys.executable` |
| 3 | P2 | **脱敏计数误导**：`脱敏命中: N` / 建库总数计的是 render **前**全文（多为随后被截断/丢弃的工具内容），与产物里实际标记数差 2~3 个数量级 | 计数发生在 `redact()`，`render()` 之后大量内容被丢弃/截断（见 E4） | 分报「原文命中」与「产物内保留」；复核 `long-id` 是否把技术 uuid/hash 当 PII 过度脱敏 |
| 4 | P3 | 首次在**无依赖机器**上建库需手动搭 venv：系统 `python3`(3.9.6) 无 `chromadb`，`python`/`py` 都不存在 | 依赖未随附；`ensure_vector_stack` 探测全失败时只报错不给 venv 步骤 | README/SKILL 增补 macOS/Linux 的 venv 建法；探测全失败时打印「建 venv」的具体命令 |
| 5 | P3 | `--person` 必填、无默认、对首次/单人建树无引导 | `build_session_tree.py:143` | 文档给「个人用就填你的 handle」示例；或缺省时交互提示而非直接退出 |

另有「部署/环境注意」若干（非脚本缺陷）见文末第二节。

---

## 修复状态（2026-07-07 · 已在 macOS 上修 3 项并验证）

> 落地者在 macOS 上把**能在 mac 验证、且不改成功路径**的 3 项就地修了并验证；其余留维护者。改动 4 个文件，每项附实测。

- **#2 ✅ 已修+验证** — `build_memory_index.py` 检索提示改按平台（`"py -3.12" if os.name=="nt" else "python3"`）。实测：重建索引后打印 `检索：python3 …`（不再 `py -3.12`）。
- **#4 ✅ 已修+验证** — (a) `recall-memory/SKILL.md` 增 macOS/Linux venv 说明 + 「首次搭建」③ 选项；(b) `_vector_env.py` 两处「无依赖」失败提示加入可直接粘贴的 ③ venv 命令（按平台）。实测：系统 `python3`（无依赖、`TC_VECTOR_PYTHON` 未设）运行时打印含 ③ venv recipe 的新提示。
- **#1 ⚠️ 部分已修（护栏）+验证** — `build_session_tree.py` 加护栏：解析出的 REPO 把 `~/.claude` 包在内（= 全局安装误判）时**拒绝并指路**，不再静默往 `~/团队协作记录` 写。实测：全局安装 `--list` → 拒绝（exit 1、未创建 `~/团队协作记录`）；项目级 `--list` → 照常列 182 会话（exit 0）。**回归**：冻结源（181 会话）下 edited-vs-original 双跑 `tree.json` **字节一致**（261==261），证明护栏对成功路径零影响。**未做**：完整 `--repo` 参数 / 缺省 cwd 上溯重设计（跨 `build_session_tree.py` + `verify_tree.py`、属设计变更）。
- **#3 / #5 / #1 完整重设计 — 未动**：#3 触及共享 `redact`/`report` + `check_pii` gate + 字节回归、且「该报什么数」是设计判断；#5 交互式 prompt 本身是 footgun，只宜文档化；#1 重设计跨 build+verify。

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

### 1.3 【P2】脱敏计数严重高于产物内实际标记数（计数口径误导）

**场景**：建树结束打印脱敏总报告；每个 `段.md` 头部也写「脱敏命中: N 处」。用户会据此判断「产物里有多少 PII 被挡掉」。

**问题**：报出的数字计的是 **render 前的全文**（含塞满 uuid/hash 的 `tool_use` 入参与 `tool_result`），而 `render()` 随后把这些内容**大量截断/丢弃**——所以最终 `段.md`（也是进入向量库的内容）里的实际脱敏标记，比报出的数字少 **2~3 个数量级**。

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
即：单节点声称 11277（占全库 13250 的绝大部分），但该节点唯一内容文件里只有 **21** 处、且全是 email；主导类型 `long-id`(10646) 在产物里**一个都没留下**——它们都在被丢弃的工具内容上。

**两个子问题**：
- (a) **计数误导**：`脱敏命中: N` 让人以为文件里满是被挡的 PII，实际产物很干净；应区分「原文命中数」与「产物内保留数」，或改为在 render/截断**之后**统计。
- (b) **疑似过度脱敏**：`long-id`(10646) 极可能是把 session uuid / git sha / 参数 hash 这类**技术标识符**当 PII。虽然这次它们多被截断掉、没污染产物，但计数口径 + 规则值得复核（研究仓库里技术长 id 很多）。

> 机制为**推断**（结合脱敏计数在 `redact()`、丢弃/截断在 `render()`）：请维护者据源码确认后再定改法。

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

*本文第一节报问题、第二节记环境注意；「修复状态」节记本次已在 macOS 就地修并验证的 3 项。其余修复请按仓库 `CONTRIBUTING.md` 开分支 + conventional commit + PR。*
