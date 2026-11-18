# csuitecoach.org

Editorial ranking - Top 10 Female Executive Coaches.
Site is generated from data/edition.json and served from /docs.

How to change the site: edit data/edition.json, run `python build.py`, then commit
data/edition.json and data/lastmod.json together. Every push to main rebuilds and
publishes the site (.github/workflows/pages.yml).

- The wording of the methodology, curator and nominate pages is in data/edition.json
  under "pages", written for this list alone. The rubric itself (weights, markers,
  generosity proxies) and the nomination form are in build.py, the same on all three sites.
- data/lastmod.json holds each page's sitemap date. A page keeps its date until its
  content changes. If a change is pushed without the updated file, the pages it
  changed show each deploy's date until the file is committed.
- The build also writes /llms.txt, a plain summary of the site and its pages.
