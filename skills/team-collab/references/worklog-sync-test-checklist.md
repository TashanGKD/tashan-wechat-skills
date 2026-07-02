# 工作日志同步模块 · 测试清单（Test Checklist）

> 被测对象：「对话树 / 工作日志」同步上传模块（`build_session_tree.py` + 未来 `sync_worklog.py` + `verify_tree.py` + 各工具入口）。
> 目标：在**所有使用场景、所有入口**下都满足 —— **准确性**（无遗漏、无错配、不覆盖人写内容、脱敏到位）+ **方便性**（新旧判定明确、操作无歧义、工具中立）。
> 状态：✅通过 / 🟡有歧义或缺指引 / 🔴会出错或缺实现 / ⚠️未实测(设计推演) / ☐待测。
> **§7 是 2026-06-19 沙盘推演（12 个冷启动智能体）汇总出的正式 Bug 列表，下表 `状态/风险点` 已据此回填、并引用 BUG-编号。**

---

## 0. 生成用例的轴（场景 = 轴的组合）

- **主轴 A · 范围**：① 同步「我这次会话」　② 同步「全项目所有对话」
- **主轴 B · 本会话相对树的状态**：B1 新会话·新根 / B2 新会话·新分支 / B3 旧会话·同节点续写 / B4 旧会话·内部新分叉 / B5 旧会话·无变化
- **修饰维度**：C 工具（Claude Code / Codex·Cursor）· D 角色（代表谁 / 一棵树一 person）· E 时机（中途 / 收尾 / 首次）

---

## 1. 范围① — 同步本会话

| ID | 场景 / 入口 | 预期（验收点） | 状态 | 风险 · 歧义点（实测） |
|---|---|---|---|---|
| A1 | 新会话·新根 | 识别为无血脉新根→建 `对话N` | ✅ | 走查通过：builder auto-discover 自动落新根 |
| A2 | 旧会话·同节点续写 | 段md 续写增量，人写内容保留 | 🟡 | BUG-1：没有"续写我这段"的入口，实际只能全量重建 |
| A3 | 新会话·新分支（末尾续接） | 找分支点→挂新分支→同步增量 | 🟡 | BUG-1：无法显式声明续接，全靠 builder 按 uuid 自动拼 |
| A4 | 旧会话·内部新分叉 | 原节点更新 + 新建 child；verify 过 | 🟡 | BUG-9：段被切短后段首时间戳是否稳定、人写记忆能否贴回，未说死 |
| A5 | 旧会话·无变化 | 树不变、不产生空提交 | 🟡 | BUG-6/E6：live 会话总在变，"无变化"难判；幂等未验证 |
| A6 | sid 滚动（压缩续接换 sid） | 按共享 uuid 判成新分支而非新根 | 🟡 | BUG-1/BUG-8：靠 uuid 血脉自动拼；同一 sid 可能合法裂成两个根，未解释 |
| A7 | rewind 到历史检查点继续 | 分支点在中间、两支都在 | ⚠️ | BUG-1：无法声明"分支点在中间"，全靠 parentUuid 自动判（断裂时会错） |
| A8 | 同会话多次并列分支 | 节点 ≥2 children，每支独立 | ⚠️ | 未实测；依赖 builder 按 children 切，无人工兜底 |
| A9 | mid-session 同步 live 会话自己 | 快照到当前；first-ts 保人写 | 🟡 | BUG-6：本会话刚同步完，源又长了→树立即又过期 |
| A10 | 空/琐碎会话（如"收到"） | 无实质内容排除；有血脉则收 | ✅ | 走查通过：f5be6919 正确排除、ef9bcfc8 靠血脉收回 |
| A11 | 跨 cwd 的本会话 | 不论 cwd 都进同一 person 树 | ✅ | 走查通过：--list 跨两个项目目录收齐 42 会话 |

---

## 2. 范围② — 同步全项目所有对话

| ID | 场景 / 入口 | 预期（验收点） | 状态 | 风险 · 歧义点（实测） |
|---|---|---|---|---|
| B1 | 首次冷启动（无树） | 全量建；verify 全过 | ✅ | 走查通过（builder 全量重建） |
| B2 | 全量刷新（树已存在） | 增量并入；人写无损；孤儿清除 | 🟡 | BUG-6：当前已提交树就是陈旧+verify 失败态，需重建 |
| B3 | self-inclusion（新会话里做全量） | 触发者自己也进树 | ✅ | 走查通过：本会话 b55e36e9 被 --list 收进 |
| B4 | 批量补节点 | 待补填满；桥接段自动完成 | 🟡 | BUG-10："待补"prose 误判；committed 树已 0 待补 ✅ |
| B5 | 归属判定 | marker + 血脉两轮 | 🟡 | BUG-14：glob 固定深度 2、marker 对 Codex 偏弱→可能漏 |

