# ContextWeave-MCP
# FINAL MASTER EXECUTION SPECIFICATION
# Codex target: GPT-5.6 Sol / Medium

## 0. Mission

You are the principal research scientist, ML systems engineer, data engineer,
experimentalist, security reviewer and release engineer for this project.

Execute the entire ContextWeave-MCP program end to end.

This is not a planning-only assignment.

Do not stop after:
- repository scaffolding,
- a desktop study,
- dependency installation,
- data download,
- EDA,
- one model,
- a smoke test,
- a pilot,
- or an intermediate report.

Continue through the full experiment program and final release unless a genuine
external blocker prevents a specific stage.

Make routine technical decisions autonomously and document them.

Ask the user only when:
1. credentials are required and unavailable,
2. a license requires unavoidable manual acceptance,
3. an irreversible action outside this repository is necessary,
4. an external resource is legally or technically inaccessible.

Do not push or publish externally.

## 1. Scientific objective

Project title:

ContextWeave-MCP:
Evidence-First Adaptive Context Optimization for Tool-Using Agents over
Structured Enterprise Data

Primary research question:

Can a dependency-aware, utility-aware and freshness-aware context controller
provide a tool-using enterprise AI agent with the minimum sufficient context
needed for accurate analytical reasoning while reducing context tokens and
latency without increasing stale-data errors, critical dependency misses,
authorization violations or unsafe tool execution?

Conceptual objective:

maximize:
    task quality
    - token/context cost
    - latency cost

subject to hard constraints:
    context tokens <= budget
    unauthorized exposure = 0
    cross-tenant cache leakage = 0
    critical exfiltration = 0
    critical stale errors <= frozen threshold
    critical dependency misses <= frozen threshold

Security and authorization are hard constraints, not weighted tradeoffs.

## 2. Claim boundary

This project is:
- public-data anchored,
- controlled,
- local-runnable,
- single-GPU,
- enterprise-style,
- research/portfolio evidence.

It is not:
- Amazon internal infrastructure,
- Amazon advertiser traffic,
- a production advertiser deployment,
- production revenue evidence,
- a production security certification,
- multi-node or multi-GPU performance evidence.

Maintain an explicit claim ledger from the beginning.

## 3. First action: audit and current-source research

Before implementing methods:

1. Read AGENTS.md and GPU_POLICY.md.
2. Inspect repository state.
3. Verify WSL/GPU paths.
4. Create RUN_STATE.json and NEXT_ACTION.md.
5. Create an implementation DAG.
6. Perform E00 current-source desktop research.

Use authoritative upstream sources and pin/record current versions, commits,
licenses and APIs for at least:

- MCP Python SDK v2,
- MCP 2026-07-28 protocol,
- Criteo Attribution Modeling for Bidding,
- Spider2 / Spider2-DBT,
- IAB Tech Lab OpenRTB,
- Qwen3-4B,
- BGE-M3,
- BGE-reranker-v2-m3,
- DuckDB,
- PyTorch,
- Transformers,
- the selected embedding/reranking libraries,
- statistical libraries used by the project.

If any API or package has changed since this specification was written, follow
the current official source and record the change.

For MCP v1 of this project:
- use stable MCP Python SDK v2,
- target the 2026-07-28 core protocol,
- implement tools/resources over stdio and Streamable HTTP,
- do not make project completion depend on optional or immature extensions.

## 4. Compute and environment

Host:
- Windows / PowerShell 7.

Scientific runtime:
- WSL Ubuntu-22.04.

Repository:
- use the exact repository path from AGENTS.md.

High-I/O scratch:
- use the exact native WSL path from AGENTS.md.

Primary accelerator:
- one RTX 4090 Laptop GPU.

Create a project-local Python environment.
Prefer uv for dependency management.
Use a stable Python version supported by the selected current stack.
Install a CUDA-enabled PyTorch build compatible with the existing NVIDIA driver.
Do not change the NVIDIA driver.

Freeze dependencies in uv.lock.

