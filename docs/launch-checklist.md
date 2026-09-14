# Launch checklist

Work down it. Anything that fails here is cheaper to fix now than after the
URLs are indexed.

## Data

- [ ] Workflow run is green, and the run log shows no `WARN` lines you have
      not read.
- [ ] `research-hub.json` committed, 25 recipes and 26 methods.
- [ ] `curl` the jsDelivr URL and get current data, not a 404.
- [ ] Re-run the workflow. Second run reports 0 creates, 0 updates. If it
      reports updates on unchanged content, the hash is being disturbed by
      something and it will churn the CMS nightly.

## CMS

- [ ] 26 items in Research Methods, 25 in Research Recipes.
- [ ] Spot-check `checkout-cart-optimisation` and `conversion-research`: the
      Research Methods reference field holds 6 and 7 items respectively, and
      `Method Sequence` lists the same methods in the same order.
- [ ] No item has an empty `Airtable ID`.
- [ ] `Also Solves` is populated on exactly two recipes.

## Pages

- [ ] Method page: facts panel renders as text, Considerations shows real
      H3s, tools link out, "Recipes that use this" is populated.
- [ ] Recipe page: problem block, triggers list, stage-grouped method
      sequence with working links to method pages.
- [ ] Every link in a method sequence resolves. No 404s, no plain text where
      a link should be.
- [ ] Empty `Resources` hides its heading rather than leaving a bare H2.
- [ ] Breadcrumbs point at the right parents.

## SEO

- [ ] Rich Results Test passes on one recipe and one method page. This is
      the check most likely to fail, because of quote escaping in the
      JSON-LD embed.
- [ ] `Meta Title` and `Meta Description` are bound in page settings and
      show in the page source, not just in the CMS.
- [ ] **Disable JavaScript and reload a recipe page.** Everything must still
      be there. The CMS pages are server-rendered; only the landing page
      directory needs JS.
- [ ] Landing page carries a plain-HTML list of all 51 URLs outside the
      embed, and it survives the JS-off test too.
- [ ] The noindex added while building the templates is removed.
- [ ] Sitemap includes both new prefixes.
- [ ] Submit both URL prefixes to Search Console on day one, so the baseline
      starts now.

## Embed

- [ ] Filters work: objective, effort, signal, data type, surface area.
- [ ] A recipe card goes to the Webflow CMS page, not to a hash route.
- [ ] The embed's stylesheet has not leaked: check the site nav and footer
      on the landing page look untouched.
- [ ] Break the data URL on purpose once and confirm the failure message
      appears rather than a blank page.

## Then

- [ ] Publish the site by hand, once.
- [ ] Set `WEBFLOW_PUBLISH` to `true`.
- [ ] Update the hub registry with the two URL prefixes.
- [ ] Start the backlink pass: the 34 Speero posts already cited in the
      Resources fields are the worklist. An in-context link from an aged,
      indexed post into the matching method or recipe page moves authority
      faster than anything on-page.