---

## 3. 边界 / 异常

| ID | 场景 | 预期（验收点） | 状态 | 风险 · 歧义点（实测） |
|---|---|---|---|---|
| C1 | 会话已归档/删除 | 同步不崩；已有节点保留 | 🔴 | BUG-5：源被物理删→该节点人写记忆变孤儿丢失，无规则 |
| C2 | 多 person | 每 person 一棵 `对话树/` | 🟡 | BUG-13：无 git 命令样例；规则未写死 |
| C3 | 我代表别人 | 只动自己负责的 person 树 | 🟡 | BUG-13：边界靠记纪律、无样例 |
| C4 | 子智能体 transcript | `subagents/` 下不进树 | 🟡 | BUG-14：现靠 glob 深度运气没收；build/verify 范围须一致 |
| C5 | 并发同步 | fetch+rebase、不强推 | 🟡 | 共享文件（README/总索引）合并细则未给 |
| C6 | 索引与实际不一致 | 一致性 gate 报错/自愈 | 🔴 | BUG-3/6/12：无一致性 gate；当前树陈旧失败；旧 README doc-drift |

---

## 4. 入口（从哪儿发起）

| ID | 入口 | 预期（验收点） | 状态 | 风险 · 歧义点（实测） |
|---|---|---|---|---|
| D1 | CC `/worklog` | 识别 sid→判新旧→同步 | 🟡 | BUG-1：实际是全量重建；builder 不读 session 变量、本机 CLAUDE_CODE_SESSION_ID 空 |
| D2 | 手动跑脚本 | 参数清晰、默认安全 | ✅ | 走查通过（只写本地、不自动提交）；BUG-11：未说收尾走 main 还是 PR |
| D3 | pre-commit 提醒 | 非阻断提示 | ✅ | 走查通过 |
| D4 | Codex/Cursor 入口 | 能判新旧/生成段md/产物一致 | 🔴 | BUG-2：无适配器、Codex 无 uuid/parentUuid、builder 只扫 ~/.claude→根本跑不了 |
| D5 | verify_tree（建后校验） | 6 查全过；自测能抓 | 🟡 | BUG-7：缺"红了怎么修"指引；BUG-15：退出码经管道会被吞 |
| D6 | 跨工具接力（CC↔Codex） | 两套逻辑产物一致、不孤儿 | 🔴 | BUG-2：Codex 侧无法落地；重建可能把另一套节点当孤儿删 |

---

## 5. 准确性 / 方便性 专项（横切）

| ID | 验收点 | 由谁保证 | 状态 | 备注（实测） |
|---|---|---|---|---|
| E1 | 无遗漏：源全集=入树+剪枝（剪枝中 0 用户消息） | verify_tree | 🔴 | BUG-6：当前树报 47 条用户消息遗漏（陈旧所致，重建即修） |
| E2 | 无错配：根→叶=真实 parentUuid 链 | verify_tree | 🔴 | BUG-6：当前树报断裂/重构（同上，陈旧） |
| E3 | 人写内容不被覆盖 | builder preserve | 🟡 | BUG-10："待补"prose 误判会触发覆盖 |
| E4 | 脱敏到位 | redact+自测+终扫 | 🔴 | BUG-4：无机器 gate、唯一靠人工过目、无字段清单 |
| E5 | 崩溃安全：重建中途崩不丢树 | `.bak` 改名再删 | ✅ | 已实现 |
| E6 | 幂等：同输入重复同步→树不变 | （待验证） | 🟡 | BUG-6：live 会话在长→很难幂等 |
| E7 | 新旧判定无歧义 | （应由 INDEX 保证） | 🔴 | BUG-1：无显式声明手段、全靠 uuid 自动拼，A6/A7 有歧义 |
| E8 | 工具中立：判定只依赖仓库索引 | 索引 manifest | 🔴 | BUG-1/2：INDEX 不存在；判定依赖 CC 专属 uuid，不中立 |

---

## 6. 沙盘推演分工（已执行，2026-06-19）

