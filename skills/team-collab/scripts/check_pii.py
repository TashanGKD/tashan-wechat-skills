#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PII 提交闸 —— 扫对话树 `.md` 里漏脱敏的 PII（手机 / 邮箱 / 微信号 / 身份证等长号）。

为什么需要：`段.md` 由 builder 渲染时已脱敏，但①正则非 100%、②**人写的 `研究历程.md`/`动机日志.md`
不过 builder 脱敏**（子智能体/人可能手滑写进真实 PII）。本闸是提交前的兜底（worklog 唯一没机器 gate 的高危环节）。

命中 → 打印 `文件:行 [类型] 掩码值`，退出码 1。复用 make_transcript_claudecode 的 PII 正则
（带前后非数字断言，13 位毫秒时间戳等不会误报）。确属误报可 `git commit --no-verify`。

用法：
  python3 check_pii.py <file.md> ...     # 只扫指定文件（pre-commit 用）
  python3 check_pii.py                    # 扫所有 person 的 对话树/ 下全部 .md
"""
import glob, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_transcript_claudecode as mt

REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
# 只取"个人信息"类（密钥类 key/token 不在对话树记忆里出现、且 git-secrets 另管）
PII = [(n, p) for n, p in mt._PATTERNS if n in ("email", "cn-phone", "long-id", "wechat-id")]


def mask(v):
    return v[:3] + "***" + v[-2:] if len(v) > 6 else "***"


def scan(path):
    out = []
    try:
        lines = open(path, encoding="utf-8", errors="ignore").readlines()
    except OSError:
        return out
    for i, ln in enumerate(lines, 1):
        for n, p in PII:
            for m in p.finditer(ln):
                out.append((i, n, mask(m.group(0))))
    return out


def main():
    args = [a for a in sys.argv[1:] if a.endswith(".md")]
    if args:
        files = args
    else:
        files = glob.glob(os.path.join(REPO, "团队协作记录", "智能体工作日志",
                                       "*", "对话树", "**", "*.md"), recursive=True)
    total = 0
    for f in sorted(set(files)):
        for i, n, v in scan(f):
            print(f"  {os.path.relpath(f, REPO)}:{i}  [{n}] {v}")
            total += 1
    if total:
        print(f"\n✗ 发现 {total} 处疑似未脱敏 PII，处理后再提交（确属误报：git commit --no-verify）。")
        return 1
    print(f"✓ PII 扫描通过（{len(files)} 文件，无手机/邮箱/微信号/长号残留）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
