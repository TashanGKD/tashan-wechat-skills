# 04 · 测试文档（策略 · 验收闸 · 子智能体审核）

## 0. 原则

- **每个阶段都有可执行、可判定的验收闸**，红不放行。软验收也要有客观 rubric（见 §6）。
- **回归优先**：任何重构先保证"CC 一家的产物逐字节不变"，再谈新增。
- **拿真实数据当夹具**：46 个 Codex / 10 个 Cursor 工作区就在本机。
- **Windows 跑法**（见 05 顶部）：`PYTHONIOENCODING=utf-8 python`（**禁用 python3**，本机是失效 Store 桩）；
  verify 独立跑读退出码、别接管道。

## 1. 黄金回归（最关键护栏）

**目的**：证明重构零行为改变——即 `--adapters cc` 的新 builder 与重构前的老 builder 产出逐字节相同。

**方法（修正）**：**不**拿"磁盘旧树"当基线——本地源是**活的、一直在长**（本会话 + 子智能体都是引用本项目的新
会话），拿 stale 快照比会假红。正确做法是**老 builder（`scripts.pre_step1`，纯 CC）vs 新 builder（`--adapters cc`）
在同一份冻结源上产出、逐字节比对**：
- `scratchpad/regress_step.sh`：① 用新 cc 适配器 `discover` 冻结当前源到 `frozen_src/`；② 老/新各
  `--src frozen --out tmp` 建到临时目录；③ tree.json 归一化 `生成时间`（`build_session_tree.py:415` 的 `now()`，
  否则假红）后 sha256 对账。全等即过。
- **命名律**：CC 节点保持裸 `对话N（sid8）`（命名律 02 §7）。
- **独立 verify**：build 后另跑 `verify_tree.py` 读退出码（build 退出 0 ≠ verify 通过）。

**已验证（Step 1，2026-07-05）**：76 生成物逐字节一致 · discover 文件集老/新一致（35）· 重构后 verify_tree 在真实
树 🔴 结构性全过。（旧的 `golden_tree_baseline/`+`regress_cc.sh` 保留为一次性快照参考，但**因源增长不能作重构判据**
——用 `regress_step.sh`。）

## 2. 逐适配器单元测试（`scripts/adapters/tests/`）

夹具用真实文件片段（脱敏后小样本）：

- **claudecode**：两层分别验——(1) **Record 层**逐条原始记录 id=uuid/parent_id=parentUuid、**无合并无丢弃**
  （供血脉与 verify 的记录数不变量）；(2) **entry 层**由 Record 流归一后，合并 tool_result 轮 / 丢空噪声轮的行为与
  旧 `entries_from_objs` 一致。**不把 Record 序列与 entries_from_objs 画等号**（二者粒度不同）。
