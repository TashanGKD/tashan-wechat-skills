#!/usr/bin/env bash
# verify_tree.py 自测：构造**已知有缺陷**的假树，证明 gate 能抓住真实失败；并构造正确假树验证放行。
# 目标 bug：遗漏(有文本用户消息没进树) / 重复(uuid 落多节点) / 错配(段内顺序≠真实 parentUuid 链)。
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
fail=0
pass(){ echo "PASS  $1"; }
bad(){ echo "FAIL  $1"; fail=1; }

# 造源：4 条因果链 u0(用户有文本)->u1(agent)->u2(用户有文本)->u3(agent)
mkdir -p "$TMP/src"
python3 - "$TMP/src" <<'PY'
import json, os, sys
src = sys.argv[1]
recs = [
 {"uuid":"u0","parentUuid":None,"timestamp":"2026-01-01 00:00:00","type":"user","message":{"role":"user","content":"开始做任务A"}},
 {"uuid":"u1","parentUuid":"u0","timestamp":"2026-01-01 00:00:01","type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"好的"}]}},
 {"uuid":"u2","parentUuid":"u1","timestamp":"2026-01-01 00:00:02","type":"user","message":{"role":"user","content":"再做任务B"}},
 {"uuid":"u3","parentUuid":"u2","timestamp":"2026-01-01 00:00:03","type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"完成"}]}},
]
open(os.path.join(src,"sess1.jsonl"),"w").write("\n".join(json.dumps(r) for r in recs))
PY

# 据节点定义生成假树（tree.json + 每节点 段.md）
gen(){ python3 - "$1" "$2" <<'PY'
import json, os, sys
tree, nodesjson = sys.argv[1], sys.argv[2]
nodes = json.loads(nodesjson)
os.makedirs(tree, exist_ok=True)
for n in nodes:
    d = os.path.join(tree, n["dir"]); os.makedirs(d, exist_ok=True)
    open(os.path.join(d,"段.md"),"w").write(f"> 节点段: {len(n['uuids'])} 条记录\n")
json.dump({"节点":nodes}, open(os.path.join(tree,"tree.json"),"w"), ensure_ascii=False)
PY
}
V(){ python3 "$HERE/verify_tree.py" --src "$TMP/src" --tree "$1"; }

# 1) 正确：单根含全部 4 条 → 应放行（结构性 0 + 陈旧 0）
gen "$TMP/good" '[{"alias":"对话1","dir":"对话1","parent_dir":null,"sessions":["sess1"],"uuids":["u0","u1","u2","u3"]}]'
V "$TMP/good" >/dev/null 2>&1 && pass "正确树放行" || bad "正确树被误报"

# 2) 漏记录：树覆盖范围内漏掉 u2（u3 的父）→ 表现为"断裂"，结构性 → 应拦
gen "$TMP/omit" '[{"alias":"对话1","dir":"对话1","parent_dir":null,"sessions":["sess1"],"uuids":["u0","u1","u3"]}]'
out=$(V "$TMP/omit" 2>&1); rc=$?
{ [ $rc -ne 0 ] && echo "$out" | grep -qE "断裂|重构"; } && pass "漏祖先(断裂)被拦" || bad "漏祖先没拦住"

# 3) 重复：u1 落在两个节点 → 应拦
gen "$TMP/dup" '[{"alias":"对话1","dir":"对话1","parent_dir":null,"sessions":["sess1"],"uuids":["u0","u1","u2","u3"]},{"alias":"X","dir":"X","parent_dir":"对话1","sessions":["sess1"],"uuids":["u1"]}]'
out=$(V "$TMP/dup" 2>&1); rc=$?
{ [ $rc -ne 0 ] && echo "$out" | grep -q "重复"; } && pass "重复被拦" || bad "重复没拦住"

# 4) 错配：段内顺序打乱(u0,u2,u1,u3) → 断裂/重构 应拦
gen "$TMP/mis" '[{"alias":"对话1","dir":"对话1","parent_dir":null,"sessions":["sess1"],"uuids":["u0","u2","u1","u3"]}]'
out=$(V "$TMP/mis" 2>&1); rc=$?
{ [ $rc -ne 0 ] && echo "$out" | grep -qE "断裂|重构"; } && pass "顺序错配被拦" || bad "顺序错配没拦住"

# 5) 陈旧：树只含 u0,u1，源还有 u2,u3 但树覆盖的会话内无断裂 → 结构性 0、应放行(退出0)；--strict 才失败
gen "$TMP/stale" '[{"alias":"对话1","dir":"对话1","parent_dir":null,"sessions":["sess1"],"uuids":["u0","u1"]}]'
V "$TMP/stale" >/dev/null 2>&1 && pass "陈旧默认放行(退出0)" || bad "陈旧被误判为失败"
python3 "$HERE/verify_tree.py" --src "$TMP/src" --tree "$TMP/stale" --strict >/dev/null 2>&1 && bad "--strict 下陈旧没拦住" || pass "--strict 下陈旧被拦"

echo "---"
if [ $fail -eq 0 ]; then echo "✓ 自测全过：遗漏/重复/错配都能抓、正确树放行"; else echo "✗ 自测有失败项"; fi
exit $fail