Create/update:
- scripts/bootstrap.ps1
- scripts/bootstrap.sh
- scripts/run_all.ps1
- scripts/run_all.sh
- scripts/resume.ps1
- scripts/resume.sh

All long runs must be resumable.

## 5. Project state and evidence governance

RUN_STATE.json must track:
- current stage,
- protocol identity,
- completed stages,
- failed/gated stages,
- dataset identities,
- model identities,
- freeze identities,
- protected accesses,
- last valid checkpoint,
- next legal action,
- active long-running process where relevant.

Every experiment must emit:
- experiment ID,
- config hash,
- code/source identity,
- data/model identity,
- environment receipt,
- device/backend,
- start/end timestamps,
- status,
- output manifest,
- evidence class.

Evidence classes:

P = preregistered / locked
Q = qualification
D = deterministic derived
E = exploratory / post-hoc
X = external validation
U = unsupported / unrun

Never silently upgrade evidence class after observing outcomes.

## 6. Evidence domains and public datasets

Use separate evidence domains.

T1 REAL ADS EVENTS, REQUIRED

Use the official Criteo Attribution Modeling for Bidding dataset.

Record:
- exact upstream source,
- license,
- retrieval timestamp,
- archive SHA-256,
- compressed size,
- member/schema validation,
- validated event count.

Use for:
- real temporal structure,
- user/campaign structure,
- clicks,
- conversions,
- transformed cost,
- attribution structure.

Do not use it to claim known causal incident truth, Amazon semantics or
production policy truth.

Raw data must not be committed to Git.

T2 LARGE ADS SCALE, OPTIONAL

KDD Cup 2012 Track 2 may be used if independently obtaining/processing it adds
useful systems evidence within reasonable storage/time cost.

Do not depend on another local portfolio repository.
This track must not block completion.

T3 CONTROLLED ENTERPRISE WAREHOUSE, REQUIRED

Construct a realistic synthetic relational enterprise extension anchored to T1
structure.

Target approximately:
- 25–35 relational tables,
- 250–400 columns,
- time-varying facts,
- schema/metric versions,
- policy documents,
- account/tenant permissions,
- freshness watermarks,
- controlled known truth.

Every generated object must identify its provenance and generated status.

T4 EXTERNAL ENTERPRISE VALIDATION, REQUIRED

Use Spider2-DBT.

Pin:
- exact upstream commit,
- task manifest/hash,
- DB identities,
- evaluator identity,
- task count.

Do not train on Spider2 gold solutions.
Do not use external results to retune the primary method.

T5 SECURITY / OOD WORLDS, REQUIRED

Generate controlled adversarial and drift worlds with known expected behavior.

T6 DOMAIN DOCUMENTATION

Use official OpenRTB documentation plus clearly labeled synthetic
enterprise-style policy and metric documents.

## 7. Acquisition, validation and EDA

Create a machine-readable source registry with:

source_id
source_name
source_url
version_or_commit
license
retrieved_at
compressed_bytes
SHA256
archive/member identity
schema
redistribution policy
evidence role

Pipeline:

download
-> transport validation
-> archive validation
-> hash
-> license/provenance receipt
-> quarantine
-> streamed parsing
-> schema/range/domain validation
-> staged Parquet
-> curated relational layer
-> DuckDB

Do not materialize multi-million-row sources in one giant pandas DataFrame.
Prefer Polars, PyArrow and DuckDB with bounded/streamed processing.

Before synthetic warehouse generation, perform full T1 EDA covering:
- temporal coverage,
- missingness,
- duplicates,
- malformed records,
- user/campaign cardinality,
- concentration,
- click/conversion/cost distributions,
- extreme activity,
- temporal drift,
- leakage hazards.

Generate reports/DATA_AUDIT.md from canonical aggregate evidence.

## 8. Controlled enterprise warehouse

Build realistic table families.

Entities:
accounts
advertisers
campaigns
ad_groups
ads
keywords
audiences
products
marketplaces

Configuration:
campaign_config
budget_config
bid_config
targeting_config
conversion_config

Facts:
impression_events
click_events
conversion_events
campaign_daily
adgroup_daily
keyword_daily
account_daily
auction_daily

