#!/usr/bin/env python3
"""
Pure rendering helpers: research-hub.json -> Webflow-ready HTML and JSON-LD.

No network, no Airtable, no Webflow. Everything here is a function of the
published JSON, so it can be exercised offline (see selftest.py).

Two rules shape this file.

  1. Webflow RichText accepts a narrow HTML subset: headings, paragraphs,
     lists, anchors, strong/em, blockquote, code. Anything structural belongs
     in the page template, not in a field. So nothing here emits a div, a
     class, a style or a script.

  2. Nothing is invented. Sub-headings come from the labels authors wrote in
     Airtable, verbatim. FAQ entries are generated only for labels that are
     already phrased as questions, because turning "Sample size" into "How
     many participants do you need?" is an editorial call, not a string
     transformation.
"""

from __future__ import annotations

import html
import json
import re

SITE = "https://speero.com"
RECIPE_BASE = "/research-recipes/"
METHOD_BASE = "/research-methods/"
TOOLS_HUB = "/ab-testing-tools/"

# Cross-hub pairs, per the link rules in research-hub-seo-aeo-spec.md section 7.
# Keyed by method slug. The testing tools hub is the only live sibling today;
# blueprint pairings go here as they are agreed.
CROSS_HUB = {
    "ab-testing": ("A/B Testing Tools Comparison",
                   "/ab-testing-tools",
                   "Compare the platforms that run these tests, with pricing, "
                   "SDKs and warehouse support side by side."),
}

ORG = {
    "@type": "Organization",
    "name": "Speero",
    "url": SITE,
}


# ---------------------------------------------------------------------------
# TEXT -> HTML
# ---------------------------------------------------------------------------

def esc(s) -> str:
    return html.escape(str(s or ""), quote=False)


def _inline(s: str) -> str:
    """Escape, then honour the only two markdown marks authors actually use."""
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
    return s


def paragraphs(raw: str) -> str:
    """Blank-line-separated text -> <p> per block, single newlines as <br>.

    Lines starting with `- ` or `* ` inside a block become a list instead, so
    the Airtable fields that are already written as bullets render as bullets.
    """
    out: list[str] = []
    for block in re.split(r"\n\s*\n", (raw or "").strip()):
        rows = [r.strip() for r in block.split("\n") if r.strip()]
        if not rows:
            continue
        if all(re.match(r"^[-*•]\s+", r) for r in rows):
            items = "".join(f"<li>{_inline(re.sub(r'^[-*•]\s+', '', r))}</li>" for r in rows)
            out.append(f"<ul>{items}</ul>")
        else:
            out.append("<p>" + "<br>".join(_inline(r) for r in rows) + "</p>")
    return "".join(out)


def labelled_sections(raw: str) -> str:
    """Considerations and friends: `Label\\nBody...` blocks -> <h3> + <p>.

    A block whose first line is short and unpunctuated is treated as a label.
    A block that is just prose stays prose, so a field written without labels
    still renders correctly.
    """
    out: list[str] = []
    for block in re.split(r"\n\s*\n", (raw or "").strip()):
        rows = [r.strip() for r in block.split("\n") if r.strip()]
        if not rows:
            continue
        head, rest = rows[0], rows[1:]
        if rest and _is_label(head):
            out.append(f"<h3>{_inline(head)}</h3>")
            out.append(paragraphs("\n".join(rest)))
        else:
            out.append(paragraphs("\n".join(rows)))
    return "".join(out)


def _is_label(line: str) -> bool:
    """A sub-heading, not a sentence. Short, and not ended like prose."""
    if len(line) > 70:
        return False
    return not line.endswith((".", ",", ";", ":")) or line.endswith("?")


def labelled_pairs(raw: str) -> list[tuple[str, str]]:
    """The same blocks as (label, body text) pairs, for FAQ schema."""
    pairs: list[tuple[str, str]] = []
    for block in re.split(r"\n\s*\n", (raw or "").strip()):
        rows = [r.strip() for r in block.split("\n") if r.strip()]
        if len(rows) >= 2 and _is_label(rows[0]):
            pairs.append((rows[0], " ".join(rows[1:])))
    return pairs


