#!/usr/bin/env python3
from __future__ import annotations
import datetime as dt, html, json, re, urllib.request, xml.etree.ElementTree as ET
from pathlib import Path
from email.utils import parsedate_to_datetime

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
BLOG_URL = CONFIG['blog_url'].rstrip('/')
FEEDS = [BLOG_URL+'/feed', BLOG_URL+'/rss']
UA = 'Mozilla/5.0 (compatible; HosakaHatenaGitHubPages/1.0)'

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def lname(tag): return tag.split('}',1)[-1]

def ctext(el, names):
    for c in el.iter():
        if lname(c.tag) in names and c.text:
            return c.text.strip()
    return ''

def parse_date(s):
    s=(s or '').strip()
    try:
        if s.endswith('Z'): s=s[:-1]+'+00:00'
        d=dt.datetime.fromisoformat(s)
    except Exception:
        d=parsedate_to_datetime(s)
    if d.tzinfo is None: d=d.replace(tzinfo=dt.timezone.utc)
    return d.astimezone(dt.timezone(dt.timedelta(hours=9)))

def clean_text(s):
    s=re.sub(r'<script[\s\S]*?</script>',' ',s or '',flags=re.I)
    s=re.sub(r'<style[\s\S]*?</style>',' ',s,flags=re.I)
    s=re.sub(r'<[^>]+>',' ',s)
    s=html.unescape(s)
    s=re.sub(r'\s+',' ',s).strip()
    return s[:130]+'…' if len(s)>130 else s

def first_image(s):
    m=re.search(r'<img[^>]+src=["\']([^"\']+)["\']',s or '',flags=re.I)
    return html.unescape(m.group(1)) if m else ''

def make(title,url,published,body):
    return {'title':title or 'タイトルなし','url':url,'date':parse_date(published),'description':clean_text(body),'image':first_image(body)}

def parse_feed(data):
    root=ET.fromstring(data); kind=lname(root.tag).lower(); out=[]
    if kind=='feed':
        for e in [x for x in root if lname(x.tag)=='entry']:
            title=ctext(e,('title',)); published=ctext(e,('published','updated')); body=ctext(e,('content','summary')); url=''
            for x in e.iter():
                if lname(x.tag)=='link' and x.attrib.get('href') and x.attrib.get('rel','alternate')=='alternate':
                    url=x.attrib['href']; break
            if not url: url=ctext(e,('id',))
            if url: out.append(make(title,url,published,body))
    elif kind=='rss':
        channel=next((x for x in root if lname(x.tag)=='channel'),None)
        if channel is None: raise RuntimeError('RSS channel not found')
        for e in [x for x in channel if lname(x.tag)=='item']:
            out.append(make(ctext(e,('title',)),ctext(e,('link',)),ctext(e,('pubDate','date')),ctext(e,('encoded','description'))))
    return out

def months(today):
    prev=today.replace(day=1)-dt.timedelta(days=1)
    return [(prev.year,prev.month),(today.year,today.month)]

def card(a):
    img=(f'<img class="thumbnail" src="{html.escape(a["image"],quote=True)}" alt="" loading="lazy">' if a['image'] else '<div class="thumbnail no-image">画像なし</div>')
    return f'''<a class="article-card" href="{html.escape(a['url'],quote=True)}" target="_blank" rel="noopener noreferrer">
<div class="profile-row"><div class="avatar">保</div><div><div class="profile-name">{html.escape(CONFIG.get('profile_name','活動情報'))}</div><div class="profile-id">id:{html.escape(CONFIG.get('profile_id','hosakaeiji'))}</div></div><div class="hatena-name">Hatena Blog</div></div>
<div class="article-content"><div><h3>{html.escape(a['title'])}</h3><p>{html.escape(a['description'])}</p></div>{img}</div>
<div class="article-date">{a['date'].strftime('%Y-%m-%d %H:%M')}</div><div class="read-more">続きを読む</div></a>'''

def build(articles):
    sections=[]
    for y,m in months(dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()):
        items=[a for a in articles if a['date'].year==y and a['date'].month==m]
        items.sort(key=lambda x:x['date'],reverse=True)
        items=items[:int(CONFIG.get('max_articles_per_month',20))]
        body=''.join(card(a) for a in items) or f'<div class="empty">{y}年{m}月の記事はありません。</div>'
        sections.append(f'<section><h2>{m}月の情報</h2>{body}</section>')
    updated=dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).strftime('%Y-%m-%d %H:%M')
    return f'''<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(CONFIG.get('site_title','活動情報'))}</title><style>
*{{box-sizing:border-box}}html,body{{margin:0;padding:0;background:#fff}}body{{padding:18px;color:#222;font-family:-apple-system,BlinkMacSystemFont,"Yu Gothic","Meiryo",sans-serif}}main{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:36px;max-width:1160px;margin:0 auto}}h2{{margin:0 0 22px;text-align:center;font-size:27px}}.article-card{{display:block;margin-bottom:22px;padding:16px;border:1px solid #d8d8d8;border-radius:7px;color:inherit;text-decoration:none;background:#fff}}.article-card:hover{{box-shadow:0 5px 16px rgba(0,0,0,.14)}}.profile-row{{display:flex;align-items:center;margin-bottom:12px}}.avatar{{width:43px;height:43px;margin-right:10px;border-radius:50%;display:grid;place-items:center;background:#d9ecf7;color:#0b6ea8;font-weight:700}}.profile-name{{color:#0878bf;font-weight:700}}.profile-id{{color:#666;font-size:13px}}.hatena-name{{margin-left:auto;color:#888;font-size:13px}}.article-content{{display:grid;grid-template-columns:minmax(0,1fr) 110px;gap:15px}}h3{{margin:0 0 9px;font-size:20px;line-height:1.45}}p{{margin:0;color:#444;font-size:14px;line-height:1.7}}.thumbnail{{width:110px;height:110px;object-fit:cover;border-radius:3px;background:#eee}}.no-image{{display:grid;place-items:center;color:#888;font-size:12px}}.article-date{{margin-top:14px;color:#777;font-size:13px}}.read-more{{margin-top:7px;color:#0878bf;font-size:13px;font-weight:700}}.empty{{padding:30px 15px;border:1px dashed #bbb;border-radius:6px;text-align:center;color:#777}}footer{{max-width:1160px;margin:8px auto 0;text-align:right;color:#888;font-size:12px}}@media(max-width:760px){{body{{padding:12px}}main{{grid-template-columns:1fr;gap:32px}}h2{{font-size:23px}}h3{{font-size:18px}}.article-content{{grid-template-columns:minmax(0,1fr) 90px}}.thumbnail{{width:90px;height:90px}}}}
</style></head><body><main>{''.join(sections)}</main><footer>最終更新：{updated}</footer></body></html>'''

def main():
    articles=[]; err=None
    for u in FEEDS:
        try:
            articles=parse_feed(fetch(u))
            if articles: break
        except Exception as e: err=e
    if not articles: raise RuntimeError(f'フィード取得失敗: {err}')
    (ROOT/'index.html').write_text(build(articles),encoding='utf-8')
    print('updated',len(articles))
if __name__=='__main__': main()
