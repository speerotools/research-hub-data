# Test Backlog Pre-Screening

**We can't test because traffic is too low**

> We don't have the volume to be statistically significant, so every change is a leap of faith.

How might we build evidence for decisions when traffic can't support A/B tests?

## You'll recognise this when

- Sessions too low to reach significance in a realistic test window

- High-stakes pages with thin behavioural data

- Polls and analytics too sparse to read

- Decisions resting on opinion or the loudest voice

## What this recipe does

The team has more test ideas than traffic to run them, so every slot spent on a weak idea is a slot lost. This recipe uses cheap, fast signals to order the backlog before any traffic is spent, then lets a live experiment make the final call.
Analytics data analysis sizes where each idea would act and how much traffic that page actually gets. Synthetic shopper simulation and predictive attention analysis then give a quick read on which variants look weakest, so they can be dropped or reworked. Both are hypotheses, not evidence. They rank options and can't predict lift, and published studies of AI-predicted A/B winners land well short of vendor claims.
The survivors go to real people. Heatmaps and session recordings show how visitors behave on the pages in question, and a preference test checks how the remaining variants compare with real participants. Only then does the strongest idea earn an A/B test, which remains the only step here that measures a causal effect.

## The method sequence

Explore. Focus. Validate.

### Explore
Size where each idea acts, then use synthetic signals to drop the weakest variants. These rank options; they don't predict lift.

- [Analytics Data Analysis](/research-methods/analytics-data-analysis)

- [Synthetic Shopper Simulation](/research-methods/synthetic-shopper-simulation)

- [Predictive Attention Analysis](/research-methods/predictive-attention-analysis)

### Focus
Take the survivors to real visitors and real participants.

- [Heatmaps](/research-methods/heatmaps)

- [Session Recordings](/research-methods/session-recordings)

- [Preference Test](/research-methods/preference-test)

### Validate
Run the strongest idea as a live experiment.

- [A/B Testing](/research-methods/ab-testing)

Source: https://speero.com/research-recipes/test-backlog-pre-screening
Last updated: 2026-11-05
