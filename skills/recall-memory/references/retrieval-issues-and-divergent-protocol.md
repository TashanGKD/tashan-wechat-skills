# 检索问题实录 + 发散式检索协议提案

> 来源：2026-07-06，一次真实的 `recall-memory` 调用（问题："回顾一下，之前我一共提到过哪些科研思维？"）。
> 本文档分两部分：**一、这次调用过程中实际遇到的问题**（每条都有原始工具/代码记录为证，不是复述印象）；
> **二、用户当场提出的"发散式检索协议"改进思路**（原话+我的理解确认，供后续把它落到 `query_memory.py`/本 skill 里）。
> 定位：`SKILL.md` 讲"怎么用"，这里记"这次用出了什么问题、以及协议该往哪改"——性质类似 team-collab 的
> `worklog-sync-test-checklist.md`（问题清单+证据），但专属 `recall-memory` 的检索质量与基础设施问题。

---

## 一、这次调用中实际遇到的问题（附原始证据）

### 1.1 默认 `python3` 不可用（环境问题，非 skill 本身的 bug）

**场景**：按 SKILL.md 指示直接跑 `python3 .claude/skills/team-collab/scripts/build_session_tree.py --person Alice --if-stale`。

**问题**：Windows 的 `python3` 是 Microsoft Store 的空壳别名，直接报错：
```
Python was not found; run without arguments to install from the Microsoft Store, or disable this shortcut from Settings > Apps > Advanced app settings > App execution aliases.
```

**我的处理/建议**：手动找到真正装了 chromadb/sentence-transformers 的解释器 `E:/conda/python.exe`，改用绝对路径调用。**建议**：SKILL.md 里"首次搭建"一节已经提到脚本会"自动探测 python3/python/py 等候选"，但这次并没有自动探测成功（直接在这个 shell 里跑 `python3` 就是硬报错，不是"探测后跳过"）——如果自动探测逻辑只在 `_vector_env.py` 内部生效（即只有 query/build 脚本本身内部会探测，而不是我在外层直接敲的 `python3` 命令行），那 SKILL.md 里给的示例命令本身就应该显式提示"如果你的默认 `python3` 是 Store 别名，直接给绝对路径"，而不是让使用者自己踩一次坑才发现。

### 1.2 `build_session_tree.py --if-stale` 静默地把"过期检查失败"兜底成了全量重建

**场景**：`--if-stale` 检查树是否需要重建。

**问题**（原始日志）：
```
--if-stale：检查 tree.json 失败：[WinError 2] 系统找不到指定的文件: '039b9bbd-a544-42de-af53-0f5ccbb1cf53'，→ 触发全量重建
```
这行日志本身不算错误级别的输出（没有 Traceback），很容易被当成正常信息略过，但它其实说明"过期检测"这个优化路径本身失败了一次，退化成了最慢的全量路径——如果不是我恰好扫了完整日志，不会注意到"本该秒过的检查"其实内部先失败了一次。

**我的建议**：这类"优化路径失败→兜底"的情况，建议输出上加一个明显的 `[WARN]` 前缀或换行强调，和"正常的 stale/fresh 判断结果"区分开，避免这种静默降级被忽略。

### 1.3 `build_session_tree.py` 最后一步因为 Windows 控制台编码崩溃（但实际工作已完成）

**问题**（原始 traceback）：
```
Traceback (most recent call last):
  File "T:\IOP\2025cell\.claude\skills\team-collab\scripts\build_session_tree.py", line 518, in <module>
    main()
  File "T:\IOP\2025cell\.claude\skills\team-collab\scripts\build_session_tree.py", line 494, in main
    print(f"✓ �������� �� {_rel}")
UnicodeEncodeError: 'gbk' codec can't encode character '✓' in position 0: illegal multibyte sequence
```
这次崩溃发生在**最后一条打印语句**（校验成功后打印 `✓` 勾号），也就是说**实际的树重建工作已经跑完并写盘了**，只是最后报喜的那一行 print 崩了，把整个命令的退出码变成了非 0，看起来像是彻底失败。

**验证方式**（我怎么确认它其实成功了）：
```bash
ls -la "团队协作记录/智能体工作日志/Alice/对话树/"
# tree.json 的 mtime 是刚跑完那一刻，且大小合理（4.68MB）——证明确实重写了
```

**我的建议**：这是一个明确、可直接修的 bug——`build_session_tree.py` 里凡是往 stdout 打印 Unicode 符号（✓ 之类）的地方，应该在 Windows 下用 `sys.stdout.reconfigure(encoding='utf-8')` 或者干脆换成 ASCII 替代（`[OK]` 而不是 `✓`），否则**每一次**在 GBK 控制台下跑这个脚本，最后都会以"看起来失败"收场，容易让使用者误判、重复无意义的重跑。

### 1.4 `记忆向量库` 的 HNSW 持久化索引已损坏（真实的基础设施故障，不是我这次操作造成的）