| 角度 | 覆盖用例 | 主要发现 |
|---|---|---|
| 甲 · sid 滚动/rewind/并列分支 | A2 A6 A7 A8 | BUG-1（无续接声明）、BUG-8（裂多根） |
| 乙 · 全项目全量+self-inclusion+归属 | B1 B2 B3 B5 A11 | BUG-6（陈旧失败）、BUG-12（旧 README）、BUG-14 |
| 丙 · 批量补节点+人写vs机器 | B4 E3 E4 | BUG-10（待补误判）、BUG-4（脱敏无 gate） |
| 丁 · 跨工具(Codex)+入口 | D1 D4 D6 E8 | BUG-2（Codex 走不通）、BUG-1 |
| 戊 · 边界异常+并发+一致性 | C1 C5 C6 E5 E6 | BUG-5（删源丢记忆）、BUG-7（红了不会修）、BUG-15（退出码假象，已澄清） |
| 己 · live 会话+空会话+新根 | A1 A9 A10 | BUG-3（verify 非硬门）、BUG-6 |

---

## 7. 正式 Bug 列表（2026-06-19 · 12 智能体冷启动沙盘走查）

### 7.0 修复进度（更新 2026-06-19）

> 战略决策：**放弃"增量同步 + 独立 INDEX + 手动判新旧"，确认"全量重建"为唯一机制**（自动判新旧、`tree.json` 即索引）。

| BUG | 状态 | 落点 |
|---|---|---|
| BUG-1 增量未实现 | ✅ 已对齐文档 | worklog.md 写死"唯一机制=全量重建、自动判新旧、tree.json=索引" |
| BUG-3 verify 非硬门 | ✅ 已修 (0a614fb) | pre-commit 暂存对话树→verify 完整性硬门（只拦🔴）+ builder 建后自检 |
| BUG-4 脱敏无 gate | ✅ 已修 (0a614fb) | `check_pii.py`(+自测) 接 pre-commit + CI |
| BUG-7 陈旧vs真错配混 | ✅ 已修 (2669676) | verify 分 🔴结构性/🟡陈旧、重构只比树内记录 |
| BUG-10 待补哨兵脆弱 | ✅ 已修 (0a614fb) | builder 改行锚定 `has_placeholder()` |
| BUG-5 源删除丢记忆 | ✅ 已定规则 | worklog.md：源删→节点随之消失；要留先挪 `_旧归档/` |
| BUG-8 同会话多根 | ✅ 已说明 | worklog.md：压缩续接断链→合法多根、verify 通过 |
| BUG-9 段身份稳定性 | ✅ 已说明 | worklog.md：节点身份=段首时间戳；内部分叉留意重贴 |
| BUG-11 main vs PR | ✅ 已定 | worklog.md：记忆层文档类，main 直推、不开 PR |
| BUG-12 旧 README 漂移 | ✅ 已修 | `智能体工作日志/README.md` 重写为指针式、删死链 |
| BUG-13 多person/AaronGrity | 🟡 部分 | git 样例已写；AaronGrity 身份注册待 Boyuan 确认 |
| BUG-15 退出码管道吞 | ✅ 已说明 | worklog.md：查退出码别接管道 |
| BUG-6 当前树陈旧失败 | ⏳ 待重建 | 用新 builder 重建即修绿（结构性4→0）；挑安静点做 |
| BUG-2 Codex 走不通 | ⏳ P2 | worklog.md 已标"暂不支持自动同步"；适配器待写 |
| BUG-14 glob 深度2/marker | ⏳ P2 | 同上；递归 glob 待改 |



### A 类 · 设计漏洞 / 缺实现（要改方案或写代码）

