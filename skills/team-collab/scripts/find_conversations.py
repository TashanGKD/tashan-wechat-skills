# -*- coding: utf-8 -*-
"""find_conversations.py —— 「回顾项目工作，找到 xx 相关的对话」的确定性数据步。

给一句主题/关键词，**主动回顾**过去所有对话，产出一张表格（默认直接打 markdown）：
  | 对话编号(session-id) | 该对话总结 | 最近 3 个完整交互记录 |
供用户一眼认出想继续哪条 → 把「对话编号(session-id)」报给智能体即可「生成续接包」(pack_conversation.py)。

取数两路、合并排序：
  1. **语义召回**：调 query_memory.py --json（对话树向量库），把命中按 tree.json 的 parent_dir 链上溯到**根对话**，
     根的最高命中分即该对话的相关度；
  2. **关键词兜底**：扫 tree.json 每个根的 摘要/auto_summary + 段.md 开头，子串命中也算相关（语义库没建/召回空时仍可用）。
对每个相关的根对话：session-id = 根 sessions[0]（稳定本地编号）· 总结 = 根 摘要/auto_summary ·
最近 3 个完整交互 = 从整棵子树所有轮次按时间排、取最后 3 组 user→assistant 往来（全文，单条超 --chars 才截）。

用法（在仓库根运行或传 --repo/--tree；用装了 chromadb 的解释器语义才生效，否则自动退关键词兜底）：
  python find_conversations.py "可视化 网页 布局" --person Alice
  python find_conversations.py "接口 限流 重试" --person Alice --top 8 --k 20 --chars 400
  python find_conversations.py "公式 推导 脚本" --tree "/path/to/对话树" --json 2>/dev/null
见 references/conversation-handoff.md（第二入口：语义回顾出表格）。
"""
import argparse, json, os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
try:
    import _vector_env as ve
except Exception:
    ve = None
from pack_conversation import turns_of


def _tree_dir(a):
    if a.tree:
        return a.tree
    if not a.person:
        sys.exit("需 --person（或 --tree）")
    repo = ve.resolve_repo(a.person, a.repo) if ve else (a.repo or os.getcwd())
    return os.path.join(repo, "团队协作记录", "智能体工作日志", a.person, "对话树")


def _load_tree(tree_dir):
    tj = os.path.join(tree_dir, "tree.json")
    if not os.path.exists(tj):
        sys.exit(f"✗ 没有 tree.json：{tj}")
    d = json.load(open(tj, encoding="utf-8"))
    NODES = {n["dir"]: n for n in d["节点"]}
    KIDS = {}
    for n in d["节点"]:
        p = n.get("parent_dir")
        if p:
            KIDS.setdefault(p, []).append(n["dir"])
    return d, NODES, KIDS


def _root_of(node, NODES):
    cur = node; guard = 0
    while cur is not None and cur.get("parent_dir") and guard < 50:
        cur = NODES.get(cur["parent_dir"]); guard += 1
    return cur


def _subtree_dirs(root_dir, KIDS):
    out = [root_dir]
    for c in KIDS.get(root_dir, []):
        out += _subtree_dirs(c, KIDS)
    return out


def semantic_hits(query, a, k):
    """调 query_memory.py --json，返回命中列表（失败/无库则 []）。"""
    cmd = [sys.executable, os.path.join(HERE, "query_memory.py"), query, "--k", str(k), "--json"]
    if a.person:
        cmd += ["--person", a.person]
    if a.repo:
        cmd += ["--repo", a.repo]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=90)
        # query_memory 把 JSON 打到 stdout；日志/telemetry 可能混入 → 从第一个 '{' 起解析
        s = p.stdout
        i = s.find("{")
        if i < 0:
            return []
        return (json.loads(s[i:]) or {}).get("hits", [])
    except Exception:
        return []


def keyword_roots(query, d, NODES, KIDS, tree_dir):
    """关键词兜底：扫每个根的 摘要/auto_summary + 段.md 开头，返回 {root_dir: score}。"""
    terms = [t for t in re.split(r"[\s，,、;；]+", query.strip()) if t]
    if not terms:
        return {}
    roots = [n for n in d["节点"] if not n.get("parent_dir")]
    hits = {}
    for r in roots:
        blob = (r.get("摘要") or "") + " " + (r.get("auto_summary") or "")
        # 摘要外再补 段.md 开头，增加召回面
        seg = os.path.join(tree_dir, r["dir"], "段.md")
        if os.path.exists(seg):
            try:
                blob += " " + open(seg, encoding="utf-8", errors="ignore").read(4000)
            except Exception:
                pass
        low = blob.lower()
        c = sum(1 for t in terms if t.lower() in low)
        if c:
            hits[r["dir"]] = 0.3 + 0.1 * c   # 关键词分低于语义分基线，语义命中优先
    return hits


# 系统/后台注入的噪声轮次（对"认出这条对话"没帮助）——从"最近交互"里滤掉
_NOISE_RE = re.compile(
    r"(^\s*\w{6,12}\s+(toolu_[A-Za-z0-9]+|Monitor event))"     # 后台 shell 回执/Monitor 事件：<id> toolu_xxx… / <id> Monitor event…
    r"|No completion record was found for this background"
    r"|^\s*\[?(Request interrupted|external_agent_tool_call)"
    r"|API Error|Failed to authenticate|socket connection was closed"
    r"|Failed to send telemetry|syntax error near unexpected token")


