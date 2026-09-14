# One-time setup

Everything below is done once. After that the hub runs itself.

## 1. Create the two repos

Under the `speerotools` org, both public (jsDelivr only serves public repos):

```bash
gh repo create speerotools/research-hub-data  --public --source=. --push
gh repo create speerotools/research-hub-embed --public --source=../research-hub-embed --push
```

Without `gh`:

```bash
git remote add origin git@github.com:speerotools/research-hub-data.git
git push -u origin main
```

Tag the embed as soon as it is pushed, because the Webflow snippet pins a tag:

```bash
cd ../research-hub-embed && git tag v1.0.0 && git push --tags
```

## 2. Airtable token

Create a Personal Access Token at
<https://airtable.com/create/tokens> with scopes `data.records:read` and
`schema.bases:read`, granted to base `apppcPYWsZzUeEOZ9` only.

Store it in `research-hub-data` → Settings → Secrets and variables → Actions
→ **Secrets** as `AIRTABLE_TOKEN`.

## 3. Webflow token

Webflow → site settings → Apps & integrations → API access → generate a site
token with **CMS read and write** and **publish**. Store as `WEBFLOW_TOKEN`.

A site token is the right shape here. An OAuth app would be more machinery
for no benefit on a single-site pipeline.

## 4. Actions variables

Same screen, the **Variables** tab:

| Variable | Value |
|---|---|
| `WEBFLOW_METHODS_COLLECTION` | `6aa7a1bd0bfd0f44768d2230` |
| `WEBFLOW_RECIPES_COLLECTION` | `6aa7a1bd15cd9e02755eb211` |
| `WEBFLOW_PUBLISH` | `false` for now. Flip to `true` once the templates are built. |

## 5. Airtable fields to add

Two required, three optional. All are schema changes, so they need a click
in Airtable.

**Required before the dates and the strict sync work properly:**

| Table | Field | Type | Why |
|---|---|---|---|
| Recipes | `Last Modified` | Last Modified Time | The visible "last updated" date and `dateModified`. Without it pages carry no date at all. |
| Research Methods | `Last Modified` | Last Modified Time | Same. |

**Optional, each restores something the prototype had:**

| Table | Field | Type | Restores |
|---|---|---|---|
| Recipes | `New` | Checkbox | The "New" badge, on 10 recipes in the prototype |
| Research Methods | `Related method` | Link to Research Methods | The "often paired with" line |
| both | `Meta Title`, `Meta Description` | Single line text | Hand-written meta on the pages worth it; generated otherwise |

## 6. First run

Actions → **Sync Airtable to hub** → Run workflow, with **dry run** ticked.

Read the plan it prints. It should say roughly 26 creates in Research Methods
and 25 in Research Recipes, and nothing to archive. If `sync.py` fails
instead, it will name the exact Airtable record and field. Fix those, re-run.

Then run it again with dry run off.

## 7. Verify the CDN

```bash
curl -s https://cdn.jsdelivr.net/gh/speerotools/research-hub-data@main/research-hub.json | head -c 300
```

If it 404s, give jsDelivr a minute on a brand-new repo. The workflow purges
the cache on every run, so a stale file after a later sync is not expected.

## Working on the scripts without any secrets

```bash
python .github/scripts/selftest.py
```

Renders all 51 pages from the committed fixture and checks them. No Airtable,
no Webflow, no token.
