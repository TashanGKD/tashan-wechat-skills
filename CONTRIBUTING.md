# 贡献与更新规范（Contributing）

本仓库是他山公众号写作 skill 的**单一真源**。任何改进请回流到这里，不要只改本地副本（否则各处副本漂移）。规范对齐《他山 GitHub 上传与发布规范》。

## 分支

```
main                 稳定分支，发布从此打 tag
  └── feature/xxx    新功能 / 新 skill
  └── fix/xxx        修复
  └── docs/xxx       仅文档
```

- 不直接 push `main`，走 PR。
- 分支名全小写，`-` 分隔，前缀 `feature/` `fix/` `docs/` `refactor/`。

## Commit 规范（Conventional Commits）

```
<类型>(<范围>): <简短描述>
```

类型：`feat` `fix` `docs` `refactor` `chore` `breaking`。范围用 skill 名，例：

```
feat(wechat-article-writer): 新增轻量活动推送模板
fix(ai-image-generator): 修正 DashScope 轮询超时
docs(readme): 补充 Cursor 安装说明
```

破坏性变更在尾部加：

```
BREAKING CHANGE: <不兼容内容>
迁移方案: <如何从旧版迁移>
```

## 改 skill 的注意事项

1. **保持自包含**：skill 需要的资源放进它自己的 `references/` `assets/` `templates/`，SKILL.md 里用相对该 skill 目录的路径引用。不要引用仓库外或跨 skill 的绝对路径。
2. **不硬编码密钥**：一律读环境变量（见 [SECURITY.md](SECURITY.md)）。提交前自查 `git diff` 无 `sk-`、token、`.env` 值、凭据路径。
3. **frontmatter 完整**：每个 `SKILL.md` 必须有 `name`（kebab-case，与目录同名）和 `description`（含触发词）。
4. **改了 references/ 里的手册**：同步在 `CHANGELOG.md` 记一笔；若三处副本（不同 skill 各带一份）内容需一致，一并更新。
5. **版本**：改动合入后按 [SemVer](https://semver.org/lang/zh-CN/) 更新 `CHANGELOG.md` 与 `manifest.yml` 的 `version`，发布打 tag：`git tag vX.Y.Z -m "Release vX.Y.Z: 一句话"`。

## PR

标题用 commit 类型格式；正文说明「做了什么 / 为什么 / 变动类型 / 是否破坏性 / 是否测过」。至少一人 review（独立开发阶段可自 review，但必须走 PR）。合并优先 Squash。

## 提交前自检清单

- [ ] 每个改动的 skill：frontmatter 完整、路径相对自身目录、资源已放进自己的 references/assets/templates
- [ ] 无硬编码密钥 / 凭据路径 / 内部工作区绝对路径
- [ ] CHANGELOG.md 已更新，破坏性变更含迁移方案
- [ ] `manifest.yml` 与 `skills/` 实际目录一致
