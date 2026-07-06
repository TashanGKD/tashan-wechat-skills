# 01 · 产品文档（跨框架记忆层）

## 1. 一句话

让 **Claude Code 侧的 team-collab skill** 能把本机上 **Claude Code + Codex + Cursor** 三家智能体
在**同一个项目**里做过的所有工作记录，统一整理成**一份**去重对话树（L2）并嵌入**一份**语义向量库（L1）——
**按项目组织，不按智能体组织**。

## 2. 问题

今天记忆层只认 Claude Code：`build_session_tree.py` 写死扫 `~/.claude/projects`、整棵树建在 CC 专属的
`uuid`/`parentUuid` 上（见 [`build_session_tree.py:29,57,244`](../scripts/build_session_tree.py)）。但用户
（Alice）实际在**多个框架**里推进同一个研究项目：本机 `~/.codex/sessions/` 有 61 个 Codex 会话、其中
**46 个**属于 `T:\IOP\2025cell`；Cursor 有 108 个工作区、**10 个**属于该项目。这些工作**当前完全不在记忆里**，
"回顾这个项目做过什么"会漏掉一大半、且无法语义检索。

## 3. 用户与场景

- **主用户**：Alice（研究者），在 CC / Codex / Cursor 间切换做同一个项目。
- **消费者**：任一智能体入口 + `recall-memory` skill —— "这个项目里我在 Codex 里改过哪个 tex？"
  "上次那个相图脚本是在 Cursor 还是 CC 做的？" 都应命中，命中后能按真源下钻回原始记录。
- **触发**：收尾/归档（`/team-collab`、`build_session_tree.py`），以及"读本地历史对话"的检索路径。

## 4. 价值

1. **完整**：一个项目的记忆不再因换工具而残缺。
2. **统一入口**：L1/L2 与框架无关，任何智能体都读同一份、检索同一份。
3. **可追溯**：跨框架节点同样带 `来源工具` + `真源` 指针，命中后可回到该框架原始记录读无损细节。
4. **架构副产品**：三家并存逼出干净的"核心 vs 适配层"边界，为后续（纵轴：把适配器分发进各框架本体）打地基。

## 5. 范围（本轮）

**做**：
- 一个实现，**只住在 Claude Code 拷贝**里（`~/.claude/skills/team-collab/`），从 CC 侧读三家 L3。
- 把 builder 切成「框架无关核心 + 每框架源适配器」（CC / Codex / Cursor 三个适配器）。
- 三家会话按项目 marker/cwd 归属、跨框架合并成**每项目一片森林**，嵌入同一向量库。
- `verify_tree` 增加"线性源"校验模式；`check_pii` 覆盖新增的跨框架 `段.md`。

**不做（本轮明确排除）**：
- **不**把可运行适配器分发进 Codex/Cursor 本体（那是纵轴"多适配器分发"，后续）。因此本轮**不解决**
  "3 份拷贝漂移"（roadmap 缺口②的分发面）——只在 CC master 拷贝里改，改完同步项目本地孪生。
- **不**改语义模型/daemon/检索前端（`query_memory.py`/`memory_daemon.py`/`recall-memory` 保持不变）。
- **不**回填历史 Codex/Cursor 的人写 `研究历程/动机`（脚手架照生成，人写内容按需另补）。

## 6. 已定关键决策（2026-07-05，见 roadmap §本轮 scope）

1. **三家一起上**——用 ≥3 个真实实现逼出核心/适配边界。
2. **跨框架去重 = 接成分支**——Codex Desktop 导入并续接过的 CC 会话，挂成对应 CC 节点下的
   `分支（codex·…）`；原生 Codex 会话作为自己的根。靠 `~/.codex/external_agent_session_imports.json` 识别。
3. **子目录上卷**——cwd/工作区落在项目根之下的（如 `…\2025cell\URDME20251221`）并进顶层项目一片森林。
4. **子智能体**——CC 子智能体行为不变；Codex worker 子线程（`parent_thread_id`）挂父会话节点下（比照 CC
   `subagents/`，受同一 `--with-subagents` 开关）；Cursor 若有子会话按 spike 结果处理。

## 7. 验收标准（Definition of Done）

- **回归**：只跑 CC 一家时，重建产物与本轮开工前的 63 节点树**逐字节一致**（黄金基线，见 04）。
- **Codex**：2025cell 会话按计数等式（discover 命中 − 合法空会话 = 入树）核对；worker 子线程挂父会话；导入自 CC
  的会话接成分支（含多叶/一源多枝/目标缺失降级）、不双计；`段.md` 按忠实 rubric 判定（见 04 §6）。
- **Cursor**：属于 2025cell 的**非空**工作区会话入树（尽力而为，先 spike **全局库** schema——见 03 §5；全空则以
  schema 落文档为过，不死锁）。
- **合并**：`对话树/Alice/` 是一片跨三家的森林（顶层根数 = CC 根 + 原生 Codex 根 + Cursor 根 − 接成分支数），
  节点带 `来源工具`；`verify_tree`（含线性模式）/ `check_pii` / node_dir 唯一断言全绿。
- **L1**：向量库覆盖三家节点，`recall-memory` 能召回 Codex/Cursor 来源的节点并带真源。
- **无漂移退路**：master 拷贝改动同步到项目本地孪生（字节一致）；Codex 拷贝本轮不碰。

## 8. 非目标下的风险与缓解

| 风险 | 缓解 |
|---|---|
| Cursor `state.vscdb` 格式无文档、随版本变 | 先做只读 spike 探 schema 再写；Cursor 适配器标注"尽力而为、版本敏感"，失败降级为跳过而非崩溃 |
| 跨框架重复双计 | 用 import-map 精确识别、接成分支并裁掉重述前缀（见 03 §跨框架去重） |
| 重构改坏现有 CC 通路 | 先建黄金基线，重构后逐字节 diff 才算过（见 04） |
| 线性源召回边界：Codex/Cursor 无跨文件 uuid 血脉，纯靠 cwd → 漏"项目建立前起源/中途 cd 进项目"的会话 | 全会话扫 `turn_context.cwd` + import-map 续接补召回；作为已知边界诚实标注、非默认无损（见 02 §9） |
| `check_pii` 抓不到绝对路径/机器名（只扫 4 类 PII） | 明确其范围；如需机器化拦截则补 redact 模式并入 check_pii 白名单，否则靠私有仓 + 人工过目（见 04 §5） |
