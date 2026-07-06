#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""adapters —— 源适配器注册表（框架无关核心据此发现/解析各框架会话）。

Step 1 只注册 cc；codex/cursor 在 Step 2/3 注册。核心用 get_adapters(names) 取实例。
"""
from .base import SourceAdapter
from .claudecode import ClaudeCodeAdapter
from .codex import CodexAdapter
from .cursor import CursorAdapter

_REGISTRY = {"cc": ClaudeCodeAdapter, "codex": CodexAdapter, "cursor": CursorAdapter}

def available():
    return list(_REGISTRY)

def get_adapters(names=None):
    names = names if names else list(_REGISTRY)
    out = []
    for n in names:
        n = n.strip()
        if n not in _REGISTRY:
            raise SystemExit(f"✗ 未知适配器: {n!r}（可用: {', '.join(_REGISTRY)}）")
        out.append(_REGISTRY[n]())
    return out
