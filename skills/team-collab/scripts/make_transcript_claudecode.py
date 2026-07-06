#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_transcript_claudecode.py —— Claude Code 对话记录 → 统一 md（脱敏 · 无 AI 提炼）

这是「对话记录统一格式」的 **Claude Code 参考实现**。规范见同级
`../references/conversation-log-spec.md`。只做格式转换 + 脱敏，绝不做 AI 提炼。

结构（其他工具照抄改读取器即可）：
  reader  —— 读 Claude Code 的 .jsonl，解析成统一原语 {role,time,text,tool_use,tool_result}
  redact  —— 脱敏（共享，可直接复用）
  render  —— 原语 → 统一 md 格式（共享，可直接复用）

用法：
  python3 make_transcript_claudecode.py --person Alice                 # 当前会话($CLAUDE_CODE_SESSION_ID)
  python3 make_transcript_claudecode.py --person Alice --session <sid>
  python3 make_transcript_claudecode.py --person Alice --merge <sid1>,<sid2>,<sid3>
  python3 make_transcript_claudecode.py --person Alice --out FILE | --stdout
  python3 make_transcript_claudecode.py --scan FILE         # 只扫描某文件里的敏感命中（不改文件）

安全：默认不覆盖已存在文件（需 --force）；person 防路径穿越；缺 session-id 即退出。
"""
import argparse, glob, json, os, re, sys
from datetime import datetime

# ───────────────────────── 脱敏器（共享，可复用）─────────────────────────
_PATTERNS = [
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S)),
    ("jwt",          re.compile(r"\beyJ[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{6,}")),
    ("aws-key",      re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("google-key",   re.compile(r"\bAIza[0-9A-Za-z_\-]{20,}\b")),
    ("slack-token",  re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{8,}")),
    ("github-token", re.compile(r"\bgh[posru]_[A-Za-z0-9]{20,}\b")),
    ("api-key",      re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_-]{16,}")),
    ("auth-header",  re.compile(r"(?i)\b(?:authorization|bearer)\b\s*[:=]?\s*[A-Za-z0-9._\-]{16,}")),
    ("email",        re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),   # 邮箱属 PII，宁枉勿纵
    ("cn-phone",     re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")),   # 中国大陆手机号（11 位，前后非数字防误切长串）
    ("long-id",      re.compile(r"(?<!\d)\d{15,19}(?!\d)")),     # 15–19 位长号：身份证/银行卡/统一信用代码等，宁枉勿纵
    ("wechat-id",    re.compile(r"wxid_[A-Za-z0-9_\-]+")),       # 微信内部用户标识（标识个人账号，属 PII；不加 \b 以免前接字符时漏切）
]
_KV = re.compile(
    r'(?i)(\b(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|secret[_-]?key|private[_-]?key|client[_-]?secret)\b\s*[:=]\s*)(["\']?)([^\s"\',}]{4,})\2'
)

def redact(text, counts):
    """返回脱敏后的文本；命中数累加进 counts。"""
    if not text:
        return text
    for name, pat in _PATTERNS:
        def repl(m, name=name):
            counts[name] = counts.get(name, 0) + 1
            return f"[已脱敏:{name}]"
        text = pat.sub(repl, text)
    def kv(m):
        counts["cred-kv"] = counts.get("cred-kv", 0) + 1
        return f"{m.group(1)}{m.group(2)}[已脱敏:cred-kv]{m.group(2)}"
    return _KV.sub(kv, text)

# ───────────────────────── 渲染器（共享，可复用）─────────────────────────
def render(entries, human, source_tool, sids, counts, extra_lines=None, source_files=None):
    """entries: [{role, time, text, tools:[(name,input_str)], results:[str]}] → 统一 md

    source_files: 本机原始 .jsonl 的**绝对路径**列表 = 这份 md 回到「唯一真相」的回程票。
      本 md 是去重整理后的**视图**；真源 jsonl 才是逐条原文。把真源路径写进头部，读者/agent 便可
      顺着它回原始 jsonl 做无损重读。注意：路径是**该工作日志所有者的本机路径**——他人机上无此源时，
      以本 md 为准（这正是「自己拥有才下钻、否则读 md」的依据）。"""
    _red_start = sum(counts.values())   # 记本次 render 前的累计 → 末尾算「本节点自身」命中（不含跨节点累加，见 install-and-build-issues.md#1.3）
    times = [e["time"] for e in entries if e["time"]]
    hl = [
        "# 完整对话记录（统一格式）", "",
        f"> 来源工具: {source_tool}",
        f"> 会话(session): {', '.join(sids)}",
    ]
    if source_files:
        hl.append(f"> 真源(source-of-truth): {' ; '.join(source_files)}")
    hl += [
        f"> 参与者(human): {human}",
        f"> 时间: {min(times) if times else '?'} → {max(times) if times else '?'}",
    ]
    for x in (extra_lines or []):
        hl.append(f"> {x}")
    hl += [
        "> 处理: 仅格式转换 + 脱敏，无 AI 提炼 | 脱敏命中: __REDCOUNT__ 处",
        "> 规范: .claude/skills/team-collab/references/conversation-log-spec.md",
        "", "---",
    ]
    head = "\n".join(hl) + "\n"
    body = []
    for e in entries:
        ts = e["time"] or ""
        if e["role"] == "human":
            body.append(f"\n### [{ts}] 🧑 {human}\n\n{redact(e['text'], counts)}\n")
        else:
            body.append(f"\n### [{ts}] 🤖 agent\n")
            if e["text"].strip():
                body.append(f"\n{redact(e['text'], counts)}\n")
            for name, inp in e["tools"]:
                body.append(f"\n<details><summary>⟨工具调用 · {name}⟩</summary>\n\n```json\n{redact(inp, counts)}\n```\n</details>\n")
            for res in e["results"]:
                body.append(f"\n<details><summary>⟨工具结果（{len(res)} 字符）⟩</summary>\n\n```\n{redact(res, counts)}\n```\n</details>\n")
    node_total = sum(counts.values()) - _red_start   # 本节点自身命中（修：原用 sum(counts)，跨节点共享 counts 时各节点头部显示的是「累计到此」的 running total）
    return head.replace("__REDCOUNT__", str(node_total)) + "".join(body), node_total

# ───────────────────────── 读取器（Claude Code 专属）─────────────────────────
_NOISE = [
    re.compile(r"<system-reminder>.*?</system-reminder>", re.S),
    re.compile(r"<local-command-[^>]*>.*?</local-command-[^>]*>", re.S),
    re.compile(r"<command-[^>]*>.*?</command-[^>]*>", re.S),
    re.compile(r"<command-[^>]*/>", re.S),
]
def _strip_noise(t):
    for p in _NOISE:
        t = p.sub("", t)
    return t.strip()

def _fmt_ts(iso):
    if not iso:
        return ""
    return iso.replace("T", " ").replace("Z", "")[:19]

def entries_from_objs(objs):
    """已（去重+按时间排序后的）原始记录列表 → 统一原语 entries。
    供 read_claudecode 和 build_session_tree.py 共用，避免解析逻辑重复漂移。"""
    fmt_ts = _fmt_ts
    out = []
    for o in objs:
        msg = o.get("message", {}); role = msg.get("role"); c = msg.get("content")
        ts = fmt_ts(o.get("timestamp", ""))
        if role == "user":
            if isinstance(c, list) and any(isinstance(x, dict) and x.get("type") == "tool_result" for x in c):
                results = []
                for x in c:
                    if isinstance(x, dict) and x.get("type") == "tool_result":
                        cont = x.get("content", "")
                        if isinstance(cont, list):
                            cont = "\n".join(cc.get("text", "") if isinstance(cc, dict) else str(cc) for cc in cont)
                        results.append(str(cont))
                if out and out[-1]["role"] == "agent":
                    out[-1]["results"].extend(results)
                else:
                    out.append({"role": "agent", "time": ts, "text": "", "tools": [], "results": results})
                continue
            text = c if isinstance(c, str) else "\n".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text")
            text = _strip_noise(text or "")
            if text:
                out.append({"role": "human", "time": ts, "text": text, "tools": [], "results": []})
        elif role == "assistant":
            if not isinstance(c, list):
                c = [{"type": "text", "text": str(c)}]
            text_parts, tools = [], []
            for x in c:
                if not isinstance(x, dict):
                    continue
                if x.get("type") == "text" and x.get("text", "").strip():
                    text_parts.append(x["text"])
                elif x.get("type") == "tool_use":
                    try:
                        inp = json.dumps(x.get("input", {}), ensure_ascii=False, indent=2)
                    except Exception:
                        inp = str(x.get("input", {}))
                    tools.append((x.get("name", ""), inp))
            if text_parts or tools:
                out.append({"role": "agent", "time": ts, "text": "\n".join(text_parts), "tools": tools, "results": []})
    return out

def read_claudecode(paths):
    """读若干 .jsonl → 去重(按 uuid) + 按时间排序 → entries_from_objs。"""
    seen, objs = set(), []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                uid = o.get("uuid") or (json.dumps(o.get("message", {}), ensure_ascii=False)[:200] + str(o.get("timestamp")))
                if uid in seen:
                    continue
                seen.add(uid)
                objs.append(o)
    objs.sort(key=lambda o: o.get("timestamp") or "")
    return entries_from_objs(objs)

# ───────────────────────── 工具：定位会话 json ─────────────────────────
def find_jsonl(sid):
    hits = glob.glob(os.path.expanduser(f"~/.claude/projects/*/{sid}.jsonl"))
    if not hits:
        sys.exit(f"✗ 找不到会话 json：~/.claude/projects/*/{sid}.jsonl")
    return hits[0]

PERSON_RE = re.compile(r"^[\w一-鿿\-]+$")
SID_RE = re.compile(r"^[\w\-]+$")
META_RE = re.compile(r"<!--\s*worklog-meta(.*?)-->", re.S)

def find_session_folder(person_dir, sid):
    for log in glob.glob(os.path.join(person_dir, "*", "工作日志.md")):
        m = META_RE.search(open(log, encoding="utf-8").read())
        if m and any(sid == s.strip() for line in m.group(1).splitlines()
                     if line.strip().lower().startswith("sessions:")
                     for s in line.split(":", 1)[1].split(",")):
            return os.path.dirname(log)
    return None

def report(counts):
    total = sum(counts.values())
    print(f"── 脱敏报告 ── 共 {total} 处", file=sys.stderr)
    for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"   {k}: {v}", file=sys.stderr)
    if total == 0:
        print("   （未命中已知敏感模式；注意正则脱敏非 100% 保证）", file=sys.stderr)

def main():
    HERE = os.path.dirname(os.path.abspath(__file__))
    # 档案根：.claude/skills/team-collab/scripts/ → 仓库根 → 团队协作记录/智能体工作日志
    repo = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
    archive = os.path.join(repo, "团队协作记录", "智能体工作日志")

    ap = argparse.ArgumentParser(description="Claude Code 对话记录 → 统一 md（脱敏，无 AI 提炼）")
    ap.add_argument("--person")
    ap.add_argument("--session")
    ap.add_argument("--merge")
    ap.add_argument("--out")
    ap.add_argument("--stdout", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--scan", help="只扫描指定文件的敏感命中（不改文件、不转换）")
    ap.add_argument("--mirror", help="镜像模式：给一个主会话 id，把它+所有子智能体(含 workflow)按原生结构批量转换")
    ap.add_argument("--out-dir", help="镜像模式的输出根目录")
    args = ap.parse_args()

    # 镜像模式：主会话 + 所有子智能体 → 统一 md，1:1 镜像 Claude Code 原生结构
    if args.mirror:
        if not PERSON_RE.match(args.person or ""):
            sys.exit(f"✗ --person 非法：{args.person!r}")
        if not args.out_dir:
            sys.exit("✗ --mirror 需要 --out-dir 指定输出根目录")
        sid = args.mirror
        hits = glob.glob(os.path.expanduser(f"~/.claude/projects/*/{sid}.jsonl"))
        if not hits:
            sys.exit(f"✗ 找不到主会话 json：{sid}")
        projdir = os.path.dirname(hits[0])
        counts = {}; n = 0

        def mirror_one(src, out, sids, extra):
            nonlocal n
            entries = read_claudecode([src])
            if not entries:
                return
            md, _ = render(entries, args.person, "Claude Code", sids, counts, extra, source_files=[os.path.normpath(src)])
            os.makedirs(os.path.dirname(out), exist_ok=True)
            open(out, "w", encoding="utf-8").write(md)
            n += 1

        # 主会话
        mirror_one(hits[0], os.path.join(args.out_dir, f"{sid}.md"), [sid], None)
        # 直接子智能体
        for f in sorted(glob.glob(os.path.join(projdir, sid, "subagents", "*.jsonl"))):
            aid = os.path.basename(f)[:-6]
            meta = {}
            mp = f[:-6] + ".meta.json"
            if os.path.exists(mp):
                try: meta = json.load(open(mp, encoding="utf-8"))
                except Exception: pass
            extra = [f"子智能体: {aid}", f"类型: {meta.get('agentType','')}", f"任务: {meta.get('description','')}"]
            mirror_one(f, os.path.join(args.out_dir, sid, "subagents", aid + ".md"), [aid], extra)
        # workflow 子智能体
        for f in sorted(glob.glob(os.path.join(projdir, sid, "subagents", "workflows", "*", "*.jsonl"))):
            aid = os.path.basename(f)[:-6]
            if aid.endswith(".meta"):
                continue
            wf = os.path.basename(os.path.dirname(f))
            meta = {}
            mp = f[:-6] + ".meta.json"
            if os.path.exists(mp):
                try: meta = json.load(open(mp, encoding="utf-8"))
                except Exception: pass
            extra = [f"workflow: {wf}", f"子智能体: {aid}", f"任务: {meta.get('description','')}"]
            mirror_one(f, os.path.join(args.out_dir, sid, "subagents", "workflows", wf, aid + ".md"), [aid], extra)

        report(counts)
        print(f"✓ 镜像完成：{n} 个对话 → {os.path.relpath(args.out_dir)}（主会话 {sid[:8]}…）")
        return

    # 扫描模式：检查现有文件是否含敏感信息
    if args.scan:
        counts = {}
        redact(open(args.scan, encoding="utf-8").read(), counts)
        report(counts)
        return

    if not PERSON_RE.match(args.person or ""):
        sys.exit(f"✗ --person 非法（防路径穿越）：{args.person!r}")
    if args.merge:
        sids = [s.strip() for s in args.merge.split(",") if s.strip()]
    else:
        sid = args.session or os.environ.get("CLAUDE_CODE_SESSION_ID")
        if not sid:
            sys.exit("✗ 拿不到 session-id：设 $CLAUDE_CODE_SESSION_ID 或传 --session/--merge")
        sids = [sid]
    for s in sids:
        if not SID_RE.match(s):
            sys.exit(f"✗ session-id 非法：{s!r}")

    src_paths = [os.path.normpath(find_jsonl(s)) for s in sids]
    entries = read_claudecode(src_paths)
    if not entries:
        sys.exit("✗ 没解析到对话内容")
    counts = {}
    md, total = render(entries, args.person, "Claude Code", sids, counts, source_files=src_paths)

    if args.stdout:
        try:
            sys.stdout.write(md)
        except BrokenPipeError:
            pass
        report(counts)
        return

    out = args.out
    if not out:
        person_dir = os.path.join(archive, args.person)
        folder = find_session_folder(person_dir, sids[-1]) or os.path.join(person_dir, f"{datetime.now():%Y-%m-%d}_{sids[-1][:8]}")
        os.makedirs(folder, exist_ok=True)
        out = os.path.join(folder, "完整对话记录.md")
    if os.path.exists(out) and not args.force:
        report(counts)
        sys.exit(f"✗ 目标已存在（不覆盖）：{out}\n  确认脱敏报告后加 --force 覆盖，或 --out/--stdout。")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write(md)
    print(f"✓ 已生成统一格式完整对话记录（{len(md.encode('utf-8'))//1024} KB，脱敏 {total} 处）")
    print(f"  写入: {os.path.relpath(out, repo)}")
    report(counts)
    print("  提醒: 先看脱敏报告，确认无误再按 git 纪律提交。", file=sys.stderr)

if __name__ == "__main__":
    main()
