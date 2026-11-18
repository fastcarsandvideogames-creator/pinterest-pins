"""Builds the picks site and Pinterest RSS feeds from pins.json.

Product pages are built for every pin. A pin only enters its board's RSS feed
once its publish time (US Eastern) has passed, so Pinterest picks up a few
new pins per day instead of everything at once. Run on a schedule by
.github/workflows/build.yml.
"""
import json, html, os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from email.utils import format_datetime

SITE = "https://picks.yourecomempire.com"
TAG = "ecom305-20"
NAME = "Home & Gift Picks"
TZ = ZoneInfo("America/New_York")
PIN_VERIFY = os.environ.get("PIN_VERIFY") or "509ece0c29b64baa0280d802719967e3"  # Pinterest domain-claim meta content
BOARDS = {
    "kitchen": "Kitchen Gadgets Worth Buying",
    "gifts": "Holiday Gift Ideas 2026",
    "decor": "Cozy Home Decor Ideas",
    "org": "Home Organization Ideas",
}
DISCLOSURE = "As an Amazon Associate I earn from qualifying purchases. Links on this site are affiliate links."
ROOT = os.path.dirname(os.path.abspath(__file__))

def e(s): return html.escape(s, quote=True)

def amazon(asin): return f"https://www.amazon.com/dp/{asin}?tag={TAG}"

def when(p): return datetime.fromisoformat(p["publish"]).replace(tzinfo=TZ)

CSS = """
*{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:#faf7f2;color:#222}
header{padding:20px;text-align:center;border-bottom:1px solid #eadfd2;background:#fff}header a{color:#8c1c2b;text-decoration:none;font-weight:800;font-size:22px}
main{max-width:980px;margin:0 auto;padding:24px 16px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:18px}
.card{background:#fff;border-radius:14px;overflow:hidden;text-decoration:none;color:#222;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.card img{width:100%;display:block}.card div{padding:10px 12px;font-weight:600;font-size:14px}
.pick{display:grid;grid-template-columns:minmax(0,380px) 1fr;gap:28px;align-items:start}
.pick img{width:100%;border-radius:14px}
h1{font-size:28px;line-height:1.2;margin:0 0 12px}h2{margin:32px 0 12px}
.btn{display:inline-block;background:#f0b23f;color:#111;font-weight:800;padding:14px 26px;border-radius:999px;text-decoration:none;margin:16px 0}
.small{font-size:13px;color:#666}footer{max-width:980px;margin:30px auto;padding:16px;font-size:13px;color:#666;text-align:center}
@media(max-width:700px){.pick{grid-template-columns:1fr}}
"""

def page(title, body, desc="", image="", url=""):
    meta = f'<meta name="p:domain_verify" content="{e(PIN_VERIFY)}">' if PIN_VERIFY else ""
    og = (f'<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">'
          f'<meta property="og:image" content="{e(image)}"><meta property="og:url" content="{e(url)}">') if image else ""
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)}</title>
<meta name="description" content="{e(desc)}">{meta}{og}<style>{CSS}</style></head>
<body><header><a href="/">{NAME}</a></header><main>{body}</main>
<footer>{e(DISCLOSURE)}</footer></body></html>"""

def build():
    pins = json.load(open(os.path.join(ROOT, "pins.json")))
    now = datetime.now(timezone.utc)
    live = [p for p in pins if when(p) <= now]
    os.makedirs(os.path.join(ROOT, "p"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "feeds"), exist_ok=True)
    for p in pins:
        url = f"{SITE}/p/{p['id']}.html"
        img = f"{SITE}/{p['img']}"
        body = f"""<div class="pick"><img src="/{e(p['img'])}" alt="{e(p['name'])}">
<div><p class="small">{e(BOARDS[p['board']])}</p><h1>{e(p['title'])}</h1>
<p><strong>{e(p['name'])}</strong></p><p>{e(p['desc'])}</p>
<a class="btn" href="{e(amazon(p['asin']))}" rel="sponsored nofollow">See it on Amazon</a>
<p class="small">{e(DISCLOSURE)}</p></div></div>"""
        open(os.path.join(ROOT, "p", f"{p['id']}.html"), "w").write(page(p["title"], body, p["desc"], img, url))
    # home page: live picks, newest first, one card per product
    seen, cards = set(), []
    for p in sorted(pins, key=when):
        if p["asin"] in seen: continue
        seen.add(p["asin"])
        cards.append(f'<a class="card" href="/p/{p["id"]}.html"><img src="/{e(p["img"])}" alt="{e(p["name"])}" loading="lazy"><div>{e(p["name"])}</div></a>')
    body = f"<h1>{NAME}</h1><p>Hand-picked kitchen gadgets, gifts, cozy decor and organization finds.</p><div class='grid'>{''.join(cards)}</div>"
    open(os.path.join(ROOT, "index.html"), "w").write(page(NAME, body, "Hand-picked home and gift finds."))
    # one RSS feed per board, newest 50 live pins
    for key, board in BOARDS.items():
        items = []
        for p in sorted([x for x in live if x["board"] == key], key=when, reverse=True)[:50]:
            url = f"{SITE}/p/{p['id']}.html"
            img = f"{SITE}/{p['img']}"
            items.append(f"""<item><title>{e(p['title'])}</title><link>{url}</link><guid isPermaLink="true">{url}</guid>
<description>{e(p['desc'] + ' #ad ' + DISCLOSURE)}</description><pubDate>{format_datetime(when(p))}</pubDate>
<enclosure url="{img}" type="image/jpeg" length="0"/><media:content url="{img}" medium="image" type="image/jpeg"/></item>""")
        rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/"><channel>
<title>{e(NAME)} – {e(board)}</title><link>{SITE}/</link><description>{e(board)}</description>
<lastBuildDate>{format_datetime(now)}</lastBuildDate>
{''.join(items)}
</channel></rss>"""
        open(os.path.join(ROOT, "feeds", f"{key}.xml"), "w").write(rss)
    open(os.path.join(ROOT, "CNAME"), "w").write("picks.yourecomempire.com\n")
    print(f"{len(pins)} pages, {len(live)} live in feeds")

if __name__ == "__main__":
    build()