def _is_noise(role, txt):
    t = (txt or "").strip()
    if not t:
        return True
    return bool(_NOISE_RE.search(t[:160]))


def last_rounds(subtree_dirs, tree_dir, n_rounds, chars):
    """从整棵子树取所有轮次、按时间排、滤噪声，配成 user→assistant 组，返回最后 n_rounds 组有意义往来。"""
    allt = []
    for nd in subtree_dirs:
        allt += turns_of(os.path.join(tree_dir, nd, "段.md"))
    allt.sort(key=lambda x: x[0])
    allt = [(ts, role, txt) for ts, role, txt in allt if not _is_noise(role, txt)]
    rounds = []; i = 0
    while i < len(allt):
        ts, role, txt = allt[i]
        if role == "user":
            u = txt; ans = ""; j = i + 1
            while j < len(allt) and allt[j][1] == "assistant":
                ans += ("\n" if ans else "") + allt[j][2]; j += 1
            rounds.append((ts, u, ans)); i = j
        else:
            i += 1
    return rounds[-n_rounds:]


def _cap(s, n):
    s = re.sub(r"\s+", " ", (s or "")).strip()
    return s if len(s) <= n else s[:n] + " …"


def main():
    if ve:
        ve.safe_console()
    ap = argparse.ArgumentParser(description="语义回顾：找到与主题相关的所有对话，出表格")
    ap.add_argument("query")
    ap.add_argument("--person")
    ap.add_argument("--repo")
    ap.add_argument("--tree", help="对话树目录（含 tree.json）")
    ap.add_argument("--k", type=int, default=16, help="语义召回条数（会聚合到更少的根对话）")
    ap.add_argument("--top", type=int, default=6, help="表格里最多列几个相关对话")
    ap.add_argument("--rounds", type=int, default=3, help="每个对话展示最近几组完整交互")
    ap.add_argument("--chars", type=int, default=500, help="每条消息全文超过多少字才截断")
    ap.add_argument("--json", action="store_true", help="输出结构化 JSON（供智能体自定义排版）")
    a = ap.parse_args()

    tree_dir = _tree_dir(a)
    d, NODES, KIDS = _load_tree(tree_dir)

    # ① 语义召回 → 上溯到根，取根的最高分
    root_score, root_why = {}, {}
    for h in semantic_hits(a.query, a, a.k):
        duan = h.get("duan_md", "")
        if "对话树/" not in duan:
            continue
        nd = duan.split("对话树/", 1)[1].rsplit("/段.md", 1)[0]
        root = _root_of(NODES.get(nd), NODES)
        if not root:
            continue
        rd = root["dir"]; sc = float(h.get("score") or 0)
        if sc > root_score.get(rd, -1):
            root_score[rd] = sc
        root_why.setdefault(rd, h.get("snippet", "")[:120])

    # ② 关键词兜底（语义没命中的根也纳入，分数更低）
    for rd, sc in keyword_roots(a.query, d, NODES, KIDS, tree_dir).items():
        if rd not in root_score:
            root_score[rd] = sc

    ranked = sorted(root_score.items(), key=lambda kv: kv[1], reverse=True)[:a.top]
    if not ranked:
        print(f"（没找到与「{a.query}」相关的对话。可换措辞多试几次，或先建/更新语义库：build_memory_index.py。）")
        return

    rows = []
    for rd, sc in ranked:
        root = NODES[rd]
        sid = (root.get("sessions") or ["(无session)"])[0]
        summary = root.get("摘要") or root.get("auto_summary") or "(无总结)"
        rounds = last_rounds(_subtree_dirs(rd, KIDS), tree_dir, a.rounds, a.chars)
        rows.append({
            "对话编号": sid, "alias": root.get("alias"), "相关度": round(sc, 3),
            "总结": summary,
            "最近交互": [{"时间": ts, "user": u, "assistant": ans} for ts, u, ans in rounds],
        })

    if a.json:
        print(json.dumps({"query": a.query, "对话数": len(rows), "rows": rows}, ensure_ascii=False, indent=2))
        return

    # markdown 表格
    print(f"## 与「{a.query}」相关的对话（共 {len(rows)} 条，按相关度排）\n")
    print("| # | 对话编号 (session-id) | 该对话总结 | 最近 3 个完整交互记录 |")
    print("|---|---|---|---|")
    for i, r in enumerate(rows, 1):
        cell = []
        for k, it in enumerate(r["最近交互"], 1):
            cell.append(f"**{k}. [{it['时间']}]** 🧑 {_cap(it['user'], a.chars)}<br>🤖 {_cap(it['assistant'], a.chars)}")
        inter = "<br><br>".join(cell) if cell else "（无）"
        summ = _cap(r["总结"], 300)
        print(f"| {i} | `{r['对话编号']}`<br>〔{r['alias']}〕 | {summ} | {inter} |")
    print(f"\n> 想继续哪条 → 把它的 **对话编号 (session-id)** 报给我，我就派子智能体从根整条 compact、套续接壳，"
          f"给你一份即开即用的**续接包**（换框架/换账号/新会话都能粘贴续上）。")


if __name__ == "__main__":
    main()
