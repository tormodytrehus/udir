#!/usr/bin/env python3
"""Low-noise Udir publication monitor for a local newsroom."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from datetime import date, datetime, timezone
from email.utils import format_datetime
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent
MONTHS = {
    "januar": 1, "februar": 2, "mars": 3, "april": 4,
    "mai": 5, "juni": 6, "juli": 7, "august": 8,
    "september": 9, "oktober": 10, "november": 11, "desember": 12,
}


@dataclass(frozen=True)
class Candidate:
    key: str
    title: str
    url: str
    source_id: str
    source_title: str
    due: str | None = None


class UdirHTMLParser(HTMLParser):
    """Collect headings and links without executing page scripts."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.headings: list[tuple[str, str, str | None]] = []
        self.links: list[tuple[str, str]] = []
        self._heading_tag: str | None = None
        self._heading_text: list[str] = []
        self._heading_href: str | None = None
        self._anchor_href: str | None = None
        self._anchor_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag in {"h2", "h3"}:
            self._heading_tag = tag
            self._heading_text = []
            self._heading_href = None
        if tag == "a" and values.get("href"):
            self._anchor_href = values["href"]
            self._anchor_text = []
            if self._heading_tag:
                self._heading_href = values["href"]

    def handle_data(self, data: str) -> None:
        if self._heading_tag:
            self._heading_text.append(data)
        if self._anchor_href:
            self._anchor_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._anchor_href:
            self.links.append((normalized_text(" ".join(self._anchor_text)), self._anchor_href))
            self._anchor_href = None
            self._anchor_text = []
        if tag == self._heading_tag:
            self.headings.append(
                (tag, normalized_text(" ".join(self._heading_text)), self._heading_href)
            )
            self._heading_tag = None
            self._heading_text = []
            self._heading_href = None


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} må inneholde et JSON-objekt")
    return value


def save_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temp, path)


def fetch(url: str, timeout: int = 45) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": "udir-radar/1.0 (+public newsroom monitoring)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def normalized_text(value: str) -> str:
    return " ".join(value.split())


def matches(title: str, terms: list[str]) -> bool:
    folded = title.casefold()
    return any(term.casefold() in folded for term in terms)


def topic_for(title: str, config: dict) -> str | None:
    folded = title.casefold()
    for topic in config.get("topics", []):
        if any(term.casefold() in folded for term in topic["terms"]):
            return topic["id"]
    return None


def release_year(item: Candidate, today: date) -> int:
    if item.due:
        return int(item.due[:4])
    years = [int(value) for value in re.findall(r"20\d{2}", item.title)]
    return max(years) if years else today.year


def parse_calendar(html: str, source: dict) -> list[Candidate]:
    parser = UdirHTMLParser()
    parser.feed(html)
    current_year: int | None = None
    current_month: int | None = None
    found: list[Candidate] = []

    for tag, text, href in parser.headings:
        month_match = re.fullmatch(r"([A-Za-zÆØÅæøå]+)\s+(20\d{2})", text)
        if tag == "h2" and month_match:
            current_month = MONTHS.get(month_match.group(1).casefold())
            current_year = int(month_match.group(2))
            continue
        if tag != "h3" or current_year is None or current_month is None:
            continue

        event_match = re.match(r"(\d{1,2})\.\s*(?:[A-Za-zÆØÅæøå]+\.?)?\s*(.+)", text)
        if not event_match:
            continue
        event_title = normalized_text(event_match.group(2))
        if not matches(event_title, source["terms"]):
            continue
        day = int(event_match.group(1))
        due = date(current_year, current_month, day).isoformat()
        url = urljoin(source["url"], href) if href else source["url"]
        key = f"calendar:{due}:{event_title.casefold()}"
        found.append(Candidate(key, event_title, url, source["id"], source["title"], due))
    return found


def parse_links(html: str, source: dict) -> list[Candidate]:
    parser = UdirHTMLParser()
    parser.feed(html)
    found: list[Candidate] = []
    for title, href in parser.links:
        if not title or not matches(title, source["terms"]):
            continue
        url = urljoin(source["url"], href)
        if not url.startswith("https://www.udir.no/"):
            continue
        digest = hashlib.sha256(url.encode()).hexdigest()[:20]
        found.append(Candidate(f"link:{digest}", title, url, source["id"], source["title"]))
    return list({item.key: item for item in found}.values())


def collect(config: dict, fetcher: Callable[[str], str] = fetch) -> list[Candidate]:
    all_candidates: list[Candidate] = []
    for source in config["sources"]:
        html = fetcher(source["url"])
        parsed = parse_calendar(html, source) if source["kind"] == "calendar" else parse_links(html, source)
        if len(parsed) < source.get("minimum_matches", 1):
            raise RuntimeError(
                f"Kilden {source['id']} ga bare {len(parsed)} relevante treff. "
                "Tilstanden ble ikke endret."
            )
        all_candidates.extend(parsed)
    return list({item.key: item for item in all_candidates}.values())


