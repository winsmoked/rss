#!/usr/bin/env python3
# binance_rss.py  –  HTML-scraping version (no API key needed)

import datetime
import re
import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from requests.adapters import HTTPAdapter, Retry

# -------- 1  Target page --------
PAGE = "https://www.binance.com/zh-CN/support/announcement/list/48"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.binance.com/zh-CN/support/announcement",
}

SESSION = requests.Session()
SESSION.mount(
    "https://",
    HTTPAdapter(
        max_retries=Retry(total=4, backoff_factor=1, status_forcelist=[502, 503, 504])
    ),
)

# -------- 2  Scrape page --------
resp = SESSION.get(PAGE, headers=HEADERS, timeout=20)
resp.raise_for_status()

soup = BeautifulSoup(resp.text, "html.parser")

# Every announcement card lives inside an <a> that starts with /zh-CN/support/announcement/
cards = soup.select('a[href^="/zh-CN/support/announcement/"]')

articles = []
for a in cards:
    href = a["href"].split("?")[0]  # strip tracking params
    title = a.get_text(" ", strip=True)
    # Try to find a YYYY-MM-DD inside the anchor (date div is nested)
    m = re.search(r"\d{4}-\d{2}-\d{2}", a.text)
    date_str = m.group(0) if m else None
    pubdate = (
        datetime.datetime.strptime(date_str, "%Y-%m-%d")
        if date_str
        else datetime.datetime.utcnow()
    )
    articles.append(
        {
            "title": title,
            "link": f"https://www.binance.com{href}",
            "pubDate": pubdate,
            "guid": href.rsplit("/", 1)[-1],
        }
    )

# De-duplicate & keep newest 20
seen = set()
unique = []
for art in articles:
    if art["guid"] not in seen:
        unique.append(art)
        seen.add(art["guid"])
unique = unique[:20]

# -------- 3  Build RSS --------
fg = FeedGenerator()
fg.title("Binance – 新数字货币及交易对上新 (scraped)")
fg.link(href=PAGE)
fg.description("Automated RSS feed built by GitHub Actions (HTML scraping)")
fg.language("zh-cn")

for art in unique:
    fe = fg.add_entry()
    fe.title(art["title"])
    fe.link(href=art["link"])
    fe.guid(art["guid"])
    fe.pubDate(art["pubDate"])

fg.rss_file("launchpool.xml", pretty=True)
