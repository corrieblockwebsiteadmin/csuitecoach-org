#!/usr/bin/env python3
"""Static site generator for one ranking in the Coach Index Network.

The same generator builds all three sites; everything that differs between
them lives in data/edition.json:
  site      - name, domain, edition dates, curator, contact
  pages     - the wording of the methodology, curator and nominate pages,
              written for this site's own list
  coaches, ones_to_watch, not_included, outstanding - the ranking itself

Quarterly refresh = edit data/edition.json and re-run. No HTML is hand-edited.
Each run also updates data/lastmod.json, which keeps each page's sitemap
date: a page keeps its date until its content changes. Commit that file
with the data.
"""
import json, os, re, shutil, html, hashlib, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(os.path.join(ROOT, "data", "edition.json"), encoding="utf-8"))
OUT = os.path.join(ROOT, "docs")
S = DATA["site"]
P = DATA["pages"]
BASE = "https://" + S["domain"]

# Structured-data identities shared by every page. The curator is the
# publisher of the site; he is never one of the ranked coaches.
WEBSITE_ID = BASE + "/#website"
RANKING_ID = BASE + "/#ranking"
CURATOR_ID = BASE + "/curator.html#curator"
CURATOR_SITE = "https://www.corrieblock.com"

# Stands in for a page's last-modified date until main() knows it.
LASTMOD = "__LASTMOD__"

NAV = [("/", "The Ranking"), ("/about.html", "Methodology"),
       ("/curator.html", "Curator"), ("/nominate.html", "Nominate")]


def esc(t):
    return html.escape(t, quote=True)


def plain(t):
    """Text without tags or entities, for llms.txt."""
    return html.unescape(re.sub(r"<[^>]+>", "", t))


def fill(t):
    """Site values inside the page wording held in data/edition.json."""
    return (t.replace("{curator}", esc(S["curator"])).replace("{contact}", S["contact"])
             .replace("{domain}", S["domain"]).replace("{title}", esc(S["title"])))


def initials(name):
    """Monogram from a person's name. Titles stripped so 'Dr Carol Kauffman' -> CK."""
    drop = {"dr", "dr.", "prof", "prof.", "professor", "mr", "mrs", "ms", "sir", "the"}
    words = [w for w in name.replace("-", " ").split() if w.strip(".").lower() not in drop]
    letters = [w[0].upper() for w in words if w[:1].isalpha()]
    if not letters:
        return "?"
    return (letters[0] + letters[-1]) if len(letters) > 1 else letters[0]


def avatar(c, size="md"):
    """Render a coach avatar.

    A real photograph is rendered ONLY when the record carries an explicit
    src, credit and licence. Absent any of the three we fall back to a
    monogram. This keeps the image rights position structural rather than a
    matter of memory: an unlicensed headshot cannot reach the page by
    accident, because the generator will not emit one.
    """
    ph = c.get("photo") or {}
    if ph.get("src") and ph.get("credit") and ph.get("licence"):
        return ('<div class="avatar avatar--%s"><img src="%s" alt="%s" loading="lazy" '
                'width="160" height="160"></div>' % (size, esc(ph["src"]), esc(c["name"])))
    return ('<div class="avatar avatar--%s" role="img" aria-label="%s">%s</div>'
            % (size, esc(c["name"]), esc(initials(c["name"]))))


def website_node():
    return {"@type": "WebSite", "@id": WEBSITE_ID, "name": S["title"], "url": BASE + "/",
            "description": S["tagline"], "inLanguage": "en",
            "publisher": {"@id": CURATOR_ID}}


def curator_node():
    return {"@type": "Person", "@id": CURATOR_ID, "name": S["curator"],
            "url": BASE + "/curator.html",
            "jobTitle": "Curator, " + S["title"],
            "description": "Owns, curates and publishes this ranking. He is not ranked on it.",
            "sameAs": [CURATOR_SITE]}


def breadcrumb(name, url):
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": S["title"], "item": BASE + "/"},
        {"@type": "ListItem", "position": 2, "name": name, "item": url}]}


