#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对话树完整性校验 gate —— 证明"把节点重新拼起来 = 原始会话，逐条不丢、不错配"。

全量重建是记忆层的唯一机制；本 gate 是它的验收闸。两类结论**严格分开**：

  🔴 结构性问题（树自身不自洽——必须重建/修，退出码 1，可当 commit 硬门）：
     · 重复：同一 uuid 落在多个节点
     · 幽灵：节点 uuid 不在源记录里
     · 断裂：节点内 uuid 不是连续 parentUuid 链
     · 接缝：分支节点首条的 parent ≠ 父节点末条
     · 根错：标为根却仍有在源里的父
     · 重构不符：根→叶拼接 ≠ 真实链（**只比树覆盖到的记录**，不受陈旧影响）
     · 段.md 记录数 ≠ uuid 数

  🟡 陈旧（源里有、树里没有的新会话/增长——只是"该重建了"，不是 bug，退出码 0；
         `--strict` 时才计为失败）：
     · N 个会话未纳入 / M 条用户消息未进树

这样 live 会话期间"陈旧"不会误拦提交；只有真错配才 fail-closed。

用法：
  python3 verify_tree.py --person Boyuan            # 校验该人对话树
  python3 verify_tree.py --person Boyuan --strict   # 陈旧也算失败（要求树完全最新）
  python3 verify_tree.py --tree <目录> --src <项目目录>   # 自测/指定源
