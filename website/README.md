# Evolutionary Biology University Ranking website

Open `index.html` in a browser. The site is self-contained and does not need a
server, build tool, API key, or network connection (system-font fallbacks are
used if Google Fonts is unavailable).

The ranking becomes a card list on narrow phone screens, so no sideways table
scrolling is required. The header's 中文 / English button switches the site
interface and methodology; official university names and paper titles remain
in their original language.

The Results area has separate university and included-paper tabs. The latter
lists all 2,378 papers, with title/author/DOI search, a journal filter and a
CSV download. `assets/ranking-data.js` holds ranking rows and journal weights;
`assets/paper-data.js` holds paper records and per-university contributions.
Neither list is written into `index.html`.

The data in `assets/` is generated from the project's reviewed ranking CSVs:

```bash
python3 scripts/build_ranking_website.py
```

Run that command from the repository root whenever the underlying ranking
changes. It verifies that all 100 institutional scores equal the exact sum of
their paper-level credits, then refreshes the separate site data files and
downloadable CSVs.
The website labels the 2026-09-27 snapshot as final by the project owner's
decision; the original research exports remain unmodified.
