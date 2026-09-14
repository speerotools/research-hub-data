# Speero Research Recipe Hub — Data

Airtable is the source of truth. A GitHub Action turns it into the published
JSON and into the Webflow CMS pages. Nothing here is edited by hand except the
scripts.

```
https://cdn.jsdelivr.net/gh/speerotools/research-hub-data@main/research-hub.json
```

## The loop

`sync.yml` runs nightly at 05:00 UTC and on demand:

1. `sync.py` reads the five Airtable tables and writes `research-hub.json`.
2. `selftest.py` renders every page offline and fails on anything broken.
3. `publish_assets.py` writes the markdown mirrors, `llms.txt`, `llms-full.txt`.
4. Everything is committed, so every change to live data has a diff.
5. `webflow_sync.py` reconciles the two CMS collections and purges the CDN.

Edit Airtable, the site follows. No monthly scan, no AI in this pipeline.

## Scripts

| Script | What it does |
|---|---|
| `sync.py` | Airtable → `research-hub.json`. Strict: unresolvable method names, malformed method sequences and link fields that disagree with the sequence text all fail the run. |
| `render.py` | Pure functions: JSON → Webflow-ready HTML and JSON-LD. No network. |
| `webflow_sync.py` | Reconciles both collections, matched on Airtable record id. Refreshes landing page schema. |
| `publish_assets.py` | Markdown mirrors, `llms.txt`, `llms-full.txt`. |
| `selftest.py` | Offline validation. `python .github/scripts/selftest.py` needs no secrets. |

## Secrets and variables

| Kind | Name | Value |
|---|---|---|
| Secret | `AIRTABLE_TOKEN` | PAT, `data.records:read` + `schema.bases:read`, base `apppcPYWsZzUeEOZ9` |
| Secret | `WEBFLOW_TOKEN` | Site token, CMS read/write + publish |
| Variable | `WEBFLOW_METHODS_COLLECTION` | `6aa7a1bd0bfd0f44768d2230` |
| Variable | `WEBFLOW_RECIPES_COLLECTION` | `6aa7a1bd15cd9e02755eb211` |
| Variable | `WEBFLOW_PUBLISH` | `true` publishes the CMS items each run changed |
| Variable | `WEBFLOW_SITE_PUBLISH` | `true` also publishes the whole site. Pushes every staged change across speero.com, including unfinished Designer work |
| Variable | `WEBFLOW_CUSTOM_DOMAINS` | `5fc6336ebdd770a40b4cc91e,5fc6336ebdd7702abe4cc91d`. Required with site publish, or it only reaches the webflow.io subdomain |

Webflow site `5fbb892601063dd93dd166d7`. Templates: methods
`6aa7a1bd0bfd0f44768d2236`, recipes `6aa7a1be15cd9e02755eb217`. Landing pages:
recipes `6aa7afe0091e3b99dd1f5cee`, methods `6aa7afe1091e3b99dd1f5d56`.

## Making changes

**Content, a new recipe, a new method, a tool.** Edit Airtable. That is the
whole job. The nightly run creates the page, URL, meta, internal links both
ways and the landing page index entry. Run the workflow manually to see it
sooner.

A new record needs Name, Slug, Description; recipes also need a linked
Opportunity, Research Methods and a Method sequence. The sequence must be
`Stage` / rationale / `Methods: A, B, C` blocks separated by blank lines, and
every method it names must match a record and appear in the link field too. If
those disagree the run stops and names the record.

**Design.** Webflow Designer, then publish.

**The embed.** Edit `speerotools/research-hub-embed`, push, tag, then bump the
version in the Code Embed on both landing pages and publish. Pinned on purpose:
a tag is immutable, so a rollback is a one-character edit.

**A slug.** Don't, unless it matters. The sync aborts on slug changes. Add the
301 in Webflow site settings by hand first (the redirects API is
Enterprise-only), then re-run with `allow_slug_change`.

## Safety rails

- Strict transforms. A method name that does not resolve is an error, not a
  silently unlinked bit of plain text.
- The link field and the sequence text must agree.
- Slug changes abort the run.
- Removals archive, never delete, and are capped by `MAX_ARCHIVE`.
- Fewer than 10 recipes or 10 methods reads as a failed sync, not a deletion.
- Site publish is opt-in and skipped when nothing changed.

## Known constraints

**JSON-LD on item pages does not work.** Webflow HTML-escapes PlainText CMS
tokens and entities are not decoded inside `<script>`, so a bound blob
publishes as invalid JSON. A custom block also suppresses Webflow's own
automatic `WebPage` schema, so both templates are cleared and rely on that.
The landing pages carry full `WebSite` + `Organization` + `ItemList` schema,
rebuilt every run, because static JSON is not affected.

**Conditional visibility is Designer-only**; the visibility setting has zero
bindable sources. So section headings are generated inside their field: an
empty field renders nothing at all, rather than a bare heading.

**Optional Airtable fields.** `Last Modified` (both tables) drives the visible
date and `dateModified`. `New` on Recipes restores the badge. `Related method`
on Research Methods restores the paired-method line. `Meta Title` and
`Meta Description` override the generated values.