def bullets(items: list[str]) -> str:
    items = [i for i in (items or []) if str(i).strip()]
    if not items:
        return ""
    return "<ul>" + "".join(f"<li>{_inline(i)}</li>" for i in items) + "</ul>"


def links(pairs: list[list[str]]) -> str:
    """[[title, url]] -> a list of anchors. Used for Resources."""
    pairs = [p for p in (pairs or []) if len(p) == 2 and p[1]]
    if not pairs:
        return ""
    items = "".join(
        f'<li><a href="{esc(url)}">{_inline(title)}</a></li>' for title, url in pairs
    )
    return f"<ul>{items}</ul>"


NO_VALIDATE_NOTE = (
    "Where's Validate? For this problem, validation lands in the "
    "experimentation programme itself: the hypotheses this research produces "
    "become A/B tests and product bets, measured against the outcome metric."
)


def sequence_html(stages: list, methods: dict) -> str:
    """[[stage, rationale, [slug]]] -> <h3> stage, <p> rationale, linked <ul>.

    This is the field the whole recipe page turns on. A nested Collection List
    could not carry the stage grouping or the rationale, so the sequence is
    rendered here instead.

    The H2 is the stage names joined ("Explore. Focus. Validate."), which is
    both the wireframe's heading and an accurate summary of what follows. It
    lives in the field rather than the template for the reason in titled():
    a recipe with no stages then renders nothing at all rather than a bare
    heading.

    A recipe that stops before Validate gets the explanatory note, as a
    blockquote because that is the only callout shape RichText allows.
    """
    out: list[str] = []
    names = [stage for stage, _, _ in stages or []]
    if not names:
        return ""
    out.append(f"<h2>{esc('. '.join(names))}.</h2>")
    for stage, rationale, slugs in stages or []:
        out.append(f"<h3>{esc(stage)}</h3>")
        if rationale:
            out.append(f"<p>{_inline(rationale)}</p>")
        items = []
        for slug in slugs:
            m = methods.get(slug)
            if not m:
                continue
            items.append(
                f'<li><a href="{METHOD_BASE}{esc(slug)}">{_inline(m["name"])}</a></li>'
            )
        if items:
            out.append("<ul>" + "".join(items) + "</ul>")
    if "Validate" not in names:
        out.append(f"<blockquote>{_inline(NO_VALIDATE_NOTE)}</blockquote>")
    return "".join(out)


def chip_list(values: list[str]) -> str:
    """Values -> a list, one item each, for the chip rows under a heading.

    The facts panel wants these joined into one line, the chips under the H1
    want one pill per value, and a comma-joined string cannot be split back
    apart in CSS. So the two shapes are two fields rather than one.
    """
    items = "".join(f"<li>{_inline(v)}</li>" for v in values or [] if v)
    return f"<ul>{items}</ul>" if items else ""


def paired_html(related_slug: str, methods: dict) -> str:
    """The "often paired with" line, or nothing when there is no pairing.

    17 of 29 methods carry one. The sentence lives in the field so the 12
    without a pairing render nothing, rather than a dangling label.
    """
    m = (methods or {}).get(related_slug or "")
    if not m:
        return ""
    return (f'<p>Often paired with <a href="{METHOD_BASE}{esc(related_slug)}">'
            f'<strong>{_inline(m["name"])}</strong></a>.</p>')


def tools_html(tool_names: list[str], tools: dict, vendor_pages: dict | None = None) -> str:
    """Tool names -> links.

    A tool that already has a page on the A/B Testing Tools hub links there
    instead of outward. That is the cross-hub link the SEO spec asks for, and
    it keeps the authority on speero.com rather than passing it to a vendor.
    Everything else links to the vendor site, nofollowed.
    """
    vendor_pages = vendor_pages or {}
    items = []
    for name in tool_names or []:
        label = _inline(name)
        slug = vendor_pages.get(name.lower())
        if slug:
            items.append(f'<li><a href="{TOOLS_HUB}{esc(slug)}">{label}</a></li>')
            continue
        url = (tools.get(name) or {}).get("url")
        items.append(f'<li><a href="{esc(url)}" rel="nofollow">{label}</a></li>'
                     if url else f"<li>{label}</li>")
    return "<ul>" + "".join(items) + "</ul>" if items else ""


