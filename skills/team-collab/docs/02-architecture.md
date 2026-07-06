# 02 · 架构文档（核心 + 适配器）

## 1. 现状（重构前）的框架相关面

读遍脚本后，框架相关的代码**只集中在几处**（其余全是通用的）：

| 关注点 | 现在在哪 | 框架相关? |
|---|---|---|
| 发现属于本项目的会话 | `build_session_tree.py:51 discover_session_files()`（扫 `~/.claude/projects` + REPO_MARKER grep + uuid 血脉） | **是** |
| 读一条会话、去重 | `build_session_tree.py:95 load_records()`（按 `uuid` 去重） | **是** |
| 取文本/角色 · 段→entries | `text_of()` · `make_transcript_claudecode.py entries_from_objs()` | 处理**规范化(CC 形状)**格式；适配器归一成该形状后通用（不迁走） |
| 拼树 / 剪枝 / 分段 | `build_session_tree.py`（`parentUuid`、`walk_seg`）——在规范化 dict 上运作 | 通用（依赖规范化的 uuid/parentUuid） |
| 剪枝信号 is_user_text | 内联 `mine`（role==user 且去噪后有文本，不排除 tool_result）；旧 `:251` 死函数 **Step 1 已删** | 半 |
| 段身份（贴回人写记忆） | `build_session_tree.py:131 _seg_key_from_md()`（首个 `### [时间]`） | 半（CC 靠时间锚，线性源需另立键） |
| 脱敏 | `make_transcript_claudecode.py:44 redact()` | **否** ✅ |
| 渲染统一 md | `make_transcript_claudecode.py:59 render()`（**已带 `source_tool` 参数**） | **否** ✅ |
| tree.json / TREE / 目录 / 思维导图 / 规范 | `build_session_tree.py:414-475` | 否 |
| 校验 | `verify_tree.py`（全建立在 `parentUuid` 链 + `节点段: N 条记录` 行上） | **是** |
| PII 提交闸 | `check_pii.py`（只扫 email/cn-phone/long-id/wechat-id 4 类） | **否**（框架无关，按需补 redact 模式） |
| 嵌入向量库（L1） | `build_memory_index.py`（读节点目录 tree.json+段.md+研究历程+动机 4 类产物） | **否** ✅ |
| 检索 / daemon | `query_memory.py` / `memory_daemon.py` | **否** ✅ |

**结论**：L1（索引+检索）与渲染/脱敏**已框架无关**；要动的只有"发现 + 解析 + 血脉/校验"这条窄带。

## 2. 目标结构：一核 + 多适配器（Step 1 已落地）

**内部规范化格式 = CC 形状的记录 dict**（见 §3）——把 CC 的记录 schema 直接用作"通用内部格式"：各适配器把本框架
记录**翻译成这个形状**，于是现有的 tree 构建 / entries_from_objs / render 全都无需为每家改写。

```
scripts/
  build_session_tree.py     ← 框架无关核心（编排：collect(objs,sess)→森林→接枝→剪枝→分段→emit→索引→verify）
  adapters/
    __init__.py             ← 注册表 get_adapters(names)；Step1 注册 cc，codex/cursor 后续
    base.py                 ← SourceAdapter 接口（discover/load/sid_of）+ 规范化格式约定
    claudecode.py           ← CC discover+load（恒等：原始 jsonl 记录本就是规范化形状）
    codex.py / cursor.py    ← 把各自记录翻译成 CC 形状 dict（后续步骤）
  make_transcript_claudecode.py  ← 通用 render()/redact() + entries_from_objs（**处理规范化=CC 形状格式**；
                                    各适配器产出该形状，故不迁走、由核心框架无关地调用）
  verify_tree.py            ← 增 linear 校验模式（按节点 _source_tool 选模式）
  check_pii.py / build_memory_index.py / query_memory.py / memory_daemon.py / _vector_env.py  ← 不动
```

**Step 1 实际做法（比原 Record-dataclass 设计更省、零改变）**：核心仍在 CC 形状 dict（`objs`）上运作；
`discover_session_files`/`load_records` 收敛为薄封装、真身迁入 `adapters/claudecode.py`（`verify_tree` 仍可调）；
**未引入 Record dataclass**（那会大改核心、抬高回归风险）。`--adapters cc` 复现纯 CC 输出，`regress_step.sh` 证明
76 生成物逐字节一致、discover 文件集老/新一致。

## 3. 适配器契约（`adapters/base.py`）

