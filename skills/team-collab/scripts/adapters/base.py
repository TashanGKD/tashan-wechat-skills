#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""adapters/base.py —— 源适配器契约（框架无关核心 ⟷ 每框架适配器 的接缝）。

核心只认"规范化记录"。本轮内部规范化格式 = **Claude Code 的记录 dict**
（`{uuid, parentUuid, timestamp, message:{role,content}, ...}`）——CC 是恒等；Codex/Cursor 在后续步骤
把各自原始记录翻译成这个 dict 形状（含把 content 归一成 CC 的 text/tool_use/tool_result），
这样现有的 tree 构建 / entries_from_objs / render 无需为每家改写。

适配器三件事（框架相关面全在这里）：
  discover(repo_root, src=None) -> [会话文件路径]   本框架属于该项目的会话（跨 cwd）
  load(paths)                   -> (objs, sess)      解析+去重成规范化记录 dict
  sid_of(path)                  -> session-id        从会话文件反解 sid（真源指针 / --list 用）
元数据：name（来源工具显示名）、lineage_mode（"tree"=真实分叉 | "linear"=一会话一链）。
"""
import os
import urllib.parse


def canonicalize(path):
    """把各家的路径归一成可比较形式：URL 解码（Cursor folder）→ 剥 \\?\ 前缀（Codex import source_path）→
    剥 file:// → 分隔符统一 → casefold（大小写不敏感）。三家 discover 都过它再比对，消除口径分裂。"""
    if not path:
        return ""
    p = urllib.parse.unquote(path)
    if p.startswith("\\\\?\\"):
        p = p[4:]
    if p.startswith("file:///"):
        p = p[8:]
    elif p.startswith("file://"):
        p = p[7:]
    p = p.replace("\\", "/").rstrip("/")
    return p.casefold()


def under(child, root):
    """child 是否 == root 或在 root 之下（子目录上卷判据）。二者都应先 canonicalize。"""
    if not child or not root:
        return False
    return child == root or child.startswith(root + "/")


class SourceAdapter:
    name = "?"
    lineage_mode = "tree"

    def discover(self, repo_root, src=None):
        raise NotImplementedError

    def load(self, paths):
        """→ (objs, sess): objs={记录key: 规范化 dict}, sess={记录key: {session-id,...}}。"""
        raise NotImplementedError

    def sid_of(self, path):
        return os.path.basename(path)[:-6]

    def mtime_of(self, ref):
        """会话"文件"的修改时间，供 --if-stale 新鲜度判断。默认按真实文件路径取 mtime；
        令牌型来源（如 Cursor 的 composerId 非路径）需 override，否则裸 getmtime 会 WinError 2。"""
        return os.path.getmtime(ref) if os.path.exists(ref) else 0.0
