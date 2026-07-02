#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_session_tree.py —— 把本地 Claude Code 会话重建成「去重分支树」并落盘。

把 ~/.claude/projects/<proj> 下所有会话 jsonl，按 uuid/parentUuid 拼成一棵**去重**的分支树
（共享主干只存一份，分支只存分叉后的增量），落成：
  - A 布局节点目录（物理嵌套）：对话N（sid）/ 段.md · 研究历程.md · 动机日志.md · 子智能体/ · 分支M（sid）/…
  - tree.json     ← 机器源（单一真源，其它视图由它生成）
  - TREE.md       ← 嵌套列表索引
  - 思维导图.md   ← Mermaid 流程图（GitHub 原生渲染、节点可点击跳转）

随对话增多，**重跑即长大**。生成物（段.md/TREE/思维导图/tree.json）一律**别手改**——
要改改源或脚本重生成；只有 研究历程.md / 动机日志.md 是人写的"节点记忆"，脚本只脚手架、绝不覆盖。

用法：
  python3 build_session_tree.py --person Boyuan            # 默认源=当前会话所在的项目目录
  python3 build_session_tree.py --person Boyuan --src ~/.claude/projects/<proj> --out <目录>
  python3 build_session_tree.py --person Boyuan --keep-stubs   # 不剪枝（连无用户文本的死桩也建）
