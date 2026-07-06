# 03 · 数据文档（数据模型与三家 L3 格式）

> 全部基于本机真实数据侦察（2026-07-05，含审核 recon-data 子智能体的复核修正）。数字是当时实测值。

## 1. 统一原语（两层）

**归一化记录 `Record`**（核心的原子，见 02 §3）：`{id, parent_id, ts, raw_role, entry, session_id,
source_tool, source_file, is_user_text, seg_key_hint?, parent_thread?, continues_external?}`。
- `raw_role`（原始角色，如 CC 的 user/assistant、Codex 的 user/assistant/developer）——**与 `entry["role"]`
  的渲染词表 human/agent 不同**（见 §下方警示）。
- `is_user_text`：是否"有实质文本的用户轮"，对齐 `build_session_tree.py:259` 现行剪枝判据
  （raw_role==user 且去噪后有文本，**不排除 tool_result**；注意 :251 的同名函数是死代码、判据不同，别照它）。

**渲染原语 `entry`**（喂 `render()`，现成、框架无关，见
[`make_transcript_claudecode.py:59`](../scripts/make_transcript_claudecode.py)）：
```
{role: "human"|"agent", time, text, tools:[(name, input_json_str)], results:[str]}
```
> ⚠️ **两套角色词表，别混**：`render()` 只认 `entry["role"] ∈ {human, agent}`
> （`make_transcript_claudecode.py:89`）。适配器把原始 user→human、assistant/agent→agent。
> `Record.raw_role` 保留原值供血脉/剪枝判定，**绝不**把 user/assistant 填进 `entry["role"]`，否则用户轮被当
> agent 渲染。

**Record 与 entry 是两种粒度**（审核 grounding 提醒）：`Record` **逐条原始记录一个**（载 id/parent_id 血脉，
满足 verify 的"节点段 N 条记录==记录数"不变量）；`entry` 由核心把 Record 流喂给 `entries_from_objs` 式归一
后产出，会**合并** tool_result 轮进前一条 agent、**丢弃**空/噪声轮——entry 数 ≠ Record 数。二者不可画等号。

## 2. Claude Code（L3 · 现状基准）

- 路径：`~/.claude/projects/<编码cwd>/<session-id>.jsonl`；子智能体在 `<sid>/subagents/*.jsonl`
  （`--with-subagents` 才入树）。
- 每行 `{uuid, parentUuid, timestamp, message:{role, content}, ...}`；`role∈{user,assistant}`；
  `content` 是 str 或 list（`text` / `tool_use{name,input}` / `tool_result{content}`）。
- **续接即重抄前文**：session 换 id 时逐条原样拷贝（**uuid 不变**）→ 按 uuid 去重。
- 映射：id=uuid，parent_id=parentUuid，去重键=uuid，lineage=**tree**。归属：`REPO_MARKER` grep + uuid 血脉扩展。

## 3. Codex（L3 · 本轮新增）

- 路径：`~/.codex/sessions/YYYY/MM/DD/rollout-<ISO>-<session_id>.jsonl`（本机 **61** 文件 = 61 个文件名级
  session-id；`session_meta` 层去重后约 40，口径不同——均**非**去重键，去重按文件/thread_id）。
- 每行 `{timestamp, type, payload}`，`type∈{session_meta, event_msg, response_item, turn_context, compacted}`。

