#!/usr/bin/env python3
"""
Airtable -> research-hub.json

Builds the single published data file for the Research Recipe Hub. Two
consumers read it:

  1. embed.js on the hub landing pages (the interactive directory)
  2. webflow_sync.py, which renders the CMS pages from the same file

The JSON shape is the contract the prototype embed already speaks, so the
embed needs no reshaping beyond swapping its inlined DATA for a fetch:

  {
    "version", "commit",
    "methods":  { slug: {name, objective[], data, signal, effort, surface[],
                         tools[], related, desc, use, pros, cons,
                         considerations, resources[[title,url]], updated,
                         rid, seoTitle?, seoDesc?} },
    "recipes":  { slug: {name, outcome, problem, opp, opp2?, hmw, triggers[],
                         dstage, evidence, new?, desc,
                         stages[[stage,rationale,[methodSlug]]],
                         resources[[title,url]], updated, rid,
                         seoTitle?, seoDesc?} },
    "outcomes": [ {slug, name, metric, desc} ],
    "northStar": str,
    "tools":    { name: {cat, url, desc} },
    "toolCats": { name: cat },     # kept for embed backwards-compatibility
    "toolCount": int
  }

The script is strict on purpose. A method named in a recipe's Method sequence
that does not resolve to a real method is an error, not a silently unlinked
bit of plain text, because those links are the whole point of the cluster.
Any error fails the run and nothing is written.

Run locally:
    AIRTABLE_TOKEN=pat... python sync.py
    AIRTABLE_TOKEN=pat... python sync.py --dump-schema

Environment variables:
    AIRTABLE_TOKEN     required - PAT with data.records:read + schema.bases:read
    AIRTABLE_BASE_ID   default: apppcPYWsZzUeEOZ9
    OUTPUT_DIR         default: ./   (writes research-hub.json here)
    STRICT             default: "true"  ("false" downgrades errors to warnings)
"""

from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

try:
    from pyairtable import Api
except ImportError:
    print("ERROR: pyairtable not installed. Run: pip install 'pyairtable>=3,<4'", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

BASE_ID = os.environ.get("AIRTABLE_BASE_ID", "apppcPYWsZzUeEOZ9")
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "."))
STRICT = os.environ.get("STRICT", "true").lower() != "false"

TOKEN = os.environ.get("AIRTABLE_TOKEN")

# Table ids. Names would work too, but ids survive a table rename.
T = {
    "outcomes":      os.environ.get("AIRTABLE_OUTCOMES_TBL",      "tbl1GDFem7RFjIDnw"),
    "opportunities": os.environ.get("AIRTABLE_OPPORTUNITIES_TBL", "tbl6yzXOzhEoyir9Y"),
    "recipes":       os.environ.get("AIRTABLE_RECIPES_TBL",       "tbl3qhEltIf3QcEGV"),
    "methods":       os.environ.get("AIRTABLE_METHODS_TBL",       "tblfHb0hq34SkxmU0"),
    "tools":         os.environ.get("AIRTABLE_TOOLS_TBL",         "tbllxqVZpd3UwFInW"),
}

# Field names, one place. Rename a field in Airtable and you change it here,
# nowhere else. `python sync.py --dump-schema` prints the live field list.
F_OUTCOME = {
    "name": "Name", "level": "Level", "metric": "Metric", "desc": "Description",
}
F_OPPORTUNITY = {
    "name": "Name", "problem": "Customer problem", "hmw": "How might we",
    "outcome": "Outcome area", "stage": "Discovery stage",
    "triggers": "Triggers", "evidence": "Evidence strength",
}
F_RECIPE = {
    "name": "Name", "slug": "Slug", "desc": "Description",
    "methods": "Research Methods", "opportunities": "Opportunities",
    "sequence": "Method sequence", "resources": "Resources",
    # optional
    "new": "New", "seo_title": "Meta Title", "seo_desc": "Meta Description",
    "modified": "Last Modified",
}
F_METHOD = {
    "name": "Name", "slug": "Slug", "desc": "Description", "use": "Use Case/s",
    "pros": "Pros", "cons": "Cons", "considerations": "Considerations",
    "objective": "Objective", "data": "Primary Data Type",
    "signal": "Strength of Signal", "effort": "Effort", "tools": "Tools",
    "resources": "Resources", "surface": "Surface Area",
    # optional
    "related": "Related method", "seo_title": "Meta Title",
    "seo_desc": "Meta Description", "modified": "Last Modified",
}
F_TOOL = {
    "name": "Name", "cat": "Category", "desc": "Description", "url": "Website",
}

# Fields the run cannot proceed without.
REQUIRED = {
    "recipes": ["name", "slug", "desc", "sequence", "opportunities", "methods"],
    "methods": ["name", "slug", "desc"],
}

