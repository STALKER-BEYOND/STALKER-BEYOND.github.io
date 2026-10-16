# Stalker Beyond

v0.1 site, styled after the STALKER 2 PDA:

- Canonical home at `/home/`, with a redirect at the root `/`.
- Nav order: Home, Media, Lore, Rules, Warfare, FAQ, Apply Now
- `404.html` forwards old links from the site's previous address.

Files included:
- index.html (redirect to /home/)
- 404.html (not-found page)
- styles.css (shared styles)
- home/index.html (canonical home)
- media/index.html (featured reel, grid and viewer, built from media/media.json)
- media/media.json (media list: title, category, credit, date, featured)
- assets/media/ (compressed media made by tools/build_media.py)
- tools/build_media.py (put originals in media-src/, run `python tools/build_media.py`)
- lore/index.html
- rules/index.html
- warfare/index.html
- faq/index.html
- apply-now/index.html (Applications)

Site URL:
- https://stalker-beyond.github.io/home/