"""
import argparse, json, os, re, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_session_tree as B   # 复用 load_records / discover / text_of / mt


def is_user_text(o):
    m = o.get("message", {})
    if not isinstance(m, dict) or m.get("role") != "user":
        return False
    return bool(B.mt._strip_noise(B.text_of(o)).strip())


def load_source(args):
    if args.src:
        files = sorted(B.glob.glob(os.path.join(args.src, "*.jsonl")))
    else:
        files = B.discover_session_files()
    if args.manifest:
        keep = {ln.strip() for ln in open(args.manifest, encoding="utf-8")
                if ln.strip() and not ln.startswith("#")}
        files = [f for f in files if os.path.basename(f)[:-6] in keep]
    return B.load_records(files)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--person", default="Boyuan")
    ap.add_argument("--tree", help="对话树目录（默认按 --person 推断）")
    ap.add_argument("--src", help="只从这个项目目录取源（自测用；默认跨目录 discover）")
    ap.add_argument("--manifest", help="与建树一致的会话清单（建树用了就传同一个）")
    ap.add_argument("--strict", action="store_true", help="陈旧也算失败（退出码 1）")
    args = ap.parse_args()

    tree = args.tree or os.path.join(B.REPO, "团队协作记录", "智能体工作日志", args.person, "对话树")
    tj = os.path.join(tree, "tree.json")
    if not os.path.exists(tj):
        sys.exit(f"✗ 找不到 {tj}（先建树）")
    nodes = json.load(open(tj, encoding="utf-8"))["节点"]
    if not nodes or "uuids" not in nodes[0]:
        sys.exit("✗ tree.json 无 uuids 字段：请用当前版本 build_session_tree.py 重建后再校验")

    objs, sess = load_source(args)
    allu = set(objs)
    by_dir = {n["dir"]: n for n in nodes}
    struct = []   # 🔴 结构性
    stale = []    # 🟡 陈旧

    # ── 分区：节点 uuid 两两不相交（重复=🔴）、不含幽灵（=🔴） ──
    seen = {}
    dup = []
    for n in nodes:
        for u in n["uuids"]:
            if u in seen:
                dup.append((u[:8], seen[u], n["alias"]))
            else:
                seen[u] = n["alias"]
    if dup:
        struct.append(f"重复：{len(dup)} 个 uuid 落在多个节点，如 {dup[:3]}")
    placed = set(seen)
    ghost = placed - allu
    if ghost:
        struct.append(f"幽灵：{len(ghost)} 个节点 uuid 不在源记录里，如 {[g[:8] for g in list(ghost)[:3]]}")

    # ── 陈旧（🟡）：源里有、树里没有的会话/用户消息 = 该重建，不是错 ──
    pruned = allu - placed
    tree_sessions = set().union(*[set(n.get("sessions", [])) for n in nodes]) if nodes else set()
    src_sessions = set().union(*sess.values()) if sess else set()
    stale_sessions = src_sessions - tree_sessions
    stale_user = [u for u in pruned if is_user_text(objs[u])]
    if stale_sessions or stale_user:
        stale.append(f"{len(stale_sessions)} 个会话未纳入树、{len(stale_user)} 条用户消息未进树"
                     f"（建议重建：build_session_tree.py --person {args.person}）")

    # ── 连续性 + 接缝 + 根（=🔴，树自身是否自洽，与陈旧无关）──
    for n in nodes:
        us = n["uuids"]
        if not us:
            struct.append(f"空节点：{n['alias']} uuids 为空"); continue
        for i in range(1, len(us)):
            if objs.get(us[i], {}).get("parentUuid") != us[i - 1]:
                struct.append(f"断裂：节点 {n['alias']} 内第 {i} 条不接前一条"); break
        pu = objs.get(us[0], {}).get("parentUuid")
        pd = n.get("parent_dir")
        if pd and pd in by_dir:
            if pu != by_dir[pd]["uuids"][-1]:
                struct.append(f"接缝：节点 {n['alias']} 首条 parent ≠ 父节点 {pd} 末条（分支增量错位）")
        else:
            if pu in objs:
                struct.append(f"根错：节点 {n['alias']} 标为根但其首条 parent 仍在源里（漏祖先段）")

    # ── 根→叶可无损重构（=🔴）：只比**树覆盖到的记录**，陈旧新增不算错 ──
    parent_dirs = {n.get("parent_dir") for n in nodes}
    leaves = [n for n in nodes if n["dir"] not in parent_dirs]
    for n in leaves:
        path, cur, guard = [], n, 0
        while cur is not None and guard < 10000:
            path.append(cur); guard += 1
            cur = by_dir.get(cur.get("parent_dir")) if cur.get("parent_dir") else None
        chain = []
        for nd in reversed(path):
            chain += nd["uuids"]
        real, u, guard = [], n["uuids"][-1], 0
        while u in objs and guard < 100000:
            real.append(u); u = objs[u].get("parentUuid"); guard += 1
        real.reverse()
        real_in_tree = [u for u in real if u in placed]   # 去掉陈旧新增，只比树里有的
        if chain != real_in_tree:
            struct.append(f"重构不符：叶 {n['alias']} 根→叶拼接({len(chain)}) ≠ 树内真实链({len(real_in_tree)})")

    # ── 段.md 记录数与 uuid 数一致（=🔴）──
    for n in nodes:
        p = os.path.join(tree, n["dir"], "段.md")
        if not os.path.exists(p):
            struct.append(f"缺文件：{n['alias']} 无 段.md"); continue
        m = re.search(r"节点段:\s*(\d+)\s*条记录", open(p, encoding="utf-8").read())
        if m and int(m.group(1)) != len(n["uuids"]):
            struct.append(f"段.md：{n['alias']} 记录数 {m.group(1)} ≠ uuid 数 {len(n['uuids'])}")

    # ── 报告 ──
    print(f"源记录(去重后) {len(allu)} · 入树 {len(placed)} · 节点 {len(nodes)} · 叶 {len(leaves)}")
    if struct:
        print(f"\n🔴 结构性问题 {len(struct)}（树自身不自洽，必须重建/修）：")
        for e in struct:
            print("   -", e)
    if stale:
        print(f"\n🟡 陈旧 {len(stale)}（不是错，重建即纳入）：")
        for e in stale:
            print("   -", e)
    if not struct and not stale:
        print("✓ 全过：树自洽且与源完全一致——节点不重叠、每段真实连续链、接缝精确、"
              "根→叶可无损重构、段.md 记录数一致、无未纳入会话。")
    elif not struct:
        print("\n✅ 结构性：全过（树自洽）。" + ("（--strict：陈旧计为失败）" if args.strict else "（陈旧仅提醒，不算失败）"))

    rc = 1 if struct or (args.strict and stale) else 0
    return rc


if __name__ == "__main__":
    sys.exit(main())