| 编号 | 级 | 标题 | 涉及 | 证据 | 修复方向（草案） |
|---|---|---|---|---|---|
| BUG-1 | 🔴 | **增量同步未实现，只有全量重建**：builder 不读 session 变量、无 `sync_worklog.py`/INDEX，agent 无法声明"我是某节点续接"，全靠 builder 按 uuid 自动拼 | A2 A3 A6 A7 D1 E7 E8 | `build_session_tree.py` grep SESSION=0、只全量重建；`worklog.py` 读 CLAUDE_CODE_SESSION_ID（本机空）；仓库无 sync_worklog/INDEX | 要么**建 INDEX + sync_worklog 真增量**，要么**承认"就用全量重建"、把心智模型/skill 改成与现实一致**（二选一，见下"修复思路"） |
| BUG-2 | 🔴 | **Codex 完全走不通**：builder 写死 `~/.claude/projects`、整树建于 uuid/parentUuid，Codex 会话无此字段、适配器待写 | D4 D6 E8 | `build_session_tree.py:29,57`；`conversation-log-spec.md:89` ⬜待写；`~/.codex/sessions/.../rollout-*.jsonl` 记录=`{timestamp,type,payload}` | 写 `make_transcript_codex.py` + Codex 版血脉(`forked_from_id`/`turn_id`)→统一原语；或先在 skill 标明"Codex 暂不支持自动同步" |
| BUG-3 | 🔴 | **verify 不是 commit-time 硬门**：坏/陈旧树能照样提交 | C6 D5 | `.githooks/pre-commit` 只 check_posts+check_entrypoints；verify_tree.self-test 是 hermetic（不查真实树） | 重建脚本对 EXIT≠0 阻止提交；或 pre-commit 在暂存了 `对话树/` 时跑 verify（但要处理"陈旧≠错"，见 BUG-7） |
| BUG-4 | 🔴 | **脱敏无机器 gate**：唯一靠人工过目的高危环节、无字段清单 | E4 | `worklog.md:74` 铁律3 自承"命中0≠干净"；段.md 提交期无 PII 拦截 | 把终扫(手机/邮箱/微信/身份证/长号)做成 commit-time gate；给"重点扫报价/公司名/个人信息"清单 |
| BUG-5 | 🟡 | **源会话被物理删→人写记忆变孤儿丢失**，无规则 | C1 | `worklog.md:30` 只说改名/增减无损，未覆盖"源删除" | 定规则：源删了，其节点+人写记忆是保留(沉进 `_旧归档/`)还是随之消失；写进 skill |
| BUG-6 | 🔴 | **当前已提交树处于 verify 失败（陈旧）态**：47 条用户消息"遗漏"+断裂/重构 | E1 E2 B2 | `verify_tree.py --person Boyuan` EXIT=1；tree.json 01:00 建于 34 会话，现 --list 42；漏的 uuid 全属建树后新增会话（b55e36e9 等） | **重建即修**（非 builder bug）；但暴露"无 staleness 闸"——见 BUG-3/7 |

### B 类 · 文档 / 措辞歧义（改 skill）

| 编号 | 级 | 标题 | 涉及 | 证据 |
|---|---|---|---|---|
| BUG-7 | 🟡 | "verify 红了"多半是"该重建"非 bug，skill 没说"先 build 再 verify、对同一产物跑、红了如何区分陈旧/真错配/排除" | D5 E1 E2 | `worklog.md:34-39` |
| BUG-8 | 🟡 | 同一 session 合法裂成多个并列根（压缩续接断 parentUuid）未解释 | A6 | `对话3(022fff34)` 与 `对话8(022fff34)` 段md 头同 session id |
| BUG-9 | 🟡 | 段身份键在"内部新分叉"时是否稳定未说死 | A4 | `build_session_tree.py:125 _seg_key_from_md` 取段首时间戳 |
| BUG-10 | 🟡 | "待补"单字符串护栏脆弱：正文写"待补"二字会被误判未填、被覆盖 | E3 B4 | `build_session_tree.py:~344 "待补" not in c` |
| BUG-11 | 🟡 | worklog 提交走 main 还是分支/PR，worklog.md 与 CONTRIBUTING.md 口径不一 | D2 D3 | `worklog.md:43` vs `CONTRIBUTING.md` |
| BUG-12 | 🟡 | `智能体工作日志/README.md` 仍是旧"五件套"方案 + 2 条死链（已移 `_旧归档/`） | C6 | `智能体工作日志/README.md:11-19,81-82` |
| BUG-13 | 🟡 | 多 person 无 git 命令样例；`AaronGrity/` 有目录未在画像注册（索引漂移、无 gate） | C2 C3 | `画像/README.md` 成员表无 Aaron；`智能体工作日志/AaronGrity/` 存在 |
| BUG-14 | 🟡 | discover glob 固定深度 2 + marker 对 Codex 偏弱→可能漏深层/跨 fork 会话 | B5 C4 A11 | `build_session_tree.py:57 glob(PROJECTS,"*","*.jsonl")` |
| BUG-15 | 🟢 | verify 退出码经管道(`| tail`)会被吞，skill 应提醒"查退出码别接管道" | D5 | `verify_tree.py:147 sys.exit(main())` 真返回 1（已澄清非脚本 bug） |

### ✅ 已证实非问题
happy-path（`--person` / 精确 `git add` 不用 `-A` / 跨 cwd 自动收齐 / 无损保留 / `.bak` 崩溃安全）、verify 退出码本身正确、补节点 committed 树已 0 待补、A10 空会话取舍、A11 跨 cwd、B3 self-inclusion——12 个冷启动智能体几乎都能只凭 skill 摸对 happy-path。

> 下一步：按 §7 优先级修复（见随附"修复思路"）。修一项 → 回本表把对应 `状态` 改 ✅ + 在 §7 标注修复 commit。
