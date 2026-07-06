#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""query_memory.py —— 语义召回过去对话的记忆（对话树向量库检索）。

给一句自然语言问题，从 `记忆向量库/`（build_memory_index.py 建的 chromadb）里按语义找最相关的记忆块，
返回排序命中：每条带 **节点/时间/session · 真源指针(原始 .jsonl) · 段.md 与跳转锚 · 相邻上下文块** ——
命中后**务必顺真源/段.md 下钻读无损原文**（snippet 只是定位，不是答案；见 team-collab「读协议」第③步）。

**优先走常驻 daemon（秒回）**：若 memory_daemon.py 在跑就发给它、跳过冷启动；没开则冷查询(~15s)并顺手拉起，下次秒回。

用法（用装了 chromadb 的解释器——缺包时脚本会自动探测 python3/python/py 等候选并转过去运行，
见 _vector_env.py；**在仓库根目录下运行**或传 --repo）：
  python3 query_memory.py "四相图 可视化网页是哪个会话做的" --person Alice
  python3 query_memory.py "MinerU token 轮换" --person Alice --k 8 --context 2 --json 2>/dev/null
  python3 query_memory.py "wave pinning 推导" --person Alice --kind card --repo /path/to/your/repo
注意：解析 JSON 时用 `2>/dev/null`（别 `2>&1`），免得日志/遥测噪声混进 stdout 破坏 JSON。
"""
import argparse, json, os, re, socket, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _vector_env as ve
EMBED_MODEL = os.environ.get("TC_EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
COLLECTION  = os.environ.get("TC_MEM_COLLECTION", "worklog_memory")

def vec_dir_for(person, repo):
    return os.path.join(repo, "团队协作记录", "智能体工作日志", person, "记忆向量库")

# ───────────────────── 检索 + 格式化（daemon 与冷查询共用）─────────────────────
def _neighbor_context(col, hid, n):
    """同节点相邻 n 个 seg 块的文本，拼成一段更宽的上下文（命中块位置标出）。"""
    try:
        base, _, idx = hid.rpartition("::")   # "{dir}::seg::{i}" → base="{dir}::seg", idx="{i}"
        i = int(idx)
    except Exception:
        return ""
    want = [f"{base}::{j}" for j in range(i - n, i + n + 1) if j >= 0 and j != i]
    if not want:
        return ""
    try:
        g = col.get(ids=want, include=["documents"])
    except Exception:
        return ""
    by_id = dict(zip(g.get("ids", []), g.get("documents", [])))
    parts = []
    for j in range(i - n, i + n + 1):
        if j == i:
            parts.append("〖…命中块（见 snippet）…〗")
        else:
            d = by_id.get(f"{base}::{j}")
            if d:
                parts.append(re.sub(r"\s+", " ", d)[:400])
    return "  ⏐  ".join(parts)

def search_and_format(col, query, k, kind, person, context=0):
    where = {"kind": kind} if kind else None
    res = col.query(query_texts=[query], n_results=k, where=where,
                    include=["documents", "metadatas", "distances"])
    ids = (res.get("ids") or [[]])[0]
    docs, metas, dists = res["documents"][0], res["metadatas"][0], res["distances"][0]
    hits = []
    for hid, doc, m, dist in zip(ids, docs, metas, dists):
        src = [s for s in (m.get("source_files") or "").split(" ; ") if s]
        duan = os.path.join("团队协作记录", "智能体工作日志", person, "对话树",
                            m.get("node_dir", ""), "段.md").replace("\\", "/")
        h = {
            "id": hid, "score": round(1 - dist, 3),
            "kind": m.get("kind"), "alias": m.get("alias"),
            "time": f"{m.get('t0','')} → {m.get('t1','')}",
            "anchor": m.get("anchor"),
            "sessions": [s for s in (m.get("sessions") or "").split("; ") if s],
            "source_files": src,                 # 真源：原始 .jsonl（本机可读则下钻）
            "duan_md": duan, "摘要": m.get("摘要"),
            "snippet": re.sub(r"\s+", " ", doc)[:500],
        }
        if context > 0 and m.get("kind") == "seg":
            h["context"] = _neighbor_context(col, hid, context)
        hits.append(h)
    return hits

# ───────────────────── daemon 客户端 + 自动拉起 ─────────────────────
def daemon_query(vec_dir, payload, timeout=4):
    import memory_daemon as md
    pf = md.portfile(vec_dir)
    if not os.path.exists(pf):
        return None
    try:
        port = json.load(open(pf, encoding="utf-8"))["port"]
        s = socket.create_connection(("127.0.0.1", port), timeout=timeout)
        s.sendall((json.dumps(payload, ensure_ascii=False) + "\n").encode()); s.settimeout(timeout)
        buf = b""
        while b"\n" not in buf:
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
        s.close()
        return json.loads(buf.decode("utf-8").strip())
    except Exception:
        return None

def start_daemon_detached(person, repo):
    """把 daemon 以脱离进程后台拉起（当前查询仍走冷路，下次即秒回）。**加锁防惊群**：
    多个冷查询在 daemon 加载窗口(~10s)内并发时，只允许一个真正去拉起——否则会同时启十几个
    进程抢 CPU（踩过：16 个孤儿 python 把查询从 0.4s 拖到 5s）。"""
    import memory_daemon as md, subprocess, time
    vd = vec_dir_for(person, repo)
    if md.ping(md.port_for(vd)) or os.path.exists(md.portfile(vd)):
        return
    lock = os.path.join(vd, ".daemon.starting")
    try:
        if os.path.exists(lock) and (time.time() - os.path.getmtime(lock)) < 90:
            return                                 # 已有进程在启动 daemon，别再拉
    except Exception:
        pass
    try:
        open(lock, "w", encoding="utf-8").write(str(os.getpid()))
    except Exception:
        pass
    script = os.path.join(HERE, "memory_daemon.py")
    log = os.path.join(vd, ".daemon.log")
    kw = {"stdin": subprocess.DEVNULL, "stdout": open(log, "a", encoding="utf-8"),
          "stderr": subprocess.STDOUT, "close_fds": True}
    if os.name == "nt":
        kw["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    try:
        subprocess.Popen([sys.executable, script, "--person", person, "--repo", repo], **kw)
    except Exception:
        pass

# ───────────────────── 背景层（发散式检索协议·第①层）─────────────────────
def enrich_background(hits, tree_root):
    """给每条命中补「背景」层：顺 tree.json 的 parent_dir 链上溯到**根对话**，返回根的研究线摘要 + 从根到本节点的脉络。
    纯客户端后处理，daemon/冷路都适用（node_dir 从 duan_md 解析，不需 daemon 返回额外字段）。三层里现在补齐第①层
    （②局部上下文=--context 已有；③整段= duan_md 路径，调用方用 Read 读）。"""
    tj = os.path.join(tree_root, "tree.json")
    if not os.path.exists(tj):
        return hits
    try:
        nodes = json.load(open(tj, encoding="utf-8")).get("节点", [])
    except Exception:
        return hits
    d2n = {n.get("dir"): n for n in nodes}
    for h in hits:
        duan = h.get("duan_md", "")
        if "对话树/" not in duan:
            continue
        nd = duan.split("对话树/", 1)[1].rsplit("/段.md", 1)[0]
        cur, chain, root_node, guard = d2n.get(nd), [], None, 0
        while cur and guard < 50:
            chain.append(cur.get("alias", "")); root_node = cur
            p = cur.get("parent_dir"); cur = d2n.get(p) if p else None; guard += 1
        if root_node:
            h["背景"] = root_node.get("摘要") or root_node.get("auto_summary") or ""
            h["脉络"] = " → ".join(reversed(chain))
    return hits


# ───────────────────── 输出 ─────────────────────
def print_hits(query, hits, via):
    print(f"🔎 记忆召回：“{query}”  ·  top {len(hits)}  ·  {via}\n" + "=" * 72)
    for i, h in enumerate(hits, 1):
        print(f"\n#{i}  score={h['score']}  [{h['kind']}]  {h['alias']}  ·  {h['time']}")
        if h.get("背景"):                                    # 第①层：这条命中属于哪条研究线
            print(f"   背景: [{h.get('脉络','')}]  {h['背景']}")
        if h.get("摘要"):
            print(f"   摘要: {h['摘要']}")
        print(f"   命中: {h['snippet']}")
        if h.get("context"):                                 # 第②层：局部上下文
            print(f"   上下文: {h['context']}")
        print(f"   session: {', '.join(h['sessions'])}   锚点: {h['anchor']}")
        print(f"   段.md : {h['duan_md']}")                   # 第③层：整段（用 Read 读这个路径）
        print(f"   真源  : {'; '.join(h['source_files']) or '(无)'}")
    print("\n" + "=" * 72)
    # 第③层便捷：把要读整段的 段.md 路径去重列出，直接 Read
    uniq = list(dict.fromkeys(h["duan_md"] for h in hits))
    print("📖 读整段（三层里的第③层）——把下面 段.md 用 Read 工具打开（去重后完整对话，按锚点时间定位）：")
    for p in uniq:
        print(f"   {p}")
    print("\n发散式检索（本 skill 标准流程，别只查一次就收工）：")
    print("   ① 多角度/多措辞发散查（同一概念可能用完全不同措辞散落）；② 每条命中看『背景』定位它属于哪条研究线；")
    print("   ③ Read 整段 段.md 拿细节；④ 用命中里的新线索生成下一轮查询，滚雪球深挖，直到连续几轮挖不出新节点(loop-until-dry)。")

def main():
    ve.safe_console()   # 非 UTF-8 控制台(如 Windows 默认 GBK)也不因 emoji/中文 print 崩溃
    ap = argparse.ArgumentParser(description="语义召回对话树记忆")
    ap.add_argument("query")
    ap.add_argument("--person", required=True)
    ap.add_argument("--k", type=int, default=6)
    ap.add_argument("--kind", choices=["card", "seg"])
    ap.add_argument("--context", type=int, default=1, help="每条命中额外带同节点相邻 N 个对话块作上下文（默认1；0=只回命中块）")
    ap.add_argument("--repo", help="仓库根（默认从 cwd 上溯自动找；用全局脚本路径调用时建议 cd 到仓库或传此项）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-daemon", action="store_true", help="强制冷查询，不走/不拉起 daemon")
    args = ap.parse_args()

    repo = ve.resolve_repo(args.person, args.repo)
    vec_dir = vec_dir_for(args.person, repo)
    tree_root = os.path.join(repo, "团队协作记录", "智能体工作日志", args.person, "对话树")   # 供背景层上溯
    if not os.path.exists(vec_dir):
        sys.exit(f"✗ 无记忆向量库：{vec_dir}\n  · 若这不是你的仓库路径：请 cd 到仓库根再运行，或传 --repo <仓库根>（当前用 repo={repo}）。\n  · 若确实没建过：python build_memory_index.py --person {args.person}。")

    # ① 优先走 daemon（秒回）
    if not args.no_daemon:
        r = daemon_query(vec_dir, {"cmd": "query", "query": args.query, "k": args.k,
                                   "kind": args.kind, "context": args.context})
        if r and "hits" in r:
            enrich_background(r["hits"], tree_root)   # 补第①层：背景/脉络（客户端后处理）
            if args.json:
                print(json.dumps({"query": args.query, "via": "daemon", "hits": r["hits"]}, ensure_ascii=False, indent=2))
            else:
                print_hits(args.query, r["hits"], "via daemon ⚡")
            return

    # ② 回退冷查询（并顺手把 daemon 拉起来，下次即秒回）
    ve.ensure_vector_stack(os.path.abspath(__file__))
    import chromadb
    from chromadb.utils import embedding_functions
    try:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        device = "cpu"
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL, device=device)
    ve.clear_orphan_hnsw(vec_dir)   # 清孤儿 pickle → 冷查询据 sqlite 重建索引，避免 'Cannot open header file'
    client = chromadb.PersistentClient(path=vec_dir)
    try:
        col = client.get_collection(COLLECTION, embedding_function=ef)
    except Exception:
        sys.exit(f"✗ collection '{COLLECTION}' 不存在——先建索引：python3 build_memory_index.py --person {args.person}。")
    hits = search_and_format(col, args.query, args.k, args.kind, args.person, args.context)
    enrich_background(hits, tree_root)   # 补第①层：背景/脉络
    if not args.no_daemon:
        start_daemon_detached(args.person, repo)
    if args.json:
        print(json.dumps({"query": args.query, "via": "cold", "hits": hits}, ensure_ascii=False, indent=2))
    else:
        print_hits(args.query, hits, "via cold (daemon 未运行，已拉起，下次秒回)")

if __name__ == "__main__":
    main()
