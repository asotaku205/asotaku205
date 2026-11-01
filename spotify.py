#!/usr/bin/env python3
"""Generate spotify.svg for the GitHub profile README.

Reads SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET and SPOTIFY_REFRESH_TOKEN
from the environment, asks Spotify what is playing (falling back to the
most recently played track), and writes a small SVG card. Never fails:
any error produces a tasteful fallback card and exit code 0, so the
scheduled workflow never breaks the profile image.
"""

import base64
import html
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "spotify.svg")

BG = "#1a1b27"
BORDER = "#7c3aed"
TEXT = "#e6e6f0"
MUTED = "#9a9ab0"
GREEN = "#1db954"

W, H = 400, 120


def esc(s):
    return html.escape(str(s or ""), quote=True)


def shorten(s, n=42):
    s = str(s or "")
    return s if len(s) <= n else s[: n - 1].rstrip() + "..."


def post_form(url, data, headers):
    req = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(data).encode(),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.load(resp)


def get_json(url, token):
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read()
            if not body:
                return resp.status, None
            return resp.status, json.loads(body)
    except urllib.error.HTTPError as e:
        return e.code, None


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


def card(status, title, artist, art_b64, progress=None, accent=GREEN):
    if art_b64:
        art = '<image x="16" y="16" width="88" height="88" href="%s" clip-path="url(#artclip)" />' % art_b64
    else:
        art = (
            '<rect x="16" y="16" width="88" height="88" rx="10" fill="#2a2b3d" />'
            '<circle cx="60" cy="60" r="22" fill="none" stroke="%s" stroke-width="3" />'
            '<circle cx="60" cy="60" r="7" fill="%s" />' % (accent, accent)
        )
    bar = ""
    if progress is not None:
        pct = max(0, min(100, int(progress)))
        bw = int(264 * pct / 100)
        bar = (
            '<rect x="120" y="96" width="264" height="5" rx="2.5" fill="#2a2b3d" />'
            '<rect x="120" y="96" width="%d" height="5" rx="2.5" fill="%s" />' % (bw, accent)
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
        "%s"
        "</svg>"
        % (
            W, H, W, H, W - 2, H - 2, BG, BORDER, art, accent, MUTED,
            esc(status), TEXT, esc(shorten(title)), MUTED, esc(shorten(artist)), bar,
        )
    )


def fallback():
    return card("SPOTIFY", "Nothing playing right now", "Play something on Spotify", None)


def main():
    try:
        cid = os.environ.get("SPOTIFY_CLIENT_ID", "")
        secret = os.environ.get("SPOTIFY_CLIENT_SECRET", "")
        refresh = os.environ.get("SPOTIFY_REFRESH_TOKEN", "")
        if not (cid and secret and refresh):
            raise RuntimeError("missing credentials")
        basic = base64.b64encode(("%s:%s" % (cid, secret)).encode()).decode()
        tok = post_form(
            "https://accounts.spotify.com/api/token",
            {"grant_type": "refresh_token", "refresh_token": refresh},
            {"Authorization": "Basic " + basic},
        )
        access = tok["access_token"]

        status, track, progress = None, None, None
        code, data = get_json(
            "https://api.spotify.com/v1/me/player/currently-playing", access
        )
        if code == 200 and data and data.get("item"):
            item = data["item"]
            if data.get("is_playing"):
                status = "NOW PLAYING"
                dur = item.get("duration_ms") or 0
                prog = data.get("progress_ms") or 0
                progress = int(prog * 100 / dur / 10.0) * 10 if dur else None
                track = item
        if track is None:
            code, data = get_json(
                "https://api.spotify.com/v1/me/player/recently-played?limit=1", access
            )
            items = (data or {}).get("items") or []
            if items:
                status = "RECENTLY PLAYED"
                track = items[0]["track"]
        if track is None:
            raise RuntimeError("nothing found")
        name = track.get("name", "Unknown track")
        artists = ", ".join(a.get("name", "") for a in track.get("artists", []))
        if not artists and track.get("show"):
            artists = track["show"].get("name", "")
        images = track.get("album", {}).get("images", [])
        art = fetch_image_b64(images[-1]["url"]) if images else None
        svg = card(status, name, artists, art, progress)
    except Exception:
        svg = fallback()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
