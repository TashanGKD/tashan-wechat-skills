<!-- Logo -->
<p align="center">
  <a href="https://tashan.ac.cn" target="_blank" rel="noopener noreferrer">
    <img src="docs/assets/tashan.svg" alt="Tashan Logo" width="280" />
  </a>
</p>

<!-- Title -->
<p align="center">
  <strong>Tashan WeChat Publishing Skills</strong><br>
  <em>他山公众号写作技能包</em>
</p>

<!-- Nav -->
<p align="center">
  <a href="#overview">Overview</a> •
  <a href="#included-skills">Skills</a> •
  <a href="#quick-start">Quick start</a> •
  <a href="#updating">Updating</a> •
  <a href="#ecosystem">Ecosystem</a> •
  <a href="#contributing">Contributing</a> •
  <a href="README.md">中文</a>
</p>

<p align="center">
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT" /></a>
</p>

> **Core use**: typeset an existing manuscript (word / md / txt) and export it as Tashan WeChat-account HTML — auto-adds the content summary, fixes citation formatting, applies the footer template. **Proofreading is optional.** Writing from scratch is also supported.

---

## Overview

Tashan continuously publishes content around "interdisciplinary exchange x AI for Science". This project is the agent-facing tooling layer for Tashan's **content production / WeChat publishing** step: it reliably turns a finished manuscript into a deliverable that follows the layout and writing conventions of the "他山学科交叉" WeChat account, removing the manual typesetting cost between "written" and "publishable".

**Core ideas**

- **Manuscript in**: the core use is typeset-and-export — give it word/md/txt, get WeChat HTML, wording preserved paragraph by paragraph.
- **Spec as source of truth**: layout / writing / illustration rules come from the bundled `references/` manuals, so output style stays consistent.
- **Self-contained distribution**: each skill ships its own `references/`, `assets/`, `templates/`; copy the folder and it works — no external paths.

**Who it's for**

- Association publicity / the Tashan AI team: turn science and event drafts into WeChat HTML fast.
- Agents on Claude Code / Cursor: clone and call the whole chain.
- Partners who need to reproduce the unified Tashan WeChat style.

---

## Included skills

**8 skills**: the WeChat publishing chain plus crawling/archival.

| Skill | Path | Purpose |
|---|---|---|
| **wechat-article-writer** | [`skills/wechat-article-writer`](skills/wechat-article-writer/SKILL.md) | Entry: typeset a manuscript to WeChat HTML (core); also writes from scratch. |
| **document-pipeline** | [`skills/document-pipeline`](skills/document-pipeline/SKILL.md) | Engine: research → draft → logic → fact check → figures → (optional) proofread → citation → format conversion. |
| **article-proofreading** | [`skills/article-proofreading`](skills/article-proofreading/SKILL.md) | Review (optional): AI-tone, 4 title error types, absolute phrasing, structure, conclusion. |
| **ai-image-generator** | [`skills/ai-image-generator`](skills/ai-image-generator/SKILL.md) | Illustration layer: model choice, DashScope calls, multi-angle, style library, figure index. |
| **article-image-angles** | [`skills/article-image-angles`](skills/article-image-angles/SKILL.md) | Analyze illustration angles and draft prompts. |
| **article-image-styles** | [`skills/article-image-styles`](skills/article-image-styles/SKILL.md) | Manage the illustration style library (S01–S10). |
| **article-review-tracker** | [`skills/article-review-tracker`](skills/article-review-tracker/SKILL.md) | Track editorial feedback and resolve it item by item. |
| **wechat-article-crawler** | [`skills/wechat-article-crawler`](skills/wechat-article-crawler/SKILL.md) | Crawl/archive WeChat articles (6 methods + script); ships Tashan's own archived articles; upstream of the writing chain. |

**Chain**: `wechat-article-writer` (entry) → `document-pipeline` (engine) → (optional) `article-proofreading` + `ai-image-generator` (enhanced by `article-image-angles` / `article-image-styles`).

> Each skill is **self-contained**: `references/…`, `assets/…`, `templates/…` in a `SKILL.md` resolve relative to that skill's folder — keep each folder intact.

---

## Quick start

```bash
git clone https://github.com/TashanGKD/tashan-wechat-skills.git
cd tashan-wechat-skills

# Claude Code (project-level)
mkdir -p <your-project>/.claude/skills && cp -R skills/* <your-project>/.claude/skills/
# Cursor: cp -R skills/* <your-project>/.cursor/skills/
# or: bash scripts/install.sh <target-dir>   # default ./.claude/skills, --force to overwrite
```

Start a **new agent session** (skills are scanned at session start). Then hand over a manuscript and say "typeset this into WeChat HTML" / "把这篇排版成公众号 HTML". Input can be word(.docx)/md/txt; `.docx` is extracted to markdown first. Proofreading is optional — ask for it explicitly.

Illustration needs a key: `export DASHSCOPE_API_KEY=...` (see [SECURITY.md](SECURITY.md)). Without it, only the illustration step is skipped.

---

## Repository layout

```
tashan-wechat-skills/
├── docs/assets/tashan.svg   # unified logo
├── docs/                    # usage & update guide
├── skills/                  # 7 self-contained skills
├── scripts/install.sh       # install into a skill dir
├── manifest.yml             # skill manifest
├── CHANGELOG.md CONTRIBUTING.md SECURITY.md LICENSE
├── README.md                # Chinese (primary)
└── README.en.md             # English (this file)
```

---

## Updating

```bash
cd tashan-wechat-skills && git pull
```

If you copied skills, re-run `scripts/install.sh <target> --force`; if you symlinked, `git pull` is enough. Read [CHANGELOG.md](CHANGELOG.md) first — SemVer, MAJOR means breaking. Improve via PR — see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Ecosystem

Part of the Tashan (TashanGKD) open-source ecosystem — the **content-production / publishing tooling** layer.

| Repo | Role | Link |
|---|---|---|
| **tashan-wechat-skills** | WeChat writing / typesetting skills (this repo) | current |
| tashan-research-skills | Academic research skills | [TashanGKD/tashan-research-skills](https://github.com/TashanGKD/tashan-research-skills) |
| Tashan-TopicLab | Multi-expert roundtable platform | [TashanGKD/Tashan-TopicLab](https://github.com/TashanGKD/Tashan-TopicLab) |
| Tashan site | Association homepage | [tashan.ac.cn](https://tashan.ac.cn) |

---

## Contributing

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). Keep skills self-contained (resources under each skill's `references/`/`assets/`/`templates/`); never hardcode secrets.

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

---

## License

MIT License. See [LICENSE](LICENSE) for details.

Produced by the Tashan Interdisciplinary Innovation Association (UCAS) · Tashan AI Team.
