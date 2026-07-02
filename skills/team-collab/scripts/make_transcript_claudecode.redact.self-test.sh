#!/usr/bin/env bash
# mt.redact 脱敏自测：构造**真实形态**的 PII 验证能脱敏；构造时间戳子串验证不误脱敏。
# 目标 bug（本测要拦住的真实失败）：手机号 / 微信号 wxid_ / 身份证等长号 漏脱敏（本会话真踩过）。
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
python3 - "$HERE" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
import make_transcript_claudecode as mt
fail = 0
def must_redact(label, text, needle):
    global fail
    out = mt.redact(text, {})
    if needle in out:
        print(f"FAIL  {label}：未脱敏 → {out}"); fail = 1
    else:
        print(f"PASS  {label}")
def must_keep(label, text, needle):
    global fail
    out = mt.redact(text, {})
    print(f"PASS  {label}" if needle in out else f"FAIL  {label}：误脱敏 → {out}")
    if needle not in out: fail = 1
# —— 必须脱敏的真实形态 PII ——
must_redact("手机号",     "联系电话 13800138000 谢谢",              "13800138000")
must_redact("微信号",     "文件在 wxid_zv3mnxp1p4sy22_6a74 目录",   "wxid_zv3mnxp1p4sy22_6a74")
must_redact("身份证18位", "证件号 110101199003078515 完",          "110101199003078515")
must_redact("邮箱",       "邮箱 someone@example.com 发我",          "someone@example.com")
must_redact("API key",    "key=sk-ant-abcdefghijklmnop1234",        "sk-ant-abcdefghijklmnop1234")
# —— 不该误脱敏：13 位毫秒时间戳（手机号子串不该被切出来）——
must_keep("毫秒时间戳不误切", "backup.1781706458693.json", "1781706458693")
print("---")
sys.exit(fail)
PY
rc=$?
[ $rc -eq 0 ] && echo "✓ 脱敏自测全过：真实 PII 被脱敏、时间戳不误脱敏" || echo "✗ 脱敏自测有失败项"
exit $rc