def page(slug, title, desc, body, nodes=(), canonical=None, wide=False, home=False):
    """One page. Every page carries one JSON-LD block: an @graph naming the
    site and its curator, plus the page's own nodes. The site's name sits in
    the header; it is the H1 on the home page only, and every other page
    brings its own H1."""
    nav = "".join('<a href="%s">%s</a>' % (h, l) for h, l in NAV)
    schema = {"@context": "https://schema.org",
              "@graph": [website_node(), curator_node()] + list(nodes)}
    sch = '<script type="application/ld+json">%s</script>' % json.dumps(
        schema, ensure_ascii=False, indent=None).replace("</", "<\\/")
    can = canonical or (BASE + ("/" if slug == "index" else "/" + slug + ".html"))
    depth = "../" if "/" in slug else ""
    wrapmod = " wrap--wide" if wide else ""
    tag = "h1" if home else "p"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{can}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{can}">
<link rel="stylesheet" href="{depth}style.css">
{sch}
</head>
<body>
<div class="wrap{wrapmod}">
<header class="site">
  <div class="masthead"><a href="/">{esc(S['domain'])}</a></div>
  <{tag} class="site-title">{esc(S['title'])}</{tag}>
  <p class="tagline">{esc(S['tagline'])}</p>
  <nav class="site">{nav}</nav>
</header>
<main>
{body}
</main>
<footer class="site">
  <p><strong>Ownership and independence.</strong> This site is owned and curated by {esc(S['curator'])}.
     No coach pays for placement and no coach is charged for inclusion.
     See the <a href="/curator.html">curator page</a> for full disclosure.</p>
  <p><strong>Corrections and removal.</strong> Write to
     <a href="mailto:{S['contact']}">{S['contact']}</a>. Evidenced corrections are made promptly,
     and any listed coach who asks to be removed is removed without argument.</p>
  <p>Edition {esc(S['edition'])} · published {esc(S['published'])} · next review {esc(S['next_review'])}</p>
</footer>
</div>
</body>
</html>
"""


def person_schema(c):
    d = {"@type": "Person", "name": c["name"],
         "jobTitle": "Executive Coach", "description": c["bio"],
         "url": BASE + "/coaches/" + c["slug"] + ".html"}
    same = [l["url"] for l in c["links"]]
    if same:
        d["sameAs"] = same
    return d


def build_index():
    parts = []
    parts.append('<div class="meta"><strong>Edition %s.</strong> Published %s. Next review %s. '
                 'Curated by %s against a <a href="/about.html">published methodology</a>. '
                 'All sources accessed 2026-08-06.</div>'
                 % (esc(S["edition"]), esc(S["published"]), esc(S["next_review"]), esc(S["curator"])))

    parts.append('<section class="note"><h2>How this list differs</h2>')
    for p in DATA["editorial_note"]:
        parts.append("<p>%s</p>" % p)
    parts.append("</section>")

    def _links(c):
        return "".join('<a href="%s" rel="noopener">%s</a>' % (l["url"], esc(l["label"]))
                       for l in c["links"])

    coaches = sorted(DATA["coaches"], key=lambda x: x["rank"])
    top, rest = coaches[:3], coaches[3:]

    # Ranks 1-3 carry the argument of the list, so they get room to make it.
    if top:
        parts.append('<div class="features">')
        for c in top:
            parts.append(f"""<article class="feature">
  <div class="top">
    <div class="rank">{c['rank']}</div>
    {avatar(c, "lg")}
  </div>
  <h3><a href="/coaches/{c['slug']}.html">{esc(c['name'])}</a></h3>
  <p class="where">{esc(c['location'])}</p>
  <p class="role">{c['role']}</p>
  <p class="assess">{c['assessment'][0]}</p>
  <p class="links">{_links(c)}</p>
</article>""")
        parts.append('</div>')

    if rest:
        parts.append('<div class="entries">')
        for c in rest:
            parts.append(f"""<article class="entry">
  <div class="top">
    <div class="rank">{c['rank']}</div>
    {avatar(c, "md")}
    <div>
      <h3><a href="/coaches/{c['slug']}.html">{esc(c['name'])}</a></h3>
      <p class="where">{esc(c['location'])}</p>
    </div>
  </div>
  <p class="role">{c['role']}</p>
  <p class="assess">{c['assessment'][0]}</p>
  <p class="links">{_links(c)}</p>
