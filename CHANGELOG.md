# Changelog

所有版本的变更记录均在此文档。
格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

---

## [Unreleased]
### Added
### Changed
### Fixed
### Breaking

---

## [v1.2.0] - 2026-07-02

### Added
- `docs/assets/tashan.svg`：他山统一 Logo。

### Changed
- README 按他山《01_README 写作规范》整改：新增固定 Logo 头部（居中可点击、宽 280、链 tashan.ac.cn）、标题中英双行、快速导航条、MIT badge、一行定位语、项目简介两段式、生态位置节。
- README 双语命名对齐规范：`README.md` 为中文主版本，英文版改名为 `README.en.md`；移除原 `README.zh-CN.md`。

---

## [v1.1.0] - 2026-07-02

### Changed
- 明确**核心用法**：把已有手稿（word/md/txt）排版并导出为微信 HTML（含加内容摘要、完善引用规范、套底部模板）；`.docx` 先抽取为 markdown 再进流程。
- **审稿改为可选**：`wechat-article-writer`、`document-pipeline`（Stage 7 + R8）、`article-proofreading` 及发布手册核查清单中，审稿由「强制门控」调整为「可选、按需触发」；排版导出类任务默认跳过审稿。
- 入口 `wechat-article-writer` 执行模式新增「排版导出模式」为首要路径；触发词补「排版 / 转 HTML / 导出 HTML」。

---

## [v1.0.0] - 2026-07-02

### Added
- 首次发布他山公众号写作 skill 包，含 7 个 skill：`wechat-article-writer`、`document-pipeline`、`article-proofreading`、`ai-image-generator`、`article-image-angles`、`article-image-styles`、`article-review-tracker`。
- 每个 skill 自包含：`references/`（微信公众号发布手册、写作习惯与风格手册、配图风格库）、`assets/tashan_footer/`（底部模板图）、`templates/`（审稿意见 / 配图索引模板）随各自 skill 目录发布。
- 使用与更新指南（`docs/`）、一键安装脚本（`scripts/install.sh`）、`manifest.yml`。

### Changed
- 由内部 Cursor 工作区适配为通用可分发 skill 包：路径从工作区绝对路径改为「相对各 skill 目录」的自包含引用（`references/`、`assets/`、`templates/`）。
- `document-pipeline` 的 research / 内部经验（开发规范）模式分支标注为默认不启用（面向公众号发文链路）。

### Fixed / Security
- 移除 `document-pipeline` 中一枚硬编码的 DMXAPI 密钥，改为读环境变量。
- 清理随附排版手册中的内部路径与「凭据位置」指引；所有外部服务密钥统一走环境变量。
