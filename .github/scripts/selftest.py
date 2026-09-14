#!/usr/bin/env python3
"""
Offline check on the rendering layer. No Airtable, no Webflow, no secrets.

Runs render.py over a data file (the committed fixture by default) and asserts
the things that would quietly break a page rather than throw: unresolvable
internal links, JSON-LD that is not valid JSON, HTML tags Webflow's RichText
will strip, empty required fields, over-long meta.

    python .github/scripts/selftest.py
    python .github/scripts/selftest.py research-hub.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import render  # noqa: E402

# Webflow RichText keeps this subset and silently drops the rest.
ALLOWED_TAGS = {"p", "br", "strong", "em", "ul", "ol", "li", "a",
                "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "code", "pre"}

REQUIRED_METHOD = ["name", "slug", "description", "meta-title", "meta-description",
                   "schema-jsonld"]
REQUIRED_RECIPE = ["name", "slug", "description", "opportunity-name",
                   "method-sequence", "meta-title", "meta-description",
                   "schema-jsonld"]

failures: list[str] = []
notes: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)


def check_html(where: str, field: str, value: str) -> None:
    for tag in set(re.findall(r"<\s*([a-zA-Z0-9]+)", value or "")):
        if tag.lower() not in ALLOWED_TAGS:
            fail(f"{where}.{field}: <{tag}> is not kept by Webflow RichText")
    if 'class="' in (value or "") or "style=" in (value or ""):
        fail(f"{where}.{field}: carries class/style, which RichText strips")


def check_jsonld(where: str, field: str, value: str) -> None:
    if not value:
        return
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as e:
        fail(f"{where}.{field}: not valid JSON ({e})")
        return
    if "@context" not in parsed or "@graph" not in parsed:
        fail(f"{where}.{field}: missing @context/@graph")
    for node in parsed.get("@graph", []):
        if "@type" not in node:
            fail(f"{where}.{field}: a node has no @type")


def main(path: str) -> int:
    data = json.loads(Path(path).read_text())
    methods, recipes = data["methods"], data["recipes"]
    print(f"Checking {path}: {len(recipes)} recipes, {len(methods)} methods\n")

    method_hrefs, recipe_hrefs = set(), set()

    for slug, m in methods.items():
        where = f"method:{slug}"
        fd = render.method_fields(slug, m, data)
        for key in REQUIRED_METHOD:
            if not fd.get(key):
                fail(f"{where}.{key}: empty")
        for key, value in fd.items():
            if isinstance(value, str) and "<" in value:
                check_html(where, key, value)
        check_jsonld(where, "schema-jsonld", fd["schema-jsonld"])
        check_jsonld(where, "faq-jsonld", fd["faq-jsonld"])
        if len(fd["meta-title"]) > 60:
            fail(f"{where}.meta-title: {len(fd['meta-title'])} chars (>60)")
        if len(fd["meta-description"]) > 160:
            fail(f"{where}.meta-description: {len(fd['meta-description'])} chars (>160)")
        recipe_hrefs |= set(re.findall(r'href="/research-recipes/([^"]+)"',
                                       fd["used-by-recipes"]))
        if not fd["used-by-recipes"]:
            notes.append(f"{where}: used by no recipe")
        if not fd["resources"]:
            notes.append(f"{where}: no resources, 'Go deeper' will not render")

    for slug, r in recipes.items():
        where = f"recipe:{slug}"
        fd = render.recipe_fields(slug, r, data)
        for key in REQUIRED_RECIPE:
            if not fd.get(key):
                fail(f"{where}.{key}: empty")
        for key, value in fd.items():
            if isinstance(value, str) and "<" in value:
                check_html(where, key, value)
        check_jsonld(where, "schema-jsonld", fd["schema-jsonld"])
        if len(fd["meta-title"]) > 60:
            fail(f"{where}.meta-title: {len(fd['meta-title'])} chars (>60)")
        if len(fd["meta-description"]) > 160:
            fail(f"{where}.meta-description: {len(fd['meta-description'])} chars (>160)")
        method_hrefs |= set(re.findall(r'href="/research-methods/([^"]+)"',
                                       fd["method-sequence"]))
        if not fd["resources"]:
            notes.append(f"{where}: no resources, 'Go deeper' will not render")

    for slug in sorted(method_hrefs - set(methods)):
        fail(f"a recipe links /research-methods/{slug}, which has no CMS item")
    for slug in sorted(recipe_hrefs - set(recipes)):
        fail(f"a method links /research-recipes/{slug}, which has no CMS item")

    by_kind: dict[str, int] = {}
    for n in notes:
        by_kind[n.split(": ", 1)[1]] = by_kind.get(n.split(": ", 1)[1], 0) + 1
    for kind, count in sorted(by_kind.items()):
        print(f"  note: {count} x {kind}")

    print()
    if failures:
        for f in failures:
            print(f"  FAIL {f}")
        print(f"\n{len(failures)} failure(s).")
        return 1
    print(f"All checks passed. {len(method_hrefs)} method links and "
          f"{len(recipe_hrefs)} recipe links resolve.")
    return 0


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else str(
        Path(__file__).parents[2] / "research-hub.json")
    sys.exit(main(target))
