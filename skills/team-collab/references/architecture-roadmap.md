# 目标架构与现状缺口（路线图 · 待办）

> **状态：这是"要变成什么样"的路线图，不是"现在怎么用"的规范。** 其它 references（posting / worklog /
> conversation-log-spec / worklog-sync-test-checklist）写的是现行用法与已实现机制；本文件记录
> `team-collab` 记忆层的**目标架构**与**尚未兑现的缺口**，作为后续完善、并**最终随 skill 回流 GitHub 真源**
> （`tashan-wechat-skills`）的靶子。修一项就把对应缺口标 ✅ 并注明落点，全部收口后一并 PR 上游。

---

## 一句话背景

记忆层要解决的不是"某一个智能体的对话怎么存"，而是"**同一个项目、被多个智能体框架（Claude Code / Codex /
WorkBuddy / Qcoder …）在多台入口做过的所有工作，怎么按项目统一沉淀成一份可检索的记忆**"。现行实现只把
**Claude Code 单框架**这条路走通了；本文件把完整目标画清，并标出还差哪几步。

---

## 两个正交的三层

记忆层同时活在两个正交的维度上：一个是 **skill 自身怎么分发/治理**（纵轴），一个是 **每个项目的数据怎么堆叠**
（横轴）。别把两个"三层"混为一谈。

### 轴一 · 治理维度：skill 分发血脉

```
┌──────────────────────────────────────────────┐
│ L1  GitHub 唯一真源   (tashan-wechat-skills)    │
└──────────────────────────────────────────────┘
                ▲ 回流(push 改进)   │ clone
┌──────────────────────────────────────────────┐
│ L2  本地拷贝层        各用户 clone 到本机         │
└──────────────────────────────────────────────┘
                ▲ 提意见            │ 加载
┌───────────┬───────────┬───────────┬───────────┐
│ClaudeCode │  Codex    │ WorkBuddy │  Qcoder   │  ← L3 各框架适配层
│ ✓ 已装    │ ⚠ 仅占位  │ · 规划中  │ · 规划中  │    (每个框架各加载一份)
└───────────┴───────────┴───────────┴───────────┘
```

- **真源唯一在 GitHub**；每个用户、每个智能体入口各持一份。
- **改进必须能回流**；适配层之间不能各自漂移成互不相认的孤岛。
- 目标形态是 **"一核 + 多薄适配器"**：一个**框架无关的核心** + 每框架一个**薄适配器**，而不是把整份 skill 克隆
  N 遍再逐份手改（现状就是后者，见缺口 2）。

### 轴二 · 数据维度：每个项目一份记忆（按项目，不按智能体）

```
<某项目文件夹>/
  ┌────────────────────────────────────────────┐
  │ L1  向量库     语义检索(记忆向量库) · 统一      │  ▲ 嵌入
  ├────────────────────────────────────────────┤
  │ L2  对话树     段.md · 动机日志 ·               │  ▲ 解析·脱敏·按 uuid 去重
  │                研究历程 / 目录 / 思维导图 · 统一 │
  ├────────────────────────────────────────────┤
  │ L3  各框架原始记录 (各存各的、唯一按框架分的层)  │
  │       Claude Code : ~/.claude 的 jsonl        │
  │       Codex       : ~/.codex 的 rollout json  │
  │       其它框架    : WorkBuddy / Qcoder …       │
  └────────────────────────────────────────────┘
```

- **L1、L2 统一、框架无关**：一个项目一份，所有智能体入口共享同一份、统一检索/调用。
- **L3 是唯一按框架分的层**：各框架用各自格式各存各的原始记录。
- 数据单向上卷：`L3 →〔适配器：解析成统一原语 + 脱敏 + 去重〕→ L2 →〔嵌入〕→ L1`。
  skill 不产生 L3（L3 由各框架原生自己写）；skill 的活是**持续把新增的 L3 卷进 L2、再进 L1**，让记忆跟上工作。

### 两轴的接缝（桥）

**轴一底部的"各框架适配层"就是轴二 L3 的读入口。** 目标：任一入口都通过各自适配器
**读全局各框架的 L3、写同一份统一的 L1/L2**——组织单元是**项目**（跨框架、跨 cwd 都归一个项目），不是智能体。

