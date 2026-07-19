#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import datetime as dt
import html
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))

BLOG_URL = CONFIG["blog_url"].rstrip("/")
FEEDS = [BLOG_URL + "/feed", BLOG_URL + "/rss"]
UA = "Mozilla/5.0 (compatible; HosakaHatenaGitHubPages/2.0)"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read()


def local_name(tag: str) -> str:
    return tag.split("}", 1)[-1]


def child_text(element: ET.Element, names: tuple[str, ...]) -> str:
    for child in element.iter():
        if local_name(child.tag) in names and child.text:
            return child.text.strip()
    return ""


def parse_date(value: str) -> dt.datetime:
    value = (value or "").strip()
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        result = dt.datetime.fromisoformat(value)
    except Exception:
        result = parsedate_to_datetime(value)

    if result.tzinfo is None:
        result = result.replace(tzinfo=dt.timezone.utc)

    return result.astimezone(dt.timezone(dt.timedelta(hours=9)))


def clean_text(value: str) -> str:
    value = re.sub(r"<script[\s\S]*?</script>", " ", value or "", flags=re.I)
    value = re.sub(r"<style[\s\S]*?</style>", " ", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:130] + "…" if len(value) > 130 else value


def first_image(value: str) -> str:
    patterns = [
        r'<img[^>]+src=["\']([^"\']+)["\']',
        r'<img[^>]+data-src=["\']([^"\']+)["\']',
        r'https?://cdn-ak\.f\.st-hatena\.com/images/fotolife/[^"\'>\s]+',
    ]
    for pattern in patterns:
        match = re.search(pattern, value or "", flags=re.I)
        if match:
            return html.unescape(match.group(1) if match.lastindex else match.group(0))
    return ""


def make_article(title: str, url: str, published: str, body: str) -> dict:
    return {
        "title": title or "タイトルなし",
        "url": url,
        "date": parse_date(published),
        "description": clean_text(body),
        "image": first_image(body),
    }


def parse_feed(data: bytes) -> list[dict]:
    root = ET.fromstring(data)
    kind = local_name(root.tag).lower()
    articles: list[dict] = []

    if kind == "feed":
        entries = [item for item in root if local_name(item.tag) == "entry"]
        for entry in entries:
            title = child_text(entry, ("title",))
            published = child_text(entry, ("published", "updated"))
            body = child_text(entry, ("content", "summary"))
            url = ""

            for item in entry.iter():
                if (
                    local_name(item.tag) == "link"
                    and item.attrib.get("href")
                    and item.attrib.get("rel", "alternate") == "alternate"
                ):
                    url = item.attrib["href"]
                    break

            if not url:
                url = child_text(entry, ("id",))

            if url:
                articles.append(make_article(title, url, published, body))

    elif kind == "rss":
        channel = next(
            (item for item in root if local_name(item.tag) == "channel"),
            None,
        )
        if channel is None:
            raise RuntimeError("RSS channel not found")

        entries = [item for item in channel if local_name(item.tag) == "item"]
        for entry in entries:
            articles.append(
                make_article(
                    child_text(entry, ("title",)),
                    child_text(entry, ("link",)),
                    child_text(entry, ("pubDate", "date")),
                    child_text(entry, ("encoded", "description")),
                )
            )

    return articles


def target_months(today: dt.date) -> list[tuple[int, int]]:
    previous = today.replace(day=1) - dt.timedelta(days=1)
    return [(previous.year, previous.month), (today.year, today.month)]


def article_card(article: dict) -> str:
    image_html = (
        f'<img class="thumbnail" src="{html.escape(article["image"], quote=True)}" '
        f'alt="" loading="lazy" referrerpolicy="no-referrer">'
        if article["image"]
        else '<div class="thumbnail no-image">画像なし</div>'
    )

    return f"""
<a class="article-card" href="{html.escape(article['url'], quote=True)}"
   target="_blank" rel="noopener noreferrer">
  <div class="profile-row">
    <div class="avatar">保</div>
    <div>
      <div class="profile-name">{html.escape(CONFIG.get('profile_name', '活動情報'))}</div>
      <div class="profile-id">id:{html.escape(CONFIG.get('profile_id', 'hosakaeiji'))}</div>
    </div>
    <div class="hatena">Hatena Blog</div>
  </div>

  <div class="article-content">
    <div>
      <h3>{html.escape(article['title'])}</h3>
      <p>{html.escape(article['description'])}</p>
    </div>
    {image_html}
  </div>

  <div class="date">{article['date'].strftime('%Y-%m-%d %H:%M')}</div>
  <div class="read-more">続きを読む</div>
</a>
"""