</article>""")
        parts.append('</div>')

    parts.append('<div class="section-head"><h2>Ones to Watch</h2><span class="line"></span></div>')
    parts.append('<p class="section-lede">Named, not ranked. Practitioners whose work is strong and whose published '
                 'corpus is still building. This is a different question from the ranking above, '
                 'not a lower tier of it.</p>')
    parts.append('<div class="cards">')
    for w in DATA["ones_to_watch"]:
        # A name is linked only while there is a working page to link to.
        name = (('<a href="%s" rel="noopener">%s</a>' % (w["url"], esc(w["name"])))
                if w.get("url") else esc(w["name"]))
        parts.append(f"""<div class="card">
  <div class="top">
    {avatar(w, "sm")}
    <div>
      <h3>{name}</h3>
      <p class="where">{esc(w['location'])}</p>
    </div>
  </div>
  <p>{w['text']}</p>
  <ul class="caveats"><li>{w['note']}</li></ul>
</div>""")
    parts.append('</div>')

    parts.append('<div class="section-head"><h2>Considered and not included</h2><span class="line"></span></div>')
    parts.append('<p class="section-lede">A ranking that quietly omits well-known names invites the assumption that it '
                 'did not know about them. These were assessed and left out for stated reasons.</p>')
    parts.append('<div class="cards">')
    for x in DATA["not_included"]:
        parts.append('<div class="card card--plain"><h3>%s</h3><p>%s</p></div>' % (esc(x["name"]), x["text"]))
    parts.append('</div>')

    parts.append('<div class="section-head"><h2>Verification still outstanding</h2><span class="line"></span></div>')
    parts.append('<p class="section-lede">Published openly rather than quietly resolved, because a methodology that '
                 'claims to source everything should show what it has not yet sourced.</p><ul class="caveats">')
    for o in DATA["outstanding"]:
        parts.append("<li>%s</li>" % esc(o))
    parts.append("</ul>")

    ranking = {"@type": "ItemList", "@id": RANKING_ID,
               "name": S["title"], "description": S["tagline"], "url": BASE + "/",
               "author": {"@id": CURATOR_ID}, "publisher": {"@id": CURATOR_ID},
               "isPartOf": {"@id": WEBSITE_ID},
               "numberOfItems": len(DATA["coaches"]),
               "itemListOrder": "https://schema.org/ItemListOrderDescending",
               "itemListElement": [
                   {"@type": "ListItem", "position": c["rank"],
                    "url": BASE + "/coaches/" + c["slug"] + ".html",
                    "item": person_schema(c)} for c in DATA["coaches"]]}
    return page("index", S["title"] + " — " + S["edition"], S["tagline"],
                "\n".join(parts), [ranking], canonical=BASE + "/", wide=True, home=True)


def build_coach(c):
    links = "".join('<a href="%s" rel="noopener">%s</a>' % (l["url"], esc(l["label"]))
                    for l in c["links"])
    body = [f'<div class="meta">Ranked <strong>#{c["rank"]}</strong> in the {esc(S["edition"])} edition of '
            f'<a href="/">{esc(S["title"])}</a>. Assessed against the '
            f'<a href="/about.html">published methodology</a>.</div>',
            f'<div class="profile-head">{avatar(c, "lg")}<div>'
            f"<h1>{esc(c['name'])}</h1>"
            f'<p class="where">{esc(c["location"])}</p></div></div>',
            f'<p class="role">{c["role"]}</p>',
            f"<p>{c['bio']}</p>",
            "<h3>Why this placement</h3>"]
    for a in c["assessment"]:
        body.append("<p>%s</p>" % a)
    if c.get("notes"):
        body.append("<h3>Editorial notes and exclusions</h3>")
        body.append('<ul class="caveats">')
        for n in c["notes"]:
            body.append("<li>%s</li>" % n)
        body.append("</ul>")
    body.append('<p class="links">%s</p>' % links)
    body.append('<p class="small" style="margin-top:2rem">This entry was compiled from public sources '
                'without contacting the subject. If anything here is inaccurate, write to '
                f'<a href="mailto:{S["contact"]}">{S["contact"]}</a> and it will be corrected or removed.</p>')

    url = BASE + "/coaches/" + c["slug"] + ".html"
    profile = {"@type": "ProfilePage", "url": url,
               "mainEntity": person_schema(c),
               "isPartOf": {"@id": WEBSITE_ID},
               "publisher": {"@id": CURATOR_ID}}
    return page("coaches/" + c["slug"], c["name"] + " — " + S["title"],
                "%s. Ranked #%d in the %s edition." % (c["name"], c["rank"], S["edition"]),
                "\n".join(body), [profile, breadcrumb(c["name"], url)])


ABOUT_ROWS = [
    ("30%", "Published body of work",
     "Books with recognised trade or academic publishers. Peer-reviewed journal articles and book "
     "chapters. Research the coach originated rather than summarised. Recency is weighted: work in "
     "the last 36 months counts for more than a single title from 2009."),
    ("25%", "Teaching in public",
     "Writing that transfers a method to the reader. Assessed <strong>channel-agnostically</strong> — "
     "a piece is judged on what it contains, not where it appeared. A strong essay on a paid platform "
     "outscores a weak one in a journal."),
    ("20%", "Independent recognition",
     "Juried, third-party honours, adjusted for interlink as set out below. Fee-paying platforms and "
     "memberships never count here."),
    ("15%", "Generosity and openness",
     "Scored on observable proxies, listed below. Each scored entry cites at least one specific, "
     "linkable instance. No instance, no score."),
    ("10%", "Practice standing",
     "Credentials as published, years in senior-executive practice, client tier where publicly "
     "disclosed by the coach or client, and faculty or institutional appointments."),
]

MARKERS = [
    ("Originality", "An idea, distinction or framework the reader has not met elsewhere in restated "
     "form. “Five tips for better listening” scores nothing regardless of where it ran."),
    ("Specificity drawn from practice", "Concrete detail that could only come from someone doing the "
     "work — a real situation, the resistance encountered, what was tried and failed."),
    ("Transferability", "The reader can act on it. A sequence, a question set, a decision rule, a "
     "diagnostic — something operable rather than merely agreeable."),
    ("Intellectual honesty", "States the conditions under which the approach fails and the limits of "
     "the evidence. This is the clearest single separator between a thinker and a marketer."),
    ("Engagement with evidence", "Cites research, or reports the author's own observation "
     "systematically. Distinguishes assertion from finding."),
    ("Development over time", "The body of work shows ideas being revised, tested and sometimes "
     "abandoned — not one idea recycled across a decade of posts."),
]

GENEROSITY = [
    "Frameworks published in full rather than named and withheld behind a funnel.",
    "Free or open resources — tools, assessments, templates, full-text articles — available without an email gate.",
    "Substantive public answers to practitioners' questions, rather than a booking link.",
    "Attribution: crediting the originators of models used rather than presenting inherited frameworks as their own.",
    "Teaching other coaches — supervision, mentoring, faculty roles, contribution to professional bodies.",
]


def nomination_form():
    # Posts to the same Kit form as before. Kit records every submission as a
    # subscriber; there is no marketing opt-in on this form.
    return f"""<div class="formwrap">
