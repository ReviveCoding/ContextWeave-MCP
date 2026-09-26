# Robustness analysis

> **This is post-release exploratory diagnostic analysis over qualification outcomes. It does not reopen the closed v2 scientific program, does not establish efficacy, and does not alter V2_PRE_FREEZE_INSUFFICIENT_POWER_CALIBRATED.**

Analysis identity: ContextWeave-v2-posthoc-diagnostics-v1. Parent: contextweave-v2-release-closed-2026-09-25 at 3d0d44081e3a5a6f67b58846bfcd307e448658d8.

LOFO delta range: 0.100575 to 0.155172; mean 0.130556; median 0.135057. Most influential positive family: ambiguous_period_clarification; negative: adgroup_campaign_rollup.

The 100,000-replicate family bootstrap percentile interval is [-0.016666666666666673, 0.28888888888888886]; P(delta>0)=0.955410; P(delta>-0.05)=0.992670. These are POSTHOC EXPLORATORY.

Concentration:

{
  "identity": "ContextWeave-v2-posthoc-diagnostics-v1",
  "classification": "POSTHOC_EXPLORATORY",
  "global_net_wins": 47,
  "positive_net_wins": {
    "total": 73,
    "top_shares": {
      "1": 0.1643835616438356,
      "3": 0.4931506849315068,
      "5": 0.7808219178082192,
      "10": 1.0
    },
    "herfindahl": 0.13679864890223303,
    "top_shares_of_global_net_47": {
      "1": 0.2553191489361702,
      "3": 0.7659574468085106,
      "5": 1.2127659574468086,
      "10": 1.553191489361702
    },
    "note": "Positive family contributions total 73; negative family contributions net this to 47."
  },
  "c1_failures": {
    "total": 113,
    "top_shares": {
      "1": 0.10619469026548672,
      "3": 0.3185840707964602,
      "5": 0.5221238938053098,
      "10": 0.8938053097345132
    },
    "herfindahl": 0.08622444983945493
  }
}