**问题**（原始 traceback，节选）：
```
· 增量：需 upsert 25 块，删除 0 块（库内已有 8989）
Traceback (most recent call last):
  ...
  File "...\chromadb\segment\impl\vector\local_persistent_hnsw.py", line 164, in _init_index
    index.load_index(
RuntimeError: Cannot open header file
```

**诊断证据**（检查 segment 目录内容）：
```bash
find "团队协作记录/智能体工作日志/Alice/记忆向量库" -maxdepth 2
# 只有：
#   2babcf26-5d3c-44de-9806-2cee391b8e05/index_metadata.pickle   <- 只剩这一个
#   chroma.sqlite3
# 缺：HNSW 的实际索引二进制文件（header.bin / data_level0.bin 等），大概率是之前某次构建被中断留下的半成品
```

**我先猜错的原因**：以为是 daemon 占着文件锁——`memory_daemon.py --stop` 后重跑，**同样的错误**，证明不是锁冲突，是真损坏。

**修复方式**：`build_memory_index.py --rebuild`（强制全量重嵌，9013 块），重建后恢复正常。

**我的建议**：`query_memory.py`/`build_memory_index.py` 遇到 `Cannot open header file` 这类"持久化索引损坏"的特征错误时，可以直接识别并给出明确提示（"索引可能已损坏，建议 `--rebuild`"），而不是让使用者自己去翻 segment 目录诊断——这个诊断过程本身没有技术含量，纯粹是体力活，脚本完全可以自动做。

### 1.5 查询结果过大，被转存文件，多一轮读取

**问题**：`query_memory.py "..." --k 10 --context 2 --json` 直接输出被截断：
```
Output too large (34.3KB). Full output saved to: C:\Users\<user>\...\bcv0qtxzs.txt
```
**影响**：不算 bug，但意味着"发散式多轮查询"（下面第二部分要提的协议）如果每次都开大 `--k`/`--context`，很容易撞到这个上限，需要多一步专门去读转存文件——**如果协议要求"命中后返回更长上下文+整段"，这个输出体量问题会更频繁地出现，值得在协议设计时一并考虑**（比如约定"完整段.md 直接用 Read 工具读，而不是让 query_memory.py 把整段塞进 JSON 输出"）。

### 1.6 临时查询结果文件路径写错地方

**问题**：为了避免上一条的截断，我把 `query_memory.py` 的输出重定向到 `/tmp_q1.json`，结果 Read 工具报错找不到文件；用 `cygpath`/`pwd -W` 查发现 Git Bash 的 `/` 实际映射到 `T:/LLMtest/Git`，不是我以为的临时目录。

**我的建议**：这不是 skill 本身的问题，是我自己该用规定好的 scratchpad 目录（`C:\Temp\claude\<session>\scratchpad`）却图省事写了裸路径。记在这里是为了提醒以后调用这个 skill 时，任何"转存查询结果再读"的操作都固定走 scratchpad，别再犯。

---

## 一（补）· 修复状态（2026-07-06 查根因 + 修复，附验证）

> 逐条在真实代码里查证了根因并修掉了 4 个基础设施 bug（CC 回归仍字节一致）。原始证据上面保留不删。

- **1.1 `python3` 桩** — ✅ 文档修。根因：Store 别名在 Python 启动前拦截，脚本内部自动探测救不了外层命令；
  `recall-memory/SKILL.md` 仍写 `python3`。**改**：SKILL.md 顶部加 Windows 注意（改用 `python`/绝对路径/`py -3.12`）。
- **1.2 `--if-stale` 静默降级** — ✅ 代码修（**这是 Step 3 引入的新 bug**）。根因：Cursor 的 discover 返回 composerId
  令牌，`--if-stale` 第 199 行 `os.path.getmtime(f)` 把它当路径 → `WinError 2: '039b9bbd-...'`（就是文档里那条）。
  **改**：给适配器加 `mtime_of()`（CC/Codex=文件 mtime，Cursor=globalStorage DB mtime），`--if-stale` 改用它、不裸 getmtime。
- **1.3 `✓` print GBK 崩溃** — ✅ 代码修。根因：`build_session_tree.py` 打 Unicode 但从不 reconfigure stdout。
  **改**：`main()` 开头 `sys.stdout/stderr.reconfigure(encoding="utf-8", errors="replace")`，GBK 控制台也不崩。
- **1.4 HNSW 孤儿索引** — ✅ 代码修（我上次修了一半）。根因：chromadb 只写 `index_metadata.pickle` 不写 `.bin`。
  上次加的 `ve.clear_orphan_hnsw` 只在 `build_memory_index` **末尾**，而增量 upsert 在**开库时**就撞孤儿。
  **改**：`clear_orphan_hnsw` 提到 `PersistentClient` **开库之前**（query/daemon 早已如此）；实测增量 upsert 不再报
  `Cannot open header file`。**遗留**：chromadb 每次操作后又写回孤儿 pickle，是"开库前清"的自愈式绕过，非根治
  （根治需换 chromadb 版本或改持久化策略）。
- **1.5 输出超限** — 设计问题（非 bug），并入下面发散协议一起考虑（约定"整段用 Read 读 段.md，别塞进 JSON"）。
- **1.6 临时路径** — 使用纪律：任何转存查询结果固定走 `C:\Temp\claude\<session>\scratchpad`，别用裸 `/tmp`。