<form id="nominate" method="post" action="https://app.kit.com/forms/9784201/subscriptions">
  <input type="hidden" name="fields[cin_source_site]" value="{S['domain']}">
  <label for="nom-name">Coach's full name *</label>
  <input type="text" id="nom-name" name="fields[cin_nominee_name]" required>

  <label for="nom-site">Their website</label>
  <input type="url" id="nom-site" name="fields[cin_nominee_website]" placeholder="https://">

  <label for="nom-li">Their LinkedIn</label>
  <input type="url" id="nom-li" name="fields[cin_nominee_linkedin]" placeholder="https://www.linkedin.com/in/">

  <label for="nom-why">Why do they qualify? *</label>
  <textarea id="nom-why" name="fields[cin_rationale]" required
    placeholder="Point us at specific published work where possible — what they wrote, where, and what was good about it."></textarea>

  <label for="sub-name">Your name *</label>
  <input type="text" id="sub-name" name="first_name" required>

  <label for="sub-email">Your email *</label>
  <input type="email" id="sub-email" name="email_address" required>

  <label for="sub-rel">Your relationship to them *</label>
  <select id="sub-rel" name="fields[cin_relationship]" required>
    <option value="">Please choose</option>
    <option value="self">This is me — I am nominating myself</option>
    <option value="colleague">Colleague or peer</option>
    <option value="client">Client</option>
    <option value="other">Other</option>
  </select>

  <button type="submit">Submit nomination</button>