- **codex**：
  - 归属：`session_meta.cwd` **及全会话 `turn_context.cwd`** 经 canonicalize 判定（大小写/子目录上卷/中途 cd 进
    项目）正确；huaxiang 等无关 cwd 不收。
  - `message` content：input_text/output_text/**input_image**（占位/alt）三类正确；`developer` 角色**跳过**
    （不产 entry、不计入 Record 覆盖集）。
  - `function_call(+output)` 按 `call_id` 配对；`custom_tool_call`→tool；`reasoning`→跳过。
  - **compacted**：跨 compact 会话样本 → transcript 无摘要重述、不断档。
  - **子线程**：`parent_thread_id` → worker 挂父 Codex 节点下、不平铺为独立根。
  - **import**：命中 `imported_thread_id` → 打 `continues_external`（ref 含 uuid）+ 裁导入摘要首轮；一源多枝
    （同 CC 源 → 2 Codex 线程）各自成枝、按 thread_id 去重不误删。
  - 线性：id=`sid#i`、parent=前一条、seg_key_hint 写入。
- **cursor**（先 spike→再测）：Spike 用例见 05 Step 3.1（dump **全局库** cursorDiskKV + composerHeaders +
  workspace 关联链，产出即验收物）。之后：一个已知工作区 → 非空 Record 序列，角色/文本正确；解析异常→返回空+告警不抛。

## 3. 跨框架合并测试

- **接分支落点**（02 §5 算法）：一对"CC 会话 X + 其 Codex 导入 T" → T 出现在 X 中被续接 uuid 所在段节点下
  `分支（codex·…）`、`段.md` 不含导入摘要；X 不双计。**多叶**时挂到正确叶；**目标未入树/被剪枝**时 T 降级为原生根
  `对话N（codex·…）` + 告警、不崩、不丢。**一源多枝**：同 X 下出现 2 个 codex 分支。
- **子线程**：Codex worker 挂父会话节点下（受 `--with-subagents`）。
- **原生并列根**：原生 Codex + Cursor 会话各成 `对话N（codex/cursor·…）` 根，与 CC 根并列同一 `对话树/`。
- **归属边界**：子目录会话（`…\2025cell\URDME20251221`、`DRL-main/DRL-main`、CJK 编码目录）上卷进 2025cell；
  无关项目（`T:\TashanAgent4S_2026\…`、`Documents\New project`、huaxiang）**不**收入。**大小写变体**
  （`T:\…2025cell` 与 `t:/iop/2025cell`）落进同一森林、不重复计数。
- **计数等式**（可核对，非裸数字）：`discover 命中 − 合法空会话 = 入树`；顶层根数 = CC 根 + 原生 Codex 根 +
  Cursor 根 − 接成分支数。`--list` 预览人工过目。

## 4. verify_tree 两模式

- CC 节点走 `tree`：现有 7 项 🔴 结构性检查全过（回归后仍全绿）。
- Codex/Cursor 节点走 `linear`：①id 无重复；②节点内 id 顺序 = emit 序；③根→叶覆盖该 session **经 `adapter.parse`
  实际 emit 的 Record 序列**（基准=parse 产出集：response_item 流映射后，**排除** reasoning/developer/非 response_item
  事件含 compacted/import 摘要首轮，再经 is_user_text 剪枝），顺序一致（**不用"非桥接"概念**）；④`段.md` 的
  `节点段: N 条记录`（线性 emit 必须输出）= 节点 id 数。🟡 陈旧照旧只提醒。
- 全局：**node_dir 唯一性断言**（去重后数==节点数）。
- 跑法：独立 `PYTHONIOENCODING=utf-8 python verify_tree.py --person Alice; echo $?`（0=结构性全过）。

## 5. PII 闸

- 三家 `段.md` 全过 `check_pii.py`（提交硬门）。**但 `check_pii.py:23` 只扫 4 类**
  （email/cn-phone/long-id/wechat-id）——**结构上抓不到**绝对路径/机器名。Codex/Cursor 记录常含它们：如需机器化
  拦截，**新增 redact 模式并并入 `check_pii.py:23` 白名单**（否则 render 补了、闸仍不查）；否则明确"路径/机器名靠
  私有仓 + 人工过目"。别暗示 check_pii 能兜住它。

## 6. 子智能体审核 / 验收（客观 rubric）

- **忠实性 rubric**（抽样 `段.md` 对真源，固定抽样比例 ≥20%）：逐条核 ①工具名/入参 ②工具结果 ③轮序 ④无新增
  内容（无幻觉）⑤角色正确（用户轮非 agent）。任一条不符即 finding。
- **"子智能体验收过" = 其结构化 findings 中 blocker/major = 0**（nit/minor 记录但不拦）。
- **recall 验收**：固定一组查询（如"Codex 里改的第二章 tex""Cursor 那个相图脚本"）→ 期望 top-k 命中含 Codex/
  Cursor 来源节点、且带真源。
- 子智能体只读/只审/只报，不改核心（单点写入、防并发漂移）。

## 7. 阶段验收闸一览（详见 05）

| 阶段 | 验收闸（红不放行） |
|---|---|
| Step 0a/0b | 5 文档过审并修订；黄金树+归一化哈希+regress 冒烟 PASS |
| Step 1 | `regress_cc.sh check` 逐字节全等 + 独立 verify tree 模式退 0 + 孪生 diff 空 |
| Step 2 | 计数等式核对入树、子线程挂父、接分支(含多叶/一源多枝/降级)、抽样忠实 rubric、linear verify 退 0、子智能体 blocker/major=0 |
| Step 3 | spike 全局库 schema 落文档、非空会话入树、坏库降级不崩、子智能体验收 |
| Step 4 | 一片森林计数等式、两模式 verify + check_pii + node_dir 唯一断言全绿、向量库覆盖三家、recall 固定查询命中 |