**session_meta（首行）**：`payload.{session_id, id, cwd, originator, cli_version, source, ...}`。
- `cwd` 即项目根（本机 2025cell 经 canonicalize 后：35 在项目根 + 11 在 `URDME20251221`（含 2 个小写盘符 `t:\`
  变体经 casefold 归并）= **46**）。
- **子智能体线程**（recon 修正，原文漏）：`payload.source.subagent.thread_spawn.parent_thread_id / depth /
  agent_role`。本机 2025cell 有 **2 个 worker 子线程**，其一 parent 就是另一个 2025cell 会话。
  → **不是"纯线性无树"**：Codex 有"父会话 + worker 子线程"这层。规则：识别 `parent_thread_id`，把子线程挂在
  **父 Codex 会话节点下**（对应 CC 的 `subagents/`，受同一 `--with-subagents` 开关约束），**不当独立原生根**。

**response_item（取这条流做忠实 transcript）**：`payload.type∈`
- `message`：`{role, content:[...]}`。**实测** `content[].type ∈ {input_text, output_text, input_image}`
  （裸 `text` 从不出现；`input_image` 58 次需占位/取 alt 文本）。`role∈{user, assistant, developer}`——
  **`developer`**（107 次）是系统/开发者注入：**本轮跳过**（不产 entry、不计入 Record 覆盖集；entry 词表只有
  human/agent、无 system 落点，故不设"归 system"分支）。
- **用户轮去噪**（类比 CC `_strip_noise`）：Codex 往 user 轮注入上下文——`<environment_context>`（10 会话内 108 次）/
  `<INSTRUCTIONS>` / `<permissions…>` / 整段 `# AGENTS.md instructions` / `# Context from my IDE setup`（open tabs）/
  `# In app browser`——适配器从 user 文本剥掉；**IDE 注入常把真实请求埋在 `## My request for Codex:` 之后 → 只取其后那段**；
  剥净后为空则跳过该轮（否则污染 transcript/摘要）。（acceptance 实测发现并已处理。）
- `function_call`：`{name, arguments, call_id}` → tool（名, 入参）
- `function_call_output`：`{call_id, output}` → tool result（按 `call_id` 配对）
- `custom_tool_call` / `custom_tool_call_output`（如 `apply_patch`）：同上
- `tool_search_call` / `tool_search_output`：并入 tool / 略
- `reasoning`：**加密（`encrypted_content`）→ 跳过**

**event_msg**：UI 事件流（冗余），取 response_item 为准。

**compacted / turn_context（spike 实测修正）**：
- `compacted`：payload=`{message, replacement_history}`，是 Codex **上下文压缩事件**——`replacement_history` 是前文
  摘要（模型内部用）。**实测压缩前的原始 response_item 仍留在 rollout 日志里**（compacted 前的 message 数 =
  43/82/17/43）→ 所以**直接跳过 compacted 记录、按序渲染全部 response_item 即得完整忠实对话**，不丢内容、不引摘要
  重复。（原"从最后一个 compacted 之后取流"会误丢压缩前真实轮次，已弃。）
- `turn_context`：payload 含 `cwd`（+ turn_id/model/approval_policy 等），承载 cwd **中途切换**。→ 归属**不能只读
  首行 `session_meta.cwd`**，须扫全会话 `turn_context.cwd`，"任一 turn 落在项目根之下"即归属本项目。

**血脉/去重**：会话内 response_item 线性、id=`f"{sid}#{i}"`、parent=前一条（`lineage=linear`）；子线程见上
（父子层级）。无跨文件重抄，文件内按行序即可。**`i` 按 parse 实际 emit 的 Record（response_item 映射后）计数**
——与 verify 判据②"id 顺序=emit 序"、判据③"覆盖 parse 产出集"一致（见 02 §8）。

**体量（实测坑）**：Codex rollout 可达数百 MB（最大 **876MB**，工具输出巨大）→ 单会话 9383 轮、未截断 段.md 达
**319MB**，撑爆内存 / 无法浏览 / 无法嵌入。适配器对策：① **截断**超大内容（tool_result 8KB、tool_use 入参 4KB、
文本 20KB，标注截断量；**仅 Codex/Cursor，CC 保全文以保回归**）→ 段.md 降到 ~22MB；② **流式 load**（不 `list()`
全量物化文件）避免 OOM。**遗留**：超长会话（9383 轮）单节点仍偏大，未来可按体量 / compacted 边界拆多节点（本轮不做）。

## 4. 跨框架去重 · import-map（关键）

