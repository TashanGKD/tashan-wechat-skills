#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_memory_index.py —— 把对话树(工作日志)嵌入向量库，供 AI 语义召回过去对话的记忆。

它读 `团队协作记录/智能体工作日志/<person>/对话树/` 的每个节点（tree.json + 段.md + 研究历程/动机），
切成「记忆块」→ 用 bge-m3 向量化 → 存进 chromadb（PersistentClient）。每块元数据都带该节点的
**真源指针 source_files**（原始 .jsonl 绝对路径）与跳转锚（`### [时间]`），所以语义命中后能直接下钻回真源。

两类块（对应默认「节点记忆卡 + 段.md 分块 混合」）：
  · kind=card：节点的 研究历程(摘要+主线/转向/踩坑+任务目录)+动机 —— 人写的精炼记忆，高信号。
  · kind=seg ：段.md 的对话原文（已脱敏），按轮次拼成 ~1600 字块；用户轮全留、agent 轮截断但**保留所有
               工具调用里的文件名/命令**（如 Write phase_explorer.html），丢掉臃肿的工具结果。

存放：`团队协作记录/智能体工作日志/<person>/记忆向量库/`（**在 对话树/ 之外**——因为 build_session_tree
重建时会 rmtree 掉 对话树/，放里面会被一起清掉）。

默认**增量 upsert**：按块内容 hash 跳过未变的块、删掉已消失的块；`--rebuild` 清空整个 collection 重嵌。

用法（要用装了 chromadb+sentence-transformers 的解释器；脚本会在当前解释器缺包时自动探测
python3/python/py 等候选并转过去运行，见 _vector_env.py）：
  python3 build_memory_index.py --person Alice
  python3 build_memory_index.py --person Alice --rebuild
