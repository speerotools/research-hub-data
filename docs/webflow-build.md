# Webflow build: templates and landing pages

Everything the sync writes is already in the CMS. This doc is the Designer
half: what to bind where, and the handful of details that are easy to get
subtly wrong.

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

Add an HTML Embed to each template:

```html
<script type="application/ld+json">
  <!-- insert the Schema JSONLD field here via + Add Field -->
</script>
```

And on the method template, a second one bound to `FAQ JSONLD` with the
conditional visibility rule above.

**Verify this on one item before building the other fifty.** Webflow
sometimes HTML-escapes quotes in a bound plain text field, which turns valid
JSON-LD into silent junk. Publish one method page, run it through Google's
Rich Results Test, and check the block parses.

If it does not, build the skeleton in the embed instead and bind the
individual fields at the value positions:

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "<!-- Name -->",
  "description": "<!-- Meta Description -->",
  "dateModified": "<!-- Last Modified -->",
  "author": { "@type": "Organization", "name": "Speero" }
}
</script>
```

That pattern is known to work. The generated field stays either way, because
it keeps the schema logic in Python where it can be tested.

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
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/speerotools/research-hub-embed@v1.0.0/dist/embed.css">

<div id="app"></div>

<script>
  window.RESEARCH_HUB_CONFIG = {
    recipeBase: "/research-recipes/",
    methodBase: "/research-methods/"
  };
</script>
<script src="https://cdn.jsdelivr.net/gh/speerotools/research-hub-embed@v1.0.0/dist/embed.js"></script>
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
