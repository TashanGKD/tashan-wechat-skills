#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_wechat.py — 抓取单篇微信公众号文章为带 frontmatter 的 Markdown。

用法:
  python fetch_wechat.py "https://mp.weixin.qq.com/s/xxxxx" --source "他山学科交叉" --out ./output
  python fetch_wechat.py URL --playwright        # 前两种策略失败时用无头浏览器

策略（依次尝试，直到拿到正文）:
  1. 移动端微信 UA（最轻量，国内 IP 常有效）
  2. PC Chrome UA（备选）
  3. playwright 无头浏览器（最可靠，需 pip install playwright && playwright install chromium）

设计原则:
  - 只抓取用户有权访问的公开文章（如本组织自有公众号），用于归档/研究，非批量商用转载。
  - 不含任何 cookie / 凭据；如需登录态，另见 references/抓取方案.md。
  - 命中"环境异常"拦截页时明确报错，提示改用 --playwright 或手动收集链接。
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, re, sys

MOBILE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 "
             "(KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.0")
PC_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
         "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

BLOCK_MARKERS = ("环境异常", "去验证", "verify_status")  # 拦截页特征（避免误判正文里的 __mp_verify）


def _looks_blocked(html: str) -> bool:
    head = html[:4000]
    return ("环境异常" in head) or ("完成验证" in head)


def _extract(html: str):
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        sys.exit("需要 beautifulsoup4：pip install beautifulsoup4 lxml markdownify requests")
    soup = BeautifulSoup(html, "lxml")
    title = ""
    for sel in ("#activity-name", "h1.rich_media_title", "meta[property='og:title']"):
        el = soup.select_one(sel)
        if el:
            title = (el.get("content") or el.get_text()).strip()
            if title:
                break
    author = ""
    a = soup.select_one("#js_name") or soup.select_one("meta[name='author']")
    if a:
        author = (a.get("content") or a.get_text()).strip()
    body = soup.select_one("#js_content") or soup.select_one("div.rich_media_content")
    if body is None:
        return title, author, None
    try:
        from markdownify import markdownify as md
        content = md(str(body), heading_style="ATX").strip()
    except ImportError:
        content = body.get_text("\n", strip=True)
    content = re.sub(r"\n{3,}", "\n\n", content)
    return title, author, content


def _via_requests(url: str, ua: str):
    import requests
    r = requests.get(url, headers={"User-Agent": ua,
                                   "Referer": "https://mp.weixin.qq.com/"}, timeout=30)
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def _via_playwright(url: str):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        # 内置 chromium 在部分 Windows 上崩溃，可改 channel="msedge"
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=MOBILE_UA)
        page.goto(url, wait_until="networkidle", timeout=60000)
        html = page.content()
        browser.close()
        return html


def fetch(url: str, use_playwright: bool = False):
    attempts = [] if use_playwright else [("mobile", MOBILE_UA), ("pc", PC_UA)]
    for name, ua in attempts:
        try:
            html = _via_requests(url, ua)
        except Exception as e:
            print(f"[{name}] 请求失败: {e}", file=sys.stderr); continue
        if _looks_blocked(html):
            print(f"[{name}] 命中拦截页（环境异常）", file=sys.stderr); continue
        title, author, content = _extract(html)
        if content:
            return title, author, content
        print(f"[{name}] 未提取到正文", file=sys.stderr)
    # fallback / 显式指定
    try:
        html = _via_playwright(url)
        title, author, content = _extract(html)
        if content:
            return title, author, content
    except Exception as e:
        print(f"[playwright] {e}", file=sys.stderr)
    sys.exit("抓取失败：可能被拦截。请改用 --playwright，或按 references/抓取方案.md 手动收集链接。")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--source", default="", help="公众号名称，用于归类")
    ap.add_argument("--out", default="./output", help="输出目录")
    ap.add_argument("--playwright", action="store_true", help="直接用无头浏览器")
    args = ap.parse_args()

    title, author, content = fetch(args.url, args.playwright)
    today = datetime.date.today().isoformat()
    uid = hashlib.sha256(args.url.encode()).hexdigest()[:6]
    safe = re.sub(r"[\\/:*?\"<>|\n]", " ", title or uid).strip()[:60]
    sub = args.source or "未分类"
    outdir = os.path.join(args.out, sub)
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, f"{today}_{safe}_{uid}.md")
    fm = (f"---\ntitle: \"{(title or '').replace(chr(34), '')}\"\n"
          f"source: \"{args.source}\"\nsource_type: wechat\n"
          f"url: \"{args.url}\"\nauthor: \"{author}\"\n"
          f"scraped_at: \"{datetime.datetime.now().isoformat()}\"\n---\n\n")
    with open(path, "w", encoding="utf-8") as f:
        f.write(fm + f"# {title}\n\n" + content + f"\n\n---\n*原文：[{args.source or '微信'}]({args.url})*\n")
    print("已保存:", path)


if __name__ == "__main__":
    main()