def titled(heading: str, body: str) -> str:
    """Put the H2 inside the generated field, not in the template.

    Webflow's conditional visibility is a Designer-only control with no API
    equivalent, so a static heading above an empty field renders bare. Making
    the heading part of the content means an empty field produces nothing at
    all, on every page, with no manual step.
    """
    return f"<h2>{esc(heading)}</h2>{body}" if body else ""


def cross_hub_html(slug: str) -> str:
    """The cross-hub slot. Renders only where a pairing exists."""
    pair = CROSS_HUB.get(slug)
    if not pair:
        return ""
    name, url, blurb = pair
    return (f'<p>{_inline(blurb)} '
            f'<a href="{esc(url)}"><strong>{_inline(name)}</strong></a></p>')


def recipe_links(slugs_and_names: list[tuple[str, str]]) -> str:
    items = "".join(
        f'<li><a href="{RECIPE_BASE}{esc(slug)}">{_inline(name)}</a></li>'
        for slug, name in slugs_and_names
    )
    return f"<ul>{items}</ul>" if items else ""


# ---------------------------------------------------------------------------
# META
# ---------------------------------------------------------------------------

def first_sentence(raw: str) -> str:
    s = " ".join((raw or "").split())
    m = re.match(r"^.*?[.!?](?=\s|$)", s)
    return (m.group(0) if m else s).strip()


def meta_description(raw: str, limit: int = 155, floor: int = 90) -> str:
    """Whole sentences up to the limit, never cut mid-word, never padded.

    A single short opening sentence makes a thin snippet, so sentences are
    added while they still fit. Nothing is invented to reach a length: if the
    source is short, the description is short.
    """
    s = " ".join((raw or "").split())
    if not s:
        return ""
    if len(s) <= limit:
        return s

    sentences = re.findall(r"[^.!?]+[.!?]?", s)
    out = ""
    for sentence in sentences:
        candidate = (out + sentence).strip()
        if len(candidate) > limit:
            break
        out = candidate
        if len(out) >= floor:
            break
    if out:
        return out

    cut = s[:limit].rsplit(" ", 1)[0].rstrip(" ,;:-")
    return cut + "..."


def meta_title(name: str, suffix: str, limit: int = 60) -> str:
    full = f"{name} {suffix}".strip()
    return full if len(full) <= limit else name


# ---------------------------------------------------------------------------
# JSON-LD
# ---------------------------------------------------------------------------

def _breadcrumb(trail: list[tuple[str, str]]) -> dict:
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": name,
             "item": SITE + path}
            for i, (name, path) in enumerate(trail)
        ],
    }


def _article(name: str, description: str, url: str, updated: str) -> dict:
    a = {
        "@type": "Article",
        "headline": name,
        "description": description,
        "url": SITE + url,
        "author": ORG,
        "publisher": ORG,
        "mainEntityOfPage": {"@type": "WebPage", "@id": SITE + url},
    }
    if updated:
        a["dateModified"] = updated
        a["datePublished"] = updated
    return a


def method_jsonld(slug: str, m: dict) -> str:
    url = METHOD_BASE + slug
    graph = [
        _article(m["name"], first_sentence(m.get("desc", "")), url, m.get("updated", "")),
        _breadcrumb([
            ("Home", "/"),
            ("Research methods", METHOD_BASE.rstrip("/")),
            (m["name"], url),
        ]),
    ]
    return _dump(graph)


def method_faq_jsonld(m: dict) -> str:
    """FAQPage, but only from Considerations labels already written as questions."""
    qas = [(q, a) for q, a in labelled_pairs(m.get("considerations", "")) if q.endswith("?")]
    if not qas:
        return ""
    return _dump([{
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in qas
        ],
    }])


