---
name: recall-memory
description: >-
  语义召回**本项目过去的对话记忆**——当你需要想起"我们以前是不是做过 / 讨论过 / 决定过某件事"、
  "上次那个结论 / 脚本 / 网页 / 报错 / 参数是在哪个会话弄的"、"回顾一下之前关于 X 的讨论"、
  "我记得做过 Y，找出来"时，用本 skill 去检索 team-collab 建的**对话树记忆向量库**，
  拿到按语义排序的命中：每条带 节点摘要 · session · **真源指针(原始 .jsonl 路径)** · 段.md 与跳转锚，
  命中后可顺真源下钻读无损原文。**务必在这些"回忆过去工作"的场景主动使用**，即使用户没说"检索"二字——
  这是 AI 把过去对话当"记忆"随时调取的入口，比裸 grep 本地 jsonl 快且准。若这个仓库还从没建过语义记忆
  索引（第一次用），本 skill 同样是**建索引的入口**——见下文「首次搭建」。
  边界：本 skill 只管**自己过去的对话/工作记忆**；找**外部论文/文献**请用 `search-literature`（若已安装该
  文献库 skill）；读一个已知路径的 PDF 用 `read-pdf`；只是想**重建/归档**对话树本身看 `team-collab`。
---

# recall-memory —— 语义召回过去的对话记忆

把 `team-collab` 生成的**对话树**（本地 Claude Code 会话的去重镜像 + 人写的研究历程/动机）嵌成向量库，
让你能**按意思**找回过去做过/决定过的事，而不是靠关键词碰运气或裸 grep 一堆重复的 jsonl。

它是 team-collab「读本地历史对话」协议的**第②步检索引擎**：语义命中 → 拿真源指针 → 下钻回原始 jsonl 读无损细节。
引擎脚本都在 `team-collab/scripts/`（`build_memory_index.py` 建库、`query_memory.py` 检索、`memory_daemon.py`
常驻加速）——本 skill 自己不带脚本，是对它们的一层薄前端 + 使用说明。

## 什么时候用（主动触发）

- "我们以前是不是做过/讨论过/决定过 X？" · "上次那个结论/脚本/网页/报错/参数在哪个会话？"
- "回顾一下之前关于 X 的讨论" · "我记得做过 Y，帮我找出来" · "之前为什么选了 A 不选 B？"
- 任何"把过去的对话当记忆调取"的场景——**不必等用户说"检索"**。
- **这个仓库还没建过语义记忆索引**（第一次接触/新仓库）：本 skill 也是入口，见下「首次搭建」。

**不要用在**：找外部论文/文献（若装了 `search-literature` 之类的文献库 skill，用那个）；
读已知路径的 PDF（→ `read-pdf`）；重建或归档对话树本身（→ `team-collab`）。

## 前提：先有对话树

语义记忆库建在 `team-collab` 的**对话树**之上，所以要先有它：

> ⚠️ **Windows 注意**：默认 `python3` 常是 Microsoft Store 的空壳别名，直接报 `Python was not found…`——
> 它在 Python 启动**之前**就拦截，脚本内部的自动探测救不了外层命令。那就把下面所有 `python3` 换成 **`python`**
> （缺依赖时脚本会自动转到装了 chromadb 的解释器），或直接用绝对路径 / `py -3.12`。示例写 `python3` 只是通用写法。

```bash
python3 .claude/skills/team-collab/scripts/build_session_tree.py --person <你代表谁>
```

如果这一步还没做过，去读 `team-collab` 的 SKILL.md/`references/worklog.md`（对话树怎么建、什么是「段」/「节点」）。
对话树已建好、只是**语义索引还没建**（即将首次给这个仓库/这个人建记忆库）时，接着看下一节。

## 首次搭建：这个仓库/这个人还没建过记忆索引

```bash
# 装了 chromadb + sentence-transformers 的解释器都行；缺包时脚本会自动探测 python3/python/py 等候选并转过去运行
python3 .claude/skills/team-collab/scripts/build_memory_index.py --person <你代表谁>
```