ERRORS: list[str] = []
WARNINGS: list[str] = []


def err(msg: str) -> None:
    ERRORS.append(msg)


def warn(msg: str) -> None:
    WARNINGS.append(msg)


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[()]", "", s)
    s = re.sub(r"[/&\\]", "-", s)
    s = re.sub(r"[^a-zA-Z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s).strip("-").lower()
    return re.sub(r"-+", "-", s)


def norm(s: str) -> str:
    """Loose key for matching a method name written in free text back to its
    record. Case, punctuation and & / and spelling all stop mattering."""
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii")
    s = s.lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, dict):
        return str(v.get("name", "")).strip()
    return str(v).strip()


def as_list(v) -> list[str]:
    """A single- or multi-select field as a clean list of labels."""
    if v is None:
        return []
    if isinstance(v, list):
        return [text(x) for x in v if text(x)]
    t = text(v)
    return [t] if t else []


def lines(v) -> list[str]:
    return [ln.strip() for ln in text(v).split("\n") if ln.strip()]


def parse_resources(v, where: str) -> list[list[str]]:
    """`Title: URL` (or `Title | URL`) per line -> [[title, url]].

    Split on the last separator before the scheme so a colon inside the title
    does not eat half the title.
    """
    out: list[list[str]] = []
    for ln in lines(v):
        m = re.match(r"^(.*?)\s*[|:]\s*(https?://\S+)$", ln)
        if not m:
            m = re.match(r"^(.*?)\s+(https?://\S+)$", ln)
        if m:
            title, url = m.group(1).strip().rstrip(":|").strip(), m.group(2).strip()
            if title and url:
                out.append([title, url])
                continue
        if ln.startswith("http"):
            out.append([ln, ln])
            continue
        warn(f"{where}: unparseable resource line, skipped: {ln!r}")
    return out


def parse_sequence(v, where: str, resolve) -> list[list]:
    """`Stage\\nRationale\\nMethods: A, B, C` blocks -> [[stage, rationale, [slug]]].

    Blocks are separated by a blank line. Anything that does not match the
    three-line shape is an error rather than a quiet drop.
    """
    raw = text(v)
    if not raw:
        err(f"{where}: Method sequence is empty")
        return []

    stages: list[list] = []
    for block in re.split(r"\n\s*\n", raw):
        rows = [ln.strip() for ln in block.split("\n") if ln.strip()]
        if len(rows) < 3:
            err(f"{where}: malformed Method sequence block: {block[:80]!r}")
            continue
        stage, rationale = rows[0], rows[1]
        methods_line = " ".join(rows[2:])
        m = re.match(r"^methods\s*:\s*(.+)$", methods_line, re.I)
        if not m:
            err(f"{where}: stage {stage!r} has no 'Methods:' line")
            continue
        if stage not in ("Explore", "Focus", "Validate"):
            err(f"{where}: unknown stage {stage!r} (expected Explore/Focus/Validate)")
            continue
        slugs = []
        for name in [n.strip() for n in m.group(1).split(",") if n.strip()]:
            slug = resolve(name)
            if slug:
                slugs.append(slug)
            else:
                err(f"{where}: stage {stage!r} names method {name!r}, which "
                    f"matches no record in Research Methods")
        if slugs:
            stages.append([stage, rationale, slugs])

    order = {"Explore": 0, "Focus": 1, "Validate": 2}
    stages.sort(key=lambda s: order.get(s[0], 9))
    return stages


def iso_date(v) -> str:
    return str(v)[:10] if v else ""


# ---------------------------------------------------------------------------
# AIRTABLE
# ---------------------------------------------------------------------------

def fetch_all() -> dict[str, dict[str, dict]]:
    """Every table as {record_id: fields}."""
    api = Api(TOKEN)
    base = api.base(BASE_ID)
    out: dict[str, dict[str, dict]] = {}
    for key, table_id in T.items():
        rows = base.table(table_id).all()
        out[key] = {r["id"]: r["fields"] for r in rows}
        print(f"  {key:14} {len(rows):3} records")
    return out


# ---------------------------------------------------------------------------
# TRANSFORM
# ---------------------------------------------------------------------------

def build_outcomes(rows: dict[str, dict]) -> tuple[list[dict], str, dict[str, str]]:
    """-> (outcome areas, north star description, {record_id: outcome slug})."""
    areas: list[dict] = []
    north_star = ""
    by_id: dict[str, str] = {}

    for rid, f in rows.items():
        name = text(f.get(F_OUTCOME["name"]))
        level = text(f.get(F_OUTCOME["level"]))
        if not name:
            continue
        if level == "North Star":
            north_star = text(f.get(F_OUTCOME["desc"]))
            by_id[rid] = slugify(name)
            continue
        slug = slugify(name)
        by_id[rid] = slug
        areas.append({
            "slug": slug,
            "name": name,
            "metric": text(f.get(F_OUTCOME["metric"])),
            "desc": text(f.get(F_OUTCOME["desc"])),
        })

    if not north_star:
        warn("Outcomes: no record with Level = 'North Star'")
    if not areas:
        err("Outcomes: no outcome areas found")

    order = {"acquisition": 0, "conversion": 1, "retention": 2, "foundational": 3}
    areas.sort(key=lambda a: (order.get(a["slug"], 9), a["name"]))
    return areas, north_star, by_id


