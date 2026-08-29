#!/usr/bin/env python3
"""
Daily job watcher for Ismail Mahid.

Checks three Maldives job sources for new listings matching a keyword
profile (healthcare operations / clinic administration / general
management leadership roles), and sends new matches to Telegram.
Designed to run once a day via GitHub Actions (see
.github/workflows/daily-check.yml).

Sources:
  - job-maldives.com  (has a proper RSS feed)
  - jobsicle.mv        (server-rendered HTML, scraped directly)
  - mycareer.gov.mv     (government portal, server-rendered HTML, scraped directly)

State (which job links have already been sent) is kept in seen.json so
the same listing is never sent twice.
"""

import json
import os
import re
import sys
from pathlib import Path

import feedparser
import requests
from bs4 import BeautifulSoup

STATE_FILE = Path(__file__).parent / "seen.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

# --- Feeds / pages to check ------------------------------------------------
RSS_FEEDS = [
    "https://www.job-maldives.com/feeds/posts/default?alt=rss",
]

JOBSICLE_PAGES = [
    "https://jobsicle.mv/",
    "https://jobsicle.mv/?page=2",
]

MYCAREER_PAGES = [
    "https://mycareer.gov.mv/en/jobs",
]

# --- Keyword profile ------------------------------------------------------
# Tune this list any time — it's the only thing you need to edit to
# change what counts as "a fit".
KEYWORDS = [
    "operations manager",
    "operations and compliance",
    "clinic administrator",
    "clinic manager",
    "practice manager",
    "healthcare manager",
    "hospital administrator",
    "administrative manager",
    "senior administrative officer",
    "administration manager",
    "administrator",
    "general manager",
    "relationship management",
    "business manager",
    "director of operations",
    "head of operations",
]

EXCLUDE_KEYWORDS = [
    "housekeeping",
    "waiter",
    "waitress",
    "steward",
    "bartender",
    "kitchen",
    "chef",
    "spa therapist",
    "lifeguard",
    "driver",
]


def load_seen() -> set:
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text()))
    return set()


def save_seen(seen: set) -> None:
    STATE_FILE.write_text(json.dumps(sorted(seen), indent=2))


def matches_profile(title: str, summary: str = "") -> bool:
    text = f"{title} {summary}".lower()
    if any(bad in text for bad in EXCLUDE_KEYWORDS):
        return False
    return any(kw in text for kw in KEYWORDS)


def fetch_rss_matches() -> list[dict]:
    matches = []
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
        except Exception as e:
            print(f"Failed to fetch {feed_url}: {e}", file=sys.stderr)
            continue

        for entry in feed.entries:
            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "").strip()
            summary = re.sub(r"<[^>]+>", " ", getattr(entry, "summary", ""))
            if not title or not link:
                continue
            if matches_profile(title, summary):
                matches.append({"title": title, "link": link, "source": "Job-Maldives"})
    return matches


def fetch_jobsicle_matches() -> list[dict]:
    matches = []
    seen_links = set()
    for url in JOBSICLE_PAGES:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as e:
            print(f"Failed to fetch {url}: {e}", file=sys.stderr)
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/job/" not in href:
                continue
            link = href if href.startswith("http") else f"https://jobsicle.mv{href}"
            title = a.get_text(strip=True)
            if not title or link in seen_links:
                continue
            seen_links.add(link)
            if matches_profile(title):
                matches.append({"title": title, "link": link, "source": "Jobsicle"})
    return matches


def fetch_mycareer_matches() -> list[dict]:
    matches = []
    seen_links = set()
    for url in MYCAREER_PAGES:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as e:
            print(f"Failed to fetch {url}: {e}", file=sys.stderr)
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/en/jobs/" not in href or href.rstrip("/").endswith("/en/jobs"):
                continue
            link = href if href.startswith("http") else f"https://mycareer.gov.mv{href}"
            title = a.get_text(strip=True)
            if not title or link in seen_links:
                continue
            seen_links.add(link)
            if matches_profile(title):
                matches.append({"title": title, "link": link, "source": "MyCareer"})
    return matches


def fetch_matches() -> list[dict]:
    matches = []
    matches += fetch_rss_matches()
    matches += fetch_jobsicle_matches()
    matches += fetch_mycareer_matches()
    return matches


def send_telegram(bot_token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    resp = requests.post(
        url,
        data={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=20,
    )
    resp.raise_for_status()


def main() -> None:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        print("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID env vars", file=sys.stderr)
        sys.exit(1)

    seen = load_seen()
    matches = fetch_matches()
    new_matches = [m for m in matches if m["link"] not in seen]

    if not new_matches:
        print("No new matching jobs today.")
        return

    lines = ["<b>New job matches today:</b>", ""]
    for m in new_matches:
        lines.append(f"• [{m['source']}] <a href=\"{m['link']}\">{m['title']}</a>")
    message = "\n".join(lines)

    # Telegram messages cap at 4096 chars; chunk if needed.
    for i in range(0, len(message), 4000):
        send_telegram(bot_token, chat_id, message[i:i + 4000])

    seen.update(m["link"] for m in new_matches)
    save_seen(seen)
    print(f"Sent {len(new_matches)} new job(s) to Telegram.")


if __name__ == "__main__":
    main()

