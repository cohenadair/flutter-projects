#!/usr/bin/env python3
"""Builds one HTML page showing every placement preview for one or more creatives.

Usage: python3 preview_page.py <input.json> <out.html>

input.json:
{
  "title": "Activity Log ad previews",
  "note": "optional subtitle",
  "sections": [
    {"name": "iOS", "creative_id": "123",
     "previews": [{"label": "Facebook Feed", "format": "MOBILE_FEED_STANDARD",
                   "url": "<preview_url from ads_get_ad_preview>"}]}
  ]
}

Preview URLs come from ads_get_ad_preview and expire; regenerate before sharing.
"""
import html
import json
import sys

# Placements rendered as full-screen vertical frames; everything else is a feed.
TALL_FORMATS = {
    "INSTAGRAM_STORY",
    "INSTAGRAM_REELS",
    "FACEBOOK_REELS_MOBILE",
    "MESSENGER_MOBILE_STORY_MEDIA",
}

STYLE = """
:root{--bg:#f6f7f8;--fg:#1c1e21;--muted:#65676b;--card:#fff;--line:#dadde1}
@media (prefers-color-scheme:dark){:root{--bg:#18191a;--fg:#e4e6eb;--muted:#b0b3b8;--card:#242526;--line:#3a3b3c}}
body{margin:0;padding:24px 16px;background:var(--bg);color:var(--fg);font:15px/1.4 -apple-system,system-ui,sans-serif}
h1{font-size:22px;margin:0 0 4px} p{color:var(--muted);margin:0 0 24px}
h2{font-size:18px;margin:32px 0 12px} h2 span{font-weight:400;color:var(--muted);font-size:13px}
.grid{display:flex;flex-wrap:wrap;gap:16px;align-items:flex-start}
figure{margin:0;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px}
figcaption{font-weight:600;font-size:13px;margin-bottom:8px}
iframe{border:0;display:block;max-width:100%}
.feed iframe{width:335px;height:560px} .tall iframe{width:320px;height:600px}
"""


def build_section(section):
    cards = []
    for p in section["previews"]:
        kind = "tall" if p.get("format") in TALL_FORMATS else "feed"
        url = html.unescape(p["url"])
        cards.append(
            f'<figure class="{kind}"><figcaption>{html.escape(p["label"])}</figcaption>'
            f'<iframe src="{html.escape(url)}" loading="lazy" allow="autoplay"></iframe></figure>'
        )
    return (
        f'<section><h2>{html.escape(section["name"])} '
        f'<span>creative {html.escape(section.get("creative_id", ""))}</span></h2>'
        f'<div class="grid">{"".join(cards)}</div></section>'
    )


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    with open(sys.argv[1]) as f:
        data = json.load(f)
    title = html.escape(data.get("title", "Ad previews"))
    note = html.escape(data.get("note", "Preview links expire; regenerate before sharing."))
    sections = "".join(build_section(s) for s in data["sections"])
    page = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{title}</title><style>{STYLE}</style></head><body>"
        f"<h1>{title}</h1><p>{note}</p>{sections}</body></html>"
    )
    with open(sys.argv[2], "w") as f:
        f.write(page)


if __name__ == "__main__":
    main()