def build_tools(rows: dict[str, dict]) -> tuple[dict[str, dict], dict[str, str]]:
    """-> ({tool name: {cat, url, desc}}, {record_id: tool name})."""
    tools: dict[str, dict] = {}
    by_id: dict[str, str] = {}
    for rid, f in rows.items():
        name = text(f.get(F_TOOL["name"]))
        if not name:
            continue
        by_id[rid] = name
        tools[name] = {
            "cat": text(f.get(F_TOOL["cat"])),
            "url": text(f.get(F_TOOL["url"])),
            "desc": text(f.get(F_TOOL["desc"])),
        }
    return tools, by_id


def build_methods(rows: dict[str, dict], tool_names: dict[str, str]) -> tuple[dict[str, dict], dict[str, str], dict[str, str]]:
    """-> (methods by slug, {record_id: slug}, {normalised name: slug})."""
    methods: dict[str, dict] = {}
    by_id: dict[str, str] = {}
    by_name: dict[str, str] = {}

    for rid, f in rows.items():
        name = text(f.get(F_METHOD["name"]))
        slug = text(f.get(F_METHOD["slug"]))
        where = f"Research Methods/{name or rid}"

        for key in REQUIRED["methods"]:
            if not text(f.get(F_METHOD[key])):
                err(f"{where}: required field {F_METHOD[key]!r} is empty")
        if not name or not slug:
            continue
        if slug in methods:
            err(f"{where}: duplicate slug {slug!r}")
            continue

        data_types = as_list(f.get(F_METHOD["data"]))
        m = {
            "name": name,
            "objective": as_list(f.get(F_METHOD["objective"])),
            "data": " / ".join(data_types),
            "signal": text(f.get(F_METHOD["signal"])),
            "effort": text(f.get(F_METHOD["effort"])),
            "surface": as_list(f.get(F_METHOD["surface"])),
            "tools": [tool_names[t] for t in (f.get(F_METHOD["tools"]) or [])
                      if t in tool_names],
            "related": None,
            "desc": text(f.get(F_METHOD["desc"])),
            "use": text(f.get(F_METHOD["use"])),
            "pros": text(f.get(F_METHOD["pros"])),
            "cons": text(f.get(F_METHOD["cons"])),
            "considerations": text(f.get(F_METHOD["considerations"])),
            "resources": parse_resources(f.get(F_METHOD["resources"]), where),
            "updated": iso_date(f.get(F_METHOD["modified"])),
            "rid": rid,
            "_related_rid": (f.get(F_METHOD["related"]) or [None])[0],
        }
        for src, dst in (("seo_title", "seoTitle"), ("seo_desc", "seoDesc")):
            v = text(f.get(F_METHOD[src]))
            if v:
                m[dst] = v

        if not m["objective"]:
            warn(f"{where}: no Objective set; it will not appear under any stage filter")

        methods[slug] = m
        by_id[rid] = slug
        by_name[norm(name)] = slug

    # Second pass: the optional self-link, now that every slug is known.
    for slug, m in methods.items():
        related_rid = m.pop("_related_rid", None)
        if related_rid and related_rid in by_id:
            m["related"] = by_id[related_rid]

    return methods, by_id, by_name


