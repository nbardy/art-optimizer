# Experiment Receipt: <title>

**Date:** YYYY-MM-DD  
**Policy ID:**  
**Issue/PR:**  
**Conclusion:** pass / fail / inconclusive

## Hypothesis

State one falsifiable claim.

## Baseline and treatment

| Field | Baseline | Treatment |
|---|---|---|
| policy ID | | |
| renderer mode | | |
| representation | | |
| preference learner | | |
| noise policy | | |
| candidate count | | |
| command semantics | | |

## Reproducibility

```text
Git commit:
Model and revision:
Diffusers/PyTorch/CUDA:
GPU:
Dtype/quantization:
Resolution:
Inference steps/guidance:
Prompt set digest:
Seed/root set:
Control-basis family:
Control-basis instance:
Visual-feature encoder:
Configuration file/CLI:
Artifact location and digest:
```

## Controlled factors

List what was held constant.

## Varying factors

List what changed and why the comparison identifies the intended effect.

## Procedure

1. 
2. 
3. 

## Quantitative results

| Metric | Baseline | Treatment | Difference | Uncertainty |
|---|---:|---:|---:|---:|
| time to first candidate | | | | |
| full-slate latency | | | | |
| peak VRAM | | | | |
| minimum pairwise perceptual distance | | | | |
| duplicate/broken rate | | | | |
| time to first favorite | | | | |
| preference predictive loss | | | | |

Add treatment-specific metrics.

## Human observations

- What changed visibly?
- What was preferred, and why?
- Did users understand the commands?
- Did the result match the treatment’s product promise?

## Failure cases

Include representative failures and artifact references. Do not omit broken or boring outputs.

## State/invariant checks

```text
command retry idempotent:
restart recovery:
branch/history correct:
seed/noise provenance complete:
failed renders excluded from preference:
policy projections isolated:
retention cleanup verified:
```

## Claim table

| Claim | Supported? | Evidence | Caveat |
|---|---|---|---|
| | | | |

## Decision

- promote;
- iterate within treatment;
- reject;
- keep only as diagnostic baseline.

## Non-claims

State explicitly what this experiment did not establish.
