#!/usr/bin/env python3
"""Fetch season and episode air dates from TVmaze for every show in shows.json
and write them to data.json, which index.html displays.

Uses only the Python standard library, so there is nothing to install.
Run locally with:  python update.py
"""

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://api.tvmaze.com"
HERE = Path(__file__).resolve().parent
SHOWS_FILE = HERE / "shows.json"
DATA_FILE = HERE / "data.json"
PAUSE = 0.6  # seconds between requests; TVmaze allows ~20 requests per 10 s


def get_json(path, params=None, attempts=4):
    url = API + path
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(url, headers={"User-Agent": "reality-tv-airdate-tracker"})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as err:
            if err.code == 404:
                return None
            if err.code == 429 or err.code >= 500:
                time.sleep(5 * (attempt + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Gave up on {url}")


def normalize(name):
    s = name.lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"^the ", "", s.strip())
    return re.sub(r"\s+", " ", s).strip()


def show_country(show):
    for key in ("network", "webChannel"):
        chan = show.get(key) or {}
        country = chan.get("country") or {}
        if country.get("code"):
            return country["code"]
    return None


def channel_name(show):
    for key in ("network", "webChannel"):
        chan = show.get(key) or {}
        if chan.get("name"):
            return chan["name"]
    return None


def resolve(entry):
    """Find the TVmaze show for a shows.json entry. Returns (show, note)."""
    results = get_json("/search/shows", {"q": entry["name"]}) or []
    time.sleep(PAUSE)
    want = normalize(entry["name"])
    country = entry.get("country")

    def country_rank(show):
        c = show_country(show)
        if not country or c == country:
            return 0
        return 1 if c is None else 2

    exact = [r for r in results if normalize(r["show"]["name"]) == want]
    exact = [r for r in exact if country_rank(r["show"]) < 2]
    if exact:
        exact.sort(key=lambda r: (country_rank(r["show"]), -r.get("score", 0)))
        return exact[0]["show"], None

    close = [
        r for r in results
        if country_rank(r["show"]) < 2
        and (want in normalize(r["show"]["name"]) or normalize(r["show"]["name"]) in want)
    ]
    if close:
        close.sort(key=lambda r: (country_rank(r["show"]), -r.get("score", 0)))
        show = close[0]["show"]
        return show, f"No exact match; using closest: {show['name']}"
    return None, "Not found on TVmaze"


def build_show(entry, show_id):
    show = get_json(f"/shows/{show_id}", {"embed[]": ["seasons", "episodes"]})
    time.sleep(PAUSE)
    if not show:
        raise RuntimeError(f"TVmaze show {show_id} not found")
    emb = show.get("_embedded", {})
    episodes_by_season = {}
    for ep in emb.get("episodes", []):
        episodes_by_season.setdefault(ep.get("season"), []).append({
            "number": ep.get("number"),
            "name": ep.get("name"),
            "airdate": ep.get("airdate") or None,
            "airstamp": ep.get("airstamp"),
            "airtime": ep.get("airtime") or None,  # time as listed by the network, e.g. "20:00"
            "type": ep.get("type"),
        })
    seasons = []
    for s in emb.get("seasons", []):
        eps = sorted(episodes_by_season.get(s.get("number"), []),
                     key=lambda e: (e["number"] is None, e["number"] or 0, e["airdate"] or ""))
        seasons.append({
            "number": s.get("number"),
            "name": s.get("name") or "",
            "premiere": s.get("premiereDate"),
            "end": s.get("endDate"),
            "episode_order": s.get("episodeOrder"),
            "episodes": eps,
        })
    seasons.sort(key=lambda s: s["number"] or 0)
    image = (show.get("image") or {}).get("medium")
    return {
        "name": entry["name"],
        "group": entry.get("group", "Shows"),
        "tvmaze_id": show["id"],
        "tvmaze_name": show.get("name"),
        "tvmaze_url": show.get("url"),
        "channel": channel_name(show),
        # Streaming-only (Peacock, Hulu...) releases at one moment everywhere; TV channels
        # air at the same clock time on each coast.
        "streaming": not show.get("network") and bool(show.get("webChannel")),
        "status": show.get("status"),
        "image": image,
        "seasons": seasons,
    }


def main():
    config = json.loads(SHOWS_FILE.read_text())["shows"]
    previous = {}
    if DATA_FILE.exists():
        try:
            previous = {s["name"]: s for s in json.loads(DATA_FILE.read_text()).get("shows", [])}
        except (json.JSONDecodeError, KeyError):
            previous = {}

    out, problems, failures = [], [], 0
    for entry in config:
        name = entry["name"]
        old = previous.get(name)
        try:
            show_id = entry.get("id") or (old or {}).get("tvmaze_id")
            note = None
            if not show_id:
                found, note = resolve(entry)
                if not found:
                    raise RuntimeError(note)
                show_id = found["id"]
            data = build_show(entry, show_id)
            if note:
                data["note"] = note
                problems.append(f"{name}: {note}")
            out.append(data)
            print(f"ok   {name}  ->  {data['tvmaze_name']} ({data['channel']}, id {show_id})")
        except Exception as err:  # keep last good data for this show
            failures += 1
            problems.append(f"{name}: {err}")
            print(f"FAIL {name}: {err}", file=sys.stderr)
            if old:
                out.append(old)

    result = {
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "problems": problems,
        "shows": out,
    }
    DATA_FILE.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
    print(f"Wrote {len(out)} shows to {DATA_FILE.name}; {failures} failed.")
    if failures == len(config):
        sys.exit(1)


if __name__ == "__main__":
    main()