"""
import argparse, glob, json, os, re, shutil, sys
from collections import defaultdict
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_transcript_claudecode as mt   # 复用 解析/脱敏/渲染

REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
PROJECTS = os.path.expanduser("~/.claude/projects")
# 本仓库的标记：会话只要"够到本项目"（引用了仓库目录名 / 本 skill 路径）就算属于本项目，
# 不论它存在哪个项目目录（cwd）下。标记是 ASCII，可直接在原始 jsonl 里 grep（中文是 \u 转义的，但路径名不是）。
REPO_MARKER = os.path.basename(REPO)   # 自动取当前仓库目录名，不写死项目

def _uuids_of(f):
    s = set()
    try:
        for ln in open(f, encoding="utf-8", errors="ignore"):
            ln = ln.strip()
            if not ln:
                continue
            try:
                o = json.loads(ln)
            except Exception:
                continue
            if o.get("uuid"):
                s.add(o["uuid"])
    except OSError:
        pass
    return s

def discover_session_files():
    """扫 ~/.claude/projects/ 下**所有**项目目录，返回属于本仓库的会话 jsonl 路径（跨 cwd）。
    两轮判定，确保不遗漏：
      ① 内容引用了本仓库目录名（REPO_MARKER）的会话；
      ② 与①**共享 uuid**（同一会话血脉：续接/分支会复制记录）的会话——捕捉**早于仓库命名**的
         起源会话（其 transcript 里还没有仓库名，但记录被后续会话延续，否则会漏掉项目最初那几轮）。"""
    allf = sorted(glob.glob(os.path.join(PROJECTS, "*", "*.jsonl")))
    marker, rest = [], []
    for f in allf:
        try:
            hit = REPO_MARKER in open(f, encoding="utf-8", errors="ignore").read()
        except OSError:
            hit = False
        (marker if hit else rest).append(f)
    known = set()
    for f in marker:
        known |= _uuids_of(f)
    extra = [f for f in rest if _uuids_of(f) & known]
    return sorted(marker + extra)

def sanitize(s, n=20):
    s = re.sub(r"\s+", " ", (s or "").strip())
    s = re.sub(r'["\[\](){}<>|#`*]', "", s)
    return s[:n]

# 占位符（未填）判定：只认**整行**的 `⚠️ 待补` / `- ⚠️ 待补` / `> 摘要：⚠️待补`，
# 正文里随手提到"待补"二字（如"`⚠️ 待补` 骨架""宁可标记待补"）不算未填——消除 prose 误判（BUG-10）。
PLACEHOLDER_RE = re.compile(r"(?m)^\s*(?:[-*] )?⚠️ ?待补\s*$|摘要[:：]\s*⚠️待补")
def has_placeholder(content):
    return bool(PLACEHOLDER_RE.search(content))

def read_zhaiyao(dir_path):
    """读节点 研究历程.md 顶部的「摘要：…」行（人写，喂思维导图）。未填/待补则返回 None。"""
    p = os.path.join(dir_path, "研究历程.md")
    if not os.path.exists(p):
        return None
    m = re.search(r"摘要[:：]\s*(.+)", open(p, encoding="utf-8").read())
    if not m:
        return None
    txt = m.group(1).strip()
    if (not txt) or txt.startswith("⚠") or txt.startswith("（待"):
        return None
    return sanitize(mt.redact(txt, {}), 42)

def load_records(paths):
    """读给定的若干会话 jsonl（可跨项目目录），按 uuid 去重，返回 (objs_by_uuid, sessions_by_uuid)。
    不同 cwd/目录的会话在这里被并到同一组记录里，再按 parentUuid 拼成一棵树——文件夹不进结构。"""
    objs, sess = {}, defaultdict(set)
    for f in paths:
        sid = os.path.basename(f)[:-6]
        for line in open(f, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except Exception:
                continue
            u = o.get("uuid")
            if not u:
                continue
            if u not in objs:
                objs[u] = o
            sess[u].add(sid)
    return objs, sess

def text_of(o):
    if not isinstance(o, dict):
        return ""
    m = o.get("message", {}); c = m.get("content") if isinstance(m, dict) else None
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        for p in c:
            if isinstance(p, dict) and p.get("type") == "text":
                return p.get("text", "")
    return ""

TS_RE = re.compile(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]")

def _seg_key_from_md(md_text):
    """段的稳定身份 = 首个 `### [时间]`（段起点）。**只用首时间戳、不含记录数/别名/路径**——
    段起点在重建、改别名、甚至 live 会话往段尾追加记录时都不变，故据此贴回已填记忆最稳，不会因记录数变动而失配。"""
    for ln in md_text.split("\n"):
        m = re.match(r"###\s*\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]", ln)
        if m:
            return m.group(1)
    return None

def read_tasks(dir_path):
    """读节点 研究历程.md 的「## 任务目录」小节 → [(缩进层级, 文本, 时间戳or None), ...]。"""
    p = os.path.join(dir_path, "研究历程.md")
    if not os.path.exists(p):
        return []
    m = re.search(r"(?ms)^##\s*任务目录\s*\n(.*?)(?=\n##\s|\Z)", open(p, encoding="utf-8").read())
    if not m:
        return []
    out = []
    for ln in m.group(1).split("\n"):
        mm = re.match(r"^(\s*)[-*]\s+(.+)$", ln)
        if not mm:
            continue
        lvl = len(mm.group(1)) // 2
        body = mm.group(2).strip()
        tsm = TS_RE.search(body)
        ts = tsm.group(1) if tsm else None
        text = mt.redact(TS_RE.sub("", body).replace("`", "").strip(" ·"), {})
        if text:
            out.append((lvl, text, ts))
    return out

