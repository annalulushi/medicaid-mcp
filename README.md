# medicaid-mcp

An MCP server that wraps the [data.medicaid.gov](https://data.medicaid.gov) API so Claude — and any MCP client — can explore US Medicaid and CHIP open data conversationally.

> **Status: design only. Not implemented.**
> This repository currently contains a `uv init` scaffold (`main.py` prints a greeting) and the design document at
> [`.claude/docs/2026-07-21-mcp-plan.md`](.claude/docs/2026-07-21-mcp-plan.md). None of the tools below exist yet.
> Nothing here is installable or runnable as an MCP server.

## What it will do

A hybrid server over the data.medicaid.gov DKAN API (OpenAPI 3.0.2, no auth):

- a **thin generic query layer** so ad-hoc questions are answerable at all, and
- a set of **curated lenses** for the questions people actually repeat — enrollment trends, drug pricing (NADAC), renewals/unwinding, managed care, and quality measures.

It is distinct from the separate Medicare Coverage MCP (Part B NCDs/LCDs): different dataset, different audience, different server.

### Planned generic tools

| Tool | Purpose |
| --- | --- |
| `search_datasets` | Search the catalog by query, publisher, keyword, or theme. |
| `get_dataset` | Full metadata for one dataset, plus a synthesized `columns` array. |
| `list_dataset_columns` | Just the columns — the cheap orientation call. |
| `query_dataset` | Filter, select, sort, and paginate rows via a friendly filter DSL. |

Intended call pattern: `search_datasets` → `list_dataset_columns` → `query_dataset`, or a lens directly.

### Planned lenses

- `get_state_enrollment_snapshot` — recent monthly Medicaid/CHIP enrollment for one state.
- `compare_states_enrollment_trend` — multi-state trend, shaped for summarization or charting.
- `get_state_eligibility_renewals` — renewal/termination churn.
- `get_drug_price_nadac` — National Average Drug Acquisition Cost lookups.
- `get_state_drug_utilization` — units, prescriptions, and amounts reimbursed.
- `get_managed_care_enrollment` — enrollment by plan and program type.
- `get_quality_measures` — Child/Adult Core Set performance measures.
- `whats_new_medicaid` — recently modified datasets.

Lens targets assume dataset shapes that have **not** been verified against the live API. A discovery pass is the first implementation task; lenses that turn out to have no backing dataset get dropped and documented, not faked with a weak proxy.

## Planned architecture

```
src/cms_medicaid_mcp/
  server.py     # MCPServer instance, instructions, ASGI app, http + stdio entrypoints
  client.py     # DKAN API client (httpx), typed error mapping
  query.py      # Friendly filter shape → DKAN query JSON (pure, no network)
  cache.py      # In-memory TTL cache
  settings.py   # Env-var configuration
  models.py     # Result shapes for structured output
  tools/        # generic.py, lenses.py
  apps/         # MCP Apps: ui:// resources (v1.1)
```

The package name is unsettled: the design doc says `cms-mcp` / `cms_medicaid_mcp`, this repository is `medicaid-mcp`. Pick one before step 1.

- **Protocol:** MCP 2026-07-28 (stateless request/response).
- **SDK:** official `mcp` Python SDK v2, pinned `<2.1`.
- **Transport:** streamable HTTP (stateless, JSON responses) at `/mcp`; stdio for local development. SSE is deprecated and will not be implemented.
- **Errors:** raised as `ToolError` with the recovery hint folded into the message, not returned as a fake-success payload.
- **Deployment:** single container on a scale-to-zero host (Cloud Run or Railway are the leading candidates). No secrets, no database, no session affinity.

## Requirements

- Python ≥ 3.12 (see `.python-version`)
- [uv](https://docs.astral.sh/uv/)

## Local development

```bash
uv sync
uv run main.py   # currently prints "Hello from medicaid-mcp!"
```

Once the server exists, this section will cover `uv run` entrypoints for both transports, MCP Inspector usage, and the `claude mcp add --transport http` / claude.ai connector setup.

## Configuration

Planned environment variables. None are secrets — the upstream API is open.

| Variable | Default |
| --- | --- |
| `CMS_MEDICAID_BASE_URL` | `https://data.medicaid.gov` |
| `CMS_MEDICAID_TIMEOUT` | `30` (seconds) |
| `CMS_MEDICAID_CACHE_TTL_SEARCH` | `900` |
| `CMS_MEDICAID_CACHE_TTL_META` | `3600` |
| `CMS_MEDICAID_LOG_LEVEL` | `INFO` |
| `PORT` | `8000` |

## Testing

Planned, TDD throughout, in this order: `query.py` (table-driven, no network) → `client.py` error mapping (httpx `MockTransport` + captured fixtures) → tools and lenses (in-memory client↔server session). A manual `scripts/smoke.py` hits the live API; no live-API tests run in CI.

## Roadmap

1. Project scaffold and dependency pins
2. `query.py`, `client.py`, `cache.py` / `settings.py` / `models.py`
3. Generic tools
4. `server.py` — instructions, both transports, `Dockerfile`
5. Dataset discovery pass against the live API
6. Lenses
7. Deploy, smoke test, client setup docs
8. *(v1.1)* MCP Apps views for enrollment trend and NADAC price history

See the [design document](.claude/docs/2026-07-21-mcp-plan.md) for non-goals, open questions, and the reasoning behind each decision.

## License

[MIT](LICENSE) — free to use, modify, and redistribute, including commercially. Copyright (c) 2026 Anna Lulushi.
