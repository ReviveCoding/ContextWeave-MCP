# E00 current-source study

Checked 2026-09-20 UTC. This is source qualification, not experimental evidence.

| Component | Verified upstream identity | Use and constraint |
|---|---|---|
| MCP | [Python SDK v2.2.0](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.2.0); [2026-07-28 protocol](https://modelcontextprotocol.io/specification/2026-07-28) | `MCPServer`, stdio and Streamable HTTP. Optional extensions are excluded. The stable v2 release supersedes older v1 APIs. |
| Criteo attribution | [Criteo AI Lab dataset page](https://ailab.criteo.com/criteo-attribution-modeling-bidding-dataset/); [Criteo-owned Hugging Face mirror](https://huggingface.co/datasets/criteo/criteo-attribution-dataset) | 30-day anonymized event sample; CC BY-NC-SA 4.0. The page's go.criteo.net archive URL returned HTTP 404 on this run; use the Criteo-owned mirror and record its hash. No causal incident or production policy ground truth. |
| Spider2-DBT | [Spider2 repository](https://github.com/xlang-ai/Spider2), MIT | 68 DuckDB/dbt code-agent tasks per upstream README. External transfer only; pin commit and evaluator before use. |
| OpenRTB | [IAB Tech Lab OpenRTB 2.6-202606](https://github.com/InteractiveAdvertisingBureau/openrtb2.x/releases/tag/2.6-202606) | Public domain documentation source; synthetic policy text must be labeled. |
| Qwen3-4B | [Model card](https://huggingface.co/Qwen/Qwen3-4B) | Apache-2.0; exact revision `1cfa9a7208912126459214e8b04321603b3df60c`. Fixed CUDA generation backend for primary comparisons. |
| BGE-M3 | [Model card](https://huggingface.co/BAAI/bge-m3) | MIT; revision `5617a9f61b028005a4858fdac845db406aefb181`; CUDA dense embeddings. |
| BGE-reranker-v2-m3 | [Model card](https://huggingface.co/BAAI/bge-reranker-v2-m3) | Apache-2.0; revision `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`; CUDA reranking. |
| DuckDB | [v1.5.5 release](https://github.com/duckdb/duckdb/releases/tag/v1.5.5) | MIT, local analytical warehouse. |
| PyTorch | [official installation guide](https://pytorch.org/get-started/locally/) | PyPI reported 2.14.0; CUDA qualification is required before neural evidence. |
| Transformers | [official releases](https://github.com/huggingface/transformers/releases) | PyPI reported 5.17.0. Confirm model loading in E01. |
| Retrieval/statistics/tooling | [sentence-transformers](https://github.com/UKPLab/sentence-transformers), [SciPy](https://scipy.org/), [statsmodels](https://www.statsmodels.org/), [Polars](https://pola.rs/), [PyArrow](https://arrow.apache.org/docs/python/) | Pin resolved versions in `uv.lock`; use paired task analysis. |

The release metadata above is a desktop check. Installed package identities and behavior must be confirmed in an E01 receipt; model revisions are proposed pins until downloaded and verified locally. The primary implementation must not turn these observations into PASS states.
