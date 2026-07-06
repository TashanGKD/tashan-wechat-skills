# -*- coding: utf-8 -*-
"""pack_conversation.py —— 把一条对话（**从根起**、含它所有续接/分支节点）打包成一份转录，
供"按需 compact → 跨框架/换账号续接"用。

一条"对话"在对话树里 = 一个根节点 + 它整棵子树（历次 compact 续接、分支都在里面）。本脚本：
  1. 按 --alias/--session 定位根节点；
  2. 收齐**从根起整棵子树**的所有节点，把各节点 段.md 里的对话轮次抽出来、**按时间排**；
  3. **滤掉**压缩摘要块（"This session is being continued…"，它是旧压缩的产物、会重复）、[Request interrupted]
     和工具结果折叠块（<details>⟨工具结果⟩</details>），**保留**对话正文 + 工具调用名（[工具:Name]）；
  4. 写成一个转录文件，打印路径 + 规模（token 估）。

这是"续接包"功能的**确定性打包步**。拿到转录后，由智能体（team-collab 的续接工作流）派子智能体、
用 compaction 模板把它 compact、再套"续接壳"→ 给用户即开即用的交接包。见 references/conversation-handoff.md。

用法：
  python3 pack_conversation.py --person Alice --alias 对话47
  python3 pack_conversation.py --person Alice --session 3def544e --out D:/x.txt
"""
import argparse, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
try:
    import _vector_env as ve
except Exception:
    ve = None

COMPACT_MARK = ("This session is being continued", "ran out of context", "Caveat: The messages below")


def turns_of(seg_md_path):
    """从一个节点的 段.md 抽轮次：[(ts, role, cleaned_text)]。清洗=删工具结果折叠块、保留工具调用名、滤压缩摘要/噪声。"""
    if not os.path.exists(seg_md_path):
        return []
    body = open(seg_md_path, encoding="utf-8", errors="ignore").read().split("\n---\n", 1)[-1]
    lines = body.splitlines(); out = []; i = 0
    while i < len(lines):
        m = re.match(r"### \[(.*?)\] (🧑|🤖) ", lines[i])
        if m:
            ts = m.group(1); role = "user" if m.group(2) == "🧑" else "assistant"
            c = []; j = i + 1
            while j < len(lines) and not lines[j].startswith("### "):
                c.append(lines[j]); j += 1
            raw = "\n".join(c)
            # 工具调用折叠块 → 保留名字；工具结果折叠块 → 整块删
            raw = re.sub(r"<details><summary>⟨工具调用 · ([^⟩]+)⟩</summary>.*?</details>",
                         r"[工具调用: \1]", raw, flags=re.S)
            raw = re.sub(r"<details>.*?</details>", " ", raw, flags=re.S)
            raw = re.sub(r"<[^>]+>", " ", raw)
            txt = re.sub(r"[ \t]+", " ", raw).strip()
            txt = re.sub(r"\n{3,}", "\n\n", txt)
            if txt and not any(k in txt[:220] for k in COMPACT_MARK) and not txt.startswith("[Request interrupted"):
                out.append((ts, role, txt))
            i = j
        else:
            i += 1
    return out


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="把一条对话（从根整条）打包成转录，供 compact 续接")
    ap.add_argument("--person")
    ap.add_argument("--repo")
    ap.add_argument("--tree", help="对话树目录（含 tree.json）；给了就直接用")
    ap.add_argument("--alias", help="根对话别名，如 对话47")
    ap.add_argument("--session", help="根会话 session-id（前缀即可），用于按 session 定位根")
    ap.add_argument("--out", help="输出转录路径（默认 <对话树>/../续接包_<alias>_原始转录.txt）")
    a = ap.parse_args()
    if a.tree:
        tree_dir = a.tree
    else:
        if not a.person:
            sys.exit("需 --person（或 --tree）")
        repo = ve.resolve_repo(a.person, a.repo) if ve else (a.repo or os.getcwd())
        tree_dir = os.path.join(repo, "团队协作记录", "智能体工作日志", a.person, "对话树")
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
    roots = [n for n in d["节点"] if not n.get("parent_dir")]

    # 定位根
    root = None
    if a.alias:
        root = next((n for n in roots if n.get("alias") == a.alias), None)
    elif a.session:
        # 用户报的 session-id（本地稳定编号）可能属于**任意节点**（根或某个分支/续接）→ 上溯到它的根
        hit = next((n for n in d["节点"] if any(s.startswith(a.session) for s in (n.get("sessions") or []))), None)
        cur = hit
        while cur is not None and cur.get("parent_dir"):
            cur = NODES.get(cur["parent_dir"])
        root = cur if (cur is not None and not cur.get("parent_dir")) else None
        if root is not None and hit is not root:
            print(f"  (session {a.session[:8]}… 属于分支节点「{hit.get('alias')}」→ 上溯到根「{root.get('alias')}」，从根整条打包)")
    if root is None:
        print("✗ 没定位到根对话。现有根：", file=sys.stderr)
        for n in sorted(roots, key=lambda x: x.get("alias", "")):
            print(f"   {n.get('alias')}  ({(n.get('t0') or '')[:10]})  {(n.get('摘要') or '')[:40]}", file=sys.stderr)
        sys.exit(1)

    # 从根收齐整棵子树
    def subtree(dir_):
        out = [dir_]
        for c in KIDS.get(dir_, []):
            out += subtree(c)
        return out
    dirs = subtree(root["dir"])

    # 收齐所有轮次、按时间排
    allturns = []
    for nd in dirs:
        for ts, role, txt in turns_of(os.path.join(tree_dir, nd, "段.md")):
            allturns.append((ts, role, txt))
    allturns.sort(key=lambda x: x[0])

    # 渲染转录
    lines = [f"# 对话「{root.get('alias')}」完整转录（从根整条，含所有续接/分支；已滤压缩摘要与工具输出）",
             f"# 根 session: {', '.join(root.get('sessions') or [])}",
             f"# 节点数 {len(dirs)} · 轮次 {len(allturns)} · 时间 {allturns[0][0] if allturns else '?'} → {allturns[-1][0] if allturns else '?'}\n"]
    for ts, role, txt in allturns:
        tag = "🧑 用户" if role == "user" else "🤖 助手"
        lines.append(f"### [{ts}] {tag}\n{txt}\n")
    doc = "\n".join(lines)

    out = a.out or os.path.join(os.path.dirname(tree_dir), f"续接包_{root.get('alias')}_原始转录.txt")
    open(out, "w", encoding="utf-8", newline="\n").write(doc)
    ntok = len(doc) // 3   # 中文偏保守估
    print(f"✓ 打包 → {out}")
    print(f"  从根「{root.get('alias')}」整条：{len(dirs)} 节点 · {len(allturns)} 轮 · {len(doc):,} 字符 ≈ {ntok:,} tokens")
    nu = sum(1 for _, r, _ in allturns if r == "user")
    print(f"  其中用户消息 {nu} 条")
    if ntok > 150000:
        print(f"  ⚠ 偏大（>{150000} tokens）：单个子智能体可能吃不下，续接工作流需分段/裁更狠——见 references/conversation-handoff.md")
    print(f"\n下一步（由智能体做）：派子智能体读这个转录、用 compaction 模板产出 9 段总结、套续接壳 → 交接包。")


if __name__ == "__main__":
    main()