</form>
</div>"""


def inserts():
    """Fixed parts of the pages that are the same on every site: the rubric
    itself and the nomination form."""
    rows = "".join('<tr><td class="w">%s</td><td><strong>%s</strong><br>%s</td></tr>' % r
                   for r in ABOUT_ROWS)
    return {
        "weights": '<table><thead><tr><th>Weight</th><th>Criterion</th></tr></thead>'
                   '<tbody>%s</tbody></table>' % rows,
        "markers": '<ul class="caveats">%s</ul>' % "".join(
            "<li><strong>%s.</strong> %s</li>" % m for m in MARKERS),
        "generosity": '<ul class="caveats">%s</ul>' % "".join("<li>%s</li>" % g for g in GENEROSITY),
        "form": nomination_form(),
    }


def blocks(spec):
    """The page wording from data/edition.json, block by block."""
    fixed = inserts()
    out = ['<h1 class="page-title">%s</h1>' % fill(spec["h1"])]
    for b in spec["blocks"]:
        if "meta" in b:
            out.append('<div class="meta">%s</div>' % fill(b["meta"]))
        elif "h2" in b:
            out.append("<h2>%s</h2>" % fill(b["h2"]))
        elif "p" in b:
            out.append("<p>%s</p>" % fill(b["p"]))
        elif "small" in b:
            out.append('<p class="small">%s</p>' % fill(b["small"]))
        elif "ul" in b:
            out.append('<ul class="caveats">%s</ul>' % "".join("<li>%s</li>" % fill(i) for i in b["ul"]))
        elif "insert" in b:
            out.append(fixed[b["insert"]])
        else:
            raise ValueError("unknown block in data/edition.json pages: %r" % b)
    return "\n".join(out)


def build_about():
    spec = P["about"]
    url = BASE + "/about.html"
    headline = plain(fill(spec["h1"]))
    article = {"@type": "Article", "@id": url + "#article", "url": url,
               "mainEntityOfPage": url, "headline": headline, "inLanguage": "en",
               "author": {"@id": CURATOR_ID}, "publisher": {"@id": CURATOR_ID},
               "datePublished": S["published"], "dateModified": LASTMOD,
               "isPartOf": {"@id": WEBSITE_ID}, "about": {"@id": WEBSITE_ID}}
    return page("about", "Methodology — " + S["title"],
                "The published rubric, weighting and verification standard behind the ranking.",
                blocks(spec), [article, breadcrumb(headline, url)])


def build_curator():
    spec = P["curator"]
    url = BASE + "/curator.html"
    name = plain(fill(spec["h1"]))
    about_page = {"@type": "AboutPage", "@id": url + "#webpage", "url": url, "name": name,
                  "inLanguage": "en", "isPartOf": {"@id": WEBSITE_ID},
                  "about": [{"@id": WEBSITE_ID}, {"@id": CURATOR_ID}],
                  "author": {"@id": CURATOR_ID}, "publisher": {"@id": CURATOR_ID}}
    return page("curator", "Curator — " + S["title"],
                "Who owns and curates this ranking, and on what basis.",
                blocks(spec), [about_page, breadcrumb(name, url)])


def build_nominate():
    spec = P["nominate"]
    url = BASE + "/nominate.html"
    name = plain(fill(spec["h1"]))
    webpage = {"@type": "WebPage", "@id": url + "#webpage", "url": url, "name": name,
               "inLanguage": "en", "isPartOf": {"@id": WEBSITE_ID},
               "publisher": {"@id": CURATOR_ID}}
    return page("nominate", "Nominate a coach — " + S["title"],
                "Nominate an executive coach for consideration in the next quarterly review.",
                blocks(spec), [webpage, breadcrumb(name, url)])


def llms_txt():
    """/llms.txt: what the site is, who is behind it, and its pages."""
    coaches = sorted(DATA["coaches"], key=lambda x: x["rank"])
    lines = [
        "# " + S["title"],
        "",
        "> %s Edition %s, published %s. This site is reviewed quarterly; the next review is %s. "
        "The ranking is curated and published by %s, who is not ranked on it. "
        "No coach pays for placement or is charged for inclusion."
        % (S["tagline"], S["edition"], S["published"], S["next_review"], S["curator"]),
        "",
        "## Pages",
        "",
        "- [%s](%s/): the ranking, %d coaches in rank order, with Ones to Watch, the coaches "
        "considered and not included, and what is still to be verified."
        % (S["title"], BASE, len(coaches)),
        "- [%s](%s/about.html): the published rubric, its weights, the interlink adjustment and "
        "the verification standard every entry is assessed against." % (plain(fill(P["about"]["h1"])), BASE),
        "- [%s](%s/curator.html): who owns, curates and publishes the ranking, with full disclosure."
        % (plain(fill(P["curator"]["h1"])), BASE),
        "- [%s](%s/nominate.html): how to nominate a coach for the next quarterly review; "
        "no payment is involved at any stage." % (plain(fill(P["nominate"]["h1"])), BASE),
        "",
        "## Ranked coaches",
        "",
    ]
    for c in coaches:
        lines.append("- [%s](%s/coaches/%s.html): ranked #%d. %s."
                     % (plain(c["name"]), BASE, c["slug"], c["rank"], plain(c["role"])))
    return "\n".join(lines) + "\n"


def main():
    os.makedirs(os.path.join(OUT, "coaches"), exist_ok=True)

    def w(p, c):
        with open(os.path.join(OUT, p), "w", encoding="utf-8", newline="\n") as f:
            f.write(c)

    pages = [("index.html", BASE + "/", build_index()),
             ("about.html", BASE + "/about.html", build_about()),
             ("curator.html", BASE + "/curator.html", build_curator()),
             ("nominate.html", BASE + "/nominate.html", build_nominate())]
    for c in DATA["coaches"]:
        pages.append(("coaches/" + c["slug"] + ".html",
                      BASE + "/coaches/" + c["slug"] + ".html", build_coach(c)))

    # Sitemap dates: a page keeps the date it last changed. data/lastmod.json
    # holds each page's content hash and date; a page whose hash has changed
    # since that file was written gets today's date.
    manifest = os.path.join(ROOT, "data", "lastmod.json")
    known = json.load(open(manifest, encoding="utf-8")) if os.path.exists(manifest) else {}
    today = datetime.date.today().isoformat()
    dates = {}
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, url, content in pages:
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        was = known.get(path) or {}
        date = was["lastmod"] if was.get("sha256") == digest and was.get("lastmod") else today
        dates[path] = {"sha256": digest, "lastmod": date}
        w(path, content.replace(LASTMOD, date))
        sm.append("<url><loc>%s</loc><lastmod>%s</lastmod></url>" % (url, date))
    sm.append("</urlset>")
    w("sitemap.xml", "\n".join(sm))
    with open(manifest, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(dates, indent=2, sort_keys=True) + "\n")

    shutil.copy(os.path.join(ROOT, "static", "style.css"), os.path.join(OUT, "style.css"))
    w("CNAME", S["domain"] + "\n")
    w(".nojekyll", "")
    w("robots.txt", "User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % BASE)
    w("llms.txt", llms_txt())

    print("built %d pages and llms.txt into %s" % (len(pages), OUT))


if __name__ == "__main__":
    main()