Semantics:
metric_definitions
metric_dependencies
business_terms
schema_aliases

Policies:
budget_policies
bid_policies
targeting_policies
account_constraints

System:
schema_versions
metric_versions
data_freshness
permission_scope
audit_events
cache_versions

Generate DDL and machine-readable lineage.

After construction/freeze, evaluation DBs must be immutable/read-only.

## 9. Semantic catalog

Represent metrics as governed objects containing:

metric_id
canonical_name
aliases
formula
required_tables
required_columns
grain
unit
freshness
sensitivity
authorization scope
version
provenance

Include realistic metrics such as:
CTR
CVR
spend
CPA
attributed conversions
attributed value
ROAS

Exact metric IDs/formulas may not be hallucinated by downstream compression.

## 10. Schema and dependency graph

Node types:
TABLE
COLUMN
METRIC
ENTITY
POLICY
DOCUMENT

Edge types:
foreign_key
contains
metric_requires
derived_from
synonym_of
documented_by
governed_by
freshness_depends_on

Implement deterministic dependency closure.

If a selected metric requires source columns, joins, numerator/denominator or
policy documents, complete those dependencies before execution.

## 11. Benchmark task compiler

Do not build the benchmark through trivial template substitution alone.

Use four task sources:
1. programmatic known-answer tasks,
2. compositional held-out tasks,
3. independently authored adversarial tasks,
4. security/OOD tasks.

For adversarial tasks, use an independent reviewer/subagent that does not inspect
the candidate method implementation before authoring/finalizing that task set.

Task families:
- lookup,
- aggregation,
- temporal comparison,
- multi-table join,
- metric reasoning,
- diagnostic reasoning,
- policy-grounded reasoning,
- ambiguity/clarification,
- freshness/schema drift,
- authorization/refusal.

Each task must include:

task_id
family
semantic_family
difficulty
query
gold_sql when applicable
gold_result_hash
required_tables
required_columns
required_metrics
required_docs
expected_behavior
tenant/account scope
schema_version
metric_version

Expected behavior:
ANSWER
CLARIFY
REFRESH
REFUSE
RETRY
ABSTAIN

Use group-disjoint splits by semantic/template family.

## 12. Gold answer validation

Correctness hierarchy:

1. result-set equivalence,
2. executable SQL,
3. SQL-text match.

For every generated SQL task:

gold SQL
-> execute
-> normalize types/order/nulls
-> canonical result
-> SHA-256 result hash.

Use metamorphic/known-answer tests to reject broken generated tasks.

## 13. Pilot, power and benchmark freeze

Do not arbitrarily freeze final test N.

E06:
- build roughly 300–500 pilot tasks,
- measure baseline success,
- paired discordance,
- task-family variance.

E07:
- perform paired power/non-inferiority planning,
- freeze locked task count,
- NI margin,
- alpha,
- bootstrap settings,
- multiplicity rules,
- feasible compute ceiling.

If required N exceeds the prespecified feasible maximum, return
INSUFFICIENT_POWER rather than weaken the margin after seeing protected data.

E08:
freeze the benchmark identity and protected final set.

## 14. Frozen primary models

Primary generation model:
Qwen3-4B.

Verify official model card/license and pin an exact revision.

Primary scientific comparisons must keep fixed:
- model checkpoint,
- tokenizer,
- chat template,
- system prompt,
- generation/decoding controls,
- output parser,
- retry policy,
- inference backend.

Only context strategy may change.

Primary context-budget frontier:
512
1024
2048
4096
8192 tokens.

Use CUDA for primary neural inference.

Retrieval:
- BM25,
- BGE-M3 dense retrieval,
- BGE-reranker-v2-m3.

Pin exact model revisions and licenses.

Generate static embeddings in GPU batches and persist them before protected
evaluation.

## 15. Baseline ladder

Implement:

B-2  No Context
B-1  Random-k, token-budget matched
B0   Oracle Minimum Context, non-deployable ceiling
B1   Full Context
B2   BM25 Top-k
B3   Dense Top-k
B4   BM25 + Dense reciprocal-rank fusion
B5   Hybrid + neural reranker
B6   B5 + schema/dependency graph closure
B7   B6 + generic LLM compression

