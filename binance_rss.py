#!/usr/bin/env python3
"""
Generate an RSS feed for
https://www.binance.com/zh-CN/support/announcement/list/48
(新数字货币及交易对上新).  No API key needed – we parse the HTML that
Binance ships to the browser.

Usage (local test):
    python binance_rss.py
GitHub Actions: keep the same workflow; the script still writes
launchpool.xml in the repo root.
"""
import datetime as dt
import json
import re
import requests
from feedgen.feed import FeedGenerator

URL         = "https://www.binance.com/zh-CN/support/announcement/list/48"
FEED_FILE   = "launchpool.xml"
HEADERS     = {
    "User-Agent": (
        "Mozilla/5.0 (RSS scraper; +https://github.com/<your-repo>)"
    )
}


# ───────────────────────── helpers ──────────────────────────
def fetch_html() -> str:
    resp = requests.get(URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.text


def extract_app_state(html: str) -> dict:
    """
    Grab the big JSON blob that Next.js drops into a <script>.
    Supports id="__APP_DATA", "__APP_DATA__", or "__NEXT_DATA__".
    """
    m = re.search(
        r'<script[^>]+id="(?:__APP_DATA__?|__NEXT_DATA__)"[^>]*>'
        r'([\s\S]+?)</script>',
        html,
    )
    if not m:
        raise RuntimeError("Embedded JSON script not found – page format changed?")
    return json.loads(m.group(1))


def iter_articles(app_state: dict):
    """
    Yield article dicts that contain at least: title, code, releaseDate.
    Works for both old (`catalogArticles`) and new (`catalogDetail.articles`) schemas.
    """
    loader = app_state.get("appState", {}).get("loader", {})
    for route in loader.get("dataByRouteId", {}).values():
        if route.get("catalogArticles"):
            yield from route["catalogArticles"]
        detail = route.get("catalogDetail")
        if detail and detail.get("articles"):
            yield from detail["articles"]


def build_feed(items):
    fg = FeedGenerator()
    fg.title("Binance – 新数字货币及交易对上新 (scraped)")
    fg.link(href=URL, rel="alternate")
    fg.description("Automated RSS feed built by GitHub Actions (HTML scraping)")
    fg.language("zh-cn")
    for art in items:
        fe = fg.add_entry()
        fe.id(str(art["code"]))
        fe.title(art["title"])
        fe.link(href=f"https://www.binance.com/zh-CN/support/announcement/{art['code']}")
        pub = dt.datetime.fromtimestamp(art["releaseDate"] / 1000, dt.timezone.utc)
        fe.pubDate(pub)

    fg.rss_file(FEED_FILE, pretty=True)


# ────────────────────────── main ────────────────────────────
def main():
    html = fetch_html()
    state = extract_app_state(html)
    articles = sorted(
        iter_articles(state),
        key=lambda x: x["releaseDate"],
        reverse=True,
    )[:50]                    # keep the latest 50
    build_feed(articles)


if __name__ == "__main__":
    main()