"""
import argparse, hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _vector_env as ve

# 默认用轻量多语种模型：~470MB，冷加载快、常见消费级 GPU 显存也够，检索质量对"对话记忆召回"够用。
# （更大的模型如 BAAI/bge-m3 质量更高但显存需求也高得多、在小显存 GPU 上可能 OOM、冷加载慢很多——
#  更适合"离线批量建库不追求秒回"的场景。要换可设 TC_EMBED_MODEL=BAAI/bge-m3，并视情况调小 --batch。）
EMBED_MODEL = os.environ.get("TC_EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
COLLECTION  = os.environ.get("TC_MEM_COLLECTION", "worklog_memory")

# ───────────────────── 解析对话树节点 → 记忆块 ─────────────────────
PLACEHOLDER_RE = re.compile(r"(?m)^\s*(?:[-*] )?⚠️ ?待补\s*$|摘要[:：]\s*⚠️待补")
_TOOL_USE = re.compile(r"<details><summary>⟨工具调用 · (.*?)⟩</summary>\s*```(?:json)?\s*(.*?)```\s*</details>", re.S)
_TOOL_RES = re.compile(r"<details><summary>⟨工具结果.*?</details>", re.S)
_HDR = re.compile(r"^###\s*\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]\s*(🧑|🤖)\s*(.*)$")

def _compact(s, n=160):
    return re.sub(r"\s+", " ", s or "").strip()[:n]

def _turn_text(raw, role):
    """一轮的可检索文本：保留全部工具调用里的文件名/命令；agent 长 prose 截断；丢工具结果。"""
    tools = [f"[工具:{m.group(1)} {_compact(m.group(2), 140)}]" for m in _TOOL_USE.finditer(raw)]
    prose = _TOOL_USE.sub(" ", raw)
    prose = _TOOL_RES.sub(" ", prose)
    prose = re.sub(r"<details>.*?</details>", " ", prose, flags=re.S)
    prose = re.sub(r"```[a-zA-Z]*", " ", prose)
    prose = re.sub(r"\s+", " ", prose).strip()
    if role == "agent":
        prose = prose[:500]           # agent 冗长正文只留开头（结论/开场），关键文件名靠 tools 保住
    return " ".join(p for p in ([prose] + tools) if p).strip()

def parse_turns(duan_md):
    body = duan_md.split("\n---\n", 1)
    body = body[1] if len(body) > 1 else duan_md
    turns, cur = [], None
    for line in body.split("\n"):
        m = _HDR.match(line.strip())
        if m:
            if cur:
                turns.append(cur)
            cur = {"ts": m.group(1), "role": "user" if m.group(2) == "🧑" else "agent", "buf": []}
        elif cur is not None:
            cur["buf"].append(line)
    if cur:
        turns.append(cur)
    out = []
    for t in turns:
        txt = _turn_text("\n".join(t["buf"]), t["role"])
        if txt:
            out.append((t["ts"], t["role"], txt))
    return out

def chunk_turns(turns, size=1600):
    chunks, cur, curlen, anchor = [], [], 0, None
    for ts, role, txt in turns:
        piece = f"[{ts}] {'🧑' if role=='user' else '🤖'} {txt}"
        if anchor is None:
            anchor = ts
        if curlen + len(piece) > size and cur:
            chunks.append((anchor, "\n".join(cur)))
            cur, curlen, anchor = [], 0, ts
        cur.append(piece)
        curlen += len(piece)
    if cur:
        chunks.append((anchor, "\n".join(cur)))
    return chunks

def build_card(rh, mj):
    """节点记忆卡 = 研究历程(摘要+正文)+动机，去掉脚手架/占位。未填(待补/空桥接)则返回 None。"""
    if not rh or PLACEHOLDER_RE.search(rh) or "空续接/工具桥接" in rh:
        return None
    keep = []
    for md in (rh, mj):
        for ln in (md or "").split("\n"):
            s = ln.strip()
            if not s or s.startswith("# "):
                continue
            if s.startswith(">") and "摘要" not in s:   # 丢引导注释、留「摘要」
                continue
            keep.append(re.sub(r"^[>#*\-\s]+", "", s))
    card = re.sub(r"\s+", " ", " ".join(keep)).strip()
    return card or None

def read(p):
    try:
        return open(p, encoding="utf-8").read()
    except OSError:
        return ""

def gather_blocks(tree_root, person):
    """遍历 tree.json 节点 → [(id, document, metadata)]。"""
    tj = json.load(open(os.path.join(tree_root, "tree.json"), encoding="utf-8"))
    blocks = []
    n_card = n_seg = 0
    for node in tj["节点"]:
        d = os.path.join(tree_root, node["dir"].replace("/", os.sep))
        meta_base = {
            "person": person,
            "alias": node.get("alias", ""),
            "node_dir": node.get("dir", ""),
            "sessions": "; ".join(node.get("sessions", [])),
            "source_files": " ; ".join(node.get("source_files", [])),
            "t0": node.get("t0", ""), "t1": node.get("t1", ""),
            "摘要": node.get("摘要", ""),
        }
        card = build_card(read(os.path.join(d, "研究历程.md")), read(os.path.join(d, "动机日志.md")))
        if card:
            doc = f"[记忆卡 · {meta_base['alias']}] {card}"
            blocks.append((f"{node['dir']}::card", doc, {**meta_base, "kind": "card", "anchor": node.get("t0", "")}))
            n_card += 1
        for i, (anchor, text) in enumerate(chunk_turns(parse_turns(read(os.path.join(d, "段.md"))))):
            blocks.append((f"{node['dir']}::seg::{i}", text, {**meta_base, "kind": "seg", "anchor": anchor}))
            n_seg += 1
    return blocks, n_card, n_seg

# ───────────────────── 主流程：增量 upsert 进 chromadb ─────────────────────
def main():
    ve.safe_console()   # 非 UTF-8 控制台(如 Windows 默认 GBK)也不因 emoji/中文 print 崩溃
    ap = argparse.ArgumentParser(description="对话树 → 语义记忆向量库（bge-m3 + chromadb）")
    ap.add_argument("--person", required=True)
    ap.add_argument("--rebuild", action="store_true", help="清空 collection 全量重嵌（否则按内容 hash 增量 upsert）")
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--repo", help="仓库根（默认从 cwd 上溯自动找；或显式传入）")
    args = ap.parse_args()
    if not re.match(r"^[\w一-鿿\-]+$", args.person):
        sys.exit(f"✗ --person 非法：{args.person!r}")
    repo = ve.resolve_repo(args.person, args.repo)

    ve.ensure_vector_stack(os.path.abspath(__file__))
    import chromadb
    from chromadb.utils import embedding_functions

    tree_root = os.path.join(repo, "团队协作记录", "智能体工作日志", args.person, "对话树")
    if not os.path.exists(os.path.join(tree_root, "tree.json")):
        sys.exit(f"✗ 找不到对话树 tree.json：{tree_root}\n  · 若这不是你的仓库：cd 到仓库根再运行，或传 --repo（当前 repo={repo}）。\n  · 若确实没建过：build_session_tree.py --person {args.person}。")
    vec_dir = os.path.join(repo, "团队协作记录", "智能体工作日志", args.person, "记忆向量库")
    os.makedirs(vec_dir, exist_ok=True)

    print(f"· 解析对话树：{os.path.relpath(tree_root, repo)}")
    blocks, n_card, n_seg = gather_blocks(tree_root, args.person)
    print(f"· 记忆块：{len(blocks)}（记忆卡 {n_card} · 段块 {n_seg}）→ 嵌入模型 {EMBED_MODEL}")

    try:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        device = "cpu"
    print(f"· 嵌入设备：{device}（chromadb 的 ST 嵌入函数默认走 CPU，这里显式指定）", flush=True)
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL, device=device)
    ve.clear_orphan_hnsw(vec_dir)   # **开库前**清孤儿 pickle：否则增量 upsert 加向量到 hnsw 时会撞 'Cannot open header file'
    client = chromadb.PersistentClient(path=vec_dir)
    if args.rebuild:
        try:
            client.delete_collection(COLLECTION)
        except Exception:
            pass
    col = client.get_or_create_collection(COLLECTION, embedding_function=ef, metadata={"hnsw:space": "cosine"})

    # 每块算内容 hash 存进 metadata；增量时据此跳过未变、删掉消失的。
    want = {}
    for _id, doc, meta in blocks:
        meta = {**meta, "hash": hashlib.sha1(doc.encode("utf-8")).hexdigest()[:16]}
        want[_id] = (doc, meta)

    existing = col.get(include=["metadatas"]) if col.count() else {"ids": [], "metadatas": []}
    old_hash = {i: (m or {}).get("hash") for i, m in zip(existing["ids"], existing["metadatas"])}
    to_up = [i for i in want if old_hash.get(i) != want[i][1]["hash"]]
    to_del = [i for i in old_hash if i not in want]
    if to_del:
        col.delete(ids=to_del)
    print(f"· 增量：需 upsert {len(to_up)} 块，删除 {len(to_del)} 块（库内已有 {len(old_hash)}）"
          if not args.rebuild else f"· 全量重嵌 {len(to_up)} 块")

    for s in range(0, len(to_up), args.batch):
        batch = to_up[s:s + args.batch]
        col.upsert(ids=batch,
                   documents=[want[i][0] for i in batch],
                   metadatas=[want[i][1] for i in batch])
        print(f"  嵌入 {min(s + len(batch), len(to_up))}/{len(to_up)} …", flush=True)

    ve.clear_orphan_hnsw(vec_dir)   # 清孤儿 pickle（缺 .bin），令建后"直接查询"能据 sqlite 重建索引、可查
    print(f"✓ 记忆向量库就绪：{os.path.relpath(vec_dir, repo)}  ·  collection '{COLLECTION}' 共 {col.count()} 块")
    _q_hint = "py -3.12" if os.name == "nt" else "python3"   # 跨平台：mac/Linux 无 Windows 的 py 启动器，照抄会 command not found
    print(f"  检索：{_q_hint} {os.path.join('.claude','skills','team-collab','scripts','query_memory.py')} \"<问题>\" --person {args.person}")

if __name__ == "__main__":
    main()