---

## 现状落点（完善靶子）

图例：🟢 已实现　🟡 有风险 · 待核　🔴 缺失

| # | 状态 | 落点 | 问题 |
|---|---|---|---|
| 1 | 🟡 | 轴一 · GitHub 回流 | 本地拷贝已**领先** upstream（真源指针 / 读协议 / `--if-stale` / 语义库三兄弟 / daemon / `recall-memory` / **本轮的核心+适配器+三家支持**）；回流 `tashan-wechat-skills` **待做**（唯一剩项） |
| 2 | 🟢→🟡 | 轴一 · 拷贝/适配 | **CC 侧已重构成"框架无关核心 + `scripts/adapters/` 薄适配器"**（2026-07-05）。剩：Codex/Cursor 本体仍各持整份拷贝、未共享核心（纵轴分发面，后续） |
| 3 | 🟢 | 轴一 · Codex 适配 | ✅ **已落地**：`scripts/adapters/codex.py` 真适配器（扫 `~/.codex/sessions`、`response_item`→CC 形状、cwd 归属、import 接分支、噪声剥离、截断、流式）；`--adapters codex` 可跑 |
| 4 | 🟢 | 桥接 / 轴二 · L3 | ✅ **已落地**：`build_session_tree.py --adapters cc,codex,cursor` 跨三家读全局 L3、按项目 marker/cwd/folder 合并成**一片森林**（实测 121 会话→63 根/144 节点、verify 无损、CC 回归字节一致）；L1 向量库覆盖三家 |
| ✓ | 🟢 | 轴二 · L1/L2 | 向量库(L1，覆盖三家 8989 块) + 对话树(L2，三家一片森林) 建成、可检索；recall 命中 Codex/Cursor 带真源。**横轴去框架化完成** |

> **2026-07-05 本轮完成**：缺口 ③④ + ② 的 CC 侧全部落地（横轴数据维度去框架化）。剩：① GitHub 回流、
> ② 的纵轴分发面（把核心+适配器分发进 Codex/Cursor 本体、消除 3 份整拷贝）。工程细节见
> [`docs/`](../docs/README.md)（产品/架构/数据/测试/计划）。

---

## 依赖顺序（建议推进次序）

1. **缺口 2 先行（结构切分，是 3/4 的前提）**：把 `build_session_tree.py`（及 `make_transcript_claudecode.py`
   等）切成两层——
   - **框架无关核心**：按 uuid 去重、脱敏、渲染统一 md、脚手架、`tree.json`/思维导图、嵌入向量库；
   - **每框架薄适配器**：只回答三件事——"该框架的 L3 会话文件在哪、什么格式、怎么解析成统一原语
     `{角色, 时间戳, 文本, 工具调用, 工具结果, 血脉}`"（血脉 = CC 的 `uuid`/`parentUuid`、Codex 的
     `forked_from_id`/`turn_id` …）。
   适配器有地方挂了，才谈得上加新框架。
2. **缺口 3 / 4 并行**：写 Codex 适配器（读 `~/.codex/sessions/.../rollout-*.jsonl`，把
   `forked_from_id`/`turn_id` 映射成统一血脉）→ 让 build 能扫全局所有已适配框架、按项目 marker 跨框架合并成一棵树。
3. **缺口 1 收尾**：核心稳定、多适配器就绪后，把本地领先 upstream 的全部改进 + 本 roadmap 一并整理成 PR 回流
   GitHub 真源；三处本地拷贝再从真源重新拉齐，达到**零漂移**。

## 完成定义（Definition of Done）

- 一份框架无关核心 + N 个薄适配器；改核心**不需**逐份手改多个拷贝。
- `build_session_tree.py` 能扫全局**所有已适配框架**的会话，按项目 marker **跨框架**合并成一棵统一树；
  `verify_tree` / `check_pii` 全绿。
- 语义向量库覆盖跨框架节点。
- 全部改进**回流 GitHub 真源**，本地各拷贝从真源重新拉齐、零漂移。

---

## 本轮 scope：先把 Claude Code 做好（2026-07-05 决策）