Candidates:

C1   ContextWeave-R
C2   ContextWeave-L

B0 is not an eligible deployable comparator.

Freeze the strongest eligible baseline before the final locked experiment.

## 16. ContextWeave-R

Pipeline:

candidate generation
-> reranking
-> dependency closure
-> freshness/authorization filtering
-> utility scoring
-> token-constrained context selection
-> qualified compression

Candidate union may include:
- lexical,
- dense,
- exact entity,
- exact metric,
- semantic aliases.

Utility features may include:
- BM25,
- dense similarity,
- reranker score,
- graph distance,
- dependency role,
- centrality,
- exact metric/entity match,
- freshness,
- token cost,
- sensitivity/security risk.

Critical dependencies may not be silently dropped to meet the token budget.

If they cannot fit:
- use a structured tool retrieval,
- clarify,
- or abstain.

## 17. Direct context-utility interventions

Do not train C2 only on generic retrieval labels.

On development-only tasks run controlled interventions on top candidate context:

S
S - context_i
S - dependency_group_i
S + distractor_j

Hold all other model/inference variables fixed.

Measure downstream marginal utility and preserve interaction effects.

Limit interventions to a tractable top candidate set per task.

## 18. ContextWeave-L

Train simple development-only utility/ranking challengers such as:
- LightGBM ranker,
- XGBoost ranker,
- small MLP only if justified.

Candidate features:
lexical score
dense score
reranker score
graph distance
centrality
metric/entity match
dependency role
freshness
token cost

C2 must earn promotion over C1.

Selection order:
1. critical reliability,
2. task success,
3. token efficiency,
4. latency,
5. simpler-method tie-break.

If C1 is not materially worse, retain C1.

## 19. Context compression

Compare:

R0 Raw schema/DDL
R1 Deterministic structural compression
R2 Schema-bound abstractive compression
R3 Query-conditioned structured compression

LLM-based compression must output governed references such as:
table_id
column_ids
metric_ids
join_keys
formula_ids

IDs, formulas, units and join keys must be source-bound/copy-only.

Compression qualification metrics:
- ID preservation,
- formula preservation,
- dependency recall,
- numeric preservation,
- compression ratio.

Compression must pass its own gate before use in the final candidate.

## 20. MCP implementation

Use current stable MCP Python SDK v2 and target the current verified
2026-07-28 core protocol.

Keep core algorithms independent from the MCP adapter.

Expose read-only resources such as:
schema://
metric://
policy://
documentation://

Implement read-only tools such as:
search_schema()
describe_schema()
get_metric_definition()
run_readonly_sql()
get_campaign_timeseries()
get_freshness()
retrieve_policy()
explain_query()

Support and test:
- stdio,
- Streamable HTTP.

Do not add state-changing bid/budget/campaign actions in v1.

## 21. SQL sandbox

Use AST-based validation, not string-prefix checks.

Allow safe analytical read-only SQL.

Explicitly reject unsafe capabilities including:
INSTALL
LOAD
ATTACH
COPY
EXPORT
IMPORT
CREATE
UPDATE
DELETE
INSERT
unsafe PRAGMA
arbitrary filesystem reads
network/http extensions.

Enforce:
- allowlisted schemas/tables,
- tenant/account constraints,
- timeout,
- memory limit,
- row limit,
- output-byte limit.

Evaluation warehouse must be immutable/read-only.

## 22. Authorization

Build a local signed JWT scientific harness containing:

sub
tenant_id
account_ids
scopes
aud
iat
exp

Test:
- valid token,
- expired token,
- wrong audience,
- wrong tenant,
- wrong scope,
- wrong account,
- revoked access,
- token reuse.

Authorization must occur before protected context/data is exposed.

## 23. Cache and freshness

Keep three cache systems separate:

KA:
MCP discovery/resource metadata cache.

KB:
context-selection cache.

KC:
analytical query/result cache.