def read_feed_items(path: Path) -> list[ET.Element]:
    if not path.exists():
        return []
    root = ET.parse(path).getroot()
    channel = root.find("channel")
    return [] if channel is None else [item for item in channel.findall("item")]


def write_feed(path: Path, config: dict, events: list[Candidate], checked_at: datetime) -> None:
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = config["feed"]["title"]
    ET.SubElement(channel, "link").text = config["feed"]["home_url"]
    ET.SubElement(channel, "description").text = config["feed"]["description"]
    ET.SubElement(channel, "language").text = "nb-no"
    ET.SubElement(channel, "lastBuildDate").text = format_datetime(checked_at)

    if events:
        names = ", ".join(m["name"] for m in config["municipalities"])
        links = "".join(
            f'<li><a href="{escape(event.url, quote=True)}">{escape(event.title)}</a>'
            f' <small>({escape(event.source_title)})</small></li>'
            for event in events
        )
        description = (
            f"<p>Udir har en ny eller aktuell statistikkpublisering.</p><ul>{links}</ul>"
            f"<p>Sjekk tallene for {escape(names)}. Sammenlign med forrige år, Trøndelag og landet. "
            "Skjulte verdier skal ikke tolkes som null, og små elevkull må omtales varsomt.</p>"
        )
        digest = hashlib.sha256("|".join(sorted(e.key for e in events)).encode()).hexdigest()
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = "Udir: ny lokal statistikkilde klar til kontroll"
        ET.SubElement(item, "link").text = events[0].url
        ET.SubElement(item, "guid", isPermaLink="false").text = f"udir-radar:{digest}"
        ET.SubElement(item, "pubDate").text = format_datetime(checked_at)
        ET.SubElement(item, "description").text = description

    for old in read_feed_items(path)[: config["feed"].get("max_items", 30) - (1 if events else 0)]:
        channel.append(old)

    path.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(rss, space="  ")
    tree = ET.ElementTree(rss)
    temp = path.with_suffix(".xml.tmp")
    tree.write(temp, encoding="utf-8", xml_declaration=True)
    os.replace(temp, path)


def run(config_path: Path, state_path: Path, feed_path: Path, *, today: date | None = None,
        now: datetime | None = None, fetcher: Callable[[str], str] = fetch) -> list[Candidate]:
    config = load_json(config_path)
    state = load_json(state_path)
    today = today or date.today()
    now = now or datetime.now(timezone.utc)
    candidates = collect(config, fetcher)

    first_run = not bool(state.get("initialized"))
    known = set(state.get("known", []))
    emitted = set(state.get("emitted", []))
    emitted_topics = set(state.get("emitted_topics", []))
    pending_by_topic: dict[str, Candidate] = {}

    for item in candidates:
        topic = topic_for(item.title, config)
        topic_key = f"{topic}:{release_year(item, today)}" if topic else None
        if item.due:
            if item.due <= today.isoformat() and item.key not in emitted:
                emitted.add(item.key)
                if topic_key:
                    if first_run and config.get("silent_first_run", True):
                        emitted_topics.add(topic_key)
                    elif topic_key not in emitted_topics:
                        pending_by_topic.setdefault(topic_key, item)
        elif item.key not in known:
            known.add(item.key)
            if (topic_key and topic_key not in emitted_topics
                    and (not first_run or not config.get("silent_first_run", True))):
                # En faktisk publiseringslenke er bedre enn kalenderlenken.
                pending_by_topic[topic_key] = item

    events = list(pending_by_topic.values())
    emitted_topics.update(pending_by_topic)

    next_state = {
        "initialized": True,
        "last_successful_check": now.isoformat(),
        "known": sorted(known | {c.key for c in candidates if not c.due}),
        "emitted": sorted(emitted),
        "emitted_topics": sorted(emitted_topics),
        "scheduled": [asdict(c) for c in candidates if c.due and c.due > today.isoformat()],
    }
    write_feed(feed_path, config, events, now)
    save_json(state_path, next_state)
    return events


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "config.json")
    parser.add_argument("--state", type=Path, default=ROOT / "state" / "state.json")
    parser.add_argument("--feed", type=Path, default=ROOT / "public" / "feed.xml")
    args = parser.parse_args()
    try:
        events = run(args.config, args.state, args.feed)
    except Exception as exc:
        print(f"FEIL: {exc}", file=sys.stderr)
        return 1
    print(f"Kontroll fullført. Nye RSS-meldinger: {1 if events else 0}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