---

## 二、用户提出的"发散式检索协议"（2026-07-06，原话理解整理）

### 背景：为什么会提出这个

同一次调用里，我先后错过了一份重要内容（`RESEARCH_VISION.md` 第八节"写作规范"的具体条款：公式推导格式、正文参数取值要求、图注逻辑、SI 一致性、审核机制）。用户追问"为什么之前搜索科研思维的时候没找到"，我复盘出两个真实原因：

1. **架构原因**：这份内容的原始会话 `cd231440`（2026-04-08）在本机任何地方都找不到（`.claude/projects`、`.codex/sessions`、`对话树/TREE.md` 全部没有），说明它从未被 team-collab 的对话树收录过。它唯一的存活痕迹，是**后来（2026-07-02）另一次做"全仓库巡检"的会话**里，agent 用 `Read` 工具读取了派生出来的 `RESEARCH_VISION.md` 文件，内容作为工具调用结果被整段贴进了那次会话记录——而那次会话同时还塞满了几百条别的文件读取结果，信号被严重稀释。这也说明：**语义记忆库只索引"对话记录"，不会主动索引项目里的普通文件**；一份文件的内容能不能被检索到，完全取决于它有没有"恰好被某次对话读过"。
2. **我自己的检索策略问题**：我只问了几个偏抽象概念层面的查询（"科研思维、方法论""学习方法论、知识图谱"……），从没有专门去搜"写作规范的具体操作条款"这类偏格式细节的内容；而且我把后来整理的 `写作规范.md` 当成了"写作规范"这件事的完整版本，没有交叉核实是否存在更早、独立、内容不完全重叠的源文档（`RESEARCH_VISION.md`）。

### 用户提出的核心类比

**记忆检索应该和文献检索用同一套心法**，而不是"想一个词、查一次、看有没有命中"。具体展开：

**1. 查询阶段要发散，像文献调研拆问题轴一样，搜多个不同角度、不同措辞的关键词。**
原因：语义 embedding 对措辞很敏感，同一个概念底下可能用完全不同的措辞散落在不同节点里（这次"科研思维"就没命中"公式推导"），只问一种问法必然漏掉用别的措辞记录的部分。这和我们已经记录过的文献调研方法论（[[对话29-分支1的方法论]]：先把问题拆成生物/数学/计算/软件/工程等多个轴，而不是一个搜索词查到底）是同一件事，只是换了检索对象（从论文库换成对话记忆库）。

**2. 每条命中返回的不该只是"命中处附近几轮对话"，而应该是三层：**

| 层级 | 内容 | 现状 |
|---|---|---|
| **背景信息** | 这个命中所属的整条研究线/项目脉络，为什么会有这次讨论 | 目前**没有**，靠人工去 `TREE.md`/目录.md 里查这个节点属于哪条线 |
| **命中处的局部上下文** | 命中前后紧邻的几轮对话 | 现有 `--context N` 部分做到了这层 |
| **命中所属的整个会话** | 不是几轮对话片段，是这个节点完整的 `段.md`、乃至真源 jsonl | 目前需要使用者自己手动去读 `段.md`（工具返回了路径，但没自动展开） |

三层缺一不可：只给中间那层（现状），遇到"这个片段到底在讨论什么大背景""这个节点还有没有更多相关细节"时就会不够用——这次能补出 `RESEARCH_VISION.md` 的完整内容，靠的正是我手动跳出片段、去读了完整原文件、又去追了它的来源会话，而不是靠单次查询自动给到的东西。

**3. 命中之后要继续发散，用命中里出现的新线索生成下一轮查询，滚雪球式深挖，而不是查一次就收工。**
这次真正带来信息增量的两个动作——"这份文档有没有被后来的规范继承进去"「这个原始会话到底存不存在」——都是**看到第一次命中之后才想到要问的新问题**，不是一开始就能问出来的。这正是文献综述里"向后追引用（它从哪来）/向前追引用（后来怎么发展）"的检索逻辑，只是对象换成了"这份记忆节点还连着哪些别的节点"。停止条件应该类似"loop-until-dry"——连续几轮发散查询都挖不出新节点/新线索了，才算真正查完，而不是第一轮命中了几条就当作任务完成。

### 待落地（尚未实现，仅记录协议本身）

这份协议目前只是**思路确认**，还没有改到 `query_memory.py`/`SKILL.md` 里。可能的落地方式（供下次讨论）：
- `query_memory.py` 增加一个"背景"字段：命中节点向上找它在 `TREE.md`/`思维导图.md` 里挂在哪条研究线下，随命中结果一并返回；
- 提供一个"整段读取"的便捷模式（而不是让使用者自己拼 `段.md` 路径再调 Read）；
- `SKILL.md` 里把"发散式多轮查询、命中后继续深挖"写成和 team-collab 文献调研方法论对齐的一段标准流程，而不是现在这种"查一次、下钻一次"的单轮范式。
