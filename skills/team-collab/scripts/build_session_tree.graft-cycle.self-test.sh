#!/usr/bin/env bash
# build_session_tree.py · apply_grafts 自测 —— 目标 bug：接枝把锚点接到**自己子树内** → parentUuid 成环
# → 环组件从 roots 不可达 → has_txt DFS 跳过整块 → 用户对话内容被静默吞掉。
# （实测 softmatter：接枝把 0 个源环变成 480 环内记录，828 条用户文本消息未进树、占全部 16%。根因：块2 的
#  own=_subtree 快照在循环内 mutate 后陈旧、块1 无任何环护栏。）
# 断言：apply_grafts 后 (a) 无 parentUuid 环 (b) 全部用户文本记录仍从某个根可达 (c) 正常反向续接仍被接上（护栏不误伤）。
# 若有人删掉 _would_cycle 护栏，场景1 会重新成环、A1/B1 变不可达 → 本测 FAIL。
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
python3 - "$HERE" <<'PY'
import sys, os
sys.path.insert(0, sys.argv[1])
import build_session_tree as B
from collections import defaultdict

fail = 0
def pas(m): print("PASS ", m)
def bad(m):
    global fail; print("FAIL ", m); fail = 1

def cycles(objs):
    color, incyc = {}, set()
    for s in objs:
        if s in color: continue
        path, onp, u = [], set(), s
        while u in objs and u not in color:
            color[u] = 0; path.append(u); onp.add(u)
            u = objs[u].get("parentUuid")
            if u in onp:
                for x in path[path.index(u):]: incyc.add(x)
                break
        for x in path: color[x] = 1
    return incyc

def reachable_from_roots(objs):
    ch, roots = defaultdict(list), []
    for u, o in objs.items():
        p = o.get("parentUuid")
        (ch[p].append(u) if (p and p in objs) else roots.append(u))
    seen, st = set(), list(roots)
    while st:
        x = st.pop()
        if x in seen: continue
        seen.add(x); st.extend(ch.get(x, ()))
    return seen

def um(t): return {"message": {"role": "user", "content": [{"type": "text", "text": t}]}}
def am(t): return {"message": {"role": "assistant", "content": [{"type": "text", "text": t}]}}

# ── 场景1：跨源互相续接（块1）——无护栏必成环，用户文本 A1/B1 会被吞 ──────────────
o1 = {
 "A0": {**am(""), "parentUuid": None, "timestamp": "01", "_session_id": "sA", "_continues_external": {"ref": "sB"}},
 "A1": {**um("A1 真实用户消息"), "parentUuid": "A0", "timestamp": "02", "_session_id": "sA"},
 "B0": {**am(""), "parentUuid": None, "timestamp": "03", "_session_id": "sB", "_continues_external": {"ref": "sA"}},
 "B1": {**um("B1 真实用户消息"), "parentUuid": "B0", "timestamp": "04", "_session_id": "sB"},
}
s1 = {"A0": {"sA"}, "A1": {"sA"}, "B0": {"sB"}, "B1": {"sB"}}
B.apply_grafts(o1, s1)
cyc = cycles(o1)
if cyc: bad(f"场景1 接枝后仍有环：{sorted(cyc)}")
else:   pas("场景1 跨源互相续接 → 无环")
reach = reachable_from_roots(o1)
if {"A1", "B1"} <= reach: pas("场景1 两条用户文本都从根可达（没被吞）")
else: bad(f"场景1 用户文本不可达（被吞）：缺 {sorted({'A1','B1'} - reach)}")

# ── 场景2：正常反向 CC 压缩续接（块2）——不成环，护栏不该误伤，续接仍要被接上 ─────────
sP = "aaaaaaaa-1111-2222-3333-444444444444"; sC = "bbbbbbbb-5555-6666-7777-888888888888"
o2 = {
 "P0": {**um("前情：先做任务P"), "parentUuid": None, "timestamp": "10", "_session_id": sP},
 "P1": {**am("好的"), "parentUuid": "P0", "timestamp": "11", "_session_id": sP},
 "C0": {**um(f"This session is being continued from a previous conversation that ran out of context. 摘要引用 {sP}.jsonl"),
        "parentUuid": None, "timestamp": "20", "_session_id": sC},
 "C1": {**um("续接后：接着做任务P"), "parentUuid": "C0", "timestamp": "21", "_session_id": sC},
}
s2 = {"P0": {sP}, "P1": {sP}, "C0": {sC}, "C1": {sC}}
B.apply_grafts(o2, s2)
if cycles(o2): bad("场景2 正常续接被接成了环")
elif o2["C0"].get("parentUuid") == "P1":
    pas("场景2 正常反向续接仍被接上（C0→P1），护栏无误伤")
else:
    bad(f"场景2 续接未接上（护栏误伤/漏接）：C0.parentUuid={o2['C0'].get('parentUuid')!r}")
if {"P0", "C1"} <= reachable_from_roots(o2): pas("场景2 前情+续接用户文本均可达")
else: bad("场景2 用户文本不可达")

sys.exit(1 if fail else 0)
PY