- `~/.codex/external_agent_session_imports.json` → `{"records":[{source_path, content_sha256,
  imported_thread_id, ...}]}`（本机 **33** 条：31 指向 2025cell CC、2 指向 huaxiang）。
- `source_path` 指向原始 CC `.jsonl`，**带 Windows 扩展长度前缀 `\\?\`**（如
  `\\?\C:\Users\<user>\.claude\projects\T--IOP-2025cell\<uuid>.jsonl`）——**反解 CC sid 前先剥 `\\?\` 前缀**再取
  basename 去 `.jsonl`，并做大小写不敏感比对。
- **1 源 → N 线程**（recon 修正）：同一 CC `.jsonl` 可被导入**多个** Codex 线程（实测 3 例 ×2）→ 同一 CC 节点下
  可挂**多个** `分支（codex·各自 sid8）`；**接枝去重键用 Codex `thread_id`**（非 `source_path`），别把一源多枝误当重复。
- import-map 是**跨项目全局表**：2025cell 归属最终以 **rollout 的 cwd/turn_context 为准**，import 记录仅用于识别
  "是否续接分支"，不作归属依据（否则会误收 huaxiang）。
- 用法：Codex 会话 `session_id ∈ imported_thread_id` → 从 `source_path` 反解被续接 CC sid → 打
  `continues_external={"tool":"Claude Code","ref":{sid}}`（`source_path` 剥 `\\?\` 去 `.jsonl` = **CC session-id**；
  import-map **只到 session 级、无记录 uuid**）+ **裁掉开头导入摘要轮**（首个 user 轮，文本以
  "This session is being continued…Summary:"起）。接枝落点 = 该 CC session 最晚叶节点（算法见 02 §5）。

## 5. Cursor（L3 · 本轮新增，需先 spike）

- **内容不在 per-workspace 库**（recon 修正——原文指错方位）：
  - `…/User/workspaceStorage/<hash>/state.vscdb`：实测 `cursorDiskKV` **0 行**；`ItemTable` 只有
    `composer.composerData`、`workbench.panel.aichat.<composerId>.*` 等**会话↔工作区关联指针/GUID**，**无正文**。
  - `…/User/globalStorage/state.vscdb`：真正内容在此——`cursorDiskKV` **43 万行**，键前缀
    `bubbleId:*`（16.9 万）/`composerData:*`（1019）/`composer.content.*`/`agentKv:*`，另有未记的
    **`composerHeaders`** 表。
- 归属：`workspaceStorage/<hash>/workspace.json` 的 `folder`（URL 编码，如
  `file:///t%3A/IOP/2025cell/URDME20251221`）在项目根之下。本机 2025cell **10 个工作区**（不是 5）：根 +
  `0319_coding_tutorial`/`URDME20251221`/`20250724`/`P_U_J`/`code1`/`paxillin_papers`/`2018_pnas`/
  `DRL-main/DRL-main`（两级子目录，上卷压力样本）+ 一个 CJK URL 编码目录（`%E5%8F%82…`，需 `unquote`）。
- **Spike 结果（2026-07-05 实测，Step 3.0 验收物）**：
  - `composerData:<composerId>`（globalStorage cursorDiskKV）= `{composerId, fullConversationHeadersOnly:
    [{bubbleId, type}]（有序 bubble 列表）, createdAt, text, richText, ...}`——一条会话（composer）的骨架。
  - `bubbleId:<composerId>:<bubbleId>` = 单条消息：`{type: 1=user|2=assistant, text, isAgentic, toolResults,
    richText, ...}`（+ 大量 agentic 元数据）。**type 1=用户、2=助手**（本机分布 382:2611）。部分 bubble value 为 null（跳过）。
  - **工作区↔会话链**：workspace `ItemTable['composer.composerData'].allComposers` = `[{composerId, name,
    createdAt, lastUpdatedAt}]`——每个工作区列出它的 composerId。归属 = `workspace.folder` 在项目下 → 取其 composerIds。
  - 取数：discover 从各 2025cell 工作区收 composerId → load 从 globalStorage 按
    `composerData.fullConversationHeadersOnly` 顺序取 bubble → 映射（type1→user、type2→assistant、text；
    toolResults→tool_result）成 CC 形状线性链，**一 composer 一根**、id=`f"{composerId}#{i}"`。
    `composerHeaders` 表本机 0 行（未用）；跨库去重键 = `composerId`。DB 用 `mode=ro&immutable=1` 只读打开（防 Cursor 运行时锁）。
