---
name: wechat-article-crawler
description: 抓取/归档微信公众号文章为带 frontmatter 的 Markdown。当用户想「抓取/爬取/采集/归档 公众号文章」「把这篇 mp.weixin 文章存下来 / 打不开被环境异常拦了」「扒某公众号的历史推文」「建公众号内容语料/情报库」「WebFetch 打不开微信文章」时，都用本 skill——它汇总了 6 种抓取方案（官方 API / 手动链接 / mitmproxy / werss RSS / 搜狗 / 无头浏览器）的可行性与踩坑，并自带单篇抓取脚本绕过「环境异常」拦截。也是 wechat-article-writer 的上游：把归档文章当写作样本/风格对照。
---

# 微信公众号文章抓取 / 归档

把公开的公众号文章（本组织自有号，或用户有权访问的公开文章）稳定地抓成本地 Markdown，用于归档、写作样本、内容/风格分析。核心难点是 `mp.weixin.qq.com` 的**"环境异常"拦截**——非微信环境直接抓常被挡（这也是 WebFetch 打不开微信文章的原因）。本 skill 给出经实战验证的方案选择 + 自带脚本。

## 先选方案（不同目标走不同路）

| 你的目标 | 走哪条 |
|---|---|
| **抓 1 篇 / 几篇已知 URL** | 直接用 `scripts/fetch_wechat.py`（三策略绕拦截） |
| **补全某号全部历史** | 方案四「手动收集链接」最稳（见 `references/抓取方案.md`）→ 对每条链接跑脚本 |
| **持续订阅新文** | 方案五 werss RSS 桥（仅近期、可能不稳） |
| **自有号 + 有管理员权限** | 方案一 官方 API（需企业认证）——最完整 |
| **只是想读被拦的那篇** | 脚本加 `--playwright` |

完整的 6 种方案、可行性排序、Cookie/证书踩坑、合规边界 → **必读 `references/抓取方案.md`**。

## 单篇抓取（最常用）

```bash
python scripts/fetch_wechat.py "https://mp.weixin.qq.com/s/xxxxx" --source "他山学科交叉" --out ./output
# 被"环境异常"拦时：加 --playwright（需 pip install playwright && playwright install chromium）
```

依赖：`pip install requests beautifulsoup4 lxml markdownify`（playwright 可选）。
脚本按 移动端 UA → PC UA → playwright 依次尝试，命中拦截页会显式报错并提示回落到手动链接。

## 批量 / 历史归档

微信没有稳定的"列出全部历史"公开接口（网页版已封、getmsg 需 wxsid）。所以补全历史的稳妥做法是**方案四**：

1. 手机微信进公众号主页 → 逐篇「...」→「复制链接」→ 发到「文件传输助手」
2. 电脑端把链接每行一个存进 `links.txt`
3. 循环对每条链接跑 `fetch_wechat.py`

```bash
while read url; do [ -n "$url" ] && python scripts/fetch_wechat.py "$url" --source "公众号名" --out ./output; done < links.txt
```

## 输出格式

每篇一个 `.md`，YAML frontmatter（title/source/url/author/scraped_at）+ 正文 + 原文链接。去重用 URL 的 sha256 前缀。样例见 `references/他山文章存档/`。

## 已归档：他山自有文章（可直接复用）

`references/存档索引.md` + `references/他山文章存档/`：他山学科交叉公众号已归档的 **14 篇自有文章**（科教 / 动态 / 招新 / 预告 / 回顾各类型齐全）。用途：

- **写作样本 / 风格对照**：交给 `wechat-article-writer` / `document-pipeline` 当"他山风格"参照，或喂 `article-proofreading` 校准。
- **排版参照**：科教类的摘要/章节/引用写法可对照。

> 只收录**他山自有**文章。第三方媒体（量子位、机器之心等）全文因版权**不入本仓库**——研究外部媒体请在本地分析，不公开重发。

## 合规与边界（重要）

- 只抓**公开**且你有权访问的文章；控制频率、尊重站点；不做大规模商用转载。
- 凭据（AppSecret、Cookie）一律从环境变量/安全配置读取，**绝不写进 skill 或提交仓库**（见 `references/抓取方案.md` 方案一/三）。
- 第三方全文只本地留存与分析，不放进公开仓库。

## 与其他 skill 的关系

抓取归档（本 skill）→ 沉淀写作样本/风格 → `wechat-article-writer` 写新稿 → `article-proofreading` 审稿。即"抓取分析 → 发文"闭环的上游。