**规范化记录 = CC 形状的 dict**（核心 + `entries_from_objs` + `render` 只认这形状）：
```
{ uuid, parentUuid, timestamp,
  message: { role: "user"|"assistant",
             content: str | [ {type:"text", text}
                            | {type:"tool_use", name, input}
                            | {type:"tool_result", content} ] },
  # 可选跨框架元键（下划线前缀，核心/verify 读；CC 可省，Codex/Cursor 用）：
  _source_tool, _source_file, _session_id, _seg_key_hint, _parent_thread, _continues_external }
```
- CC 适配器 `load` 是**恒等**（原始 jsonl 记录本就是这形状）。
- Codex/Cursor 适配器把各自记录**翻译成这形状**——关键是把 content 归一成 `text/tool_use/tool_result`、role 归一成
  user/assistant（Codex `developer` 轮**跳过、不产记录**），于是 `entries_from_objs`/`render` 无需为每家改写。
- 线性源（Codex/Cursor）：`uuid`=`f"{sid}#{i}"`（i 按 emit 序）、`parentUuid`=前一条 id、一会话一根；元键
  `_seg_key_hint`=`"<tool>:<sid>#<段首 i>"` 供人写记忆贴回、`_continues_external`/`_parent_thread` 供接枝。

```python
class SourceAdapter:
    name: str                 # 来源工具显示名（→ _source_tool）
    lineage_mode: str         # "tree"（CC uuid/parentUuid 真实分叉）| "linear"（一会话一链）
    def discover(self, repo_root, src=None) -> list[str]: ...   # 本框架属于该项目的会话文件（跨 cwd）
    def load(self, paths) -> tuple[dict, dict]: ...             # (objs={id:规范化dict}, sess={id:{session-id}})
    def sid_of(self, path) -> str: ...                          # 会话文件 → session-id
```

> ⚠️ **role 词表**：规范化 dict 的 `message.role` 用 CC 的 **user/assistant**；`entries_from_objs`（不改）内部把
> user→human、assistant→agent 供 `render()`（`make_transcript_claudecode.py:89` 只认 human/agent）。适配器**只管
> message.role、不碰 human/agent**——这样两套词表不会在适配器层混淆。

## 4. 数据流（L3 → L2 → L1）

```
每个 adapter.discover(repo) → 该框架属于本项目的会话（归属过统一 canonicalize()，见 §6）
        ↓ adapter.parse()
规范化 Record 流（带 source_tool/source_file/lineage/seg_key_hint/parent_thread/continues_external）
        ↓ 核心：按 (source_tool,id) 去重 → 按 parent_id 建森林
        ↓ 接枝①同框架：parent_thread 的会话挂父会话节点下（Codex worker 子线程 / CC subagents）
        ↓ 接枝②跨框架：continues_external 的根挂目标框架对应节点下当分支（裁重述前缀，落点算法见 §5）
        ↓ 剪枝(is_user_text) → walk_seg 分段 → emit
每节点：render(entries, source_tool=本节点来源, source_files=真源) → 段.md（含 节点段:N条记录 + 段身份 行）
        + 脚手架 研究历程/动机（按段身份贴回已填：CC 用 ### 时间锚、线性源用 seg_key_hint）
        ↓ 汇总
tree.json（节点 +source_tool 字段）· TREE.md · 目录.md · 思维导图.md · 规范.md   ← L2
        ↓ build_memory_index.py（不改）
记忆向量库（chromadb）   ← L1
```

## 5. 跨源血脉与接枝（本轮新增能力）

**同框架父/子线程**：Codex 有 `session_meta.source.subagent.thread_spawn.parent_thread_id`（worker 子线程）。
核心把带 `parent_thread` 的会话挂到**父会话节点下**（对应 CC 的 `subagents/`，受同一 `--with-subagents` 约束），
**不当独立原生根**。

