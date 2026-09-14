#!/usr/bin/env python3
"""
research-hub.json -> markdown mirrors, llms.txt, llms-full.txt.

Section 6 of research-hub-seo-aeo-spec.md, and its own honest framing: these
files are a byproduct of a sync job we were writing anyway, not the strategy.
As of 2026 the major answer engines do not reliably fetch llms.txt, and it
does not measurably move citations. What it does serve is the agentic layer,
where IDE agents and coding tools fetch these routinely.

One constraint the spec already names: Webflow cannot serve arbitrary file
paths, so llms.txt cannot live at speero.com/llms.txt without a proxy in
front. These are published to the CDN instead, which is where an agent that
has found the hub can reach them.

    python .github/scripts/publish_assets.py [research-hub.json]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import render  # noqa: E402

OUT = Path(".")
CDN = "https://cdn.jsdelivr.net/gh/speerotools/research-hub-data@main"


def strip_html(html: str) -> str:
    import re
    text = re.sub(r"<li>", "\n- ", html or "")
    text = re.sub(r"</(p|h[1-6]|ul|ol|li)>", "\n", text)
    text = re.sub(r"<h3[^>]*>", "\n### ", text)
    text = re.sub(r'<a href="([^"]+)"[^>]*>(.*?)</a>', r"[\2](\1)", text, flags=re.S)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def method_md(slug: str, m: dict, data: dict) -> str:
    f = render.method_fields(slug, m, data)
    parts = [f"# {m['name']}", "", strip_html(f["description"]), ""]
    parts += [
        "| | |", "|---|---|",
        f"| Stage | {f['objective']} |",
        f"| Data type | {f['primary-data-type']} |",
        f"| Strength of signal | {f['strength-of-signal']} |",
        f"| Effort | {f['effort']} |",
        f"| Surface area | {f['surface-area']} |", "",
    ]
    for heading, key in (("When to reach for it", "use-cases"),
                         ("Strengths", "pros"), ("Limits", "cons"),
                         ("Practical considerations", "considerations"),
                         ("Common tools", "tools"),
                         ("Recipes that use this method", "used-by-recipes"),
                         ("Go deeper", "resources")):
        body = strip_html(f[key])
        if body:
            parts += [f"## {heading}", "", body, ""]
    parts += [f"Source: {render.SITE}{render.METHOD_BASE}{slug}",
              f"Last updated: {m.get('updated', 'unknown')}"]
    return "\n".join(parts) + "\n"


def recipe_md(slug: str, r: dict, data: dict) -> str:
    f = render.recipe_fields(slug, r, data)
    parts = [f"# {r['name']}", "",
             f"**{r.get('opp','')}**", "",
             f"> {r.get('problem','')}", "",
             r.get("hmw", ""), ""]
    triggers = strip_html(f["triggers"])
    if triggers:
        parts += ["## You'll recognise this when", "", triggers, ""]
    parts += ["## What this recipe does", "", strip_html(f["description"]), "",
              "## The method sequence", "", strip_html(f["method-sequence"]), ""]
    resources = strip_html(f["resources"])
    if resources:
        parts += ["## Go deeper", "", resources, ""]
    parts += [f"Source: {render.SITE}{render.RECIPE_BASE}{slug}",
              f"Last updated: {r.get('updated', 'unknown')}"]
    return "\n".join(parts) + "\n"


def main(path: str) -> None:
    data = json.loads(Path(path).read_text())
    recipes, methods = data["recipes"], data["methods"]

    md_dir = OUT / "md"
    for sub in ("research-recipes", "research-methods"):
        (md_dir / sub).mkdir(parents=True, exist_ok=True)

    for slug, r in recipes.items():
        (md_dir / "research-recipes" / f"{slug}.md").write_text(recipe_md(slug, r, data))
    for slug, m in methods.items():
        (md_dir / "research-methods" / f"{slug}.md").write_text(method_md(slug, m, data))

    lines = [
        "# Speero Research Recipe Hub", "",
        "> A research recipe is a prescription: diagnosed from the symptom and "
        "written for the problem. Each one names a customer problem in the "
        "customer's own words, then sequences the research methods that answer "
        "it across Explore, Focus and Validate, so the methods corroborate each "
        "other instead of standing alone.", "",
        "## Research recipes", "",
    ]
    for slug, r in sorted(recipes.items(), key=lambda kv: kv[1]["name"]):
        lines.append(f"- [{r['name']}]({render.SITE}{render.RECIPE_BASE}{slug}): "
                     f"{render.first_sentence(r.get('desc',''))}")
    lines += ["", "## Research methods", ""]
    for slug, m in sorted(methods.items(), key=lambda kv: kv[1]["name"]):
        lines.append(f"- [{m['name']}]({render.SITE}{render.METHOD_BASE}{slug}): "
                     f"{render.first_sentence(m.get('desc',''))}")
    lines += ["", "## Optional", "",
              f"- [Markdown mirrors of every page]({CDN}/llms-full.txt)",
              f"- [Machine-readable source data]({CDN}/research-hub.json)", ""]
    (OUT / "llms.txt").write_text("\n".join(lines))

    full = []
    for slug, r in sorted(recipes.items()):
        full.append((md_dir / "research-recipes" / f"{slug}.md").read_text())
    for slug, m in sorted(methods.items()):
        full.append((md_dir / "research-methods" / f"{slug}.md").read_text())
    (OUT / "llms-full.txt").write_text("\n\n---\n\n".join(full))

    print(f"Wrote {len(recipes) + len(methods)} markdown mirrors, "
          f"llms.txt ({(OUT / 'llms.txt').stat().st_size // 1024} KB), "
          f"llms-full.txt ({(OUT / 'llms-full.txt').stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "research-hub.json")