def recipe_jsonld(slug: str, r: dict, methods: dict) -> str:
    url = RECIPE_BASE + slug
    ordered = [s for st in r.get("stages", []) for s in st[2]]
    graph = [
        _article(r["name"], first_sentence(r.get("desc", "")), url, r.get("updated", "")),
        _breadcrumb([
            ("Home", "/"),
            ("Research recipes", RECIPE_BASE.rstrip("/")),
            (r["name"], url),
        ]),
    ]
    if ordered:
        graph.append({
            "@type": "ItemList",
            "name": f"Method sequence for {r['name']}",
            "itemListOrder": "https://schema.org/ItemListOrderAscending",
            "numberOfItems": len(ordered),
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1,
                 "name": methods[s]["name"], "url": SITE + METHOD_BASE + s}
                for i, s in enumerate(ordered) if s in methods
            ],
        })
    return _dump(graph)


def _dump(graph: list[dict]) -> str:
    """One compact @graph block. Compact because it goes in a CMS field."""
    return json.dumps({"@context": "https://schema.org", "@graph": graph},
                      ensure_ascii=False, separators=(",", ":"))


# ---------------------------------------------------------------------------
# FIELD BUILDERS  (what actually gets PATCHed into Webflow)
# ---------------------------------------------------------------------------

def method_fields(slug: str, m: dict, data: dict) -> dict:
    used = sorted(
        ((s, r["name"]) for s, r in data["recipes"].items()
         if any(slug in st[2] for st in r["stages"])),
        key=lambda p: p[1],
    )
    fd = {
        "name": m["name"],
        "slug": slug,
        "description": paragraphs(m.get("desc", "")),
        "objective": ", ".join(m.get("objective", [])),
        "primary-data-type": m.get("data", ""),
        "strength-of-signal": m.get("signal", ""),
        "effort": m.get("effort", ""),
        "surface-area": ", ".join(m.get("surface", [])),
        "use-cases": paragraphs(m.get("use", "")),
        "pros": paragraphs(m.get("pros", "")),
        "cons": paragraphs(m.get("cons", "")),
        "considerations": titled("Practical considerations",
                                 labelled_sections(m.get("considerations", ""))),
        # "Tools" rather than "Common tools": this block sits in the facts
        # panel beside the method, where the wireframe labels it Tools. The
        # fallback keeps the label honest on the three methods that need no
        # dedicated tool, instead of showing a heading over nothing.
        "tools": titled("Tools",
                        tools_html(m.get("tools", []), data.get("tools", {}),
                                   data.get("vendorPages", {}))
                        or "<p>Runs on your existing systems; no dedicated "
                           "tool required.</p>"),
        "often-paired-with": paired_html(m.get("related", ""), data["methods"]),
        # One pill per objective under the H1. The joined string above still
        # feeds the facts panel, which the wireframe writes as one line.
        "objective-chips": chip_list(m.get("objective", [])),
        "cross-hub": cross_hub_html(slug),
        "resources": titled("Go deeper", links(m.get("resources", []))),
        "used-by-recipes": recipe_links(used),
        "page-url": METHOD_BASE + slug,
        "meta-title": m.get("seoTitle") or meta_title(m["name"], "| Speero research methods"),
        "meta-description": m.get("seoDesc") or meta_description(m.get("desc", "")),
        "schema-jsonld": method_jsonld(slug, m),
        "faq-jsonld": method_faq_jsonld(m),
    }
    if m.get("updated"):
        fd["last-modified"] = m["updated"]
    return fd


def recipe_fields(slug: str, r: dict, data: dict) -> dict:
    outcome = next((o["name"] for o in data["outcomes"] if o["slug"] == r.get("outcome")), "")
    fd = {
        "name": r["name"],
        "slug": slug,
        "description": paragraphs(r.get("desc", "")),
        "opportunity-name": r.get("opp", ""),
        "customer-problem": r.get("problem", ""),
        "how-might-we": r.get("hmw", ""),
        "triggers": bullets(r.get("triggers", [])),
        "outcome-area": outcome,
        "discovery-stage": r.get("dstage", ""),
        "evidence-strength": r.get("evidence", ""),
        "method-sequence": sequence_html(r.get("stages", []), data["methods"]),
        "also-solves": r.get("opp2", ""),
        "resources": titled("Go deeper", links(r.get("resources", []))),
        "page-url": RECIPE_BASE + slug,
        "meta-title": r.get("seoTitle") or meta_title(r["name"], "| Speero research recipes"),
        "meta-description": r.get("seoDesc") or meta_description(r.get("desc", "")),
        "schema-jsonld": recipe_jsonld(slug, r, data["methods"]),
    }
    if r.get("updated"):
        fd["last-modified"] = r["updated"]
    return fd


