# 05 · 计划文档（分阶段执行）

> 逐步执行、每步有验收闸、红不放行。全程改 **master** 拷贝 `~/.claude/skills/team-collab/`，
> 每步收尾 `cp` 同步项目本地孪生并 `diff` 验字节一致；**Codex 拷贝本轮不碰**。
> 验收细节见 [04-testing](./04-testing.md)；架构/数据依据见 [02](./02-architecture.md)/[03](./03-data.md)。

## ⚠️ Windows 跑法（所有命令的硬前置）

- **一律 `python`，禁用 `python3`**：本机 `python3` 是失效的 Microsoft Store 桩（退出码 49、不执行脚本）；
  `python` = Python 3.x 可用。凡计划/脚本里的命令都写 `PYTHONIOENCODING=utf-8 python <script> …`。
  `regress_cc.sh` 只做 snapshot/check（sha256 哈希对账、**不调 python、不重建**）；**重建是外层单独手动步骤**：
  `PYTHONIOENCODING=utf-8 python build_session_tree.py --adapters cc`（用 python），再跑 `regress_cc.sh check` 比对。
- **verify 独立跑、读退出码、别接管道**：build 内置自检只 print 警告、`main()` 仍退出 0（`build_session_tree.py:486-499`）
  →"build 成功≠verify 通过"。验收必须**另跑** `PYTHONIOENCODING=utf-8 python verify_tree.py --person Alice; echo $?`，
  绝不 `| tail`（BUG-15）。
- **重建仅动 `对话树/`**；memory daemon 只锁兄弟目录 `记忆向量库/`，故**无需停 daemon**。但全量重建（`os.rename→.bak`）
  前确保没有进程（含审核子智能体、编辑器）把 cwd 或打开文件落在 `对话树/` 内，否则 WinError 32；撞上先关句柄再重跑
  （旧树在 `.bak` 可恢复）。仅 Step4 的 L1 重嵌若与重建并发，才按需 `memory_daemon.py --stop`。

## 状态表

| 阶段 | 内容 | 状态 | 验收闸 |
|---|---|---|---|
| Step 0a | 5 文档 + 审核修订 | ✅ 完成 | 5 文档过子智能体对抗审核并据 findings 修订 |
| Step 0b | 回归护栏 | ✅ 完成 | `regress_step.sh`（老/新冻结源自比）落盘并 PASS；旧 golden_hashes 法弃用（源在长会假红） |
| Step 1 | builder 切核心 + CC 适配器（零行为改变） | ✅ 完成 | 76 生成物 old==new 逐字节一致 · discover 老/新一致 · 重构后 verify 🔴 全过 · 孪生同步 |
| Step 2 | Codex 适配器 + import 接分支 | ✅ 完成+验收 | 46 会话、32 接枝、verify 全过(无损重构)退0、CC 回归 green；子智能体验收 structural=accept / fidelity=reject→已修 blocker(线性尾链被剪)+minor(IDE 噪声/worker 独立分支)，复验 15 条记录恢复 |
| Step 3 | Cursor 适配器 | ✅ 完成+验收 | 39 composers、注册进 registry；子智能体验收 accept-with-fixes→已修 _iso 时间戳(ISO 串误当 ms-epoch→42% 时间空)，复验 226/226 ISO；CC 回归 green |
| Step 4 | 跨框架合并 + L1 覆盖 + 收尾 | ✅ 完成 | 真实树重建为三家一片森林(121会话→63根/144节点)、verify 无损退0、63 CC 人写记忆保留、L1 覆盖三家(CC1229/Codex7710/Cursor50=8989块)、recall 命中 Codex/Cursor 带真源；roadmap/worklog/spec 文档更新；修 chromadb 孤儿 pickle 使 recall 稳 |

## Step 0 · 文档 + 基线（本轮，已完成）

- 0a：5 文档 + README 落 `docs/` 并同步孪生；5 视角子智能体对抗审核 → 据 findings 修订（本次已折叠：
  Codex content 类型/子线程/developer、import-map 1→N+全局、Cursor 全局库、compacted/turn_context、
  线性段身份键、接分支落点算法、命名律、role 词表、canonicalize、python3 桩、整目录快照回退、tree.json 生成时间归一化）。
- 0b：`scratchpad/golden_tree_baseline/` + `golden_hashes.txt`（68 生成物、tree.json 归一化）+ `regress_cc.sh`；
  冒烟自检 PASS。

## Step 1 · 核心 / CC 适配器切分（零行为改变）

1. **开工先留整目录快照**：`cp -r scripts scripts.pre_step1`（非 git，回退靠此，不靠单文件 .orig）。
2. 建 `adapters/{__init__,base,claudecode}.py`：`base` 定 `Record/SessionRef/SourceAdapter`；`claudecode` 搬
   现有 `discover_session_files`/`load_records`/`text_of` + `entries_from_objs`（CC 专属解析）→ 产 `Record`
   （id=uuid、parent_id=parentUuid、raw_role、lineage=tree、seg_key_hint=None）。**删除 `build_session_tree.py:251`
   的死函数 is_user_text**（真正生效的是 :259 内联，避免适配器照死函数复刻出偏差）。
