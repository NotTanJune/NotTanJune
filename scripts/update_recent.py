"""Rewrite the "Recently shipped" block in README.md from the GitHub API.

Reads scripts/recent.json, lists the user's public repos by last push, keeps
non-forks (plus forks named in include_forks), skips anything in exclude, and
writes the newest entries between the RECENT:START and RECENT:END markers.

Run: GITHUB_TOKEN=... python3 scripts/update_recent.py
"""

import json
import os
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
CONFIG = json.loads((ROOT / "scripts" / "recent.json").read_text())
START, END = "<!-- RECENT:START -->", "<!-- RECENT:END -->"


def api(path):
    req = urllib.request.Request(f"https://api.github.com{path}")
    req.add_header("Accept", "application/vnd.github+json")
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as err:
        if err.code == 404:
            return None
        raise


def parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def describe(repo):
    """A release published within two days of the last push wins; else the override or repo description."""
    release = api(f"/repos/{repo['full_name']}/releases/latest")
    if release and release.get("published_at"):
        if parse(repo["pushed_at"]) - parse(release["published_at"]) < timedelta(days=2):
            return f"Released {release['tag_name']}"
    override = CONFIG.get("descriptions", {}).get(repo["name"])
    text = (override or repo.get("description") or "").strip().replace("|", "/")
    limit = CONFIG.get("max_description", 70)
    if len(text) > limit:
        text = text[: limit - 1].rsplit(" ", 1)[0] + "…"
    return text


def build_table():
    user = CONFIG["user"]
    include_forks = set(CONFIG.get("include_forks", []))
    exclude = set(CONFIG.get("exclude", []))
    repos = api(f"/users/{user}/repos?sort=pushed&per_page=50&type=owner") or []
    picked = []
    for repo in repos:
        if repo["private"] or repo["archived"] or repo["name"] in exclude:
            continue
        if repo["fork"] and repo["name"] not in include_forks:
            continue
        picked.append(repo)
        if len(picked) == CONFIG.get("count", 5):
            break
    rows = ["| Repo | What | Pushed |", "| --- | --- | --- |"]
    for repo in picked:
        when = parse(repo["pushed_at"]).astimezone(timezone.utc)
        rows.append(f"| [{repo['name']}]({repo['html_url']}) | {describe(repo)} | {when.day} {when:%b} |")
    return "\n".join(rows)


def main():
    text = README.read_text()
    if START not in text or END not in text:
        raise SystemExit("README.md is missing the RECENT markers")
    block = f"{START}\n{build_table()}\n{END}"
    new = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: block, text, flags=re.S)
    if new != text:
        README.write_text(new)
        print("README.md updated")
    else:
        print("no change")


if __name__ == "__main__":
    main()