Every cacheable context object must track:
source version
schema version
metric version
data watermark
tenant
authorization scope
valid_from
valid_until
sensitivity/cache scope.

Eligibility requires:
Fresh AND Authorized.

Compare:

K0 no cache
K1 TTL
K2 semantic cache
K3 ContextWeave version/freshness-aware cache

Controlled sequence:
initial query
exact repeat
near duplicate
campaign/config update
schema update
metric-definition update
repeat after update
authorization change.

Measure:
hit rate
latency
tokens
stale reuse
stale wrong answers
cross-tenant reuse
refresh rate.

Critical:
CrossTenantLeak = 0.

## 24. Security experiment

Security is a required first-class experiment.

Include:
- prompt injection in retrieved docs,
- malicious tool metadata,
- cross-account access,
- stale-cache poisoning,
- cross-tenant cache reuse,
- metric-definition poisoning,
- schema-alias poisoning,
- SQL file exfiltration attempts,
- network exfiltration attempts,
- oversized tool output,
- DB/tool timeout,
- malicious text stored in DB,
- conflicting policy docs.

Predefine expected behavior.

Critical hard gates:

UnauthorizedExposure = 0
CrossTenantLeak = 0
CriticalExfiltration = 0

Any critical violation blocks PROMOTE_CONTEXTWEAVE.

## 25. OOD and stress worlds

Include at minimum:

S00 clean
S01 column rename
S02 table addition
S03 column removal
S04 metric redefinition
S05 stale schema cache
S06 delayed telemetry
S07 authorization revoke
S08 DB timeout
S09 duplicate entity
S10 wide schema with 100+ distractor tables
S11 conflicting policy docs
S12 prompt injection
S13 corrupt metric metadata
S14 cache poisoning
S15 compound OOD

Report conditional performance, not aggregate only.

## 26. Query execution modes

Compare independently from context selection:

Q0 Direct SQL
Q1 Plan -> SQL
Q2 MCP tool orchestration

Q3 CodeAct-like execution is optional after mandatory v1 work is complete.

Do not let Q3 block closure.

## 27. Metrics and statistical analysis

Primary quality:
TaskSuccess.

Primary efficiency:
ContextTokens.

Retrieval:
table recall
column recall
metric recall
document recall
dependency recall.

SQL:
execution success
result-set equivalence
invalid SQL.

Agent:
tool selection
argument validity
calls/task
recovery
clarification correctness
abstention/refusal correctness.

Systems:
p50/p95 latency
TTFT where meaningful
E2E latency
input/context tokens
output tokens
GPU time.

Reliability:
stale critical errors
unauthorized exposure
cross-tenant leakage
wrong metric
unsupported answer
security violations.

Optional exploratory:
GPU energy / successful task.

Do not collapse all dimensions into one opaque score.

Task is the primary paired experimental unit.

Use:
- McNemar for paired binary success,
- paired/bootstrap uncertainty,
- clustered/hierarchical resampling where dependence requires it,
- process/server replicate as outer unit for latency.

Only one primary confirmatory method comparison:

frozen selected ContextWeave
vs
strongest eligible frozen baseline.

Use limited Holm correction for secondary method comparisons.
Post-hoc slices are exploratory.

Primary hypothesis is conjunctive:

selected ContextWeave is non-inferior in TaskSuccess
AND
uses materially less context.

Freeze exact margins before protected final outcomes.

## 28. Task-complexity and mechanism analysis

Store:
join_depth
required table count
required column count
required metric count
graph distance
ambiguity
temporal operations
policy dependencies
distractor count.

Analyze where ContextWeave helps and where simpler methods are sufficient.

## 29. Ablation and error taxonomy

Ablate the frozen selected candidate by removing one component at a time:

BM25
dense retrieval
reranker
schema graph
metric dependency closure
learned utility
compression
freshness filter
cache
verification/retry
authorization prefilter.

Do not use ablation to reopen final selection.

Automatic error taxonomy:

R1 retrieval miss
R2 schema-link miss
R3 dependency miss
C1 compression loss
M1 wrong metric
S1 SQL generation
X1 SQL execution
F1 stale context
A1 authorization
G1 answer synthesis
B1 unnecessary abstention
B2 missing clarification
T1 wrong tool routing

