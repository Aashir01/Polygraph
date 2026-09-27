# Data sources

Every external number used in the README, slides, video and submission text, with its
source. Figures are quoted as reported by the source; we have not independently verified
them.

## Developer trust and AI code quality

| Claim | Source |
|---|---|
| 66% of developers say AI solutions are "almost right, but not quite" (top frustration); 45% say debugging AI code takes longer | Stack Overflow Developer Survey 2025 (49,000+ developers) |
| Trust in AI accuracy fell to 29% | Stack Overflow Developer Survey 2025 |
| ~42% of committed code is AI-generated or significantly AI-assisted | Sonar, State of Code 2026 |
| ~70% of agent-authored PRs face longer reviews, go unreviewed, or get rejected | UC Irvine study of 3,177 agent PRs |
| ~Half of SWE-bench-passing patches wouldn't be merged by maintainers | METR |
| Agents reward-hack tests in half or more of rollouts (3 open models) | Paper posted 2026-09-16 |

## Incidents

| Claim | Source |
|---|---|
| An AI agent deleted a production database and its backups in 9 seconds | PocketOS incident, April 2026 |
| An agent deleted a live database during a code freeze, then fabricated 4,000 records | Replit / SaaStr, July 2025 |

## Research Polygraph builds on

| Insight | Source |
|---|---|
| Successful agent runs verify before declaring done; failed runs don't | arXiv 2608.30391 |
| A LightGBM model predicted agent success from behaviour alone, AUC 0.69 on 9,191 trajectories | arXiv 2608.13598 |
| 10.7% of passing runs are "lucky passes" reached through a broken process | AgentLens, arXiv 2605.12925 |

The AgentLens paper and its open-source tool (process analysis of agent sessions) informed
the trace-behaviour checks. **Inbin Gate** is complementary pre-action work.

Note: the AUC 0.69 figure above is cited as *published prior work only*. Polygraph ships
no trained model, so it is not used as a baseline comparison anywhere in our results.

## Market

| Claim | Source |
|---|---|
| AI code tools ~$9.5B in 2026, ~$22B by 2030 | Research and Markets |
| AI code review ~$1.4B (2025), ~$10.8B by 2034 | Market Intelo |

## Our own measurements

All Polygraph results are measured in this repo and traceable to files —
see [experiment/RESULTS.md](experiment/RESULTS.md).
