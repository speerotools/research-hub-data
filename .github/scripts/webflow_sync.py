#!/usr/bin/env python3
"""
research-hub.json -> Webflow CMS (Research Recipes + Research Methods).

This replaces Whalesync. Whalesync maps fields one to one; these pages need
transforms (stage-grouped method sequences with working internal links,
labelled sub-headings, JSON-LD), so the rendering has to happen in code. See
render.py for all of it.

How items are matched
---------------------
Webflow assigns item ids, Airtable record ids are the stable identity, so
every CMS item carries its Airtable record id in an `airtable-id` field and
the map is rebuilt from Webflow on every run. No state file to go stale. On
a first run, items are matched by slug instead, so a collection populated by
hand is adopted rather than duplicated.

Order matters: methods are written first, because a recipe's
`research-methods` reference field needs their Webflow ids.

Safety
------
  - An empty or short data file aborts the run before anything is touched.
  - Removals archive the item, they never delete it, and are capped.
  - A changed slug aborts unless ALLOW_SLUG_CHANGE=true. Renaming a live URL
    needs a 301, and the Webflow redirects API is Enterprise-only, so that
    redirect has to be added by hand in site settings first.
  - Publishing is item-level by default. WEBFLOW_SITE_PUBLISH additionally
    publishes the whole site, which pushes EVERY staged change across
    speero.com, including whatever someone has half finished in the
    Designer. It is off unless you turn it on deliberately.

Environment variables:
  WEBFLOW_TOKEN                 required - CMS read/write + publish
  WEBFLOW_SITE_ID               default: 5fbb892601063dd93dd166d7
  WEBFLOW_RECIPES_COLLECTION    required once created
  WEBFLOW_METHODS_COLLECTION    required once created
  DATA_FILE                     default: research-hub.json
  WEBFLOW_PUBLISH               default: "false"  (publishes changed CMS items)
  WEBFLOW_SITE_PUBLISH          default: "false"  (also publishes the whole site)
  WEBFLOW_CUSTOM_DOMAINS        comma-separated domain ids; empty = webflow.io only
  DRY_RUN                       default: "false"  (print the plan, write nothing)
  ALLOW_SLUG_CHANGE             default: "false"
  MAX_ARCHIVE                   default: "5"
  JSDELIVR_PURGE                default: "true"
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import render  # noqa: E402

API = "https://api.webflow.com/v2"

TOKEN = os.environ.get("WEBFLOW_TOKEN")
SITE_ID = os.environ.get("WEBFLOW_SITE_ID", "5fbb892601063dd93dd166d7")
RECIPES_COLLECTION = os.environ.get("WEBFLOW_RECIPES_COLLECTION", "")
METHODS_COLLECTION = os.environ.get("WEBFLOW_METHODS_COLLECTION", "")
DATA_FILE = os.environ.get("DATA_FILE", "research-hub.json")
RECIPES_LANDING = os.environ.get("WEBFLOW_RECIPES_LANDING", "6aa7afe0091e3b99dd1f5cee")
METHODS_LANDING = os.environ.get("WEBFLOW_METHODS_LANDING", "6aa7afe1091e3b99dd1f5d56")
PROBLEMS_LANDING = os.environ.get("WEBFLOW_PROBLEMS_LANDING", "6aa7e6b3bcc91931eaca6aa4")
PUBLISH = os.environ.get("WEBFLOW_PUBLISH", "false").lower() == "true"
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
ALLOW_SLUG_CHANGE = os.environ.get("ALLOW_SLUG_CHANGE", "false").lower() == "true"
MAX_ARCHIVE = int(os.environ.get("MAX_ARCHIVE", "5"))
PURGE = os.environ.get("JSDELIVR_PURGE", "true").lower() == "true"
SITE_PUBLISH = os.environ.get("WEBFLOW_SITE_PUBLISH", "false").lower() == "true"
CUSTOM_DOMAINS = [d.strip() for d in os.environ.get("WEBFLOW_CUSTOM_DOMAINS", "").split(",") if d.strip()]

# A sync that suddenly has almost no content is a broken sync, not a deletion.
MIN_RECIPES = int(os.environ.get("MIN_RECIPES", "10"))
MIN_METHODS = int(os.environ.get("MIN_METHODS", "10"))

PURGE_URLS = [
    "https://purge.jsdelivr.net/gh/speerotools/research-hub-data@main/research-hub.json",
]

BATCH = 100  # Webflow's cap on bulk create / update / publish

# Filled by reconcile(); drives whether a site publish is worth doing.
CHANGED: list[int] = []


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def req(method: str, url: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Authorization", "Bearer " + TOKEN)
    r.add_header("accept", "application/json")
    if data is not None:
        r.add_header("Content-Type", "application/json")

    for attempt in range(5):
        try:
            with urllib.request.urlopen(r, timeout=45) as resp:
                raw = resp.read().decode()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")
            if e.code == 429 or e.code >= 500:
                wait = int(e.headers.get("Retry-After") or 2 ** attempt)
                print(f"  {e.code} on {method} {url}; retrying in {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            print(f"ERROR {e.code} {method} {url}: {detail}", file=sys.stderr)
            raise
        except urllib.error.URLError as e:
            wait = 2 ** attempt
            print(f"  network error {e.reason}; retrying in {wait}s", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"gave up on {method} {url}")


def chunks(seq: list, size: int = BATCH):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


# ---------------------------------------------------------------------------
# COLLECTION IO
# ---------------------------------------------------------------------------

def list_items(collection: str) -> list[dict]:
    out, offset = [], 0
    while True:
        res = req("GET", f"{API}/collections/{collection}/items?limit=100&offset={offset}")
        items = res.get("items", [])
        out.extend(items)
        total = (res.get("pagination") or {}).get("total", len(out))
        offset += 100
        if offset >= total or not items:
            break
    return out


def content_hash(field_data: dict) -> str:
    payload = {k: v for k, v in field_data.items() if k != "content-hash"}
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()[:32]


def index_items(items: list[dict]) -> tuple[dict[str, dict], dict[str, dict]]:
    """-> ({airtable id: item}, {slug: item}). Slug is the adoption fallback."""
    by_rid, by_slug = {}, {}
    for it in items:
        fd = it.get("fieldData") or {}
        if fd.get("airtable-id"):
            by_rid[fd["airtable-id"]] = it
        if fd.get("slug"):
            by_slug[fd["slug"]] = it
    return by_rid, by_slug


def reconcile(label: str, collection: str, desired: dict[str, dict],
              min_items: int) -> dict[str, str]:
    """Create, update and archive so the collection matches `desired`.

    `desired` is {airtable record id: fieldData}. Returns {airtable id:
    webflow item id} for everything now in the collection.
    """
    if len(desired) < min_items:
        print(f"ERROR {label}: only {len(desired)} items in the data file "
              f"(expected at least {min_items}). Treating as a failed sync and "
              f"changing nothing.", file=sys.stderr)
        sys.exit(1)

    print(f"\n== {label}: {len(desired)} items in data")
    existing = list_items(collection)
    by_rid, by_slug = index_items(existing)
    print(f"   {len(existing)} items in the collection "
          f"({len(by_rid)} already carry an airtable-id)")

    to_create: list[dict] = []
    to_update: list[dict] = []
    unchanged = 0
    renames: list[str] = []
    id_map: dict[str, str] = {}

    for rid, fd in desired.items():
        fd = dict(fd)
        fd["airtable-id"] = rid
        fd["content-hash"] = content_hash(fd)

        item = by_rid.get(rid) or by_slug.get(fd["slug"])
        if not item:
            to_create.append(fd)
            continue

        id_map[rid] = item["id"]
        old = item.get("fieldData") or {}
        if old.get("slug") and old["slug"] != fd["slug"]:
            renames.append(f"{old['slug']} -> {fd['slug']}")
        if old.get("content-hash") == fd["content-hash"]:
            unchanged += 1
            continue
        to_update.append({"id": item["id"], "fieldData": fd})

    desired_rids = set(desired)
    to_archive = [
        it for it in existing
        if (it.get("fieldData") or {}).get("airtable-id")
        and (it["fieldData"]["airtable-id"] not in desired_rids)
        and not it.get("isArchived")
    ]

    if renames and not ALLOW_SLUG_CHANGE:
        print(f"ERROR {label}: slug change(s) detected: {', '.join(renames)}.\n"
              f"      A live URL would break. Add the 301 in Webflow site "
              f"settings first, then re-run with ALLOW_SLUG_CHANGE=true.",
              file=sys.stderr)
        sys.exit(1)

    if len(to_archive) > MAX_ARCHIVE:
        print(f"ERROR {label}: would archive {len(to_archive)} items "
              f"(> MAX_ARCHIVE={MAX_ARCHIVE}). Refusing.", file=sys.stderr)
        sys.exit(1)

    print(f"   plan: {len(to_create)} create, {len(to_update)} update, "
          f"{unchanged} unchanged, {len(to_archive)} archive")
    for fd in to_create:
        print(f"     + {fd['slug']}")
    for u in to_update:
        print(f"     ~ {u['fieldData']['slug']}")
    for it in to_archive:
        print(f"     - {(it.get('fieldData') or {}).get('slug')}")

    if DRY_RUN:
        print("   DRY_RUN: nothing written")
        return id_map

    changed_ids: list[str] = []

    for batch in chunks(to_create):
        res = req("POST", f"{API}/collections/{collection}/items/bulk",
                  {"fieldData": batch, "isDraft": False, "isArchived": False})
        for it in res.get("items", res if isinstance(res, list) else []):
            rid = (it.get("fieldData") or {}).get("airtable-id")
            if rid:
                id_map[rid] = it["id"]
            changed_ids.append(it["id"])

    for batch in chunks(to_update):
        req("PATCH", f"{API}/collections/{collection}/items", {"items": batch})
        changed_ids.extend(u["id"] for u in batch)

    for it in to_archive:
        # Send the item's existing fieldData back untouched. A PATCH with an
        # empty fieldData would blank the item on its way out, and an archived
        # item is meant to stay readable.
        req("PATCH", f"{API}/collections/{collection}/items/{it['id']}",
            {"isArchived": True, "fieldData": it.get("fieldData") or {}})
        print(f"   archived {(it.get('fieldData') or {}).get('slug')}")

    if PUBLISH and changed_ids:
        for batch in chunks(changed_ids):
            req("POST", f"{API}/collections/{collection}/items/publish",
                {"itemIds": batch})
        print(f"   published {len(changed_ids)} item(s)")
    elif changed_ids:
        print(f"   {len(changed_ids)} item(s) staged, not published "
              f"(WEBFLOW_PUBLISH is off)")

    CHANGED.append(len(changed_ids))
    return id_map


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def write_landing_schema(data: dict) -> None:
    """Refresh the ItemList schema on both landing pages.

    Item pages cannot carry custom JSON-LD, because Webflow escapes CMS token
    values inside a script element. The landing pages can, because their
    schema is static JSON, so this is where the hub declares what it contains.
    """
    pages = []
    for page_id, kind in ((RECIPES_LANDING, "recipes"), (METHODS_LANDING, "methods"),
                          (PROBLEMS_LANDING, "problems")):
        if page_id:
            pages.append({"id": page_id,
                          "jsonLdSchema": json.dumps(render.landing_jsonld(kind, data),
                                                     ensure_ascii=False)})
    if not pages:
        return
    req("PATCH", f"{API}/sites/{SITE_ID}/pages/schema_markup", {"pages": pages})
    print(f"  landing page schema refreshed on {len(pages)} page(s)")


def publish_site() -> None:
    """Publish the whole site. Only called when WEBFLOW_SITE_PUBLISH is on.

    This pushes every staged change across speero.com, not only this hub's.
    With no domain ids it reaches the webflow.io subdomain only, which is a
    staging publish and will not update the live site.
    """
    body: dict = {}
    if CUSTOM_DOMAINS:
        body["customDomains"] = CUSTOM_DOMAINS
    else:
        body["publishToWebflowSubdomain"] = True
        print("  WARN no WEBFLOW_CUSTOM_DOMAINS set: publishing to the "
              "webflow.io subdomain only, speero.com will not update",
              file=sys.stderr)
    req("POST", f"{API}/sites/{SITE_ID}/publish", body)


def purge_cdn() -> None:
    for u in PURGE_URLS:
        try:
            with urllib.request.urlopen(u, timeout=30) as resp:
                resp.read()
            print(f"  purged {u}")
        except Exception as e:  # a stale CDN is not worth failing the run over
            print(f"  WARN purge failed for {u}: {e}", file=sys.stderr)


def main() -> None:
    if not TOKEN:
        print("ERROR: WEBFLOW_TOKEN env var required", file=sys.stderr)
        sys.exit(1)
    if not RECIPES_COLLECTION or not METHODS_COLLECTION:
        print("ERROR: WEBFLOW_RECIPES_COLLECTION and WEBFLOW_METHODS_COLLECTION "
              "env vars required (see README)", file=sys.stderr)
        sys.exit(1)

    data = json.loads(Path(DATA_FILE).read_text())
    methods, recipes = data["methods"], data["recipes"]

    # Methods first: recipes reference their Webflow ids.
    desired_methods = {
        m["rid"]: render.method_fields(slug, m, data)
        for slug, m in methods.items() if m.get("rid")
    }
    method_ids = reconcile("Research Methods", METHODS_COLLECTION,
                           desired_methods, MIN_METHODS)

    slug_to_webflow = {
        slug: method_ids[m["rid"]]
        for slug, m in methods.items()
        if m.get("rid") and m["rid"] in method_ids
    }

    desired_recipes = {}
    for slug, r in recipes.items():
        if not r.get("rid"):
            continue
        fd = render.recipe_fields(slug, r, data)
        refs, seen = [], set()
        for stage in r.get("stages", []):
            for mslug in stage[2]:
                wid = slug_to_webflow.get(mslug)
                if wid and wid not in seen:
                    seen.add(wid)
                    refs.append(wid)
        fd["research-methods"] = refs
        desired_recipes[r["rid"]] = fd

    reconcile("Research Recipes", RECIPES_COLLECTION, desired_recipes, MIN_RECIPES)

    if not DRY_RUN:
        try:
            write_landing_schema(data)
        except Exception as e:   # schema is worth retrying, not worth failing over
            print(f"  WARN landing schema update failed: {e}", file=sys.stderr)

    # A site publish is only worth its blast radius when something moved.
    if SITE_PUBLISH and not DRY_RUN and sum(CHANGED):
        target = ", ".join(CUSTOM_DOMAINS) if CUSTOM_DOMAINS else "webflow.io subdomain"
        print(f"\nPublishing the site ({target})...")
        publish_site()
    elif SITE_PUBLISH and not DRY_RUN:
        print("\nNothing changed, skipping the site publish.")

    if PURGE and not DRY_RUN:
        print("\nPurging jsDelivr cache...")
        purge_cdn()

    print("\nDone.")
    if not PUBLISH:
        print("Items are staged as drafts-in-waiting. Set the WEBFLOW_PUBLISH "
              "repo variable to 'true' once the templates are built.")


if __name__ == "__main__":
    main()