def main():
    ap = argparse.ArgumentParser(description="重建去重分支树 → A 布局 + tree.json + TREE.md + 思维导图.md")
    ap.add_argument("--person", required=True)
    ap.add_argument("--src", help="只扫这一个项目目录（默认：跨所有项目目录收齐引用本仓库的会话）")
    ap.add_argument("--manifest", help="只用清单文件里列出的 session-id 建树（每行一个）。"
                    "用于固定快照、稳定重建——尤其在 live 会话期间避免新生成的续接/子智能体会话不断挤进来令树漂移。"
                    "默认不传=自动收齐全部引用本仓库的会话。")
    ap.add_argument("--out", help="输出目录（默认 团队协作记录/智能体工作日志/<person>/对话树）")
    ap.add_argument("--list", action="store_true", help="只列出判定为属于本项目的会话（建树前过目防误收），不生成")
    ap.add_argument("--keep-stubs", action="store_true", help="不剪枝：连无用户文本的死桩也建")
    ap.add_argument("--with-subagents", action="store_true", help="把每个会话的子智能体镜像到其归属节点")
    args = ap.parse_args()

    if not mt.PERSON_RE.match(args.person):
        sys.exit(f"✗ --person 非法：{args.person!r}")

    out = args.out or os.path.join(REPO, "团队协作记录", "智能体工作日志", args.person, "对话树")

    # 取源：默认跨**所有**项目目录收齐"引用了本仓库"的会话（与 cwd/文件夹无关）；--src 仍可只扫单个目录
    if args.src:
        files = sorted(glob.glob(os.path.join(args.src, "*.jsonl")))
    else:
        files = discover_session_files()
    if args.manifest:
        keep = {ln.strip() for ln in open(args.manifest, encoding="utf-8") if ln.strip() and not ln.startswith("#")}
        files = [f for f in files if os.path.basename(f)[:-6] in keep]
        print(f"  manifest 固定：从清单 {len(keep)} 个 session-id 中匹配到 {len(files)} 个会话")
    if not files:
        sys.exit(f"✗ 没发现引用本仓库（{REPO_MARKER}）的会话")

    if args.list:
        print(f"判定为属于本项目（引用了 {REPO_MARKER}）的会话，共 {len(files)} 个：")
        for f in files:
            proj = os.path.basename(os.path.dirname(f)); sid = os.path.basename(f)[:-6]
            print(f"  [{proj}] {sid}")
        return 0

    objs, sess = load_records(files)
    if not objs:
        sys.exit("✗ 没读到记录")

    # 建 children / roots
    children = defaultdict(list); roots = []
    for u, o in objs.items():
        p = o.get("parentUuid")
        (children[p].append(u) if (p and p in objs) else roots.append(u))
    for u in children:
        children[u].sort(key=lambda x: objs[x].get("timestamp") or "")
    roots.sort(key=lambda x: objs[x].get("timestamp") or "")

    # 剪枝：标记"子树是否含用户文本"
    has_txt = {}
    def is_user_text(u):
        return objs[u].get("message", {}).get("role") == "user" and bool(text_of(u and objs[u]).strip()) \
            and "tool_result" not in json.dumps(objs[u].get("message", {}).get("content", ""))
    for r in roots:                       # 迭代后序
        order, stack = [], [r]
        while stack:
            x = stack.pop(); order.append(x); stack.extend(children.get(x, []))
        for x in reversed(order):
            mine = (objs[x].get("message", {}).get("role") == "user") and bool(mt._strip_noise(text_of(objs[x])).strip())
            has_txt[x] = mine or any(has_txt.get(c, False) for c in children.get(x, []))
    def kids(u):
        cs = children.get(u, [])
        return cs if args.keep_stubs else [c for c in cs if has_txt.get(c, False)]

    def walk_seg(start):
        seg = [start]; cur = start
        while len(kids(cur)) == 1:
            cur = kids(cur)[0]; seg.append(cur)
        return seg, kids(cur)

    # 遍历，分配编号 + 落盘
    counts = {}; nodes = []; mer_nodes = []; mer_edges = []; tree_lines = []; catalog_lines = []
    nid = [0]
    def emit(start, alias, dir_path, depth, parent_mer):
        seg, ch = walk_seg(start)
        # 不按时间戳排序：seg 已是 walk_seg 沿 parentUuid 走出的**因果链顺序**（start→单child→…）。
        # 时间戳非严格单调时再排序会打乱真实因果顺序、与原始会话错配（verify_tree.py 会抓）。
        ss = sorted(set().union(*[sess[u] for u in seg]))
        sid8 = ss[0][:8] if len(ss) == 1 else f"{len(ss)}sess"
        t0 = (objs[seg[0]].get("timestamp") or "")[:16]
        t1 = (objs[seg[-1]].get("timestamp") or "")[:16]
        summ = ""; has_user = False
        for u in seg:
            if objs[u].get("message", {}).get("role") == "user":
                t = mt.redact(mt._strip_noise(text_of(objs[u])), counts)
                if t.strip():
                    summ = sanitize(t, 28); has_user = True; break
        if not summ:
            summ = sanitize(mt.redact(mt._strip_noise(text_of(objs[seg[0]])), counts), 24) or "(工具/系统段)"
        os.makedirs(dir_path, exist_ok=True)
        # 段.md（复用 mt 解析+脱敏+渲染）
        entries = mt.entries_from_objs([objs[u] for u in seg])
        extra = [f"树节点: {alias}", f"涉及 session: {', '.join(ss)}", f"节点段: {len(seg)} 条记录"]
        md, _ = mt.render(entries, args.person, "Claude Code", ss, counts, extra)
        open(os.path.join(dir_path, "段.md"), "w", encoding="utf-8").write(md)
        # 研究历程（含「摘要」行）/ 动机：脚手架，不覆盖已写的
        # 桥接段（无用户实质文本 = 纯续接/工具段）自动写成"空桥接"完整内容，不算待补、不需人工补；
        # 且这类段常无 `### [时间]` 锚点，段身份键取不到、无法保留——只有自动完成才稳定。
        rp = os.path.join(dir_path, "研究历程.md")
        if not os.path.exists(rp):
            if has_user:
                open(rp, "w", encoding="utf-8").write(
                    f"# 研究历程 · {alias}\n\n"
                    f"> 摘要：⚠️待补（一句话=这个分支做了什么；喂给思维导图，可迭代更新）\n"
                    f"> 本节点（{summ}…，{t0}）的探索 / 转向 / 发现 / 踩坑。**人工补写**，脚本不覆盖。\n"
                    f"> 规则：**摘要可迭代更新；下面历程正文只增不删（append-only）**。\n\n"
                    f"## 主线\n⚠️ 待补\n\n## 关键转向 / 发现\n⚠️ 待补\n\n## 踩坑 / 修正\n⚠️ 待补\n\n"
                    f"## 任务目录\n"
                    f"> 本节点内陆续做的任务（章→节，2 空格一级）；**叶子末尾带 `[时间戳]`**（抄自 `段.md` 里驱动该任务那轮的 `### [..]` 标题），builder 据此自动算行号、生成可跳转目录。append-only。\n"
                    f"- ⚠️ 待补\n")
            else:
                open(rp, "w", encoding="utf-8").write(
                    f"# 研究历程 · {alias}\n\n"
                    f"> 摘要：空续接/工具桥接节点，无实质对话内容\n"
                    f"> 本节点（{summ}…，{t0}）为会话续接/纯工具段，无用户实质指令。**自动判定，无需人工补写。**\n\n"
                    f"## 主线\n空续接/工具桥接段：本段无用户实质指令、无 agent 实质产出；真正的工作见其子分支。本节点仅作树结构上的衔接点。\n\n"
                    f"## 关键转向 / 发现\n无。\n\n## 踩坑 / 修正\n无。\n\n"
                    f"## 任务目录\n- 无实质任务（空续接桥接节点；实际工作见子分支）\n")
        mp = os.path.join(dir_path, "动机日志.md")
        if not os.path.exists(mp):
            if has_user:
                open(mp, "w", encoding="utf-8").write(
                    f"# 动机日志 · {alias}\n\n"
                    f"> 本节点（{summ}…，{t0}）每步**为什么**这么做 / 否决了什么。**人工补写**，脚本不覆盖。\n\n"
                    f"## 关键决策与动机\n⚠️ 待补\n")
            else:
                open(mp, "w", encoding="utf-8").write(
                    f"# 动机日志 · {alias}\n\n"
                    f"> 本节点（{summ}…，{t0}）为会话续接/纯工具段。**自动判定，无需人工补写。**\n\n"
                    f"## 关键决策与动机\n无（空续接桥接节点，无决策可记；动机见其子分支）。\n")
        # 贴回已填内容：按"段身份"匹配（重建/改别名/换路径都不丢；孤儿已被 rmtree 清掉）
        # 研究历程/动机分别贴回——某一个填了另一个没填时，填了的贴回、没填的留新脚手架。
        _pv = preserved.get(_seg_key_from_md(md))
        if _pv:
            if "rh" in _pv:
                open(rp, "w", encoding="utf-8").write(_pv["rh"])
            if "mj" in _pv:
                open(mp, "w", encoding="utf-8").write(_pv["mj"])
        # 思维导图标签：优先用 研究历程 的人写摘要；没填则回退自动截取
        label = read_zhaiyao(dir_path) or (summ + "…")
        # mermaid 节点 + 边
        nid[0] += 1; mid = f"n{nid[0]}"
        rel = os.path.relpath(dir_path, out).replace(os.sep, "/")
        mer_nodes.append((mid, f'{alias}<br/>{label}', rel))
        if parent_mer:
            mer_edges.append((parent_mer, mid))
        tree_lines.append(f"{'  '*depth}- **{alias}** · {label} `[{t0}→{t1}]` ({sid8}) — [段]({rel}/段.md) · [研究历程]({rel}/研究历程.md)")
        nodes.append({"alias": alias, "dir": rel, "sessions": ss, "t0": t0, "t1": t1,
                      "n_records": len(seg), "摘要": label, "auto_summary": summ, "children": len(ch),
                      "parent_dir": os.path.relpath(os.path.dirname(dir_path), out).replace(os.sep, "/") if depth else None,
                      "uuids": list(seg)})   # 段内 uuid 有序序列：供 verify_tree.py 校验覆盖/连续/可重构
        # —— 目录：章=节点（按树嵌套）；章内=该节点任务目录，叶子按时间戳自动算行号、生成跳转链 ——
        ts2line = {}
        for i, ln in enumerate(md.split("\n"), 1):
            tm = re.match(r"###\s*\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]", ln)
            if tm:
                ts2line.setdefault(tm.group(1), i)
        catalog_lines.append(f"{'  '*depth}- **{alias}** · {label} — [对话]({rel}/段.md)")
        for lvl, ttext, ts in read_tasks(dir_path):
            jump = ""
            if ts and ts in ts2line:
                jump = f"  [↪]({rel}/段.md?plain=1#L{ts2line[ts]})"
            elif ts:
                jump = "  ⟨未定位⟩"
            catalog_lines.append(f"{'  '*(depth + 1 + lvl)}- {ttext}{jump}")
        # 递归子分支
        for i, c in enumerate(ch, 1):
            emit(c, f"{alias}-分支{i}", os.path.join(dir_path, f"分支{i}（{(sorted(set().union(*[sess[u] for u in walk_seg(c)[0]]))[0])[:8]}）"), depth + 1, mid)

    # 重建前：按"段身份"快照所有**已填**的 研究历程/动机（与路径/别名无关），随后整树 rmtree 清掉旧结构与孤儿，
    # 重建时在 emit 里据段身份贴回——使重建对已填内容**无损**、且不留旧别名孤儿目录。
    preserved = {}
    if os.path.isdir(out):
        for root, _, fs in os.walk(out):
            if "段.md" not in fs:
                continue
            key = _seg_key_from_md(open(os.path.join(root, "段.md"), encoding="utf-8").read())
            if not key:
                continue
            entry = {}
            # 研究历程 / 动机**各自独立**保留：只要该文件已填完（无未填占位行）就留，
            # 避免"研究历程填了但动机还没填"被整体丢弃（曾踩过的部分填充丢失）。
            # 判"已填"用行锚定占位符（has_placeholder），不是子串"待补"——正文提到"待补"二字不误判（BUG-10）。
            for fn, tag in (("研究历程.md", "rh"), ("动机日志.md", "mj")):
                p = os.path.join(root, fn)
                if os.path.exists(p):
                    c = open(p, encoding="utf-8").read()
                    if not has_placeholder(c):
                        entry[tag] = c
            if entry:
                preserved[key] = entry
        # 崩溃安全：不直接删旧树，先改名 .bak；重建成功后才删 .bak。
        # 这样即使重建中途崩溃，旧树仍在 <out>.bak 可恢复（曾因 rmtree→崩溃丢过整树）。
        bak = out + ".bak"
        if os.path.exists(bak):
            shutil.rmtree(bak)
        os.rename(out, bak)
        print(f"  已按段身份保留 {len(preserved)} 个节点的已填记忆（研究历程/动机分别保留），旧树暂存 .bak、重建成功后清")

    os.makedirs(out, exist_ok=True)
    rn = 0
    for r in roots:
        if not has_txt.get(r, False) and not args.keep_stubs:
            continue
        rn += 1
        sid8 = sorted(set().union(*[sess[u] for u in walk_seg(r)[0]]))[0][:8]
        emit(r, f"对话{rn}", os.path.join(out, f"对话{rn}（{sid8}）"), 0, None)

    # tree.json
    json.dump({"生成时间": datetime.now().strftime("%Y-%m-%d %H:%M"), "源": f"{len(files)} 个引用本仓库的会话（跨项目目录/cwd）",
               "对话数": rn, "节点数": len(nodes), "节点": nodes},
              open(os.path.join(out, "tree.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    # TREE.md
    open(os.path.join(out, "TREE.md"), "w", encoding="utf-8").write(
        f"# 对话树索引（{rn} 段对话 · {len(nodes)} 节点）\n\n"
        f"> 由 `build_session_tree.py` 生成，**勿手改**。源：本地 Claude Code 会话（去重后）。\n"
        f"> 可视化见 [思维导图.md](./思维导图.md)。\n\n" + "\n".join(tree_lines) + "\n")
    # 目录.md（章=节点树；章内=任务目录；↪ 跳到对话相应行）
    open(os.path.join(out, "目录.md"), "w", encoding="utf-8").write(
        f"# 工作总目录（{rn} 段对话 · {len(nodes)} 节点）\n\n"
        f"> 由 `build_session_tree.py` 生成、**勿手改**。章按节点树嵌套；章内是该节点的任务目录。\n"
        f"> 点任务后的 **↪** 跳到该节点 `段.md` 的对应位置（GitHub 上经 `?plain=1#L行号` 定位；行号每次重生成自动刷新）。\n"
        f"> **把所有任务从上往下读 = 整个项目到现在的全部工作内容。**\n\n"
        + "\n".join(catalog_lines) + "\n")
    # 思维导图.md（Mermaid flowchart + 可点击）
    ml = ["# 对话树 · 思维导图", "",
          "> 由 `build_session_tree.py` 生成、**勿手改**。GitHub 网页会把下面这张图**渲染成可视化的树**。",
          "> 注：GitHub 网页**不支持图内点击跳转**（安全限制）——要点击进对应对话，用同目录 "
          "[TREE.md](./TREE.md) 的链接，或在 VS Code / [Mermaid Live](https://mermaid.live) 里打开本图。", "",
          "```mermaid", "flowchart TD"]
    for mid, label, rel in mer_nodes:
        ml.append(f'  {mid}["{label}"]')
    for a, b in mer_edges:
        ml.append(f"  {a} --> {b}")
    for mid, label, rel in mer_nodes:
        ml.append(f'  click {mid} "./{rel}/段.md"')
    ml += ["```", ""]
    open(os.path.join(out, "思维导图.md"), "w", encoding="utf-8").write("\n".join(ml))
    # 规范.md（生成物：本目录的格式说明 + 指向 skill 完整规范）
    open(os.path.join(out, "规范.md"), "w", encoding="utf-8").write(
        "# 对话树 · 格式规范\n\n"
        "> 本文件由 `build_session_tree.py` 生成。完整团队规范见 "
        "[`.claude/skills/team-collab/references/worklog.md`](../../../../.claude/skills/team-collab/references/worklog.md)。\n\n"
        "## 这是什么\n"
        "本地 Claude Code 会话（`~/.claude/projects/<proj>/`）的**去重分支树镜像**：照搬 CC 原生 session 组织，"
        "只做「转统一 md + 脱敏」，按 `uuid`/`parentUuid` 拼成树、按 `uuid` 去重（共享主干只存一份）。\n\n"
        "## 目录布局（A：目录即树，物理嵌套）\n"
        "```\n"
        "对话N（sid前8）/        ← 一段独立对话（根）\n"
        "  段.md                 ← 本节点对话（统一格式·脱敏·不概要）【生成物·勿手改】\n"
        "  研究历程.md            ← 本节点怎么探索/转向/踩坑   【人工补·脚本不覆盖】\n"
        "  动机日志.md            ← 本节点每步为什么            【人工补·脚本不覆盖】\n"
        "  子智能体/              ← 本段 spawn 的子智能体（若有）\n"
        "  分支M（sid前8）/       ← 真实分叉后的增量（递归同构）\n"
        "TREE.md  思维导图.md  tree.json  规范.md   ← 均为生成物·勿手改\n"
        "```\n\n"
        "## 规则\n"
        "1. **节点 = 一段无分叉对话**；**分叉点 = 真实分支**（编辑重发 / 压缩续接 / 恢复都会产生新 session-id → 新分支）。\n"
        "2. **去重**：共享主干只存一份；分支只存分叉后的增量（同 uuid = 同一节点）。\n"
        "3. **命名**：`对话N` / `分支M`（时间序）+ 括注 session-id 前 8 位；层级靠物理嵌套。\n"
        "4. **剪枝**：默认丢掉「整棵子树无任何用户文本」的死桩（`--keep-stubs` 可保留）。\n"
        "5. **唯一标识 = session-id**（CC 原生）；换 id 自然成新节点，不需要我们自己锚定/编号。\n"
        "6. **生成物勿手改**（段.md/TREE/思维导图/tree.json/规范.md）；要改改源或脚本重跑。只有 研究历程/动机日志 是人写的节点记忆。\n"
        "7. **脱敏**：来自原始对话，私有仓 + 脚本脱敏报告 + 人工过目兜底（正则非 100%）。\n"
        "8. **节点记忆**：`研究历程.md` 顶部一行「摘要：…」喂思维导图标签（可迭代更新）；其「## 任务目录」节把节点内任务列成层级，叶子带 `[时间戳]`→builder 生成可跳转的 `目录.md`；历程/任务只增不删（append-only）。`动机日志.md` 记为什么。\n\n"
        "## 怎么重生成（树会自动长大）\n"
        "```bash\n"
        "python3 .claude/skills/team-collab/scripts/build_session_tree.py --person <你>\n"
        "```\n"
        "其他工具（Codex/Cursor）：各自 CC-like 会话目录同理，按 `references/conversation-log-spec.md` 写读取器、复用 render/redact。\n")

    bak = out + ".bak"   # 重建已完整落盘，安全删除暂存的旧树
    if os.path.exists(bak):
        shutil.rmtree(bak)
    print(f"✓ 树已生成 → {os.path.relpath(out, REPO)}")
    print(f"  源：{len(files)} 个引用本仓库的会话（跨项目目录）· 去重唯一节点 {len(objs)} · 对话 {rn} · 树节点 {len(nodes)}")
    mt.report(counts)
    print("  提醒：生成物勿手改；研究历程/动机日志 人工补；脱敏报告过目后再提交。", file=sys.stderr)

    # 建后自检：全量重建是唯一机制 → 刚建出的树结构性应为 0。红了说明 builder/源有真问题，别提交。
    import subprocess
    vargs = [sys.executable, os.path.join(HERE, "verify_tree.py"), "--person", args.person, "--tree", out]
    if args.src:
        vargs += ["--src", args.src]
    if args.manifest:
        vargs += ["--manifest", args.manifest]
    try:
        r = subprocess.run(vargs, capture_output=True, text=True)
        print("\n── 建后自检（verify_tree）──")
        print(r.stdout.strip())
        if r.returncode != 0:
            print("⚠️ 结构性问题未清——**别提交这棵树**，请按上面排查（陈旧不算，🔴 才算）。", file=sys.stderr)
    except Exception as e:
        print(f"（建后自检未跑：{e}）", file=sys.stderr)

if __name__ == "__main__":
    main()