聚焦**横轴 L1/L2 去框架化**，**由 Claude Code 这一份实现驱动**：让 CC 侧 skill 把
`Claude Code + Codex + Cursor` 三家 L3 按项目卷进统一的 **L2 对话树 + L1 向量库**。暂不分发可运行适配器到
Codex/Cursor 本体（那是纵轴，后续）。此步只有一个实现、只住在 CC 拷贝里，顺带绕开"3 份拷贝漂移"。

**侦察确证（本机真实数据）：**
- **Codex** `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`：`session_meta.payload.cwd` 即项目根（2025cell 有
  46 个会话）；`response_item` 流 1:1 映射统一原语（`message` role/content · `function_call(+_output)` ·
  `custom_tool_call(+_output)`；`reasoning` 加密→跳过）；基本线性、无 parentUuid 树。把握高。
- **Cursor** `…/Cursor/User/workspaceStorage/<hash>/state.vscdb`（SQLite）+ 全局库；归属靠
  `workspace.json` 的 `folder`（2025cell ≥5 个工作区）；聊天存 SQLite blob、**格式无文档、需逆向**。把握低、要先 spike。
- **跨框架重复**：`~/.codex/external_agent_session_imports.json` 的 `records` 表把 **CC 源 jsonl 路径 +
  content_sha256 → Codex 线程 id** 精确对应——可检测、可去重。

**已定决策：**
1. **三家一起上**（CC + Codex + Cursor 同轮接入）。理由：只有 ≥3 个真实实现同时在，才能逼出"哪些是适配层专属、
   哪些是通用核心"的干净边界——**用三家来解耦架构本身**。
2. **跨框架去重 = 接成分支，不是丢弃**。Codex Desktop 导入并续接过的 CC 会话，语义上就是"在 Codex 里给这棵 CC 树
   续了一根枝"→ 把该 Codex 会话**挂成对应 CC 节点下的 `分支（codex·…）`**（开头那段"导入摘要"是 CC 前文重述，
   比照 CC 去重重抄前缀的做法裁掉）。原生 Codex 会话（不在导入表里）= 自己的根 `对话N（codex·…）`。
3. **子目录上卷**：凡 cwd/工作区落在某项目根之下的（如 `…\2025cell\URDME20251221`），一律并进顶层项目
   `2025cell` 的**一片森林**；一个项目一份对话树 + 一份向量库。与现有 CC marker 行为一致。

**据此细化的适配器契约（每个源一个适配器，核心框架无关）：**
- `discover(项目根) → 本框架属于该项目的会话`（CC=marker grep · Codex=`session_meta.cwd` 上卷含子目录 ·
  Cursor=`workspace.json.folder` 上卷）；
- `parse(会话) → 统一原语 {角色, 时间戳, 文本, 工具调用(名,入参), 工具结果, 血脉, 来源工具, 真源}`；
- **血脉语义**：CC=`uuid`/`parentUuid` 树 + 按 uuid 去重；Codex/Cursor=线性、一会话一根；
- **新增 · 跨源续接指针** `continues_external={源工具, 源id/路径}`：核心据它把一家的会话接成另一家某节点下的
  分支（当前仅 Codex-import 需要，但为通用能力）——这是"跨框架血脉"，CC 单框架时不存在。

**推进次序（每步可验证）：** ① 先把 builder 切成「框架无关核心 + CC 适配器」、**行为零改变**（回归 = 重建仍是那棵
63 节点树、逐字不变）→ ② Codex 适配器（46 真实会话验证 + import 表接分支去重）→ ③ Cursor 适配器（先 spike 探
`state.vscdb` schema 再尽力而为，5 工作区验证）→ ④ 跨框架合并成每项目一片森林、`verify_tree`（新增线性源校验模式）/
`check_pii` 全绿、全部嵌进同一向量库。

---

相关详规：跨框架落地路线见 [`worklog.md`](./worklog.md)（§跨框架）与
[`conversation-log-spec.md`](./conversation-log-spec.md)（第四 / 五节 · 适配器）；正式 Bug 台账见
[`worklog-sync-test-checklist.md`](./worklog-sync-test-checklist.md)（BUG-2 / BUG-14）。
