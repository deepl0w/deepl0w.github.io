# deepl0w.github.io

The landing page at <https://deepl0w.github.io/>, listing every public
repository of mine that has GitHub Pages enabled.

The list is not maintained by hand. [`tools/generate.py`](tools/generate.py)
asks the GitHub API for the account's repositories, keeps the ones with Pages
enabled, and renders them into [`templates/index.html`](templates/index.html).
Publish a new site anywhere and it appears here on the next run.

## Why only public repositories

The generator reads `/users/<name>/repos`, which returns public repositories
only, rather than `/user/repos`, which would also return private ones for an
authenticated caller. The endpoint choice is the safeguard: a private
repository cannot reach this page even if the workflow's token could see it.

## When it rebuilds

On every push to `main`, once a day at 05:17 UTC, and on demand from the
Actions tab. The daily run is the one that matters — a site published in
another repository has no way to trigger a build here.

## Running it locally

```bash
python3 tools/generate.py          # writes _site/
python3 -m http.server -d _site    # then open http://localhost:8000
```

No dependencies beyond the standard library. Set `PAGES_USER` to generate for a
different account, and `GITHUB_TOKEN` to avoid the unauthenticated rate limit.

## Layout

| Path | Purpose |
| --- | --- |
| `tools/generate.py` | Fetches the repository list and renders the page |
| `templates/index.html` | Page shell, with `{{CARDS}}` and friends substituted in |
| `static/style.css` | Styling, including the dark-mode palette |
| `.github/workflows/pages.yml` | Build and deploy |
