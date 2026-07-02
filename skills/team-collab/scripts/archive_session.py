#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""会话收尾 · 一条命令做全套深档归档（按 session 锚定）

为什么有它：工作日志的"完整规范"是五件套（工作日志 + 完整对话记录 + 会话原始记录 +
动机日志 + 研究历程）。过去只有 worklog.py 管轻量日报，深档全靠人手敲一串命令、且被
当成"按需"——于是经常被默默跳过。本脚本把五件套的**机器能做的部分一次做全**，并把
**只能动脑写的两件（动机/研究历程）脚手架好 + 显式列为待办**，让"完整"成为最省力的路。

它做什么（全部锚定 $CLAUDE_CODE_SESSION_ID 对应的那一份会话文件夹）：
  1. 追加 工作日志.md（复用 worklog.py：同会话 append、换会话新建）
  2. 生成 完整对话记录.md（主会话统一格式·脱敏，调 make_transcript_claudecode.py）
  3. 生成 会话原始记录/（主会话 + 全部子智能体原生镜像，--mirror）
  4. 脚手架 动机日志.md / 研究历程.md（若缺）—— 留模板 + 醒目 TODO，提示必须动脑补实质内容
  5. 自检五件套是否齐 + 打印脱敏提醒；**不自动提交**（脱敏是人工门，提交是另一步）

用法（仓库任意目录可运行）：
  python3 .claude/skills/team-collab/scripts/archive_session.py --person Boyuan --summary-file /tmp/s.md
  python3 .claude/skills/team-collab/scripts/archive_session.py --person Boyuan --summary "今天做了……" --topic 合同v2

退出码：0 = 五件套齐（动机/研究历程至少已存在，实质内容仍需你确认）；2 = 仍有缺件（见输出）。
"""
import argparse, os, sys, subprocess, glob

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import worklog  # 复用：ARCHIVE / resolve_session_id / find_log_for_session / create_log / append_entry

TRANSCRIPT = os.path.join(HERE, "make_transcript_claudecode.py")

MOTIVE_TMPL = """# 动机日志 · {person} · 会话 {sid8}（{date}）

> 记"每一步背后**为什么**这么做 / 这么说"。脚本只能脚手架，**实质内容必须你动脑补**。
> 配套 `工作日志.md`（做了什么）、`研究历程.md`（怎么探索）、`完整对话记录.md`（原始 transcript）。

> ⚠️ 待补：下面是骨架，请按本会话真实决策逐条填，删掉本行与未用占位。

## 关键决策与动机
- **<决策 1>**：为什么这么定（动机 / 要解决的问题 / 否决了什么备选）。
- **<决策 2>**：……
"""

RESEARCH_TMPL = """# 研究历程 · {person} · 会话 {sid8}（{date}）

> 记"怎么**探索、调研、转向、发现、踩坑**"。脚本只能脚手架，**实质内容必须你动脑补**。
> 配套 `动机日志.md`（为什么）、`工作日志.md`（做了什么）。

> ⚠️ 待补：下面是骨架，请按本会话真实历程填，删掉本行与未用占位。

## 主线
<一句话：本会话主线是什么>

## 关键转向 / 发现
- **转向 1**：从 … 到 …，因为 …
- **发现**：…

