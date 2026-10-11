#!/usr/bin/env python3
"""Update the public-data-only SVG metrics used by the GitHub profile."""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET

USERNAME = "Eng-Hadi-Ali"
BASE = "https://api.github.com"
ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "assets" / "github-glass-stats.template.svg"
OUTPUT = ROOT / "assets" / "github-glass-stats.svg"


def github_get(path: str):
    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "hadi-public-profile-stats",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(BASE + path, headers=headers)
    with urlopen(request, timeout=25) as response:
        return json.load(response)


def load_stats():
    user = github_get(f"/users/{USERNAME}")
    repos = []
    for page in range(1, 31):
        batch = github_get(f"/users/{USERNAME}/repos?type=owner&per_page=100&page={page}")
        repos.extend(
            repo for repo in batch
            if not repo.get("private")
            and repo.get("owner", {}).get("login", "").lower() == USERNAME.lower()
        )
        if len(batch) < 100:
            break
    else:
        raise RuntimeError("Repository listing exceeded pagination limit")
    original = [repo for repo in repos if not repo.get("fork")]
    pushed = max((repo["pushed_at"] for repo in repos if repo.get("pushed_at")), default=None)
    last_push = (
        dt.datetime.fromisoformat(pushed.replace("Z", "+00:00")).strftime("%d %b %Y").upper()
        if pushed else "NO PUBLIC PUSH"
    )
    return {
        "PUBLIC_REPOS": str(user["public_repos"]),
        "STARS_RECEIVED": str(sum(int(repo.get("stargazers_count") or 0) for repo in original)),
        "FOLLOWERS": str(user["followers"]),
        "LATEST_PUSH": last_push,
        "SYNCED_UTC": dt.datetime.now(dt.timezone.utc).strftime("%d %b %Y / %H:%M UTC").upper(),
    }


def main():
    stats = load_stats()
    document = TEMPLATE.read_text(encoding="utf-8")
    for key, value in stats.items():
        document = document.replace("{{" + key + "}}", escape(value))
    if "{{" in document or "}}" in document:
        raise RuntimeError("Template still contains unresolved placeholders")
    ET.fromstring(document)
    OUTPUT.write_text(document, encoding="utf-8")
    print("PUBLIC_PROFILE_STATS_UPDATED: " + ", ".join(f"{k}={v}" for k, v in stats.items()))


if __name__ == "__main__":
    main()
