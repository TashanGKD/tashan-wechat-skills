#!/usr/bin/env bash
# build_mindmap_html.py 自测：生成器产出的 思维画布.html 应 (1) 内嵌 JS 语法合法 (2) 含各项修复的标记。
# 注：这是【回归/存在性守卫】——真·渲染行为验证靠浏览器（P0 分支徽标 / 体量时长徽标 / fit-to-view /
# 脱敏 pill 等已用 serve.py + preview 手动跑 对话26 实测：369 框 0 console 报错、bbadge×8、rd×9）。
# 若有人改模板把某项修复删了，本测会 FAIL。
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
fail=0; pass(){ echo "PASS  $1"; }; bad(){ echo "FAIL  $1"; fail=1; }

mkdir -p "$TMP/tree"; printf '{"节点":[]}' > "$TMP/tree/tree.json"
python3 "$HERE/build_mindmap_html.py" --tree "$TMP/tree" >/dev/null 2>&1 || { bad "生成器运行失败"; exit 1; }
H="$TMP/tree/思维画布.html"
[ -f "$H" ] && pass "思维画布.html 生成" || { bad "未生成 html"; exit 1; }

# 内嵌 JS 语法检查（抽 <script> → node --check）
python3 - "$H" "$TMP/app.js" <<'PY'
import sys,re
h=open(sys.argv[1],encoding="utf-8").read()
m=re.search(r'<script>(.*)</script>',h,re.S)
open(sys.argv[2],"w",encoding="utf-8").write(m.group(1) if m else "")
PY
if command -v node >/dev/null; then
  node --check "$TMP/app.js" 2>/dev/null && pass "内嵌 JS 语法合法 (node --check)" || bad "内嵌 JS 语法错误"
else
  echo "SKIP  node 不可用，跳过 JS 语法检查"
fi

# 各项修复存在性（P0 + 9 quick-wins）
grep -q 'function box(turn,id,col,yy,bhead)' "$H" && pass "P0 分支首块 box 带 bhead 参数" || bad "P0 box(bhead) 缺失"
grep -q 'class="bbadge' "$H" && grep -q '⑂ ' "$H" && pass "P0 ⑂ 分支徽标渲染" || bad "P0 ⑂ 徽标缺失"
grep -q 'function fmtDur' "$H" && grep -q 'n_records' "$H" && pass "QW 体量/时长徽标" || bad "体量/时长徽标缺失"
grep -q 'length>200?' "$H" && pass "QW 预览不再硬砍 20 字" || bad "预览截断未放宽"
grep -q 'world.offsetWidth' "$H" && pass "QW ⊡ 真 fit-to-view" || bad "fit-to-view 缺失"
grep -q 'writeText(sid).then' "$H" && pass "QW 复制 session-id 诚实反馈" || bad "复制反馈仍无条件✓"
grep -q "closest('.box.exp')" "$H" && pass "QW 展开框放行文本选择" || bad "文本选择未放行"
grep -q 'function fmtTx' "$H" && grep -q 'class="rd"' "$H" && pass "QW 脱敏标记 pill" || bad "脱敏 pill 缺失"
grep -q 'function zoomBy' "$H" && pass "QW +/− 缩放绕中心" || bad "缩放绕中心缺失"
grep -q 'curAbort' "$H" && grep -q 'AbortController' "$H" && pass "QW 切换取消在途请求" || bad "在途取消缺失"
grep -q '暂无对话' "$H" && pass "QW 空树≠读取失败" || bad "空树态缺失"
grep -q "split('-').pop()" "$H" && pass "QW alias 取本级名 (split-)" || bad "alias 分割未修"
# P1 分叉语义批
grep -q 'function cmpChild' "$H" && pass "P1 稳定比较器 cmpChild(相等返回0)" || bad "cmpChild 缺失"
grep -q 'NODE_COMPACT' "$H" && pass "P1 compact 自动续接检测" || bad "compact 检测缺失"
grep -q '⟳ ' "$H" && grep -q "kind==='cont'" "$H" && pass "P1 续接⟳ vs fork⑂ 双标" || bad "续接/fork 双标缺失"
grep -q 'class="src ' "$H" && grep -q '·⌥' "$H" && pass "P1 跨源来源标 + ⌥源切换标" || bad "跨源可见性缺失"

echo "----"; [ $fail -eq 0 ] && echo "✓ 全过" || echo "✗ 有失败项"
exit $fail
