#!/usr/bin/env python3
"""
Generate launchpool.xml for
https://www.binance.com/zh-CN/support/announcement/list/48
(数字货币及交易对上新).  Pure HTML-scrape – no API key required.
"""

import datetime as dt
import json
import re
import sys
from pathlib import Path

import requests
from feedgen.feed import FeedGenerator
from requests.adapters import HTTPAdapter, Retry

URL       = "https://www.binance.com/zh-CN/support/announcement/list/48"
FEED_FILE = "launchpool.xml"

HTTP = requests.Session()
HTTP.mount(
    "https://",
    HTTPAdapter(max_retries=Retry(total=4, backoff_factor=1,
                                  status_forcelist=[502, 503, 504]))
)

HEADERS = {"User-Agent": "Mozilla/5.0 (Binance RSS scraper)"}

# ───────────────────────── helpers ──────────────────────────
def fetch_html() -> str:
    r = HTTP.get(URL, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.text


def extract_app_state(html: str) -> dict:
    """
    Capture the JSON blob injected by Next.js.
    Matches id="__APP_DATA", "__APP_DATA_", "__APP_DATA__", or "__NEXT_DATA__".
    Works regardless of attribute order.
    """
    pattern = re.compile(
        r'<script[^>]*id="(?:__APP_DATA(?:_{0,2})|__NEXT_DATA__)"[^>]*>'
        r'([\s\S]+?)</script>',
        re.S | re.I,
    )
    m = pattern.search(html)
    if not m:
        raise RuntimeError("Embedded JSON script not found – page format changed?")
    return json.loads(m.group(1))


def find_article_list(node):
    """Breadth-first search: list of dicts with title+code keys."""
    from collections import deque

    q = deque([node])
    while q:
        cur = q.popleft()
        if isinstance(cur, list) and cur and isinstance(cur[0], dict):
            if {"title", "code"}.issubset(cur[0]):
                return cur
        if isinstance(cur, dict):
            q.extend(cur.values())
        elif isinstance(cur, list):
            q.extend(cur)
    raise RuntimeError("No article list with title+code found in JSON")


# ────────────────────────── main ────────────────────────────
def main():
    html = fetch_html()
    app_state = extract_app_state(html)
    articles = sorted(
        find_article_list(app_state),
        key=lambda a: a.get("releaseDate", 0),
        reverse=True,
    )[:50]                     # latest 50 items

    fg = FeedGenerator()
    fg.title("Binance – 新数字货币及交易对上新 (scraped)")
    fg.link(href=URL)
    fg.description("Automated RSS feed via GitHub Actions (HTML scrape)")
    fg.language("zh-cn")

    for a in articles:
        fe = fg.add_entry()
        fe.id(a["code"])
        fe.title(a["title"])
        fe.link(href=f'https://www.binance.com/zh-CN/support/announcement/{a["code"]}')
        ts = a.get("releaseDate") or a.get("publishDate") or 0
        fe.pubDate(dt.datetime.fromtimestamp(ts / 1000, dt.timezone.utc))

    fg.rss_file(Path(FEED_FILE), pretty=True)
    print(f"[ok] Wrote {FEED_FILE}")


if __name__ == "__main__":
    main()
