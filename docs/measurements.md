# Reproducible before/after measurements

These are **fictional** data-minimization examples. They do not measure production traffic, real credentials, Dify token use, security accuracy, or model cost. A custom Dify Code node could implement equivalent logic. This benchmark compares the exact same **unfiltered serialized JSON** against explicitly allowlisted JSON.

Run it from the repository root (Python 3.12 with dependencies installed):

    python -m benchmarks.measure

The runner checks that critical business fields survive unchanged, that deliberately excluded payload details stay out, that each policy status is `pass` for the sample, and prints JSON containing counts of excluded keys and before/after character lengths. It fails if these deterministic checks fail. The sample data contains no real customers or credentials.

## Observed output from GitHub Actions, October 20, 2026

| Synthetic workload | Original characters | Prepared characters | Reduction | Excluded JSON keys |
| --- | ---: | ---: | ---: | ---: |
| CRM lead routing (40 leads) | 25,758 | 2,641 | 89.7% | 202 |
| Support-ticket triage (25 tickets) | 14,528 | 2,328 | 84.0% | 52 |
| Webhook normalization (50 events) | 49,958 | 4,262 | 91.5% | 152 |

This is **not** a comparison against optimized Dify built-ins or a complete DLP product. Most reductions come from operators explicitly excluding unneeded fields; they are neither inferred by an AI nor guaranteed on different data. Choosing the wrong allowlist can remove necessary context or retain sensitive information.

**Do not translate character reductions into token savings, speedups, privacy compliance, or cloud bill reductions.** The prepared text may tokenize very differently and models/providers price tokens differently. Dify traces and upstream systems may still retain raw inputs. Real installation and acceptance testing in Dify Cloud/Community Edition are still required.