Generate failure galleries.

## 30. GPU and systems execution

Use the RTX 4090 efficiently.

Offline GPU stages:
- BGE embeddings,
- neural reranking,
- other explicitly qualified GPU work.

End-to-end agent:
- keep Qwen3-4B resident where stable,
- use batched requests where scientific independence is preserved.

CPU parallel stages:
- DuckDB,
- Polars/PyArrow,
- BM25,
- schema graph,
- SQL,
- task compilation,
- validation,
- statistics,
- reporting.

Primary scientific generation uses one frozen Hugging Face backend.

Only after scientific method selection, compare an alternate runtime such as
vLLM in a separate systems experiment if compatible.

Separate:
- cold process,
- warm model / cache off,
- warm model / cache on.

Decompose latency into:
retrieval
reranking
graph
context planning
compression
MCP transport
generation
SQL
validation
postprocessing.

Compare direct Python reference where appropriate, MCP stdio and Streamable
HTTP.

Use balanced/randomized run order and record process replicate, GPU
temperature, VRAM and backend.

## 31. External validation

Required:
Spider2-DBT external evaluation.

Pin repo commit, task manifest, DB identities and evaluator configuration.

Never use external outcomes to retune the primary method.

Document that unknown LLM pretraining exposure means this is external task
transfer evidence, not proof of benchmark non-contamination.

After final method freeze, if practical, perform one independent 3–4B
model-family replication.

Classify all external results as X evidence.

## 32. Experiment program

Execute all feasible mandatory stages:

E00 Desktop study
E01 Environment/GPU/MCP qualification
E02 Source acquisition/license/hash
E03 Real-data EDA
E04 Enterprise warehouse build
E05 Semantic catalog/schema graph audit
E06 Task pilot
E07 Power analysis
E08 Benchmark freeze
E09 No/random/full/oracle references
E10 BM25/dense/hybrid/reranker baselines
E11 Graph-Hybrid
E12 ContextWeave-R
E13 Direct context-utility interventions
E14 ContextWeave-L
E15 Compression qualification
E16 Token-budget frontier
E17 MCP end-to-end agent
E18 Cache/freshness
E19 Security/authorization
E20 Schema/OOD stress
E21 Systems/transport benchmark
E22 Ablation/error analysis
E23 Spider2 + optional cross-model transfer
E24 One-shot locked final
E25 Post-audit/failure slicing
E26 Final release/reproduction closure

## 33. Freeze hierarchy

E00–E07
-> DESIGN_FREEZE

E08
-> BENCHMARK_FREEZE

E09–E15
-> CANDIDATE_FREEZE

E16–E22
-> FINAL_METHOD_FREEZE

E23
-> external evidence only

E24
-> LOCKED FINAL

E25
-> post-audit only

E26
-> release closure

No external/locked/post-audit result may silently redefine the frozen method.

## 34. Final decision

Mechanically derive one:

PROMOTE_CONTEXTWEAVE
PROMOTE_SIMPLE_BASELINE
ITERATE
INSUFFICIENT_POWER
REJECT

Examples:
- C2 does not beat C1 -> retain C1.
- C1 does not materially beat Graph-Hybrid -> retain Graph-Hybrid.
- quality/efficiency good but security fails -> do not promote.
- material accuracy regression -> REJECT.
- insufficient confirmatory sample -> INSUFFICIENT_POWER.

Complexity receives no preference.

## 35. Software quality

Before closure require at minimum:

ruff format
ruff check
strict mypy on governed source
pytest
unit tests
integration tests
known-answer SQL tests
semantic catalog tests
dependency graph tests
MCP stdio smoke
MCP HTTP smoke
authorization regression tests
SQL sandbox attack tests
cache isolation tests
evidence/claim-ledger validation
package build
clean-wheel install/import smoke.

CPU CI must not pretend to rerun GPU experiments.

## 36. Required repository outputs

Create professional source/config/test layout and at least:

