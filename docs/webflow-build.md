# Webflow build: templates and landing pages

Everything the sync writes is already in the CMS. This doc is the Designer
half: what to bind where, and the handful of details that are easy to get
subtly wrong.

## What is already built

Both collections exist and the method template has been built via the API:
page chrome (GTM, Custom Nav CSS, navbar), breadcrumb, H1, facts panel,
all content sections, and the reverse-links section. What remains on it is
listed under "Still to do by hand" at the end of this doc.

The layout follows `/ab-testing-tools`: the same `navbar` and `footer`
component instances, the site's `container` class, and hub-specific classes
prefixed `rh-` so nothing touches the existing design system.

One deliberate difference from the testing tools hub. Its per-vendor pages
carry only name and slug in the CMS and render their body client-side from
`island.js`. That is the wrong shape here, because the whole argument for
these pages is that they are indexable documents. So the recipe and method
pages are server-rendered from real CMS fields, and JavaScript is only
involved on the landing pages.

## Collections

| Collection | ID | Items | URL |
|---|---|---|---|
| Research Methods | `6aa7a1bd0bfd0f44768d2230` | 26 | `/research-methods/[slug]` |
| Research Recipes | `6aa7a1bd15cd9e02755eb211` | 25 | `/research-recipes/[slug]` |

Put both IDs in the data repo's Actions **variables** as
`WEBFLOW_METHODS_COLLECTION` and `WEBFLOW_RECIPES_COLLECTION`.

Fields whose help text says "set by the sync job" are machine-owned. Editing
them by hand does nothing lasting: the next run overwrites the value, and
editing Content Hash just forces a pointless re-write.

## Before anything else: turn off the two collection template pages

Creating a collection creates its template page, and an unfinished template
page will happily get indexed. Until the templates are built:

- Page settings → SEO → tick **Exclude from site search** and add
  `<meta name="robots" content="noindex">` to the page's custom code head.
- Remove both when you publish for real.

## Method template `/research-methods/[slug]`

Top to bottom, matching section 3 of the SEO/AEO spec.

| Section | Element | Binding |
|---|---|---|
| Breadcrumb | Link + text | static "Home / Research methods" + `Name` |
| H1 | Heading h1 | `Name` |
| Answer-first definition | Rich Text | `Description` |
| Facts panel | Definition list | `Objective`, `Primary Data Type`, `Strength Of Signal`, `Effort`, `Surface Area` |
| H2 When to reach for it | Rich Text | `Use Cases` |
| H2 Strengths and limits | two Rich Text blocks | `Pros`, `Cons` |
| H2 Practical considerations | Rich Text | `Considerations` (arrives with H3s already) |
| H2 Recipes that use this method | Collection List | see below |
| H2 Common tools | Rich Text | `Tools` |
| H2 Go deeper | Rich Text | `Resources` |
| Last updated | Text | `Last Modified` |

**Facts panel as a definition list, not images.** The values have to be
extractable text. That is the whole reason the sync writes them as plain
strings rather than option pills.

**Recipes that use this method.** Add a Collection List bound to Research
Recipes, filter `Research Methods` → `contains` → `Current Research Method`,
limit 100. This is a top-level list, not a nested one, so the five-item cap
does not apply. If you would rather not build cards, bind the
`Used By Recipes` Rich Text field instead: same links, zero configuration,
generated in the same run so the two can never disagree.

**Page settings.** Title → `Meta Title`. Description → `Meta Description`.

## Recipe template `/research-recipes/[slug]`

| Section | Element | Binding |
|---|---|---|
| Breadcrumb | Link + text | static "Home / Research recipes" + `Name` |
| Eyebrow + H1 | Text + h1 | static "Research recipe" + `Name` |
| The problem block | Text | `Opportunity Name` (bold), `Customer Problem` (quote style), `How Might We` |
| You'll recognise this when | Rich Text | `Triggers` |
| H2 What this recipe does | Rich Text | `Description` |
| H2 The method sequence | Rich Text | `Method Sequence` |
| Also solves | Text | `Also Solves` |
| H2 Go deeper | Rich Text | `Resources` |
| Badges | Text | `Outcome Area`, `Discovery Stage`, `Evidence Strength` |
| Last updated | Text | `Last Modified` |

`Method Sequence` arrives as `<h3>` per stage, the rationale as a paragraph,
and the methods as a linked list. Style it in the Rich Text element's nested
selectors. Do not rebuild it as a nested Collection List: that caps at five
items and cannot carry the stage grouping or the rationale line.

## Conditional visibility

Set these or empty fields leave bare headings behind.

| Element | Rule |
|---|---|
| Go deeper section | `Resources` is set |
| Also solves | `Also Solves` is set |
| FAQ schema embed | `FAQ JSONLD` is set |
| Last updated | `Last Modified` is set |

`Resources` is empty on all 25 recipes today, so on launch day that whole
section is hidden on every recipe page. That is correct behaviour, not a bug.

## JSON-LD

Use **page settings → Schema markup → JSON-LD schema**, not a body embed. It
renders into the head and Webflow validates it in place.

On each template, type the script tags and insert the CMS field between them
with **+ Add field**:

```html
<script type="application/ld+json">
{Schema JSONLD}
</script>
```

The field already holds the complete JSON object, braces included, so the
token is the entire script body. Do not wrap it in quotes and do not paste
JSON by hand.

