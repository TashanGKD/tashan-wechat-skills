# 对话记录统一格式与转化规范

本规范定义「完整对话记录」的**统一 md 格式**，以及从各家智能体应用（Claude Code / Codex / Cursor / …）的原始对话文件转成它的**转化要求**。

> 核心原则：**只做格式转换 + 脱敏，不做任何 AI 提炼。** 转出来的 md 必须是原始对话的忠实 1:1 重排，不概要、不解读、不补写。各家工具原始 json 格式不同，但都映射到这同一套 md，便于团队统一阅读与归档。

---

## 一、统一 md 格式

```markdown
# 完整对话记录（统一格式）

> 来源工具: <Claude Code | Codex | Cursor | …>
> 会话(session): <session-id（多段用逗号）>
> 真源(source-of-truth): <本机原始 .jsonl 绝对路径；多段/子智能体用 " ; " 分隔>
> 参与者(human): <谁，如 Alice>
> 时间: <最早时间> → <最晚时间>
> 处理: 仅格式转换 + 脱敏，无 AI 提炼 | 脱敏命中: <N> 处
> 规范: .claude/skills/team-collab/references/conversation-log-spec.md

---

### [YYYY-MM-DD HH:MM:SS] 🧑 <human 名>
<人的原话>

### [YYYY-MM-DD HH:MM:SS] 🤖 agent
<agent 的原文（全文，不概要）>

<details><summary>⟨工具调用 · &lt;工具名&gt;⟩</summary>

​```json
<工具入参，已脱敏>
​```
</details>

<details><summary>⟨工具结果（&lt;字符数&gt;）⟩</summary>

​```
<工具输出，已脱敏>
​```
</details>
```

要点：
- 只有两种说话方：`🧑 <human>`（人，其 AI 替身代写视同本人）和 `🤖 agent`。
- 工具调用 / 工具结果用 `<details>` 折叠，**完整保留、不省略**。
- 按时间升序；多段会话（重启续接）按消息 id 去重后合并。
- **`真源(source-of-truth)` 是回程票（必填）**：本 md 是去重整理后的**视图**，真源 `.jsonl` 才是逐条原文。头部写清真源的**本机绝对路径**，任何读者/agent 便可顺着它回原始 jsonl 做**无损重读**（对话树节点还会在 `节点段:` 行附 `uuid` 首末，便于按 uuid 精确定位）。真源路径是**该工作日志所有者的本机路径**——他人机上没有这个源，就以本 md 为准。这条正是「读本地历史对话」协议里「命中后若真源在本机就下钻、否则读 md」的落点（见 [`worklog.md` 读协议](./worklog.md)）。

---

## 二、转化要求（机械、忠实）

1. **忠实 1:1**：agent 的文本、工具调用入参、工具结果，全文照搬，不概要、不改写、不重排（仅按时间排序）。
2. **映射到统一原语**：把各家原始记录解析成 `{角色(human/agent), 时间戳, 文本, 工具调用(名,入参), 工具结果(内容)}`，再用上面的格式渲染。
3. **去系统注入**：人的消息里把 `<system-reminder>`、命令回显等**非本人内容**剥掉，只留真实输入。
4. **去重 + 排序**：同一会话若有多个文件，按消息 `uuid` 去重，按 `timestamp` 升序。
5. **脱敏**（见第三节）后才能写盘 / 提交。
6. **不引入 AI**：本转化是纯解析 + 字符串处理，不调用模型、不做总结。

---

## 三、脱敏要求（提交到共享仓前必做）

命中以下模式即替换为 `[已脱敏:类型]`（保留键名、只抹值；尽量多抹，宁枉勿纵）：

| 类型 | 模式（示意） |
|---|---|
| api-key | `sk-…`、`sk-ant-…` |
| github-token | `ghp_/gho_/ghu_/ghs_/ghr_…` |
| aws-key | `AKIA[0-9A-Z]{16}` |
| google-key | `AIza…` |
| slack-token | `xox[baprs]-…` |
| jwt | `eyJ….….…` |
| private-key | `-----BEGIN … PRIVATE KEY----- … END` |
| auth-header | `Authorization: …` / `Bearer …` |
| cred-kv | 键名为 `password/secret/token/api_key/access_key/private_key/client_secret` 的 `键=值` 或 `"键": "值"` |

并输出一份**脱敏报告**（各类型命中几处），供人在提交前过目。

> ⚠️ **诚实边界**：正则脱敏是尽力而为、**不是 100% 保证**——它抹掉已知模式，挡不住没见过的格式。配套措施：① 仓库保持私有；② 每次转换出脱敏报告、人工过目后再提交；③ 切勿把明文密钥贴进对话。

---

## 四、各工具的对话记录在哪（写适配器时用）

| 工具 | 原始记录位置 / 格式 | 适配器状态 |
|---|---|---|
| **Claude Code** | `~/.claude/projects/<项目>/<session-id>.jsonl`；子智能体在 `<session-id>/subagents/agent-<id>.jsonl`（`sessionId` 字段=父会话）；当前会话 id 见环境变量 `$CLAUDE_CODE_SESSION_ID` | ✅ `scripts/adapters/claudecode.py` |
| **Codex** | `~/.codex/sessions/YYYY/MM/DD/rollout-<ISO>-<session_id>.jsonl`；每行 `{timestamp,type,payload}`；`session_meta.cwd`=项目；取 `response_item` 流；导入映射 `~/.codex/external_agent_session_imports.json` | ✅ `scripts/adapters/codex.py` |
| **Cursor** | `…/Cursor/User/globalStorage/state.vscdb`（SQLite）：`composerData:<id>` 骨架 + `bubbleId:<id>:<bid>` 消息（type 1=user/2=assistant）；工作区↔会话链在 `workspaceStorage/<h>/state.vscdb` 的 `ItemTable['composer.composerData']` | ✅ `scripts/adapters/cursor.py` |
| 其他 | 加一个 `SourceAdapter`（discover/load/sid_of，产出 CC 形状 dict）并在 `adapters/__init__.py` 注册；核心无需改 | 见 `docs/02-architecture.md` |

## 五、给其他框架写适配器的人

你只需做**两件事**：
1. **读取器**：知道你的工具把对话记录存在哪、什么格式，把它解析成 `{角色, 时间戳, 文本, 工具调用, 工具结果}` 这组原语。
2. **复用渲染器 + 脱敏器**：照第一节格式输出、按第三节脱敏。可直接抄 `scripts/make_transcript_claudecode.py` 里的 `render()` 和 `redact()`，只换掉读取部分。

产物丢进 `团队协作记录/智能体工作日志/<你>/<会话>/完整对话记录.md` 即可，与 Claude Code 的产物长得一模一样。