reports/FINAL_TECHNICAL_REPORT.md
reports/EXECUTIVE_SUMMARY.md
reports/DESKTOP_STUDY.md
reports/DATA_AUDIT.md
reports/METHOD_COMPARISON.md
reports/SECURITY_ASSESSMENT.md
reports/SYSTEMS_ASSESSMENT.md
reports/FAILURE_ANALYSIS.md
reports/CLAIM_LEDGER.md
reports/REPRODUCTION_GUIDE.md
reports/RESUME_EVIDENCE.md

Create canonical machine-readable:
- experiment tables,
- manifests,
- source hashes,
- freeze records,
- receipts,
- statistical outputs.

Generate at minimum:

F1 system architecture
F2 evidence-domain architecture
F3 schema/dependency graph
F4 baseline ladder
F5 task success vs context tokens
F6 task success vs p95 latency
F7 token-budget frontier
F8 task-complexity slices
F9 error taxonomy
F10 stress/OOD heatmap
F11 security gate matrix
F12 cache latency/freshness frontier
F13 ablation result
F14 external validation
F15 final decision scorecard

All figures and public numerical tables must be generated from canonical
evidence, not manually typed values.

## 37. Final technical report

Use a research narrative covering:

1. Executive Summary
2. Problem / Industry Context
3. Desktop Study / Related Work
4. Research Questions / Hypotheses
5. Evidence Domains / Claim Boundary
6. Public Data / Provenance
7. EDA
8. Enterprise Warehouse
9. Benchmark Construction
10. Semantic Catalog / Graph
11. Baselines
12. ContextWeave-R
13. Utility Intervention Study
14. ContextWeave-L
15. Compression
16. MCP / Authorization / Security
17. Experimental Protocol
18. Retrieval Results
19. Context Efficiency
20. End-to-End Agent Results
21. Cache / Freshness
22. Security
23. OOD / Stress
24. Systems / GPU
25. Ablations
26. Error Analysis
27. External Validation
28. Final Scientific Decision
29. Limitations
30. Future Work
31. Reproducibility
32. Claim Ledger

## 38. Resume-safe evidence

Only after E24/E26, generate 2–3 concise resume bullets.

Never pre-fill a percentage improvement.

Every bullet must preserve whether the supporting evidence is:
- real public data,
- controlled/synthetic,
- external,
- local GPU,
- locked.

Never convert controlled effects into production lift.

## 39. Completion criteria

Do not declare complete until all feasible mandatory stages are complete and
verified.

A mandatory stage may be GATED only for a genuine external blocker with a
written receipt.

Completion requires:
- current-source desktop study,
- required data acquisition,
- license/provenance records,
- EDA,
- warehouse,
- semantic catalog and graph,
- benchmark compiler,
- pilot/power,
- scientific freezes,
- baseline ladder,
- C1,
- direct utility study,
- C2,
- compression qualification,
- token frontier,
- MCP end-to-end,
- cache/freshness,
- security suite,
- OOD suite,
- systems benchmark,
- ablations/error analysis,
- Spider2 external evaluation or genuine blocker,
- one-shot locked final,
- post-audit,
- software quality gates,
- final reports,
- reproducibility guide,
- resume evidence.

## 40. Execution behavior

Begin immediately.

Do not return with only a plan.

Use subagents only for genuinely independent work.

Do not let subagents launch competing heavy GPU workloads.

For deterministic long-running jobs:
- use a durable supervisor/log,
- wait efficiently,
- avoid repeated model turns solely to poll unchanged state.

If implementation fails:
- preserve failure evidence,
- diagnose,
- repair,
- continue.

If a scientific hypothesis fails:
- preserve the negative result,
- derive the correct decision,
- continue all still-valid downstream analysis.

At final completion, report:

- final scientific decision,
- selected method,
- strongest baseline,
- primary locked result,
- task-success comparison,
- context-token comparison,
- latency findings,
- security hard-gate status,
- cache/freshness findings,
- Spider2 status,
- GPU/systems findings,
- major negative results,
- limitations,
- exact reproduction command,
- final report/evidence/figure paths.

START NOW.