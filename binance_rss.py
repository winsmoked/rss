#!/usr/bin/env python3
# binance_rss.py  –  scrape embedded JSON from Binance catalog page
#
# Generates launchpool.xml in the repo root.  Designed for GitHub Actions
# but can run anywhere Python ≥3.9 is available.

import datetime as dt
import html, json, re, sys
from pathlib import Path

import requests
from feedgen.feed import FeedGenerator
from requests.adapters import HTTPAdapter, Retry

# ---------------------------------------------------------------------
# 1  HTTP setup
# ---------------------------------------------------------------------
CATALOG_ID = 48  # “新数字货币及交易对上新”
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
# 2  Fetch HTML and extract the JSON blob
# ---------------------------------------------------------------------
try:
    html_resp = session.get(PAGE_URL, headers=HEADERS, timeout=20)
    html_resp.raise_for_status()
except Exception as e:
    sys.exit(f"[error] Failed to download page: {e}")

match = re.search(
    r'<script[^>]+id="__APP_DATA__"[^>]*>(.*?)</script>', 
    html_resp.text, re.S
)
if not match:
    sys.exit("[error] Could not locate __APP_DATA__ JSON in page HTML")

try:
    raw_json = html.unescape(match.group(1))
    app_data = json.loads(raw_json)
    # Path observed 2025-08-01; adjust if Binance restructures:
    articles = app_data["pageData"]["catalogArticles"]["articles"]
except Exception as e:
    sys.exit(f"[error] Failed to parse embedded JSON: {e}")

if not articles:
    sys.exit("[error] No articles found in embedded JSON")

# ---------------------------------------------------------------------
# 3  Build RSS feed
# ---------------------------------------------------------------------
fg = FeedGenerator()
fg.title("Binance – 新数字货币及交易对上新 (scraped)")
fg.link(href=PAGE_URL)
fg.description("Automated RSS feed built by GitHub Actions (HTML-embedded JSON)")
fg.language("zh-cn")

for art in articles:
    # Fallback logic for date field differences:
    ts_ms = art.get("releaseDate") or art.get("releaseDateTimestamp")
    pub_date = dt.datetime.utcfromtimestamp(ts_ms / 1000) if ts_ms else dt.datetime.utcnow()

    fe = fg.add_entry()
    fe.title(art["title"])
    fe.link(href=f'https://www.binance.com/zh-CN/support/announcement/{art["code"]}')
    fe.guid(art["code"])
    fe.pubDate(pub_date)

# ---------------------------------------------------------------------
# 4  Write launchpool.xml
# ---------------------------------------------------------------------
out = Path("launchpool.xml")
fg.rss_file(out, pretty=True)
print(f"[ok] Wrote {out.resolve()}")