- 血脉：预期线性（每会话一链）→ 同 Codex；**解析失败降级为跳过 + 告警，不崩**。

## 6. L2 落盘结构（对话树，跨框架后）

```
团队协作记录/智能体工作日志/<person>/对话树/
  对话N（a1b2c3d4）/          ← CC 根：纯 CC 森林保持裸 sid8（回归不变，见 02 §7 命名律）
  对话K（codex·019f3069）/    ← 原生 Codex 根
    分支M（codex·…）/         ← Codex worker 子线程（挂父 Codex 节点下）
  对话J（cursor·007d562a）/   ← Cursor 根
  TREE.md 思维导图.md tree.json 目录.md 规范.md
```
- `段.md` 头部（`render()` 现成）：`来源工具:` / `会话(session):` / `真源(source-of-truth):` / `参与者:` /
  `时间:` / `处理:脱敏命中N` + 节点级 `树节点 / 涉及session / 节点段: N 条记录`。
  **`节点段: N 条记录` 这行对线性源也必须输出**（verify 判据④靠它，见 02 §8）。
- **线性源段身份键**（blocker 修正）：线性源无 `### [时间]` 稳定锚点 → 段.md 头部加一行
  `段身份: <source_tool>:<session_id>#<段首记录 i>`（如 `段身份: codex:019f3069#0`），供 `_seg_key_from_md` 的
  线性分支读取，贴回人写记忆时用它、不依赖时间戳。CC 仍用首个 `### [时间]`。
- `tree.json` 每节点：现有 12 字段 **＋ 新增 `source_tool`**（`verify_tree` 据它选模式）。线性源节点的 `uuids`
  存归一化 id 列表 `["<sid>#0", …]`。**不变量**：所有 `node.dir` 全局唯一（build 末加断言：去重后数==节点数）。

## 7. L1 向量库（不改）

- `build_memory_index.py` 读**节点目录下的 tree.json + 段.md + 研究历程.md + 动机日志.md**（4 类，皆框架无关产物；
  card 块来自研究历程+动机、seg 块来自段.md——见 `gather_blocks`/`build_card` [`:117,131,136`](../scripts/build_memory_index.py)）。
  跨框架节点自动被切块，天然框架无关。
- 存 `记忆向量库/`（在 `对话树/` 之外，避免被 rmtree）；模型 `paraphrase-multilingual-MiniLM-L12-v2`；
  增量按内容 hash upsert。块 id 前缀是 `node_dir`——依赖 §6 的 node_dir 全局唯一不变量。

## 8. 脱敏（不改，覆盖面自动扩大）

- `redact()`（[`make_transcript_claudecode.py:44`](../scripts/make_transcript_claudecode.py)）对
  api-key/jwt/aws/google/slack/github-token/private-key/auth-header/email/cn-phone/long-id/wechat-id/cred-kv
  全框架适用；跨框架 `段.md` 一样过 `check_pii.py` 提交闸。
- **注意 `check_pii.py` 只扫 4 类 PII**（email/cn-phone/long-id/wechat-id，见 `check_pii.py:23`）——**抓不到**
  绝对路径/机器名。Codex/Cursor 记录常含绝对路径/主机名：要机器化拦截须**新增 redact 模式并并入
  `check_pii.py:23` 白名单**，否则 render 端补了、提交闸仍不查（见 04 §5）。正则非 100%，私有仓 + 人工兜底照旧。
