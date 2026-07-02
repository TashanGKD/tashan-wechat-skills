# Tashan WeChat Skills

[中文 README](README.zh-CN.md)

An agent-facing skill set (for Claude Code / Cursor and similar) that runs the full **Tashan official-account (WeChat) publishing chain**: drafting, logic self-check, fact verification, illustration planning and generation, proofreading, citation compliance, and final WeChat-ready HTML typesetting. Output follows the writing and layout conventions of the "他山学科交叉" WeChat account of the Tashan Interdisciplinary Innovation Association, University of Chinese Academy of Sciences.

> Every skill is **self-contained**: the `references/` (layout/writing/illustration source docs), `assets/` (footer template images), and `templates/` it needs live inside its own folder. Copy the folder and it works — no external paths.

## Included skills (7)

| Skill | Path | Purpose |
|---|---|---|
| **wechat-article-writer** | [`skills/wechat-article-writer`](skills/wechat-article-writer/SKILL.md) | Entry point: write an official-account article; forwards to document-pipeline, outputs WeChat HTML. |
| **document-pipeline** | [`skills/document-pipeline`](skills/document-pipeline/SKILL.md) | Engine: research → draft → logic check → fact check → figures → proofread → citation → format conversion. |
| **article-proofreading** | [`skills/article-proofreading`](skills/article-proofreading/SKILL.md) | Review pass: AI-tone, 4 title error types, absolute phrasing, structure, conclusion completeness. |
| **ai-image-generator** | [`skills/ai-image-generator`](skills/ai-image-generator/SKILL.md) | Illustration capability: model choice, DashScope calls, multi-angle, style library, figure index. |
| **article-image-angles** | [`skills/article-image-angles`](skills/article-image-angles/SKILL.md) | Analyze candidate illustration angles and draft prompts. |
| **article-image-styles** | [`skills/article-image-styles`](skills/article-image-styles/SKILL.md) | Manage the illustration style library (S01–S10, etc.). |
| **article-review-tracker** | [`skills/article-review-tracker`](skills/article-review-tracker/SKILL.md) | Track editorial feedback and resolve it item by item. |

**Chain**: `wechat-article-writer` (entry) → `document-pipeline` (engine) → calls `article-proofreading` + `ai-image-generator` (enhanced by `article-image-angles` / `article-image-styles`).

## Quick start

```bash
git clone https://github.com/TashanGKD/tashan-wechat-skills.git
cd tashan-wechat-skills

# Install into Claude Code (project-level) — each skill is self-contained, just copy it
mkdir -p <your-project>/.claude/skills && cp -R skills/* <your-project>/.claude/skills/
# or Cursor: cp -R skills/* <your-project>/.cursor/skills/
# or: bash scripts/install.sh <target-dir>
```

Start a **new agent session** (skills are scanned at session start), then trigger the entry skill in natural language ("write a WeChat article" / "写一篇公众号文章").

Paths like `references/…`, `assets/…`, `templates/…` inside a `SKILL.md` resolve **relative to that skill's own folder** — keep each skill folder intact.

Illustration needs an API key: `export DASHSCOPE_API_KEY=...` (see [SECURITY.md](SECURITY.md)). Without it, only the illustration step is skipped; writing/proofreading/HTML still work.

## Updating

```bash
cd tashan-wechat-skills && git pull
```

If you copied skills into a skill dir, re-run the install/copy (or `scripts/install.sh <target> --force`); if you symlinked, `git pull` is enough. Read [CHANGELOG.md](CHANGELOG.md) first — versioning follows [SemVer](https://semver.org/); MAJOR means breaking changes. To improve the skills, contribute back via PR — see [CONTRIBUTING.md](CONTRIBUTING.md).

## Layout

```text
.
├── skills/            # 7 self-contained skills (SKILL.md + references/ + assets/ + templates/)
├── docs/              # usage & update guide
├── scripts/install.sh # install into a skill dir
├── manifest.yml       # skill manifest
├── CHANGELOG.md CONTRIBUTING.md SECURITY.md LICENSE
└── README.md README.zh-CN.md
```

## Credits

Produced by the Tashan Interdisciplinary Innovation Association (UCAS) · Tashan AI Team. Site: tashan.ac.cn. Licensed under [MIT](LICENSE).