它做的事：读对话树每个节点（`段.md` + 研究历程/动机）→ 切成"记忆卡"(节点摘要，人写、高信号) 和
"段块"(对话原文分块，含文件名/工具调用) 两类 → 用一个轻量多语种嵌入模型向量化 → 存进本地 chromadb，
落在 `团队协作记录/智能体工作日志/<person>/记忆向量库/`（在 `对话树/` 之外，不受它的重建影响）。
**首次跑是全量建库**（之后重跑是增量 upsert，只处理新增/变化的节点，用 `--rebuild` 才强制全量重嵌）。

跑完你会看到类似"记忆向量库就绪 · collection 'worklog_memory' 共 N 块"——出现这行就说明库建好了，
可以直接进入下一节检索。若报错**找不到 chromadb 的解释器**：任选其一——① 当前解释器
`pip install chromadb sentence-transformers`；② 设环境变量 `TC_VECTOR_PYTHON` 指向一个已装好它们的
解释器（比如某个 conda 环境的 python）。

## 检索（建好索引之后）

> **★ 标准流程 = 发散式检索，不是"查一次就收工"**——把记忆检索当**文献调研**做（同一套心法，来源从论文库换成对话记忆库）：
>
> 1. **多角度 / 多措辞发散查**：同一概念可能用**完全不同的措辞**散落在不同节点（embedding 对措辞敏感——搜"科研思维"
>    未必命中"公式推导格式""写作规范条款""文献调研方法论"）。一个问题**拆成几条不同角度 / 不同措辞的查询分别搜**，
>    别指望一个词查全。（和 team-collab 文献调研方法论同一件事：先把问题拆成多个轴，而不是一个搜索词查到底。）
> 2. **每条命中读三层**：① `背景`（这条命中属于哪条研究线 / 根对话——query_memory 已自动给出）；
>    ② `上下文`（`--context` 的相邻轮）；③ **整段**（用 **`Read`** 打开命中的 `段.md` 拿完整细节——输出末尾的
>    "读整段"清单直接列了路径）。只看 snippet/上下文＝把索引当内容，会漏真正的来龙去脉。
> 3. **顺线索滚雪球**：命中里冒出的新名词 / 文件名 / 会话 id，是**下一轮查询的种子**（类似向前 / 向后追引用）——
>    继续发散查它们；也可去 `对话树/TREE.md`/`目录.md` 看那条研究线还挂着哪些相邻节点。
> 4. **停止条件 = loop-until-dry**：连续几轮发散都挖不出新节点 / 新线索了，才算查完；不是第一轮命中几条就收工。
>
> （详规与踩坑见 [`references/retrieval-issues-and-divergent-protocol.md`](./references/retrieval-issues-and-divergent-protocol.md)。）

```bash
# ★ 在仓库根目录下运行，或显式加 --repo <仓库根>。解析 JSON 用 2>/dev/null（别 2>&1）。
# 发散：同一问题换 3-5 种角度/措辞各查一次，别只查一条。
python3 .claude/skills/team-collab/scripts/query_memory.py "<自然语言问题>" --person <你代表谁> --k 6 --context 2 --json 2>/dev/null
```

- **必须在仓库根 cwd 下跑，或加 `--repo <仓库根>`**：脚本按 cwd 上溯定位仓库，所以全局装的脚本路径也能用——
  但若 cwd 不在仓库内又没传 `--repo`，会报"找不到记忆向量库"（它会同时告诉你当前解析到的 repo 路径，方便判断）。
- `--kind card` 只搜节点记忆卡（人写摘要，最凝练）；`--kind seg` 只搜对话原文块（含文件名/原话）；不加=两者都搜。
- `--context N`（默认 1）：每条命中额外带同节点**相邻 N 个对话块**，直接给出更宽的上下文；调大更全。
- **秒回靠常驻 daemon**：query 会**优先走 daemon**（毫秒级）；daemon 没开则**首次冷查询较慢**（要冷加载嵌入模型
  和依赖库）并**自动把 daemon 拉起**，之后就秒回。加 `--no-daemon` 可强制冷查询。
  - 手动控制：`python3 .claude/skills/team-collab/scripts/memory_daemon.py --person <你代表谁> [--status|--stop]`
    （不带 flag=前台启动；daemon 常驻、模型只加载一次、库被重嵌后自动重开 collection）。
  - 想让它**开机自启**（不必等第一次冷查询触发）：见 `memory_daemon.py` 文件头的说明，按你的系统
    （Windows 任务计划程序/注册表 Run 项，或 macOS launchd / Linux systemd）加一条自启项，指向该脚本 +
    `--person <你> --repo <仓库绝对路径>`（自启时 cwd 未定义，务必用绝对路径）。

