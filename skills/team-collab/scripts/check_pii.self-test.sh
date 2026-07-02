#!/usr/bin/env bash
# check_pii.py 自测：构造含真实形态 PII 的 .md 验证能抓；构造干净(含脱敏占位+时间戳)的 .md 验证放行。
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
fail=0
pass(){ echo "PASS  $1"; }
bad(){ echo "FAIL  $1"; fail=1; }

# 1) 脏文件：手机/邮箱/微信号/身份证 → 必须拦
cat > "$TMP/dirty.md" <<'MD'
联系电话 13800138000，邮箱 someone@example.com
文件在 wxid_zv3mnxp1p4sy22_6a74 目录
证件号 110101199003078515
MD
out=$(python3 "$HERE/check_pii.py" "$TMP/dirty.md" 2>&1); rc=$?
{ [ $rc -ne 0 ] && echo "$out" | grep -q "cn-phone" && echo "$out" | grep -q "wechat-id"; } \
  && pass "脏文件被拦(手机+微信号)" || bad "脏文件没拦住"

# 2) 干净文件：脱敏占位 + 13 位毫秒时间戳 + 公开 URL → 必须放行
cat > "$TMP/clean.md" <<'MD'
电话 [已脱敏:cn-phone]，备份 backup.1781706458693.json
政府公告 https://swj.beijing.gov.cn/.../P020230720600023195766.pdf
研究历程：建专家2工作区、调研八子专业。
MD
python3 "$HERE/check_pii.py" "$TMP/clean.md" >/dev/null 2>&1 \
  && pass "干净文件放行(时间戳/URL不误报)" || bad "干净文件被误报"

echo "---"
if [ $fail -eq 0 ]; then echo "✓ 自测全过：真实 PII 被拦、脱敏占位/时间戳/公开URL 放行"; else echo "✗ 自测有失败项"; fi
exit $fail