def build_page(articles: list[dict]) -> str:
    sections = []

    for year, month in target_months(
        dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()
    ):
        monthly = [
            article
            for article in articles
            if article["date"].year == year and article["date"].month == month
        ]
        monthly.sort(key=lambda article: article["date"], reverse=True)
        monthly = monthly[: int(CONFIG.get("max_articles_per_month", 20))]

        cards = "".join(article_card(article) for article in monthly)
        if not cards:
            cards = f'<div class="empty">{year}年{month}月の記事はありません。</div>'

        sections.append(
            f"""
<section>
  <h2>{month}月の情報</h2>
  {cards}
</section>
"""
        )

    updated = dt.datetime.now(
        dt.timezone(dt.timedelta(hours=9))
    ).strftime("%Y-%m-%d %H:%M")

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(CONFIG.get('site_title', '活動情報'))}</title>
<style>
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  padding: 18px;
  color: #222;
  background: #fff;
  font-family: -apple-system, BlinkMacSystemFont, "Yu Gothic", "Meiryo", sans-serif;
}}
main {{
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 36px;
  max-width: 1160px;
  margin: 0 auto;
}}
h2 {{
  margin: 0 0 22px;
  text-align: center;
  font-size: 27px;
}}
.article-card {{
  display: block;
  margin-bottom: 22px;
  padding: 16px;
  color: inherit;
  text-decoration: none;
  background: #fff;
  border: 1px solid #d8d8d8;
  border-radius: 7px;
}}
.article-card:hover {{
  box-shadow: 0 5px 16px rgba(0,0,0,.14);
}}
.profile-row {{
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}}
.avatar {{
  width: 43px;
  height: 43px;
  margin-right: 10px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: #d9ecf7;
  color: #0b6ea8;
  font-weight: 700;
}}
.profile-name {{ color: #0878bf; font-weight: 700; }}
.profile-id {{ color: #666; font-size: 13px; }}
.hatena {{ margin-left: auto; color: #888; font-size: 13px; }}
.article-content {{
  display: grid;
  grid-template-columns: minmax(0,1fr) 110px;
  gap: 15px;
}}
h3 {{
  margin: 0 0 9px;
  font-size: 20px;
  line-height: 1.45;
}}
p {{
  margin: 0;
  color: #444;
  font-size: 14px;
  line-height: 1.7;
}}
.thumbnail {{
  width: 110px;
  height: 110px;
  object-fit: cover;
  border-radius: 4px;
  background: #eee;
}}
.no-image {{
  display: grid;
  place-items: center;
  color: #888;
  font-size: 12px;
}}
.date {{ margin-top: 14px; color: #777; font-size: 13px; }}
.read-more {{ margin-top: 7px; color: #0878bf; font-size: 13px; font-weight: 700; }}
.empty {{
  padding: 30px 15px;
  text-align: center;
  color: #777;
  border: 1px dashed #bbb;
  border-radius: 6px;
}}
.footer {{
  max-width: 1160px;
  margin: 8px auto 0;
  text-align: right;
  color: #888;
  font-size: 12px;
}}
@media (max-width: 760px) {{
  main {{ grid-template-columns: 1fr; gap: 32px; }}
  .article-content {{ grid-template-columns: minmax(0,1fr) 90px; }}
  .thumbnail {{ width: 90px; height: 90px; }}
}}
</style>
</head>
<body>
<main>
{''.join(sections)}
</main>
<div class="footer">最終更新：{updated}</div>
</body>
</html>
"""


def main() -> None:
    articles = []
    last_error = None

    for feed_url in FEEDS:
        try:
            articles = parse_feed(fetch(feed_url))
            if articles:
                break
        except Exception as exc:
            last_error = exc

    if not articles:
        raise RuntimeError(f"フィード取得失敗: {last_error}")

    (ROOT / "index.html").write_text(
        build_page(articles),
        encoding="utf-8",
    )
    print("updated", len(articles))


if __name__ == "__main__":
    main()