**读结果 → 必须下钻**（接 team-collab 读协议第③步）：每条命中带 `摘要`、`snippet`、`上下文`、`session`、`真源(source_files)`、`段.md`、`锚点`。

> ⚠️ **`snippet`/`上下文` 只是"定位"，不是答案。** 它们告诉你"在哪个节点、哪一轮"，但**不足以回答"为什么这么做 / 当时怎么讨论的 / 做了哪些决定 / 来龙去脉"**。只凭 snippet 就作答＝把索引当内容——会漏掉真正的上下文。
>
> **凡是要回答"为什么/怎么做/前因后果"，务必先读原文再作答**：
> 1. 快速看：把命中节点的 `段.md`（去重后的**完整对话**、已脱敏）按 `锚点` 时间定位那几轮、前后多读几轮；
> 2. 要逐字/工具入参与结果：`真源` 指向的原始 `.jsonl` **在本机可读**（你是所有者）→ 打开它按 `锚点` 时间/uuid 定位，读**无损全文**；不是所有者（源不在本机）→ 以 `段.md` 为准。
> 3. 光"找文件在哪"这类事实题，直接读目标文件最硬；但"围绕它的决策与讨论"必须读对话上下文，别省这步。

## 若怀疑"最近的对话还没进索引"（先更新再检索）

索引是某次 build 的快照。若要找的是**刚刚/今天**的对话、检索却没命中，先刷新对话树与索引再查（治过期快照）：

```bash
# ① 刷新对话树（--if-stale：有新增/增长才重建，否则秒过） ② 增量重嵌新节点
python3 .claude/skills/team-collab/scripts/build_session_tree.py --person <你代表谁> --if-stale
python3 .claude/skills/team-collab/scripts/build_memory_index.py --person <你代表谁>
```

日常检索不必每次刷新（慢）；只在"明知有很新的对话没被召回"时才刷。

## 与文献检索的关系

若这个仓库还装了别的知识库检索 skill（比如某个文献库的 `search-literature`），`recall-memory`（对话记忆）
与它**各管一摊、互不冲突**：不同向量库、不同 collection、不同环境变量前缀，顶多共用嵌入模型的本地缓存。
找"我们做过什么"用本 skill；找"有哪篇论文/文献讲什么"用对应的文献检索 skill。

## 引擎在哪 / 怎么维护

- 建/更新索引：`team-collab/scripts/build_memory_index.py`（对话树 → 向量 → chromadb，增量 upsert，`--rebuild` 全量）。
- 检索：`team-collab/scripts/query_memory.py`；常驻加速：`team-collab/scripts/memory_daemon.py`；
  三者共用的仓库定位/依赖探测逻辑在 `team-collab/scripts/_vector_env.py`。
- 存储：`团队协作记录/智能体工作日志/<person>/记忆向量库/`（在 `对话树/` 之外，免被重建时清掉）。
- 默认嵌入模型是一个轻量多语种模型（几百 MB，冷加载快、常见消费级 GPU 显存也够）；要更高检索质量可设
  `TC_EMBED_MODEL=BAAI/bge-m3`（显存/下载体量都大得多，见 `build_memory_index.py` 文件头注释）。
  **build 与 query 必须用同一个模型**（改了 `TC_EMBED_MODEL` 就要 `--rebuild` 重嵌）。

## 已知问题 + 检索协议改进方向

`references/retrieval-issues-and-divergent-protocol.md` 记录了一次真实调用中踩到的坑（`python3` 别名、
`--if-stale` 静默降级、Windows 控制台 Unicode 崩溃、HNSW 索引损坏的诊断与修复、查询结果超限、临时文件
路径）——每条都附原始报错/命令为证；以及一份**尚未实现**的"发散式检索协议"提案：查询要像文献调研一样
拆多个角度/措辞发散着搜，命中后返回"背景信息 + 局部上下文 + 命中所属整段"三层而不是只给局部上下文，
命中之后还要用新线索继续发散深挖（类似向前/向后追引用），而不是查一次就收工。遇到类似基础设施故障，
或要迭代检索协议本身时，先看这份文档。
