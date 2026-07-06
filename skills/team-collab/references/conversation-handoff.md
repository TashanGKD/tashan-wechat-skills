# 对话续接包（handoff）：按需 compact 任意一条对话 → 跨框架/换账号续接

## 这是什么 / 何时触发
把**任意一条过去的对话**（从它的根起、整条，哪怕历次 compact 过）做一次"手动 compact"，产出一份
**即开即用的续接包**：用户复制它，到**任何新会话**（换了智能体框架 CC/Codex/Cursor、换了账号、或本地记录丢了）
粘贴为第一条消息，新会话就能"像没断过一样"接着这条对话继续干。相当于 CC 的 `/compact`，但对象是
**任意历史对话**、产出是**可搬运的交接包**。

**触发词**（用户说这类话就走本流程）：
> 把对话X生成续接包 / 我要换个框架继续对话X / 把对话X compact 出来 / 给我一份对话X的续接快照 /
> 换账号了，帮我把对话X接着做的交接包整出来 / handoff 对话X

## 怎么定位「要续接的那条对话」——两个入口

用户手里那条对话的 **`对话编号` = 一串很长的稳定本地编码 = 会话的 session-id**（如
`0b09b467-9fb4-4133-b92e-38a4cb7fb6b3`），**不是** `对话43` 那种会随重建变号的显示别名。把 session-id 报给
`pack_conversation.py --session <sid>` 即可（脚本会自动从**任意节点**的 sid 上溯到它的**根**，从根整条打包）。

**入口 A — 看思维画布挑**：用户先让智能体按本 skill 生成/打开思维画布
（`build_mindmap_html.py` → `思维画布.html`），每个分支/节点的**起点**都标了
`对话N + 完整 session-id + ⧉复制`；用户点复制 session-id、连同"生成续接包"指令发给智能体。

**入口 B — 语义回顾出表格**：用户说「**回顾项目工作，找到 xx 相关的对话**」时，智能体**主动**回顾、出一张表：
```
python find_conversations.py "<主题/关键词>" --person <谁> [--top 6] [--k 16] [--chars 500]
# 直接打 markdown 表：| 对话编号(session-id) | 该对话总结 | 最近 3 个完整交互记录 |
# 取数：语义召回(query_memory 向量库)→按 tree.json 上溯到根对话；关键词兜底扫 摘要/段.md 开头。
```
把该表原样贴给用户 → 用户从表里认出想续的那条 → 把它的 `对话编号(session-id)` 发回来 → 走下面工作流。
> 触发词（入口 B）：回顾项目工作找 xx 相关的对话 / 我之前做 xx 的对话是哪条 / 找出所有关于 xx 的会话列个表。

## 工作流（4 步）

**① 打包**（确定性脚本）：
```
python3 .claude/skills/team-collab/scripts/pack_conversation.py --person <谁> --session <session-id>
# 用户从入口 A/B 拿到的就是 session-id；脚本会从**任意节点**的 sid 自动上溯到它的**根**再整条打包。
# （也支持 --alias <对话N>，但别名会随重建变号，优先用 session-id。）
# 输出：<对话树同级>/续接包_<对话N>_原始转录.txt
```
脚本做的事：**从根收齐整棵子树**（含所有续接/分支）→ 各节点 段.md 抽轮次、**按时间排** →
**滤掉**压缩摘要块("This session is being continued…")、`[Request interrupted]`、工具结果折叠块 →
**保留**对话正文 + 工具调用名 → 写成转录，打印路径 + token 估。

**② 派子智能体 compact**：用 `Agent`（general-purpose）派一个子智能体，prompt =
【下面的 compaction 模板】+【让它 Read 上一步那个转录文件、完整读】+【只输出 9 段总结】。
（子智能体上下文独立，专门做总结、不受主会话干扰。）

**③ 套"续接壳"**：把子智能体产出的 9 段总结，包进下面的壳里 → 就是交接包。

**④ 返回给用户**：把交接包全文给用户（可同时存成文件 `续接包_<对话N>.txt`），告诉他：
复制它、到新会话粘贴为第一条消息即可续接。

## 规模注意
- pack 脚本会报 token 估。若 **>15 万 tokens**（历次 compact 叠起来会很大），单个子智能体可能吃不下 →
  退化做法：分段（按时间切成几段各自 compact，再把段级 compact 合并成一份），或把工具调用也删、只留纯对话。
- 实测：一条 4.5 万 token 的对话，子智能体照本模板产出的 compact 与 CC 真实 compact **结构/关键事实/
  当前状态+下一步一致**（已实测验证过，见上文 compaction 模板）。

## compaction 模板（喂给子智能体）
```
你的任务是：为这段对话生成一份详尽的总结。
背景：这份总结会取代整段对话历史，被复制到一个全新会话（可能是别的框架/别的账号）作为唯一上下文，
新会话看不到任何原文——所以必须包含"无缝继续工作所需的一切"。宁多勿少。

先在 <analysis> 里按时间逐条回顾（简短）。然后严格按这 9 段写（标题照抄、顺序不变）：
1. Primary Request and Intent   2. Key Technical Concepts   3. Files and Code Sections
4. Errors and fixes   5. Problem Solving   6. All user messages（逐条原文照录，最关键）
7. Pending Tasks   8. Current Work   9. Optional Next Step（仅当直接延续用户最新明确请求，引用其原话）
铁律：只总结真实发生过的，忠实、不添加不假设不发挥。
```

## 续接壳（第 ③ 步套在总结外面）
```
This session is being continued from a previous conversation. The summary below covers that
conversation in full so you can continue it seamlessly.

[↑ 9 段总结原样贴这 ↑]

Continue the work from where it left off. Resume directly — do not acknowledge this summary,
do not recap; pick up the last task as if the break never happened.
```
（注意：跨框架/换机器时，原始 jsonl 通常不可达，所以壳里**不放** `read the full transcript at:` 那种本机指针——
交接包要**自包含**。）