## 踩坑 / 修正（成长语料）
- …
"""

def run(cmd):
    print("  $", " ".join(cmd[1:] if cmd and cmd[0].endswith("python3") else cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    out = (r.stdout or "") + (r.stderr or "")
    for line in out.splitlines():
        print("    " + line)
    return r.returncode == 0

def main():
    ap = argparse.ArgumentParser(description="会话收尾·一条命令做全套深档归档")
    ap.add_argument("--person", required=True, help="你代表谁（声明身份），决定写进谁的文件夹")
    ap.add_argument("--summary", help="当天工作总结正文")
    ap.add_argument("--summary-file", help="从文件读总结正文")
    ap.add_argument("--topic", help="新建日志时的主题名（仅首次创建用）")
    ap.add_argument("--session-id", help="覆盖 session-id（默认取 $CLAUDE_CODE_SESSION_ID）")
    args = ap.parse_args()

    if not worklog.PERSON_RE.match(args.person or ""):
        worklog.die(f"--person 非法（只允许中英文/数字/连字符）：{args.person!r}")
    sid = worklog.resolve_session_id(args.session_id)

    summary = args.summary
    if args.summary_file:
        try: summary = open(args.summary_file, encoding="utf-8").read()
        except OSError as e: worklog.die(f"读 --summary-file 失败：{e}")
    if summary is None and not sys.stdin.isatty():
        summary = sys.stdin.read()
    if not summary or not summary.strip():
        worklog.die("总结正文为空：用 --summary / --summary-file / stdin 提供。深档也需要一句日报锚定。")

    from datetime import datetime
    person_dir = os.path.join(worklog.ARCHIVE, args.person)
    os.makedirs(person_dir, exist_ok=True)

    # —— 1) 工作日志（复用 worklog 逻辑：同会话 append，换会话新建）——
    print("【1/5】工作日志.md")
    log = worklog.find_log_for_session(person_dir, sid)
    if not log:
        log = worklog.create_log(person_dir, args.person, sid, args.topic)
        print("    新建本会话日志")
    worklog.append_entry(log, sid, summary)
    folder = os.path.dirname(log)            # 本会话文件夹，后续全部件锚定它
    print("    →", os.path.relpath(log, worklog.REPO))

    # —— 2) 完整对话记录（显式 --out 锁到同一文件夹，避免 topic/sid 命名分叉）——
    print("【2/5】完整对话记录.md")
    run(["python3", TRANSCRIPT, "--person", args.person, "--session", sid,
         "--out", os.path.join(folder, "完整对话记录.md"), "--force"])

    # —— 3) 会话原始记录/（主会话 + 全部子智能体镜像）——
    print("【3/5】会话原始记录/（主会话 + 全部子智能体）")
    run(["python3", TRANSCRIPT, "--person", args.person, "--mirror", sid,
         "--out-dir", os.path.join(folder, "会话原始记录"), "--force"])

    # —— 4) 动机/研究历程 脚手架（缺则建模板；实质内容必须人补）——
    print("【4/5】动机日志.md / 研究历程.md（脚手架）")
    ctx = {"person": args.person, "sid8": sid[:8], "date": f"{datetime.now():%Y-%m-%d}"}
    scaffolded = []
    for name, tmpl in [("动机日志.md", MOTIVE_TMPL), ("研究历程.md", RESEARCH_TMPL)]:
        p = os.path.join(folder, name)
        if not os.path.exists(p):
            open(p, "w", encoding="utf-8").write(tmpl.format(**ctx))
            scaffolded.append(name)
    print("    脚手架:", ", ".join(scaffolded) if scaffolded else "（两份已存在，未覆盖）")

    # —— 5) 自检五件套 + 报告 ——
    print("【5/5】五件套自检")
    mirror_dir = os.path.join(folder, "会话原始记录")
    checks = {
        "工作日志.md": os.path.exists(os.path.join(folder, "工作日志.md")),
        "完整对话记录.md": os.path.exists(os.path.join(folder, "完整对话记录.md")),
        "会话原始记录/": os.path.isdir(mirror_dir) and bool(glob.glob(os.path.join(mirror_dir, "**", "*.md"), recursive=True)),
        "动机日志.md": os.path.exists(os.path.join(folder, "动机日志.md")),
        "研究历程.md": os.path.exists(os.path.join(folder, "研究历程.md")),
    }
    for k, ok in checks.items():
        print(f"    {'✅' if ok else '❌'} {k}")
    missing = [k for k, ok in checks.items() if not ok]

    print("\n" + "─" * 56)
    print(f"会话文件夹：{os.path.relpath(folder, worklog.REPO)}")
    if missing:
        print("✗ 仍有缺件：", "、".join(missing), "—— 请排查上面的命令输出。")
    else:
        print("✓ 五件套齐。仍需你完成的两件人工活：")
        print("  1) 动机日志.md / 研究历程.md：脚手架已建，**补上本会话的实质内容**（不是留模板就算）。")
        print("  2) 脱敏过目：完整对话记录 / 会话原始记录含原始对话，提交前看脱敏报告（上方各步已打印命中数）。")
    print("提交另做（脚本不自动提交）：显式 git add 本会话文件夹 → docs(collab): 本会话深度归档 → 按 git 纪律推送。")
    sys.exit(2 if missing else 0)

if __name__ == "__main__":
    main()
