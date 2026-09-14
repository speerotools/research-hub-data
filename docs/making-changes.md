# How to change the hub

Four kinds of change. Only one of them involves Webflow.

## 1. Content: wording, a new recipe, a new method, a tool

**Edit Airtable. That is the whole job.**

The nightly run picks it up and the site follows. To see it sooner, run the
**Sync Airtable to hub** workflow manually with nothing ticked.

Adding a new recipe or method creates its page automatically, including the
URL, the meta, the internal links both ways, and its entry in the landing
page index and schema. Nobody touches Webflow.

What a new record needs before the run will accept it:

| Table | Required |
|---|---|
| Recipes | Name, Slug, Description, a linked Opportunity, Research Methods, Method sequence |
| Research Methods | Name, Slug, Description |

The `Method sequence` must be `Stage` / rationale / `Methods: A, B, C` blocks
separated by blank lines, and every method it names must match a record and
appear in the `Research Methods` link field too. If those disagree the run
stops and names the record. That is deliberate: a method name that does not
resolve looks fine on the page and silently costs an internal link.

## 2. Design: layout, styling, a new section on a page

Webflow Designer, then publish. Same as any other page on the site.

If `WEBFLOW_SITE_PUBLISH` is on, staged Designer work also ships with the
next nightly run that changes anything. Finish what you start, or leave the
variable off.

Adding a new **field** to a page means three steps in order: add the field to
the collection, have `render.py` emit it, then bind an element to it.

## 3. The interactive directory (the embed)

Edit `speerotools/research-hub-embed`, then:

```bash
git push origin main
git tag v1.2.0 && git push origin v1.2.0
```

Then update the version in the Code Embed on **both** landing pages and
publish. Two places, both pinned on purpose: a tag is immutable, so a bad
push cannot reach the live site and a rollback is a one-character edit.

## 4. Renaming a slug

Don't, unless it matters. Slugs freeze at publish.

The sync aborts on any slug change rather than silently breaking a live URL.
If a rename is genuinely wanted:

1. Add the 301 by hand in Webflow site settings (the redirects API is
   Enterprise-only, so this cannot be automated).
2. Change the Slug in Airtable.
3. Run the workflow with **allow_slug_change** ticked.

## When something looks wrong

| Symptom | Look here |
|---|---|
| Workflow failed | The run log names the Airtable record and field |
| Site not updating | `WEBFLOW_PUBLISH` variable, and whether the run reported changes |
| Embed showing old data | jsDelivr cache; the run purges it, check the purge step |
| Embed blank | The pinned tag exists on GitHub and serves a 200 |
| A page section missing | Its field is empty in Airtable; headings only render with content |

Nothing here is edited by hand in the repo. Airtable is the source of truth,
and every published change has a commit with a diff.