# ---------------------------------------------------------------------------
# LANDING PAGE SCHEMA
# ---------------------------------------------------------------------------

def landing_jsonld(kind: str, data: dict) -> dict:
    """WebSite + Organization + ItemList for a hub landing page.

    Built as plain JSON with no CMS tokens, because Webflow escapes token
    values inside a script element and the Data API rejects anything that is
    not valid JSON. The sync rewrites this every run, so the ItemList stays
    current as recipes and methods are added.
    """
    if kind == "problems":
        # Problems have no pages of their own, so each entry points at the
        # recipe prescribed for it. That is the routing the page is for.
        ordered = sorted(
            ((r["opp"], RECIPE_BASE + slug) for slug, r in data["recipes"].items() if r.get("opp")),
            key=lambda pair: pair[0])
        path, name = "/research-problems", "Research problems"
        desc = ("Customer problems in the customer's own words, each routed to "
                "the research recipe written for it.")
        return {
            "@context": "https://schema.org",
            "@graph": [
                {"@type": "WebSite", "@id": SITE + "/#website", "url": SITE,
                 "name": "Speero", "publisher": {"@id": SITE + "/#organization"}},
                {"@type": "Organization", "@id": SITE + "/#organization",
                 "name": "Speero", "url": SITE},
                {"@type": "CollectionPage", "@id": SITE + path, "url": SITE + path,
                 "name": name, "description": desc,
                 "isPartOf": {"@id": SITE + "/#website"},
                 "publisher": {"@id": SITE + "/#organization"}},
                {"@type": "BreadcrumbList", "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE},
                    {"@type": "ListItem", "position": 2, "name": name, "item": SITE + path},
                ]},
                {"@type": "ItemList", "name": name, "numberOfItems": len(ordered),
                 "itemListElement": [
                     {"@type": "ListItem", "position": i + 1, "name": opp,
                      "url": SITE + url}
                     for i, (opp, url) in enumerate(ordered)
                 ]},
            ],
        }

    if kind == "recipes":
        items, base, path = data["recipes"], RECIPE_BASE, "/research-recipes"
        name = "Research recipes"
        desc = ("Every Speero research recipe: the customer problem it answers "
                "and the sequence of methods that answers it.")
    else:
        items, base, path = data["methods"], METHOD_BASE, "/research-methods"
        name = "Research methods"
        desc = ("Every research method in the Speero library, with what it is "
                "for, the strength of its signal and what it costs in effort.")

    ordered = sorted(items.items(), key=lambda kv: kv[1]["name"])
    return {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "WebSite", "@id": SITE + "/#website", "url": SITE,
             "name": "Speero", "publisher": {"@id": SITE + "/#organization"}},
            {"@type": "Organization", "@id": SITE + "/#organization",
             "name": "Speero", "url": SITE},
            {"@type": "CollectionPage", "@id": SITE + path, "url": SITE + path,
             "name": name, "description": desc,
             "isPartOf": {"@id": SITE + "/#website"},
             "publisher": {"@id": SITE + "/#organization"}},
            {"@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE},
                {"@type": "ListItem", "position": 2, "name": name, "item": SITE + path},
            ]},
            {"@type": "ItemList", "name": name, "numberOfItems": len(ordered),
             "itemListElement": [
                 {"@type": "ListItem", "position": i + 1, "name": it["name"],
                  "url": SITE + base + slug}
                 for i, (slug, it) in enumerate(ordered)
             ]},
        ],
    }
