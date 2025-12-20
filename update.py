#!/usr/bin/env python3
# /// script
# dependencies = ["httpx"]
# ///

import json
import sys
from pathlib import Path
from dataclasses import dataclass
import httpx


@dataclass
class AppConfig:
    name: str
    repo: str
    ipa_pattern: str


@dataclass
class Release:
    version: str
    url: str
    size: int
    date: str
    description: str


def fetch_release(repo: str, ipa_pattern: str) -> Release | None:
    url = f"https://api.github.com/repos/{repo}/releases/latest"

    try:
        response = httpx.get(
            url, headers={"Accept": "application/vnd.github+json"}, timeout=10
        )
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, json.JSONDecodeError) as e:
        print(f"Failed to fetch {repo}: {e}", file=sys.stderr)
        return None

    asset = next(
        (
            a
            for a in data.get("assets", [])
            if (ipa_pattern == ".ipa" and a["name"].endswith(".ipa"))
            or a["name"] == ipa_pattern
        ),
        None,
    )

    if not asset:
        print(f"No IPA matching '{ipa_pattern}' in {repo}", file=sys.stderr)
        return None

    return Release(
        version=data["tag_name"].lstrip("v"),
        url=asset["browser_download_url"],
        size=asset["size"],
        date=data["published_at"],
        description=data.get("body", ""),
    )


def load_apps_json(path: Path = Path("apps.json")) -> dict:
    return json.loads(path.read_text())


def save_apps_json(data: dict, path: Path = Path("apps.json")):
    path.write_text(json.dumps(data, indent=2) + "\n")


def update_app(data: dict, config: AppConfig, release: Release) -> tuple[dict, bool]:
    app = next((a for a in data["apps"] if a.get("name") == config.name), None)

    if not app:
        app = {"name": config.name}
        data["apps"].append(app)
        print(f"+ {config.name} added to apps.json")

    if app.get("version") == release.version:
        print(f"✗ {config.name} already at {release.version}")
        return data, False

    old_version = app.get("version", "new")
    app.update(
        {
            "downloadURL": release.url,
            "version": release.version,
            "size": release.size,
            "versionDate": release.date,
            "versionDescription": release.description,
        }
    )

    print(f"✓ {config.name} updated: {old_version} → {release.version}")
    return data, True


def main():
    apps = [
        AppConfig("RedditFilter", "level3tjg/RedditFilter", ".ipa"),
        AppConfig("BTLoader (Kettu Discord mod)", "CloudySn0w/BTLoader", "discord.ipa"),
    ]

    data = load_apps_json()
    updated = False

    for config in apps:
        release = fetch_release(config.repo, config.ipa_pattern)
        if release:
            data, changed = update_app(data, config, release)
            updated = updated or changed

    if updated:
        save_apps_json(data)
        print("\nUpdates saved to apps.json")
    else:
        print("\nNo updates needed")

    sys.exit(0 if updated else 1)


if __name__ == "__main__":
    main()
