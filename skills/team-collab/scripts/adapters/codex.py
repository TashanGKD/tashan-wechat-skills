#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""adapters/codex.py —— Codex 源适配器（把 Codex rollout 记录翻译成 CC 形状 dict）。

Codex 会话：~/.codex/sessions/YYYY/MM/DD/rollout-<ISO>-<session_id>.jsonl，每行 {timestamp,type,payload}。
归属：session_meta.payload.cwd + 全会话 turn_context.cwd 经 canonicalize 落在项目根之下（子目录上卷）。
解析：只取 response_item 流并映射成 CC 形状（message→text、function_call/custom_tool_call→tool_use、
      *_output→tool_result）；跳过 reasoning、developer 轮、非 response_item 事件（session_meta/event_msg/
      turn_context/compacted——compacted 前的原始 response_item 仍在日志里，全渲染即完整、不丢内容）。
血脉：线性、一会话一根，uuid=f"{sid}#{i}"、parentUuid=前一条。
元键：_source_tool/_source_file/_session_id（每条）；根记录带 _seg_key_hint、以及 _parent_thread（worker 子线程）/
      _continues_external（Codex Desktop 导入的 CC 会话 → 供核心接成 CC 节点下分支）。
"""
import glob, json, os, re
from collections import defaultdict
from .base import SourceAdapter, canonicalize, under

CODEX = os.path.expanduser("~/.codex/sessions")
IMPORTS = os.path.expanduser("~/.codex/external_agent_session_imports.json")

# Codex 注入的上下文（非用户真实输入，类比 CC 的 <system-reminder>）——从用户轮剥掉，避免污染 transcript/摘要。
_NOISE = [re.compile(p, re.S) for p in (
    r"<environment_context>.*?</environment_context>",
    r"<INSTRUCTIONS>.*?</INSTRUCTIONS>",
    r"<user_instructions>.*?</user_instructions>",
    r"<permissions[^>]*>.*?</permissions[^>]*>",
)]
def _strip_noise(t):
    for p in _NOISE:
        t = p.sub("", t)
    # Codex IDE 注入：真实请求埋在 "## My request for Codex:" 之后 → 只取其后那段（丢掉 open tabs / URL 等模板前缀）
    m = t.rfind("## My request for Codex:")
    if m != -1:
        t = t[m + len("## My request for Codex:"):]
    t = t.strip()
    # 整段就是注入模板（AGENTS.md / IDE 上下文 / in-app browser，且无真实请求）→ 视为噪声、清空
    for lead in ("# AGENTS.md instructions", "# Context from my IDE setup", "# In app browser"):
        if t.startswith(lead):
            return ""
    return t


def _cap(s, n):
    """截断超大内容（Codex 工具输出可达数百 MB → 单节点 段.md 上百 MB，无法浏览/嵌入、且撑爆内存）。
    保留头部 + 标注截断量。仅 Codex/Cursor 适配器用；CC 保持全文（其会话小、且回归要字节一致）。"""
    if s is None:
        return s
    if not isinstance(s, str):
        s = str(s)
    return s if len(s) <= n else s[:n] + f"\n…[截断 {len(s) - n} 字符]"


def _iter(f):
    for ln in open(f, encoding="utf-8", errors="ignore"):
        ln = ln.strip()
        if not ln:
            continue
        try:
            yield json.loads(ln)
        except Exception:
            continue


def _import_map():
    """imported_thread_id → 被续接的 CC session-id（source_path 剥 \\?\ 去 .jsonl 取 basename）。"""
    m = {}
    try:
        for r in json.load(open(IMPORTS, encoding="utf-8")).get("records", []):
            sp = r.get("source_path", "")
            if sp.startswith("\\\\?\\"):
                sp = sp[4:]
            if sp.lower().endswith(".jsonl") and r.get("imported_thread_id"):
                m[r["imported_thread_id"]] = os.path.basename(sp)[:-6]
    except Exception:
        pass
    return m


def _to_obj(p):
    """一条 response_item.payload → CC 形状 message dict（或 None=跳过）。"""
    t = p.get("type")
    if t == "message":
        role = p.get("role")
        if role == "developer":
            return None                      # 系统/开发者注入，跳过
        parts = []
        for x in (p.get("content") or []):
            xt = x.get("type")
            if xt in ("input_text", "output_text", "text"):
                parts.append(x.get("text", ""))
            elif xt == "input_image":
                parts.append("[图片]")
        text = "\n".join(s for s in parts if s)
        if role == "user":
            text = _strip_noise(text)        # 剥掉 Codex 注入的上下文（AGENTS.md/<environment_context> 等）
            if not text:
                return None                  # 纯注入噪声 → 跳过
        return {"message": {"role": "user" if role == "user" else "assistant",
                            "content": [{"type": "text", "text": _cap(text, 20000)}]}}
    if t in ("function_call", "custom_tool_call", "tool_search_call", "web_search_call"):
        name = p.get("name") or t
        raw = p.get("arguments") if "arguments" in p else p.get("input", p.get("action"))
        raw = _cap(raw, 4000) if isinstance(raw, str) else raw
        try:
            inp = json.loads(raw) if isinstance(raw, str) else (raw or {})
        except Exception:
            inp = raw                        # 截断后可能不是合法 json → 原样留字符串（render 会 dumps 它）
        return {"message": {"role": "assistant",
                            "content": [{"type": "tool_use", "name": name, "input": inp}]}}
    if t in ("function_call_output", "custom_tool_call_output", "tool_search_output"):
        out = p.get("output")
        if out is None and "tools" in p:
            out = json.dumps(p.get("tools"), ensure_ascii=False)
        return {"message": {"role": "user",
                            "content": [{"type": "tool_result", "content": _cap(out if isinstance(out, str) else str(out), 8000)}]}}
    return None                              # reasoning 等 → 跳过


class CodexAdapter(SourceAdapter):
    name = "Codex"
    lineage_mode = "linear"

    def _meta(self, f):
        """读首行 session_meta.payload（None 若无）。"""
        try:
            first = next(_iter(f))
            return first.get("payload", {}) if first.get("type") == "session_meta" else {}
        except StopIteration:
            return {}

    def sid_of(self, path):
        m = self._meta(path)
        return m.get("session_id") or os.path.basename(path)[:-6].split("rollout-")[-1][20:]

    def _belongs(self, f, root_canon):
        m = self._meta(f)
        if under(canonicalize(m.get("cwd")), root_canon):
            return True
        for o in _iter(f):                   # 扫全会话 turn_context.cwd（中途 cd 进项目）
            if o.get("type") == "turn_context" and under(canonicalize(o.get("payload", {}).get("cwd")), root_canon):
                return True
        return False

    def discover(self, repo_root, src=None):
        root_canon = canonicalize(repo_root)
        base = src if src else CODEX
        files = sorted(glob.glob(os.path.join(base, "**", "*.jsonl"), recursive=True))
        return [f for f in files if self._belongs(f, root_canon)]

    def load(self, paths):
        imap = _import_map()
        objs, sess = {}, defaultdict(set)
        for f in paths:
            it = _iter(f)                    # 流式读，不 list()——rollout 可达数百 MB，全量物化会撑爆内存
            try:
                first = next(it)
            except StopIteration:
                continue
            meta = first.get("payload", {}) if first.get("type") == "session_meta" else {}
            sid = meta.get("session_id") or self.sid_of(f)
            src_file = os.path.normpath(f)
            parent_thread = None             # worker 子线程 → 挂父 Codex 会话下
            sub = meta.get("source", {})
            if isinstance(sub, dict) and isinstance(sub.get("subagent"), dict):
                pt = sub["subagent"].get("thread_spawn", {}).get("parent_thread_id")
                if pt:
                    parent_thread = {"tool": "Codex", "ref": pt}
            # Codex Desktop 导入的 CC 会话 → 接成 CC 节点下分支；首个用户轮是导入摘要，裁掉
            cont = {"tool": "Claude Code", "ref": {"sid": imap[sid]}} if sid in imap else None
            st = {"prev": None, "i": 0, "trim": cont is not None}

            def _emit(r):
                if r.get("type") != "response_item":
                    return
                norm = _to_obj(r["payload"])
                if norm is None:
                    return
                if st["trim"] and norm["message"]["role"] == "user":
                    st["trim"] = False       # 裁掉导入摘要首个用户轮
                    return
                i = st["i"]
                rid = f"{sid}#{i}"
                norm["uuid"] = rid
                norm["parentUuid"] = st["prev"]
                norm["timestamp"] = r.get("timestamp", "")
                norm["_source_tool"] = "Codex"
                norm["_source_file"] = src_file
                norm["_session_id"] = sid
                if i == 0:
                    norm["_seg_key_hint"] = f"codex:{sid}#0"
                    if parent_thread:
                        norm["_parent_thread"] = parent_thread
                    if cont:
                        norm["_continues_external"] = cont
                objs[rid] = norm
                sess[rid].add(sid)
                st["prev"] = rid
                st["i"] = i + 1

            if first.get("type") != "session_meta":
                _emit(first)                 # 首行罕见地不是 session_meta → 也当记录
            for r in it:
                _emit(r)
        return objs, sess
