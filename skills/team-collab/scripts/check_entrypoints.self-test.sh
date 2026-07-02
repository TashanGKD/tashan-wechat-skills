#!/usr/bin/env bash
# check_entrypoints.py 自测：构造真实漂移（过时术语 / 死链）验证 gate 能拦；并验证真实入口通过。
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
CHECK="$HERE/check_entrypoints.py"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
fail=0
pass() { echo "PASS  $1"; }
bad()  { echo "FAIL  $1"; fail=1; }

# 1) 真实入口（全量）应通过
python3 "$CHECK" >/dev/null 2>&1 && pass "真实入口全量通过" || bad "真实入口未通过（修完入口再跑）"

# 2) 含已废术语 ③ 讨论 → 必须拦
printf '# x\n回复请追加到 ③ 讨论 区。\n' > "$TMP/AGENTS.md"
out=$(python3 "$CHECK" "$TMP/AGENTS.md" 2>&1); rc=$?
{ [ $rc -ne 0 ] && echo "$out" | grep -q "已废术语"; } && pass "过时术语被拦" || bad "过时术语没拦住"

# 3) 死链（引用不存在的真源路径）→ 必须拦
printf '# x\n见 .claude/skills/team-collab/no-such-file.md 和 references/no-such.md\n' > "$TMP/note.md"
out=$(python3 "$CHECK" "$TMP/note.md" 2>&1); rc=$?
{ [ $rc -ne 0 ] && echo "$out" | grep -q "死链"; } && pass "死链被拦" || bad "死链没拦住"

echo "---"
if [ $fail -eq 0 ]; then echo "✓ 自测全过：gate 能拦过时术语+死链、放行合规真实入口"; else echo "✗ 自测有失败项"; fi
exit $fail
