#!/usr/bin/env python3
"""Generate lastfm.svg for the GitHub profile README.

Reads LASTFM_USER and LASTFM_API_KEY from the environment, asks the
Last.fm API for the most recent scrobble (flagged as now playing while
the user is scrobbling), and writes a small SVG card. Never fails: any
error produces a tasteful fallback card and exit code 0, so the
scheduled workflow never breaks the profile image.
"""

import base64
import html
import json
import os
import sys
import urllib.parse
import urllib.request

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lastfm.svg")

BG = "#1a1b27"
BORDER = "#7c3aed"
TEXT = "#e6e6f0"
MUTED = "#9a9ab0"
RED = "#d51007"

W, H = 400, 120


def esc(s):
    return html.escape(str(s or ""), quote=True)


def shorten(s, n=42):
    s = str(s or "")
    return s if len(s) <= n else s[: n - 1].rstrip() + "..."


def fetch_image_b64(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
        if len(raw) > 300_000:
            return None
        return "data:image/jpeg;base64," + base64.b64encode(raw).decode()
    except Exception:
        return None


def card(status, title, artist, art_b64, accent=RED):
    if art_b64:
        art = '<image x="16" y="16" width="88" height="88" href="%s" clip-path="url(#artclip)" />' % art_b64
    else:
        art = (
            '<rect x="16" y="16" width="88" height="88" rx="10" fill="#2a2b3d" />'
            '<circle cx="60" cy="60" r="22" fill="none" stroke="%s" stroke-width="3" />'
            '<circle cx="60" cy="60" r="7" fill="%s" />' % (accent, accent)
        )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">'
        '<defs><clipPath id="artclip"><rect x="16" y="16" width="88" height="88" rx="10" /></clipPath></defs>'
        '<rect x="1" y="1" width="%d" height="%d" rx="14" fill="%s" stroke="%s" stroke-width="1" />'
        "%s"
        '<circle cx="132" cy="30" r="4" fill="%s" />'
        '<text x="144" y="34" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="11" letter-spacing="2" fill="%s">%s</text>'
        '<text x="120" y="62" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="16" font-weight="600" fill="%s">%s</text>'
        '<text x="120" y="82" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="13" fill="%s">%s</text>'
        "</svg>"
        % (
            W, H, W, H, W - 2, H - 2, BG, BORDER, art, accent, MUTED,
            esc(status), TEXT, esc(shorten(title)), MUTED, esc(shorten(artist)),
        )
    )


def fallback():
    return card("LAST.FM", "Nothing scrobbled yet", "Play something on Spotify", None)


def main():
    try:
        user = os.environ.get("LASTFM_USER", "")
        key = os.environ.get("LASTFM_API_KEY", "")
        if not (user and key):
            raise RuntimeError("missing credentials")
        params = urllib.parse.urlencode({
            "method": "user.getrecenttracks",
            "user": user,
            "api_key": key,
            "format": "json",
            "limit": 1,
        })
        req = urllib.request.Request(
            "https://ws.audioscrobbler.com/2.0/?" + params,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.load(resp)
        tracks = (data.get("recenttracks") or {}).get("track") or []
        if isinstance(tracks, dict):
            tracks = [tracks]
        if not tracks:
            raise RuntimeError("no tracks")
        track = tracks[0]
        now_playing = (track.get("@attr") or {}).get("nowplaying") == "true"
        status = "NOW PLAYING" if now_playing else "RECENTLY PLAYED"
        name = track.get("name", "Unknown track")
        artist = (track.get("artist") or {}).get("#text", "")
        art_url = ""
        for img in track.get("image") or []:
            url = (img or {}).get("#text", "")
            if url:
                art_url = url
        art = fetch_image_b64(art_url) if art_url else None
        svg = card(status, name, artist, art)
    except Exception:
        svg = fallback()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
