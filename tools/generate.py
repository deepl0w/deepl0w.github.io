#!/usr/bin/env python3
"""Generate the landing page listing every public repository with GitHub Pages.

The repository list comes from /users/<name>/repos, which only ever returns
public repositories. That is deliberate: it means a private repository cannot
leak onto the published page even if the token the workflow runs with happens
to be able to see it.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html import escape
from pathlib import Path

USER = os.environ.get("PAGES_USER", "deepl0w")
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_site"
TIMEOUT = 20


def api(url: str) -> list | dict:
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USER}-pages-index",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    # Authenticating only raises the rate limit; the endpoint stays public-only.
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.load(response)


def public_repos() -> list[dict]:
    repos, page = [], 1
    while True:
        batch = api(f"https://api.github.com/users/{USER}/repos"
                    f"?per_page=100&page={page}&sort=updated")
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def is_live(url: str) -> bool:
    """A site can have Pages enabled yet serve nothing, e.g. mid first deploy."""
    request = urllib.request.Request(url, method="HEAD",
                                     headers={"User-Agent": f"{USER}-pages-index"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.status < 400
    except urllib.error.HTTPError as error:
        return error.code < 400
    except Exception:
        return False


def pages_url(repo: dict) -> str:
    # A repo named <user>.github.io is the user site and serves at the root.
    if repo["name"].lower() == f"{USER.lower()}.github.io":
        return f"https://{USER.lower()}.github.io/"
    return f"https://{USER.lower()}.github.io/{repo['name']}/"


def card(repo: dict, live: bool) -> str:
    url = pages_url(repo)
    name = escape(repo["name"])
    description = escape(repo.get("description") or "No description.")
    language = escape(repo.get("language") or "")
    updated = repo.get("pushed_at", "")[:10]
    badge = "" if live else ' <span class="badge">deploying</span>'
    meta = " \u00b7 ".join(filter(None, [language, f"updated {updated}" if updated else ""]))
    # The title anchor is stretched over the whole card by CSS, so the card is
    # clickable without nesting the "source" link inside another anchor.
    return f"""      <li class="card">
        <h2><a class="stretch" href="{url}">{name}</a>{badge}</h2>
        <p>{description}</p>
        <footer>
          <span class="meta">{escape(meta)}</span>
          <a class="src" href="{escape(repo['html_url'])}">source</a>
        </footer>
      </li>"""


def main() -> int:
    repos = [r for r in public_repos()
             if r.get("has_pages") and not r.get("archived")]
    # The user site is this page itself; listing it would just link to here.
    repos = [r for r in repos if r["name"].lower() != f"{USER.lower()}.github.io"]
    repos.sort(key=lambda r: r.get("pushed_at", ""), reverse=True)

    if not repos:
        print("warning: no public repositories with Pages found", file=sys.stderr)

    cards = "\n".join(card(r, is_live(pages_url(r))) for r in repos)
    count = f"{len(repos)} site{'s' if len(repos) != 1 else ''}"
    stamp = datetime.now(timezone.utc).strftime("%d %B %Y")

    css = (ROOT / "static" / "style.css").read_text(encoding="utf-8")
    # GitHub Pages serves assets with max-age=600, so without a content hash in
    # the URL a style change is invisible to anyone who loaded the page in the
    # last ten minutes.
    css_hash = hashlib.sha256(css.encode("utf-8")).hexdigest()[:12]

    html = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    for key, value in {
        "{{USER}}": escape(USER),
        "{{CARDS}}": cards,
        "{{COUNT}}": count,
        "{{UPDATED}}": stamp,
        "{{CSSHASH}}": css_hash,
    }.items():
        html = html.replace(key, value)

    OUT.mkdir(exist_ok=True)
    (OUT / "index.html").write_text(html, encoding="utf-8")
    (OUT / "style.css").write_text(css, encoding="utf-8")
    # Without this, Pages runs the output through Jekyll and drops _-prefixed paths.
    (OUT / ".nojekyll").write_text("", encoding="utf-8")

    print(f"wrote {OUT/'index.html'} with {count}")
    for repo in repos:
        print(f"  - {repo['name']}  {pages_url(repo)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