**跨框架接分支**（Codex Desktop 导入并续接的 CC 会话）：
1. Codex 适配器据 import-map（见 03 §4）给根 Record 打 `continues_external={tool:"Claude Code", ref:{sid}}`
   （`source_path` 剥 `\\?\` 前缀、去 `.jsonl` = **CC session-id**；**import-map 只到 session 级、拿不到记录 uuid**），
   并裁掉导入摘要首轮。
2. 核心**确定性落点算法**（`apply_grafts()`，session 级锚定）：
   - 按 `ref.sid` 找该目标 session **时间戳最晚的记录** → 把接枝会话根的 `parentUuid` 指到它；建 children/roots
     时它自然挂在目标节点下；
   - `walk_seg` **不跨来源工具、也不跨 session**：锚点记录的孩子只要来源工具或 session_id 不同就断段 → 接枝会话
     （含同源 Codex worker 子线程）成为**真正的分支** `分支（codex·<sid8>）`，而非并进目标段（CC 无这两个元键 → 不触发）；
   - **兜底**：目标 session 未加载（marker 没命中 / 不在 --adapters / 跨项目）→ `parentUuid` 保持 None →
     **降级为原生根 `对话N（codex·…）`，绝不丢弃**。
3. **一源多枝**：同一 CC 会话可被多个 Codex 线程续接（import-map 1→N）→ 同一记录下允许多个
   `分支（codex·各自 sid8）`；接枝去重靠 Codex 各自 session_id（各线程独立），不会误并。
4. **build 与 verify 共用 `apply_grafts()`**（关键）：verify 从原始源重构时也调用它，否则重构（未接枝）与树
   （已接枝）对不上 → 假 🔴 断裂/接缝。这是实测踩过并修掉的坑。
5. **子线程**（Codex worker）：`_parent_thread` 同理经 `apply_grafts` 挂到父 Codex 会话最晚记录之后成分支。

## 6. 归属（按项目、跨框架、子目录上卷、统一规范化）

**统一 `canonicalize(path)`**（三家 discover 都过它再比对，消除口径分裂）：URL 解码（`unquote`）→ 剥
`\\?\` 前缀 → 盘符/分隔符统一 → `casefold`（大小写不敏感）。

| 框架 | 归属判据 |
|---|---|
| Claude Code | 内容 grep `REPO_MARKER` + uuid 血脉扩展（保持现状；血脉扩展是线性源没有的召回，见 §9 边界） |
| Codex | `session_meta.cwd` **及全会话 `turn_context.cwd`** 经 canonicalize 后在项目根之下（子目录上卷） |
| Cursor | `workspace.json.folder` 经 canonicalize 后在项目根之下（含多级子目录如 `DRL-main/DRL-main`、CJK 编码目录） |

"项目根"取 `REPO`（当前 `T:\IOP\2025cell`）。一个项目 → 一片森林 → 一份对话树 + 一份向量库。

## 7. 命名律与 tree.json 变化

**唯一命名律**（收口 CC 前缀冲突，决定黄金回归判据）：
- **CC 节点恒不带 tool 前缀**，保持裸 `对话N（sid8）` / `分支M（sid8）`——纯 CC 森林逐字节等于旧产物（回归门）。
- **Codex/Cursor 节点带 tool 前缀**：`对话N（codex·sid8）` / `分支M（codex·sid8）`、`（cursor·sid8）`。
  （sid8 = session-id 前 8 位，与代码 `ss[0][:8]` 一致。）
- 这条唯一律让 03 §6 示例、04 §1 回归判据都引用它，不再自相矛盾。

`tree.json` 每节点**新增 `source_tool` 字段**；`段.md` 头部已有 `来源工具:`/`真源:`（`render()` 现成）。

## 8. 校验（verify_tree 两模式）

按每节点 `source_tool` → 对应 adapter 的 `lineage_mode` 选模式：
- `tree`（CC）：现有全部 🔴 结构性检查（uuid 去重、parentUuid 连续、接缝、根、无损重构、`节点段` 数=uuids 数）。
- `linear`（Codex/Cursor）：①节点 id 无重复；②节点内 id 顺序 = emit 序；③根→叶覆盖该 session **经 `adapter.parse`
  实际 emit 的 Record 序列**（基准=parse 产出集）——parse 只取 response_item 流并映射，**排除**：reasoning、developer
  轮、非 response_item 事件（session_meta/event_msg/turn_context/**compacted**）、import 摘要首轮，再经 is_user_text
  剪枝（**不用"非桥接"这一 CC 树概念**）；④`段.md` 的 `节点段: N 条记录` = 节点 id 数（**线性 emit 必须输出该行**）。
  🟡 陈旧判定通用。
- **全局不变量**（新增断言，build 末 + verify）：所有 `node.dir` 去重后数量 == 节点数（防跨框架同名）。
- **线性源不套用 CC 死桩剪枝**（实测 blocker）：CC 的 `is_user_text` 剪枝会把"最后一个用户轮之后的 agent 答复 +
  工具往返"整条尾链当死桩删掉——对线性 Codex 会话是灾难（实测 15 条会话只剩 1 条）。故线性源 `is_user_text` 恒真、
  整条会话全保留（一会话就是一段真实对话，无死桩可剪）。CC 判据不变 → 回归不变。

## 9. 兼容、召回边界与回退

- 全程改 **master** 拷贝；每步 `cp` 同步项目本地孪生并 `diff` 验字节一致。**Codex 拷贝本轮不碰**。
- **召回边界**（诚实标注）：Codex/Cursor 线性、无跨文件 uuid 血脉，discover 只靠 cwd → 对"项目建立前的起源
  会话 / 中途 cd 进项目"会漏；缓解 = 全会话扫 `turn_context.cwd` + import-map 续接补召回。写入 01 §8 风险表。
- 回退：非 git → 靠**整目录快照**（`cp -r scripts scripts.pre_stepN`），不靠单文件 `.orig`（拆包无法逐文件还原）；
  黄金树护 L2 产物、`.bak` 崩溃安全保留。
