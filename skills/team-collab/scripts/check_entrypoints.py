#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""入口防漂移 gate —— 守住"各工具入口适配器只指真源、不漂移"。

协作 skill 的真源是 `.claude/skills/team-collab/`。各工具的入口（AGENTS.md / .codex wrapper /
README / 团队协作skill说明）都应**只指向真源、不复制规则正文**。本 gate 抓三类真实漂移：
  1. **过时术语**：入口文件里出现已废术语（如 `③ 讨论`，真源已改用 `💬 回复`）——这正是真实踩过的坑。
  2. **死链**：入口引用的 `.claude/skills/team-collab/...` / `references/...` / `scripts/...` 路径不存在。
  3. **断了指针**：本应指向真源的入口（AGENTS.md / .codex wrapper / README）没引用真源 SKILL.md。

不合格 → 打印问题 + 怎么修，退出码 1。
用法：
  python3 check_entrypoints.py                 # 检查所有已知入口文件
  python3 check_entrypoints.py <file> ...      # 只检查指定文件（pre-commit 用）
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
SRC = os.path.join(".claude", "skills", "team-collab")               # 真源（repo 相对）
SRC_SKILL = os.path.join(SRC, "SKILL.md")

# 已废术语登记表：真源演进后，旧说法不许残留在入口文件里（只查入口，不查历史 transcript / 归档）
BLOCKLIST = [
    ("③ 讨论", "现已改为「💬 回复」区（话题→帖→回复 模型）"),
]
# 入口文件（repo 相对）→ 是否必须引用真源 SKILL.md
ENTRYPOINTS = {
    "AGENTS.md": True,
    os.path.join(".codex", "skills", "ai-paperwriter-team-collab", "SKILL.md"): True,
    "README.md": True,
    os.path.join("团队协作记录", "README.md"): False,
    os.path.join("团队协作记录", "团队协作skill说明.md"): False,
}
# 真源路径引用：① 显式 .claude/skills/team-collab/...；② references|scripts/<带扩展名的文件>
# （要求扩展名，避免把口语 "references/scripts" 误判成路径）
PATH_RE = re.compile(r"\.claude/skills/team-collab/[\w./\-]+|(?<![\w./])(?:references|scripts)/[\w\-]+\.[A-Za-z0-9]+")

def check_file(path, require_pointer):
    errs = []
    txt = open(path, encoding="utf-8").read()
    # 1. 过时术语
    for term, why in BLOCKLIST:
        if term in txt:
            errs.append(f"含已废术语 `{term}`（{why}）——入口不该残留旧规则字眼")
    # 2. 死链：引用的真源路径必须存在
    for m in set(PATH_RE.findall(txt)):
        ref = m.rstrip(").,;:`")
        cand = os.path.join(REPO, ref) if ref.startswith(".claude/") else os.path.join(REPO, SRC, ref)
        if not os.path.exists(cand):
            errs.append(f"死链：引用了不存在的真源路径 `{ref}`")
    # 3. 断指针
    if require_pointer and "claude/skills/team-collab/SKILL.md" not in txt:
        errs.append("必须引用真源 `.claude/skills/team-collab/SKILL.md`（这是指向真源的入口，断了就找不到真源）")
    return errs

def main():
    args = sys.argv[1:]
    if args:
        targets = []
        for a in args:
            rel = os.path.relpath(os.path.abspath(a), REPO)
            targets.append((rel, ENTRYPOINTS.get(rel, False)))
    else:
        targets = [(p, req) for p, req in ENTRYPOINTS.items()]

    total = 0
    for rel, req in targets:
        full = os.path.join(REPO, rel)
        if not os.path.exists(full):
            if not sys.argv[1:]:  # 全量模式下入口缺失才告警；指定文件模式跳过非入口
                print(f"✗ {rel}：入口文件缺失")
                total += 1
            continue
        errs = check_file(full, req)
        if errs:
            total += len(errs)
            print(f"✗ {rel}")
            for e in errs:
                print(f"    - {e}")
    if total:
        print(f"\n共 {total} 处入口漂移。入口只能**指向**真源、不复制规则；真源 = {SRC_SKILL}。")
        print("（改规则去真源改；改完把入口里的过时字眼/死链一并修掉。）")
        return 1
    print(f"✓ 入口检查通过（{len(targets)} 个）：无过时术语、无死链、指针完好。")
    return 0

if __name__ == "__main__":
    sys.exit(main())
