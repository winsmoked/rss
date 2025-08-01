#!/usr/bin/env python3
# binance_rss.py  –  resilient HTML-embedded JSON scraper
#
# Generates launchpool.xml (RSS 2.0).  Works on GitHub Actions or locally.

import datetime as dt
import html, json, re, sys
from collections import deque
from pathlib import Path

import requests
from feedgen.feed import FeedGenerator
from requests.adapters import HTTPAdapter, Retry

# ---------------------------------------------------------------------
# 1  Config
# ---------------------------------------------------------------------
CATALOG_ID = 48  # 新数字货币及交易对上新
PAGE_URL   = f"https://www.binance.com/zh-CN/support/announcement/list/{CATALOG_ID}"

HEADERS = {
    "User-Agent":  "Mozilla/5.0 (X11; Linux x86_64)",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.binance.com/zh-CN/support/announcement",
}

session = requests.Session()
session.mount(
    "https://",
    HTTPAdapter(max_retries=Retry(total=4, backoff_factor=1,
                                  status_forcelist=[502, 503, 504]))
)

# ---------------------------------------------------------------------
# 2  Download page and pull embedded JSON
# ---------------------------------------------------------------------
try:
    html_resp = session.get(PAGE_URL, headers=HEADERS, timeout=20)
    html_resp.raise_for_status()
except Exception as e:
    sys.exit(f"[error] Failed to download page: {e}")

pattern = r'<script[^>]+id="(?:__APP_DATA__|__NEXT_DATA__)"[^>]*>(.*?)</script>'
m = re.search(pattern, html_resp.text, re.S)
if not m:
    sys.exit("[error] Could not locate embedded JSON (<script id='__APP_DATA__' | '__NEXT_DATA__'>)")

try:
    raw_json = html.unescape(m.group(1))
    root     = json.loads(raw_json)
except Exception as e:
    sys.exit(f"[error] Embedded JSON unparseable: {e}")

# ---------------------------------------------------------------------
# 3  Locate the article list generically
# ---------------------------------------------------------------------
def find_article_list(node):
    """Breadth-first search for a list of dicts with title+code keys."""
    queue = deque([node])
    while queue:
        cur = queue.popleft()
        if isinstance(cur, list) and cur and isinstance(cur[0], dict):
            if "title" in cur[0] and "code" in cur[0]:
                return cur
        if isinstance(cur, dict):
            queue.extend(cur.values())
        elif isinstance(cur, list):
            queue.extend(cur)
    return None

articles = find_article_list(root)
if not articles:
    sys.exit("[error] Embedded JSON does not contain an article list")

# ---------------------------------------------------------------------
# 4  Build RSS
# ---------------------------------------------------------------------
fg = FeedGenerator()
fg.title("Binance – 新数字货币及交易对上新 (scraped)")
fg.link(href=PAGE_URL)
fg.description("Automated RSS feed built by GitHub Actions (HTML-embedded JSON)")
fg.language("zh-cn")

for art in articles[:20]:                       # keep latest 20
    ts_ms = art.get("releaseDate") or art.get("timeRelease")  # fallback key names
    pub_dt = dt.datetime.utcfromtimestamp(ts_ms / 1000) if ts_ms else dt.datetime.utcnow()

    fe = fg.add_entry()
    fe.title(art["title"])
    fe.link(href=f'https://www.binance.com/zh-CN/support/announcement/{art["code"]}')
    fe.guid(art["code"])
    fe.pubDate(pub_dt)

out = Path("launchpool.xml")
fg.rss_file(out, pretty=True)
print(f"[ok] Wrote {out.resolve()}")
