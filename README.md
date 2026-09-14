# Speero Research Recipe Hub — Data

Airtable is the source of truth. A GitHub Action turns it into the published
JSON and into the Webflow CMS pages. Nothing in this repo is edited by hand
except the scripts themselves.

Published data (served via jsDelivr, read by the embed):

```
https://cdn.jsdelivr.net/gh/speerotools/research-hub-data@main/research-hub.json
```

## One loop

`sync.yml` runs nightly and on demand:

1. `sync.py` reads the five Airtable tables and writes `research-hub.json`.
2. `selftest.py` renders every page offline and fails on anything broken.
3. The JSON is committed, so every change to the live data has a diff.
4. `webflow_sync.py` reconciles the two CMS collections and purges the CDN.

Edit Airtable, the site follows. There is no monthly scan and no AI in this
pipeline; the hub's content is written, not scraped.

## Scripts (`.github/scripts/`)

| Script | What it does |
|---|---|
| `sync.py` | Airtable → `research-hub.json`. Strict: unresolvable method names, malformed method sequences and link fields that disagree with the sequence text all fail the run. |
| `render.py` | Pure functions turning the JSON into Webflow-ready HTML and JSON-LD. No network. |
| `webflow_sync.py` | Reconciles Research Recipes + Research Methods. Creates, updates only what changed, archives what left, publishes item by item. |
| `selftest.py` | Offline validation of the rendered output. Runs against the committed fixture with no arguments. |

Run the validator with no secrets at all:

```bash
python .github/scripts/selftest.py
```

## Docs

- [`docs/setup.md`](docs/setup.md) — repos, tokens, variables, Airtable fields, first run
- [`docs/webflow-build.md`](docs/webflow-build.md) — collection ids, template bindings, JSON-LD, landing pages
- [`docs/launch-checklist.md`](docs/launch-checklist.md) — what to verify before publishing

## Secrets and variables

| Kind | Name | Value |
|---|---|---|
| Secret | `AIRTABLE_TOKEN` | PAT with `data.records:read` + `schema.bases:read` on base `apppcPYWsZzUeEOZ9` |
| Secret | `WEBFLOW_TOKEN` | Webflow site token with CMS read/write + publish |
| Variable | `WEBFLOW_RECIPES_COLLECTION` | `6aa7a1bd15cd9e02755eb211` |
| Variable | `WEBFLOW_METHODS_COLLECTION` | `6aa7a1bd0bfd0f44768d2230` |
| Variable | `WEBFLOW_PUBLISH` | `true` once the templates are built. Publishes the CMS items each run changed, which is what makes Airtable edits reach the site on their own |
| Variable | `WEBFLOW_SITE_PUBLISH` | `false` by default. `true` also publishes the whole site each time something changes |
| Variable | `WEBFLOW_CUSTOM_DOMAINS` | `5fc6336ebdd770a40b4cc91e,5fc6336ebdd7702abe4cc91d` (www.speero.com, speero.com). Required if `WEBFLOW_SITE_PUBLISH` is on, or the publish only reaches the webflow.io subdomain |

## Safety rails

These exist because the failure modes are silent, not loud.

- **Strict transforms.** A method named in a `Method sequence` that matches no
  record is an error. Those links are the cluster; a plain-text method name
  looks fine on the page and quietly costs an internal link.
- **Both sides must agree.** The `Research Methods` link field and the
  `Method sequence` text describe the same relationship. If they disagree,
  someone edited one and forgot the other, and the run stops.
- **Slug changes abort.** A renamed slug breaks a live URL, and Webflow's
  redirects API is Enterprise-only, so the 301 has to be added by hand in site
  settings first. Then re-run with `allow_slug_change`.
- **Removals archive, never delete**, and are capped at `MAX_ARCHIVE`.
- **A thin data file aborts the run.** Fewer than 10 recipes or 10 methods is
  read as a failed sync, not as a deletion.
- **Site publish is opt-in.** By default the pipeline publishes only the CMS
  items it touched, which covers every content change including brand new
  recipes and methods. `WEBFLOW_SITE_PUBLISH=true` additionally publishes the
  whole site, which is the only way to ship template and page changes
  automatically, and which pushes every staged change across speero.com
  including unfinished Designer work. It is skipped when nothing changed.

## Optional Airtable fields

The sync works without these. Each one turns a feature back on:

| Field | Table | Effect |
|---|---|---|
| `Last Modified` (Last Modified Time) | Recipes, Research Methods | Fills the visible "last updated" date and `dateModified` in the schema. Without it, pages carry no date. |
| `New` (checkbox) | Recipes | Restores the "New" badge the prototype shows on 10 recipes. |
| `Related method` (link to self) | Research Methods | Restores the related-method link. |
| `Meta Title` / `Meta Description` | both | Overrides the generated meta for pages worth hand-writing. |

## Data contract

`research-hub.json` is the shape the prototype embed already speaks, so
`embed.js` needed no reshaping beyond fetching instead of inlining. Recipes
and methods are keyed by slug; `rid` on each carries the Airtable record id,
which is what the Webflow sync matches on.
