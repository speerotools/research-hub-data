# Synthetic Shopper Simulation

AI agents acting as shoppers browse or judge a control and one or more variants, and the tool predicts which version would perform better. Some tools drive real browsers on live or staged pages, others compare screenshots. It is a way to pre-screen ideas, not a substitute for a live experiment.

| | |
|---|---|
| Stage | Explore, Focus |
| Data type | Quantitative |
| Strength of signal | Low |
| Effort | Low |
| Surface area | Landing pages, Checkout & cart, Any surface |

## When to reach for it

Pre-screen a test backlog and drop the weakest variants before spending traffic.Sanity-check a variant for obvious friction before launch.Compare two themes or page versions when traffic is too low to test both live.

## Strengths

Returns a prediction in hours rather than weeks of live traffic.
Session replays and agent reasoning can surface friction worth investigating.
Useful for ordering a backlog when traffic is the constraint.

## Limits

Independent studies of predicting A/B winners land well below vendor headlines, and one study of 330 CRO tests found model judges close to chance.
Predicted effect sizes are often shrunk or inflated, so they cannot feed revenue forecasts or sample size planning.
Headline match rates can mislead, because many 'winners' in test archives come from non-significant tests.
Agents don't behave like real shoppers with real money, time pressure and habits.

## Practical considerations

Practical considerations

### Pair it
Anything worth shipping still goes through an A/B Test. Use synthetic results to decide what to test, never what to ship.

### Tool scope
Shopify SimGym compares two themes only, and bot protection can block its shoppers. Squoosh and VWO's synthetic test suit backlog screening better.

### Vendor claims
Ask how a match rate was measured, how many tests it covers and whether non-significant tests count as winners.

## Common tools

Tools

- [Squoosh](https://squoosh.ai)

- [Shopify SimGym](https://help.shopify.com/en/manual/online-store/simgym)

- [VWO](https://vwo.com)

## Recipes that use this method

- [Researching With Low Traffic](/research-recipes/researching-low-traffic)

- [Test Backlog Pre-Screening](/research-recipes/test-backlog-pre-screening)

Source: https://speero.com/research-methods/synthetic-shopper-simulation
Last updated: 2026-11-05