Publish one page and run it through Google's Rich Results Test before doing
the rest. Webflow sometimes escapes quotes in bound plain text, which turns
valid JSON-LD into silent junk. If that happens, build the skeleton in the
panel and insert individual fields at the value positions instead:

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{Name}",
  "description": "{Meta Description}",
  "dateModified": "{Last Modified}",
  "author": { "@type": "Organization", "name": "Speero" }
}
</script>
```

### FAQPage: not wired yet, on purpose

Only 1 of 26 methods currently produces FAQ schema, because FAQ entries are
generated only from Considerations sub-labels already phrased as questions,
and 41 of 42 labels are not. Wiring it now would put an empty script block on
25 pages to serve one question on one page.

The `FAQ JSONLD` field keeps generating at no cost. Add a second script block
in the same panel once the labels have been rewritten as real questions:
"Sample size" becomes "How many participants do you need?" only where the
field genuinely answers it. The generator picks up any label ending in `?`
with no code change.

That rewrite is the highest-value content edit on this hub. It turns 42
existing sub-headings into question-shaped answers.

Do not use `schema.org/Recipe` anywhere on this hub. That vocabulary is for
cooking. The name collision is ours.

## Landing pages

`/research-recipes` and `/research-methods` are static pages. In Webflow a
static page can share a slug with a CMS collection prefix, so the landing
page and the collection coexist.

Each carries one Code Embed:

```html
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Poppins:ital,wght@0,300;0,400;0,600;0,900;1,900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/speerotools/research-hub-embed@v1.1.0/dist/embed.css">

<div id="speero-research-hub"></div>

<script>
  window.RESEARCH_HUB_CONFIG = {
    recipeBase: "/research-recipes/",
    methodBase: "/research-methods/"
  };
</script>
<script src="https://cdn.jsdelivr.net/gh/speerotools/research-hub-embed@v1.1.0/dist/embed.js"></script>
```

Pin the tag. `@main` is mutable, jsDelivr caches it, and a rollback then is
not a rollback.

**The part that is easy to skip and matters most.** Below the embed, add a
plain Collection List of all recipes and all methods, rendered as ordinary
links, outside the embed. Those links are what pass authority into 51 new
URLs, and they have to exist with JavaScript off. The embed enhances that
list. It must not be the only place those links live.

Also on `/research-recipes`: a definitional paragraph answering "what is a
research recipe?" in one liftable block, plus `WebSite` + `Organization`
schema and an `ItemList` of the recipes.

## Publishing order

1. Build both templates with `WEBFLOW_PUBLISH` still `false`. Items sit in
   the CMS unpublished, so nothing is live.
2. Publish the site once by hand. This is the only full site publish in the
   process, and it must be a person, not CI: a site publish pushes every
   staged change on the whole site.
3. Check a handful of pages.
4. Set the `WEBFLOW_PUBLISH` variable to `true`. From then on the nightly
   run publishes only the items it changed.

## Slugs are frozen at publish

Webflow's redirects API is Enterprise-only, so a renamed slug needs a manual
301 in site settings. The sync aborts on any slug change rather than
silently breaking a live URL. If a rename is genuinely wanted: add the 301
first, then re-run the workflow with `allow_slug_change` ticked.

---

## Built via the API: what exists and what does not

Four pages were built programmatically. Element ids and bindings are in place;
what is listed under "Still to do by hand" needs the Designer, because the
Webflow API does not expose those controls.

| Page | ID | State |
|---|---|---|
| Research Methods Template | `6aa7a1bd0bfd0f44768d2236` | built and bound |
| Research Recipes Template | `6aa7a1be15cd9e02755eb217` | built and bound |
| `/research-recipes` landing | `6aa7afe0091e3b99dd1f5cee` | hero, embed, index lists |
| `/research-methods` landing | `6aa7afe1091e3b99dd1f5d56` | hero, embed, index list |

Each carries the site's own `GTM Snippet`, `Custom Nav CSS`, `navbar` and
`footer` component instances, the `container` class, and hub classes prefixed
`rh-`. Rich text internals are styled from a `<style>` embed at the top of
each template, because Webflow's class editor cannot express descendant
selectors and the HTML inside a CMS rich text field carries no classes.

Both landing pages carry the hub embed pinned to `@v1.1.0`, mounted at
`#speero-research-hub` (the same namespacing `/ab-testing-tools` uses), plus a
Collection List of every item rendered as plain links below it. That list is
what passes authority into the 51 new URLs and it works with JavaScript off.
`/research-methods` passes `defaultRoute: "methods"` so it opens on the
method directory instead of the hub landing view.

### Still to do by hand

Four things, all of them small, none of them exposed by the API.

1. **Schema markup in page settings.** Both templates need
   `{Schema JSONLD}` inserted between script tags in page settings → Schema
   markup. The Data API has no write access to that panel. See the JSON-LD
   section above. FAQ schema stays unwired until the Considerations labels
   are rewritten as questions.

2. **Conditional visibility.** Set "show only if set" on the Go deeper
   section, the Also Solves line, the FAQ embed and the Last updated row.
   Conditional visibility is a Designer-only control; a direct API binding is
   rejected with "not inside a CMS context".

3. **Page settings SEO.** On both templates, bind Title to `Meta Title` and
   Description to `Meta Description`. The Data API only accepts static strings
   for page SEO, so the CMS token has to be picked in the UI.

4. **Reverse links as cards, if wanted.** The method template binds the
   generated `Used By Recipes` rich text, which works as is. To get styled
   cards instead, swap it for a Collection List of Research Recipes filtered
   by `Research Methods` contains `Current Research Method`.