def build_recipes(rows, opportunities, outcome_slugs, method_by_id, method_by_name) -> dict[str, dict]:
    def resolve(name: str) -> str | None:
        return method_by_name.get(norm(name))

    recipes: dict[str, dict] = {}
    for rid, f in rows.items():
        name = text(f.get(F_RECIPE["name"]))
        slug = text(f.get(F_RECIPE["slug"]))
        where = f"Recipes/{name or rid}"

        for key in REQUIRED["recipes"]:
            if not f.get(F_RECIPE[key]):
                err(f"{where}: required field {F_RECIPE[key]!r} is empty")
        if not name or not slug:
            continue
        if slug in recipes:
            err(f"{where}: duplicate slug {slug!r}")
            continue

        opp_ids = f.get(F_RECIPE["opportunities"]) or []
        opps = [opportunities[i] for i in opp_ids if i in opportunities]
        if not opps:
            err(f"{where}: links no Opportunity, so the page has no problem block")
            continue
        primary = opps[0]

        outcome_ids = primary.get(F_OPPORTUNITY["outcome"]) or []
        outcome = outcome_slugs.get(outcome_ids[0]) if outcome_ids else ""
        if not outcome:
            err(f"{where}: opportunity {text(primary.get(F_OPPORTUNITY['name']))!r} "
                f"has no Outcome area")

        stages = parse_sequence(f.get(F_RECIPE["sequence"]), where, resolve)

        # The link field and the sequence text describe the same relationship.
        # If they disagree, someone edited one and forgot the other.
        linked = {method_by_id[i] for i in (f.get(F_RECIPE["methods"]) or [])
                  if i in method_by_id}
        sequenced = {s for st in stages for s in st[2]}
        for missing in sorted(linked - sequenced):
            err(f"{where}: {missing!r} is in the Research Methods link field but "
                f"not in Method sequence")
        for missing in sorted(sequenced - linked):
            err(f"{where}: {missing!r} is in Method sequence but not in the "
                f"Research Methods link field")

        r = {
            "name": name,
            "outcome": outcome,
            "problem": text(primary.get(F_OPPORTUNITY["problem"])),
            "opp": text(primary.get(F_OPPORTUNITY["name"])),
            "hmw": text(primary.get(F_OPPORTUNITY["hmw"])),
            "triggers": lines(primary.get(F_OPPORTUNITY["triggers"])),
            "dstage": text(primary.get(F_OPPORTUNITY["stage"])),
            "evidence": text(primary.get(F_OPPORTUNITY["evidence"])),
            "desc": text(f.get(F_RECIPE["desc"])),
            "stages": stages,
            "resources": parse_resources(f.get(F_RECIPE["resources"]), where),
            "updated": iso_date(f.get(F_RECIPE["modified"])),
            "rid": rid,
        }
        if len(opps) > 1:
            r["opp2"] = text(opps[1].get(F_OPPORTUNITY["name"]))
        if f.get(F_RECIPE["new"]):
            r["new"] = True
        for src, dst in (("seo_title", "seoTitle"), ("seo_desc", "seoDesc")):
            v = text(f.get(F_RECIPE[src]))
            if v:
                r[dst] = v

        recipes[slug] = r

    return recipes


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    print(f"Fetching base {BASE_ID}...")
    tables = fetch_all()

    outcomes, north_star, outcome_slugs = build_outcomes(tables["outcomes"])
    tools, tool_names = build_tools(tables["tools"])
    methods, method_by_id, method_by_name = build_methods(tables["methods"], tool_names)
    recipes = build_recipes(tables["recipes"], tables["opportunities"],
                            outcome_slugs, method_by_id, method_by_name)

    # Every outcome slug a recipe points at has to exist, or the embed throws.
    known = {o["slug"] for o in outcomes}
    for slug, r in recipes.items():
        if r["outcome"] and r["outcome"] not in known:
            err(f"Recipes/{r['name']}: outcome {r['outcome']!r} is not an outcome area")

    orphans = sorted(set(methods) - {s for r in recipes.values() for st in r["stages"] for s in st[2]})
    for o in orphans:
        warn(f"Research Methods/{methods[o]['name']}: used by no recipe, so its "
             f"page will have an empty 'Recipes that use this' section")

    for w in WARNINGS:
        print(f"  WARN  {w}", file=sys.stderr)
    for e in ERRORS:
        print(f"  ERROR {e}", file=sys.stderr)

    if ERRORS and STRICT:
        print(f"\n{len(ERRORS)} error(s). Nothing written. Fix Airtable and re-run, "
              f"or set STRICT=false to publish anyway.", file=sys.stderr)
        sys.exit(1)

    out = {
        "version": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commit": os.environ.get("GITHUB_SHA", "local"),
        "methods": methods,
        "outcomes": outcomes,
        "northStar": north_star,
        "recipes": recipes,
        "tools": tools,
        "toolCats": {name: t["cat"] for name, t in tools.items()},
        "toolCount": len(tools),
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / "research-hub.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(f"\nWrote {path} ({path.stat().st_size / 1024:.1f} KB)")
    print(f"  {len(recipes)} recipes, {len(methods)} methods, {len(outcomes)} outcome "
          f"areas, {len(tools)} tools, {len(WARNINGS)} warning(s)")


def dump_schema() -> None:
    api = Api(TOKEN)
    base = api.base(BASE_ID)
    for key, table_id in T.items():
        print(f"\n== {key} ({table_id})")
        for field in base.table(table_id).schema().fields:
            print(f"   {field.id}  {field.type:24} {field.name}")


if __name__ == "__main__":
    if not TOKEN:
        print("ERROR: AIRTABLE_TOKEN env var required", file=sys.stderr)
        sys.exit(1)
    if "--dump-schema" in sys.argv:
        dump_schema()
        sys.exit(0)
    main()
