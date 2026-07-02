#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""团队协作记录 · 帖子格式 gate

校验 `团队协作记录/NNN-*.md`（话题帖）是否符合「话题 → 帖 → 回复」模板
（模板与规则见 team-collab skill：references/posting.md）。
不合格 → 打印问题清单 + 指向 skill，退出码 1；合格 → 退出码 0。

这个 gate 要抓的真实 bug（不是"文件存在就算过"）：
  - 把多件事揉成一条流水账、没有 `## 帖` 结构
  - 某个帖漏了 ① 想做什么 / ② 方案 / 💬 回复
  - 状态值乱填（不是 🟢/⏳/✅/⏸）
  - 回复没按 `> [名字 · 日期]` 署名
  - 文件名编号与标题话题号不一致、或 README 索引漏登记

用法：
  python3 check_posts.py                      # 校验 团队协作记录/ 下所有 NNN-*.md
  python3 check_posts.py 团队协作记录/001-x.md  # 只校验指定文件（pre-commit 用）
"""
import os, re, sys, glob

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
RECORDS = os.path.join(REPO, "团队协作记录")
SKILL_HINT = ".claude/skills/team-collab/references/posting.md"

TOPIC_FILE_RE = re.compile(r"^\d{3}-.*\.md$")
H1_RE = re.compile(r"^#\s*话题\s*(\d{3})\s*·\s*\S.*")
META_RE = re.compile(r"<!--\s*topic-meta(.*?)-->", re.S)
POST_RE = re.compile(r"^##\s*帖\s*(\d+)\s*·\s*\S.*", re.M)
STATUS_TOKENS = ["🟢", "⏳", "✅", "⏸"]
META_KEYS = ["id", "创建", "发起人", "状态", "摘要"]

def check_file(path):
    errs = []
    name = os.path.basename(path)
    txt = open(path, encoding="utf-8").read()
    lines = txt.splitlines()

    # 1. H1：第一行必须是 `# 话题 NNN · 标题`
    first = next((l for l in lines if l.strip()), "")
    m = H1_RE.match(first.strip())
    topic_id = None
    if not m:
        errs.append("第一行必须是 `# 话题 NNN · 标题`")
    else:
        topic_id = m.group(1)
        if name[:3] != topic_id:
            errs.append(f"文件名编号 {name[:3]} 与标题话题号 {topic_id} 不一致")

    # 2. topic-meta 块 + 必填字段 + 状态值
    mm = META_RE.search(txt)
    if not mm:
        errs.append("缺 `<!-- topic-meta ... -->` 元信息块")
    else:
        meta = mm.group(1)
        for k in META_KEYS:
            if not re.search(rf"(?m)^\s*{k}\s*:", meta):
                errs.append(f"topic-meta 缺字段 `{k}:`")
        sm = re.search(r"(?m)^\s*状态\s*:\s*(.+)$", meta)
        if sm and not any(t in sm.group(1) for t in STATUS_TOKENS):
            errs.append(f"topic-meta 状态值非法：`{sm.group(1).strip()}`（须含 🟢/⏳/✅/⏸ 之一）")

    # 3. 至少一个 `## 帖 N · 标题`，且每帖结构完整
    posts = list(POST_RE.finditer(txt))
    if not posts:
        errs.append("至少要有一个 `## 帖 N · 标题`（话题下没有任何帖）")
    for i, pm in enumerate(posts):
        start = pm.end()
        end = posts[i + 1].start() if i + 1 < len(posts) else len(txt)
        body = txt[start:end]
        tag = f"帖 {pm.group(1)}"
        if not re.search(r"(?m)^\s*-\s*\*\*发帖\*\*：\s*\[.+\].*·.*\d", body):
            errs.append(f"{tag} 缺 `- **发帖**：[名] · 日期`")
        sm = re.search(r"(?m)^\s*-\s*\*\*状态\*\*：\s*(.+)$", body)
        if not sm:
            errs.append(f"{tag} 缺 `- **状态**：…`")
        elif not any(t in sm.group(1) for t in STATUS_TOKENS):
            errs.append(f"{tag} 状态值非法：`{sm.group(1).strip()}`（须含 🟢/⏳/✅/⏸）")
        if "**①" not in body:
            errs.append(f"{tag} 缺 `**① 想做什么**`")
        if "**②" not in body:
            errs.append(f"{tag} 缺 `**② 方案 / 内容**`")
        if "**💬 回复**" not in body:
            errs.append(f"{tag} 缺 `**💬 回复**` 区")

    # 4. 回复署名格式：以 `> [` 开头的（排除引用里的 markdown 链接）须是 `> [名 · 日期]`
    for ln in lines:
        if re.match(r"^>\s*\[", ln) and "](" not in ln and not re.match(r"^>\s*\[.+·.+\]", ln):
            errs.append(f"回复署名格式错：`{ln.strip()}`（须 `> [名字 · YYYY-MM-DD]`）")

    # 5. 一致性：同目录 README.md 的话题索引须登记本话题（dir-local，自测临时目录无 README 则跳过）
    readme = os.path.join(os.path.dirname(path), "README.md")
    if topic_id and os.path.exists(readme):
        if name not in open(readme, encoding="utf-8").read():
            errs.append(f"同目录 README.md 话题索引未登记本话题（应有指向 {name} 的一行）")

    return errs

def main():
    args = sys.argv[1:]
    if args:
        files = [os.path.abspath(a) for a in args if TOPIC_FILE_RE.match(os.path.basename(a))]
    else:
        files = sorted(glob.glob(os.path.join(RECORDS, "[0-9][0-9][0-9]-*.md")))
    if not files:
        print("（没有要校验的话题帖）")
        return 0

    total = 0
    for f in files:
        errs = check_file(f)
        if errs:
            total += len(errs)
            print(f"✗ {os.path.relpath(f, REPO)}")
            for e in errs:
                print(f"    - {e}")
    if total:
        print(f"\n共 {total} 处不符合帖子模板。请按 team-collab skill 重写：{SKILL_HINT}")
        print("（模板：话题=1个md；`# 话题 NNN·标题` + topic-meta + 一个或多个 `## 帖 N`，每帖含 发帖/状态/①/②/💬回复）")
        return 1
    print(f"✓ {len(files)} 个话题帖全部符合模板。")
    return 0

if __name__ == "__main__":
    sys.exit(main())
