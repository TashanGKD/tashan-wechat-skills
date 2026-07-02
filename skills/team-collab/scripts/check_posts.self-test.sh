#!/usr/bin/env bash
# check_posts.py 的自测：构造**真实形态**的违规帖，验证 gate 能拦住；并验证合格帖放行。
# 这不是"脚本能跑就算过"——每个反例都对应 check_posts 要防的一类 bug。
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
CHECK="$HERE/check_posts.py"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
fail=0

pass() { echo "PASS  $1"; }
bad()  { echo "FAIL  $1"; fail=1; }

# 1) 合格帖（最小合规）→ 必须放行
cat > "$TMP/010-good.md" <<'EOF'
# 话题 010 · 自测合格样例

<!-- topic-meta
id: 010
创建: 2026-06-17
发起人: Tester
状态: 🟢 进行中
摘要: 自测用合格帖。
-->

> 话题说明。

---

## 帖 1 · 一个合规的帖
- **发帖**：[Tester] · 2026-06-17
- **状态**：🟢 进行中

**① 想做什么**
动机。

**② 方案 / 内容**
内容。

**💬 回复**
> [别人 · 2026-06-17]
> 一条回复。
EOF
python3 "$CHECK" "$TMP/010-good.md" >/dev/null 2>&1 && pass "合格帖放行" || bad "合格帖被误拦"

# 2) 流水账（无 ## 帖结构）→ 必须拦
cat > "$TMP/011-flat.md" <<'EOF'
# 话题 011 · 流水账反例

<!-- topic-meta
id: 011
创建: 2026-06-17
发起人: Tester
状态: 🟢 进行中
摘要: 没有帖结构、全揉一块。
-->

> 全揉一块。

> [Boyuan · 2026-06-17]
> 一段话。
EOF
out=$(python3 "$CHECK" "$TMP/011-flat.md" 2>&1); rc=$?
{ [ $rc -ne 0 ] && echo "$out" | grep -q "至少要有一个"; } && pass "流水账被拦" || bad "流水账没拦住"

# 3) 帖缺① + 状态值乱填 → 必须拦
cat > "$TMP/012-bad-post.md" <<'EOF'
# 话题 012 · 帖缺项反例

<!-- topic-meta
id: 012
创建: 2026-06-17
发起人: Tester
状态: 进行中
摘要: 状态没 emoji、帖缺①。
-->

> 说明。

---

## 帖 1 · 缺①的帖
- **发帖**：[Tester] · 2026-06-17
- **状态**：开心

**② 方案 / 内容**
只有②。

**💬 回复**
> 无
EOF
out=$(python3 "$CHECK" "$TMP/012-bad-post.md" 2>&1); rc=$?
{ [ $rc -ne 0 ] && echo "$out" | grep -q "① 想做什么" && echo "$out" | grep -q "状态值非法"; } \
  && pass "缺①/状态乱填被拦" || bad "没拦住缺①或状态乱填"

# 4) 回复没署名日期 → 必须拦
cat > "$TMP/013-bad-reply.md" <<'EOF'
# 话题 013 · 回复格式反例

<!-- topic-meta
id: 013
创建: 2026-06-17
发起人: Tester
状态: 🟢 进行中
摘要: 回复没署名日期。
-->

> 说明。

---

## 帖 1 · 帖
- **发帖**：[Tester] · 2026-06-17
- **状态**：🟢 进行中

**① 想做什么**
动机。

**② 方案 / 内容**
内容。

**💬 回复**
> [乱写没有分隔符]
EOF
out=$(python3 "$CHECK" "$TMP/013-bad-reply.md" 2>&1); rc=$?
{ [ $rc -ne 0 ] && echo "$out" | grep -q "回复署名格式错"; } && pass "回复格式被拦" || bad "回复格式没拦"

# 5) 文件名编号与标题话题号不一致 → 必须拦
cat > "$TMP/099-mismatch.md" <<'EOF'
# 话题 014 · 号不一致反例

<!-- topic-meta
id: 014
创建: 2026-06-17
发起人: Tester
状态: 🟢 进行中
摘要: 文件名099、标题014。
-->

> 说明。

---

## 帖 1 · 帖
- **发帖**：[Tester] · 2026-06-17
- **状态**：🟢 进行中

**① 想做什么**
x。

**② 方案 / 内容**
y。

**💬 回复**
> [a · 2026-06-17]
> z。
EOF
out=$(python3 "$CHECK" "$TMP/099-mismatch.md" 2>&1); rc=$?
{ [ $rc -ne 0 ] && echo "$out" | grep -q "不一致"; } && pass "号不一致被拦" || bad "号不一致没拦"

echo "---"
if [ $fail -eq 0 ]; then echo "✓ 自测全过：gate 能拦真实违规、放行合格帖"; else echo "✗ 自测有失败项"; fi
exit $fail
