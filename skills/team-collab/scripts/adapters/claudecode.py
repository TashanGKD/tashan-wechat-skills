#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""adapters/claudecode.py —— Claude Code 源适配器。

发现 `~/.claude/projects/` 下引用了本仓库的会话（跨 cwd），按 uuid 去重解析成规范化记录。
规范化格式 = CC 原生记录 dict，故 load 基本是恒等（读 jsonl + 去重）。
（发现/解析逻辑原在 build_session_tree.py，Step 1 切分迁入这里，作为"框架相关面"的落点；
 行为与原 discover_session_files / load_records 逐字一致，黄金回归保证零改变。）
"""
import glob, json, os
from collections import defaultdict
from .base import SourceAdapter

PROJECTS = os.path.expanduser("~/.claude/projects")


def _uuids_of(f):
    s = set()
    try:
        for ln in open(f, encoding="utf-8", errors="ignore"):
            ln = ln.strip()
            if not ln:
                continue
            try:
                o = json.loads(ln)
            except Exception:
                continue
            if o.get("uuid"):
                s.add(o["uuid"])
    except OSError:
        pass
    return s


class ClaudeCodeAdapter(SourceAdapter):
    name = "Claude Code"
    lineage_mode = "tree"

    def discover(self, repo_root, src=None):
        """扫 ~/.claude/projects/ 下所有项目目录，返回属于本仓库的会话 jsonl 路径（跨 cwd）。
        两轮判定：① 内容引用了仓库目录名（marker）的会话；② 与①共享 uuid 的会话（续接/分支复制记录，
        捕捉早于仓库命名的起源会话）。--src 时只扫单个目录。"""
        if src:
            return sorted(glob.glob(os.path.join(src, "*.jsonl")))
        marker = os.path.basename(repo_root)
        allf = sorted(glob.glob(os.path.join(PROJECTS, "*", "*.jsonl")))
        matched, rest = [], []
        for f in allf:
            try:
                hit = marker in open(f, encoding="utf-8", errors="ignore").read()
            except OSError:
                hit = False
            (matched if hit else rest).append(f)
        known = set()
        for f in matched:
            known |= _uuids_of(f)
        extra = [f for f in rest if _uuids_of(f) & known]
        return sorted(matched + extra)

    def load(self, paths):
        """读若干会话 jsonl（可跨项目目录），按 uuid 去重，返回 (objs_by_uuid, sessions_by_uuid)。"""
        objs, sess = {}, defaultdict(set)
        for f in paths:
            sid = os.path.basename(f)[:-6]
            for line in open(f, encoding="utf-8"):
                line = line.strip()
                if not line:
                    continue
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                u = o.get("uuid")
                if not u:
                    continue
                if u not in objs:
                    objs[u] = o
                sess[u].add(sid)
        return objs, sess