3. `build_session_tree.py` 改为面向 `Record` 编排；新增 **`--adapters cc`** 开关（限定只挂 CC 适配器）；
   `render(source_tool=节点来源)`；**CC 节点保持裸 `对话N（sid8）`**（命名律 02 §7）。
4. `verify_tree.py` 抽出 `tree` 模式（现有逻辑原样）+ 预留 `linear` 钩子（此步不接线性源）。
5. `make_transcript_claudecode.py` 只留 render/redact（entries_from_objs 迁走）。
- **验收**：`regress_cc.sh check` 逐字节全等（`regress` 固定用 `--adapters cc`）；独立跑 verify tree 模式退出 0；
  `check_pii` 绿；孪生 diff 空。
- **回退**：删 `adapters/` 整包 + `scripts.pre_step1` 整目录还原。

## Step 2 · Codex 适配器

1. **只读 spike 前置**：dump `~/.codex/external_agent_session_imports.json`（确认 records 结构、
   `imported_thread_id`↔rollout `<session_id>`、`source_path` 剥 `\\?\` 反解 CC sid 的正则）+ 一个含子线程的
   rollout（确认 `source.subagent.thread_spawn`）→ 回填 03 §3/§4。
2. `adapters/codex.py`：`discover` 扫 `~/.codex/sessions/**/rollout-*.jsonl`，读 `session_meta.cwd` **及全会话
   `turn_context.cwd`** 经 `canonicalize` 判归属；`parse` 走 response_item（message 的 input_text/output_text/
   input_image；function_call(+output by call_id)；custom_tool_call；reasoning 跳过；developer 归 system/跳过），
   处理 `compacted`（压缩边界、摘要不当轮渲染），线性 id=`sid#i`、`seg_key_hint`。
3. 子线程：`parent_thread` → 挂父 Codex 会话下。import：`continues_external` + 裁摘要 → 核心接分支（§5 落点算法、
   一源多枝去重键=thread_id、目标缺失降级为原生根）。
4. `verify_tree` 接 `linear` 模式；node_dir 唯一性断言。
- **验收**：46 个 2025cell Codex 会话按"discover 命中 − 合法空会话 = 入树"等式核对；子线程挂父节点、不平铺；
  导入者接分支且一源多枝各就位、CC 不双计；抽样 `段.md` 按 04 §忠实 rubric 判定；linear verify 退 0；
  子智能体验收 blocker/major=0；`check_pii` 绿（路径/机器名如需机器拦则补 redact 模式）。

## Step 3 · Cursor 适配器

1. **Spike（只读）**：dump **globalStorage/state.vscdb** 的 `cursorDiskKV`（bubbleId/composerData/composer.content）
   + `composerHeaders`，与一个 2025cell workspace 库的 `composerId↔workspace` 关联链 → 补全 03 §5（一条会话由哪些
   bubble 组成、角色/文本/工具/时间戳、跨库去重键与取数优先级）。产出即验收物。
2. `adapters/cursor.py`：`discover` 用 `workspace.json.folder` 经 canonicalize 归属；`parse` 按 spike schema 从
   **全局库**提取会话正文→线性 Record；**任何解析异常→返回空 + 告警，不抛**。
- **验收**：schema 落文档；**若存在非空会话则入树**（全空时"≥1"降级为"schema 落文档"即可，不死锁）；坏库降级不崩；
  子智能体验收。

## Step 4 · 合并 + L1 + 收尾

1. 三适配器同挂 `ADAPTERS` 全量重建 → 一片森林；`--list` 人工过目。
2. 两模式 `verify_tree` + `check_pii` 全绿；node_dir 唯一断言过。
3. `build_memory_index.py`（不改）重嵌 → `记忆向量库` 覆盖三家；用**固定查询集**抽查 `recall-memory` 命中
   Codex/Cursor 节点并带真源。
4. 同步孪生；更新 `references/architecture-roadmap.md`（缺口④ + CC 侧②标已落地；顺手把"一棵统一树"措辞改"一片森林"）；
   更新 auto-memory 指针。
- **验收**：产品文档 §7 DoD 全绿（含"一片森林"计数等式：顶层根数 = CC 根 + 原生 Codex 根 + Cursor 根 − 接成分支数）。

## 子智能体使用点

- Step 0a：文档对抗审核（已做，5 视角）。
- Step 2/3 末：适配器产出忠实性验收（只读抽样 + 对真源，按 04 rubric）。
- Step 4 末：合并 + 检索端到端验收。
- 约束：子智能体只读/只审/只报；核心代码由主循环单点修改。

## 回退与安全

- 非 git → 脚本级回退靠**整目录快照**（Step0/每步前 `cp -r scripts scripts.pre_stepN`），不靠逐文件 .orig；
  回退含删半建的 `adapters/` 包。黄金树是 L2 最后防线；`.bak` 崩溃安全保留。
- 重建纪律见顶部 Windows 跑法（进程别驻留 `对话树/`；用 python 非 python3；verify 独立读退出码）。
