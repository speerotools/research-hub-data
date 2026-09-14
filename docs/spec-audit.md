# Audit against the specs

Checked on 14 Sep 2026 against `research-hub-sync-spec.md`,
`research-hub-seo-aeo-spec.md`, `research-hub-schema-summary-v2.md`, the
prototype mockup, and ClickUp 86e2dh1w8. Verified by inspection of the live
pages, the published JSON and the Webflow element trees, not by memory.

## Data contract: complete

Every property `embed.js` reads was checked against what the sync emits.

| Reads | Emitted | Missing |
|---|---|---|
| 3 top-level keys | 9 | none |
| 13 method props | 17 | none |
| 13 recipe props | 14 | `new` |
| outcome props | 4 | none |

All five Airtable tables and every field in the schema summary are read. The
v2 growth (121 records, the brand perception branch) syncs with no changes:
no fields were added or retyped.

## Embed: every view, checked against live data

| View | Reachable | Live-data check |
|---|---|---|
| Landing | `/research-recipes`, hub nav | renders, hero suppressed in favour of the page's own |
| Problem browser | hub nav | 26 cards, 5 filters |
| Recipe directory | `/research-recipes` default | 26 cards |
| Method directory | `/research-methods` default | 29 cards, 5 filter groups |
| Recipe detail | links out to the CMS page | by design, avoids two URLs for one page |
| Method detail | links out to the CMS page | by design |

**Found and fixed: the hub nav had never been extracted.** The prototype
carried it as static HTML around `#app`, so it was not in `embed.js` at all.
Without it there was no route to the problem browser, which is the hub's
front door and has no URL of its own. Rebuilt in v1.2.0, including the XOS
locator strip that cross-links Blueprints and Testing tools.

## Method page, spec section 3

All eleven items present and verified on the live page: breadcrumb, H1,
answer-first definition, facts panel as extractable text, when to reach for
it, strengths and limits, practical considerations with real H3s, recipes
that use this method, common tools, go deeper, visible date and byline.

Schema markup is the exception, see below.

## Recipe page, spec section 4

Items 1 to 6, 8 and 9 present: breadcrumb, eyebrow and H1, problem block
(opportunity, customer quote, how might we), you'll recognise this when,
what this recipe does, the stage-grouped method sequence, go deeper, CTA,
date and byline.

**Item 7, the cross-hub slot, is not built.** The spec conditions it on "a
mapping exists per the hub cross-link rules": which blueprint operationalises
a method in which recipe. That mapping does not exist yet. The method-side
equivalent is built and live (A/B Testing links to the testing tools hub).

## Landing page, spec section 5

Definitional block, embed, plain-HTML index of every URL, and WebSite +
Organization + CollectionPage + BreadcrumbList + ItemList schema, rebuilt by
the sync on every run so it never goes stale.

## Sync outputs, spec section 6

`llms.txt`, `llms-full.txt` and 55 markdown mirrors, on the CDN. Not at
`speero.com/llms.txt`, which Webflow cannot serve without a proxy, exactly as
the spec anticipated.

## Open, with the reason each is open

| Gap | Why | Whose call |
|---|---|---|
| Item-page Article and BreadcrumbList schema | Webflow escapes CMS tokens inside `<script>`; entities are not decoded there, so the block never parses. Confirmed live. Webflow's automatic `WebPage` schema is in place instead | Ben: hand-build a skeleton and accept `&amp;` in 14 of 55 headlines, or leave it |
| FAQPage | Generated only from Considerations labels already written as questions; 41 of 42 are not | Content |
| "New" badge on 10 recipes | No `New` field in Airtable | 2 minutes in Airtable |
| "Often paired with" line | No `Related method` field in Airtable | 2 minutes in Airtable |
| Open Graph image | No 1200x630 asset exists; OG title and description already inherit | Design, then one API call |
| Recipe cross-hub slot | No recipe-to-blueprint mapping agreed | Ben |
| Considerations sub-labels as questions | Editorial rewrite of 42 headings. Highest-value content work on the hub: it also switches FAQ schema on automatically | Content |
| Tool naming drift | Lyssna, Medallia DXA, UserTesting, Contentsquare | Ben, flagged since v1 |
| Four new slugs never reviewed | Added 6 Aug, after the slug review. Already live, so a rename now needs a manual 301 | Ben |
