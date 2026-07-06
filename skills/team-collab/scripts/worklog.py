#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""智能体工作日志归档工具（按 session 锚定）

把"当天的工作总结"追加到【本人 + 本会话】对应的那一份工作日志里：
  - 同一个会话（session-id 不变）→ 永远 append 到同一份日志（即使跨天）。
  - 换一个会话（新的 session-id）→ 自动归到另一份新日志。

会话身份从环境变量 CLAUDE_CODE_SESSION_ID 取（Claude Code 运行时自带）；
取不到可用 --session-id 显式给。脚本只写本地文件，**不提交、不推送**（提交是另一步，按 git 纪律显式做）。

归档位置自解析：脚本无论从哪运行，都会定位到仓库根下的
`团队协作记录/智能体工作日志/`（与 make_transcript_claudecode.py 同约定）。

用法（可在仓库任意目录运行）：
  python3 .claude/skills/team-collab/scripts/worklog.py --person Alice --summary "今天做了……"
  python3 .claude/skills/team-collab/scripts/worklog.py --person Alice --summary-file /tmp/s.md --topic 合同与协作体系
  echo "总结正文" | python3 .claude/skills/team-collab/scripts/worklog.py --person Alice

约定：
  - 你（智能体）必须用自己的"声明身份"作为 --person（你代表谁就填谁），这决定写进谁的文件夹。
  - 总结正文由你（智能体）生成；本脚本只负责"放到对的那份日志、对的日期下、append 不覆盖"。
"""
import argparse, os, re, sys, glob
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))          # .../.claude/skills/team-collab/scripts
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))   # 仓库根
ARCHIVE = os.path.join(REPO, "团队协作记录", "智能体工作日志")        # 归档根
PERSON_RE = re.compile(r"^[\w一-鿿\-]+$")           # 防路径穿越：只允许中英文/数字/连字符
META_RE = re.compile(r"<!--\s*worklog-meta(.*?)-->", re.S)

def die(msg):
    print(f"✗ {msg}", file=sys.stderr); sys.exit(1)

def resolve_session_id(arg):
    sid = arg or os.environ.get("CLAUDE_CODE_SESSION_ID")
    if not sid:
        die("拿不到 session-id：环境变量 CLAUDE_CODE_SESSION_ID 为空，也没传 --session-id。"
            "为避免写错日志，这里直接退出，不乱写。")
    if not re.match(r"^[\w\-]+$", sid):
        die(f"session-id 含非法字符：{sid!r}")
    return sid

def parse_meta_sessions(md_path):
    try:
        txt = open(md_path, encoding="utf-8").read()
    except OSError:
        return None
    m = META_RE.search(txt)
    if not m:
        return None
    sessions = []
    for line in m.group(1).splitlines():
        low = line.strip().lower()
        # 标准字段 session-id:；兼容历史遗留的 sessions:（旧做法可能登记多个）
        if low.startswith("session-id:") or low.startswith("sessions:"):
            sessions += [s.strip() for s in line.split(":", 1)[1].split(",") if s.strip()]
    return sessions

def find_log_for_session(person_dir, sid):
    """在 person 目录下找 工作日志.md 的 meta.sessions 含本 sid 的那一份；返回其路径或 None。"""
    for log in glob.glob(os.path.join(person_dir, "*", "工作日志.md")):
        sessions = parse_meta_sessions(log)
        if sessions and sid in sessions:
            return log
    return None

def slug(s):
    s = re.sub(r"[^\w一-鿿\-]+", "-", s.strip())
    return s.strip("-")[:40] or "工作"

def create_log(person_dir, person, sid, topic):
    folder_name = f"{datetime.now():%Y-%m-%d}_{slug(topic) if topic else sid[:8]}"
    folder = os.path.join(person_dir, folder_name)
    os.makedirs(folder, exist_ok=True)
    log = os.path.join(folder, "工作日志.md")
    if not os.path.exists(log):
        header = (
            f"# 工作日志 · {person}" + (f" · {topic}" if topic else "") + "\n\n"
            "<!-- worklog-meta\n"
            f"person: {person}\n"
            f"session-id: {sid}\n"
            "-->\n\n"
            "> 本日志以 **session-id 为唯一标识**：一份日志只认一个 session-id。同一 session-id 一直 append 于此（即使跨天）；"
            "**换 session-id 一律另起新日志**（即使是同一段工作的重启续接）。机制见 [`../../README.md`](../../README.md)。\n\n"
            "---\n"
        )
        open(log, "w", encoding="utf-8").write(header)
    return log

def append_entry(log, sid, summary):
    txt = open(log, encoding="utf-8").read()
    today = f"{datetime.now():%Y-%m-%d}"
    now = f"{datetime.now():%H:%M}"
    day_header = f"## {today}"
    entry = f"\n### {now} · session `{sid[:8]}`\n\n{summary.rstrip()}\n"
    if day_header in txt:
        # 当天已有小节：在文末追加一个带时间戳的子条目（不覆盖、不丢历史）
        txt = txt.rstrip() + "\n" + entry
    else:
        txt = txt.rstrip() + f"\n\n{day_header}\n" + entry
    open(log, "w", encoding="utf-8").write(txt)

def main():
    ap = argparse.ArgumentParser(description="智能体工作日志归档（按 session 锚定，append 不覆盖）")
    ap.add_argument("--person", required=True, help="你代表谁（声明身份），决定写进谁的文件夹，如 Alice")
    ap.add_argument("--summary", help="当天工作总结正文")
    ap.add_argument("--summary-file", help="从文件读总结正文")
    ap.add_argument("--topic", help="新建日志时的主题名（仅首次创建用）")
    ap.add_argument("--session-id", help="覆盖 session-id（默认取 $CLAUDE_CODE_SESSION_ID）")
    args = ap.parse_args()

    if not PERSON_RE.match(args.person or ""):
        die(f"--person 非法（只允许中英文/数字/连字符，防路径穿越）：{args.person!r}")

    sid = resolve_session_id(args.session_id)

    summary = args.summary
    if args.summary_file:
        try: summary = open(args.summary_file, encoding="utf-8").read()
        except OSError as e: die(f"读 --summary-file 失败：{e}")
    if summary is None and not sys.stdin.isatty():
        summary = sys.stdin.read()
    if not summary or not summary.strip():
        die("总结正文为空：用 --summary / --summary-file / stdin 提供。不写空条目。")

    person_dir = os.path.join(ARCHIVE, args.person)
    os.makedirs(person_dir, exist_ok=True)

    log = find_log_for_session(person_dir, sid)
    action = "append（命中本会话已有日志）"
    if not log:
        log = create_log(person_dir, args.person, sid, args.topic)
        action = "新建（本会话首次归档）"

    append_entry(log, sid, summary)
    rel = os.path.relpath(log, ARCHIVE)
    print(f"✓ {action}")
    print(f"  person : {args.person}")
    print(f"  session: {sid}")
    print(f"  写入   : 团队协作记录/智能体工作日志/{rel}")
    print(f"  提醒   : 仅写本地，请按 git 纪律自行提交（docs(collab): 更新工作日志）")

if __name__ == "__main__":
    main()
