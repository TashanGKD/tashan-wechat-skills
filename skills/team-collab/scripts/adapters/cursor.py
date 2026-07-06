#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""adapters/cursor.py —— Cursor 源适配器（把 Cursor composer 会话翻译成 CC 形状 dict）。

Cursor 聊天存 SQLite：内容在 globalStorage/state.vscdb 的 cursorDiskKV
（composerData:<id> 骨架 + bubbleId:<id>:<bid> 逐条消息）；工作区↔会话链在 workspace 库
ItemTable['composer.composerData'].allComposers。归属：workspace.json.folder 经 canonicalize 在项目根下。
一个 composer = 一条线性链（一根），id=f"{composerId}#{i}"。DB 只读打开（mode=ro&immutable=1，防 Cursor 运行时锁）。
解析异常 → 跳过该 composer、不崩（尽力而为、版本敏感）。
"""
import glob, json, os, sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from .base import SourceAdapter, canonicalize, under

UROOT = os.path.expanduser("~/AppData/Roaming/Cursor/User")
GLOB_DB = os.path.join(UROOT, "globalStorage", "state.vscdb")


def _ro(path):
    return sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)


def _iso(ts):
    """两种形态都接受：**逐 bubble 的 createdAt 常是 ISO 串**（如 '2025-10-17T18:25:29.325Z'，直接用，render 会格式化）；
    **composer 级 createdAt 是毫秒 epoch**（数字，转 ISO 兜底）。原实现只当毫秒 epoch → 对 ISO 串 int() 报错→丢时间
    （实测 42% Cursor 记录时间为空，acceptance 发现）。"""
    if ts is None:
        return ""
    if isinstance(ts, str):
        return ts                            # 逐 bubble createdAt：已是 ISO 串
    try:
        return datetime.fromtimestamp(int(ts) / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    except Exception:
        return ""


class CursorAdapter(SourceAdapter):
    name = "Cursor"
    lineage_mode = "linear"

    def sid_of(self, path):
        return path                          # discover 返回的就是 composerId

    def mtime_of(self, ref):
        # composerId 非文件路径 → 用 globalStorage DB 的 mtime 作"任何 Cursor 变化"的粗代理（供 --if-stale）
        return os.path.getmtime(GLOB_DB) if os.path.exists(GLOB_DB) else 0.0

    def discover(self, repo_root, src=None):
        root = canonicalize(repo_root)
        ids = []
        for wj in glob.glob(os.path.join(UROOT, "workspaceStorage", "*", "workspace.json")):
            try:
                folder = json.load(open(wj, encoding="utf-8")).get("folder", "")
            except Exception:
                continue
            if not under(canonicalize(folder), root):
                continue
            wdb = os.path.join(os.path.dirname(wj), "state.vscdb")
            if not os.path.exists(wdb):
                continue
            try:
                wc = _ro(wdb)
                row = wc.execute("SELECT value FROM ItemTable WHERE key='composer.composerData'").fetchone()
                wc.close()
                if row and row[0]:
                    for comp in (json.loads(row[0]).get("allComposers") or []):
                        if comp.get("composerId"):
                            ids.append(comp["composerId"])
            except Exception:
                continue
        return sorted(set(ids))

    def _to_obj(self, bd):
        role = "user" if bd.get("type") == 1 else "assistant"
        text = (bd.get("text") or "").strip()
        if len(text) > 20000:                # 截断超大 bubble（同 Codex 的理由），保头部
            text = text[:20000] + f"\n…[截断 {len(text) - 20000} 字符]"
        content = []
        if text:
            content.append({"type": "text", "text": text})
        for tr in (bd.get("toolResults") or []):     # agentic 工具活动 → 保住"用了什么工具"
            if isinstance(tr, dict):
                content.append({"type": "tool_use", "name": tr.get("toolName") or tr.get("name") or "tool", "input": {}})
        return {"message": {"role": role, "content": content}} if content else None

    def load(self, composer_ids):
        objs, sess = {}, defaultdict(set)
        if not composer_ids or not os.path.exists(GLOB_DB):
            return objs, sess
        try:
            db = _ro(GLOB_DB)
        except Exception:
            return objs, sess
        for cid in composer_ids:
            try:
                row = db.execute("SELECT value FROM cursorDiskKV WHERE key=?", (f"composerData:{cid}",)).fetchone()
                if not row or not row[0]:
                    continue
                cd = json.loads(row[0])
                prev, i = None, 0
                for h in (cd.get("fullConversationHeadersOnly") or []):
                    bid = h.get("bubbleId") if isinstance(h, dict) else None
                    if not bid:
                        continue
                    br = db.execute("SELECT value FROM cursorDiskKV WHERE key=?", (f"bubbleId:{cid}:{bid}",)).fetchone()
                    if not br or not br[0]:
                        continue
                    norm = self._to_obj(json.loads(br[0]))
                    if norm is None:
                        continue
                    bd_ts = json.loads(br[0]).get("createdAt")
                    rid = f"{cid}#{i}"
                    norm["uuid"] = rid
                    norm["parentUuid"] = prev
                    norm["timestamp"] = _iso(bd_ts or cd.get("createdAt"))
                    norm["_source_tool"] = "Cursor"
                    norm["_source_file"] = os.path.normpath(GLOB_DB)
                    norm["_session_id"] = cid
                    if i == 0:
                        norm["_seg_key_hint"] = f"cursor:{cid}#0"
                    objs[rid] = norm
                    sess[rid].add(cid)
                    prev = rid
                    i += 1
            except Exception:
                continue                     # 坏 composer → 跳过、不崩
        db.close()
        return objs, sess
