# medicaid-mcp

An MCP server that wraps the [data.medicaid.gov](https://data.medicaid.gov) API so Claude — and any MCP client — can explore US Medicaid and CHIP open data conversationally.

> **Status: design only. Not implemented.**
> This repository contains a `uv init` scaffold (`main.py` prints a greeting), a design document, and an
> implementation plan. None of the tools below exist yet, and nothing here is installable or runnable as an
> MCP server.
>
> - [`.claude/docs/2026-07-21-mcp-plan.md`](.claude/docs/2026-07-21-mcp-plan.md) — design: what and why
> - [`.claude/docs/2026-09-23-impl-plan.md`](.claude/docs/2026-09-23-impl-plan.md) — implementation: order and done-when

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

Lens targets assume dataset shapes that have **not** been verified against the live API. The discovery pass that confirms them runs early (step 2) precisely because everything downstream depends on it; lenses that turn out to have no backing dataset get dropped and documented, not faked with a weak proxy.

## Planned architecture

```
src/medicaid_mcp/
  server.py     # MCPServer instance, instructions, ASGI app, http + stdio entrypoints
  client.py     # DKAN API client (httpx), typed error mapping
  query.py      # Friendly filter shape → DKAN query JSON (pure, no network)
  cache.py      # In-memory TTL cache
  settings.py   # Env-var configuration
  models.py     # Result shapes for structured output
  tools/        # generic.py, lenses.py
  apps/         # MCP Apps: ui:// resources (v1.1)
```

The design doc calls this package `cms_medicaid_mcp`; `medicaid_mcp` is shown here because it matches the
distribution name in `pyproject.toml` and the repository. That is a recommendation, not a settled decision —
see "Decisions to settle" in the implementation plan.

- **Transport:** streamable HTTP (stateless, JSON responses) at `/mcp`; stdio for local development. SSE is deprecated and will not be implemented.
- **Errors:** raised as `ToolError` with the recovery hint folded into the message, not returned as a fake-success payload.
- **Deployment:** single container on a scale-to-zero host (Cloud Run or Railway are the leading candidates). No secrets, no database, no session affinity.

### Unverified targets

The design doc was written 2026-07-20 and targets dates that have since passed. These are **stated intentions, not confirmed facts**, and step 0 of the implementation plan gates all coding on checking them:

- **Protocol:** MCP revision 2026-07-28 (stateless request/response) — did it land as specified?
- **SDK:** official `mcp` Python SDK v2, pinned `<2.1` — stable was targeted for 2026-07-27; did it ship?
- **API surface:** `MCPServer` as the class name, with `stateless_http` / `json_response` kwargs.

If any of these turns out false, the design doc gets amended before code is written.

## Requirements

- Python ≥ 3.12 (see `.python-version`)
- [uv](https://docs.astral.sh/uv/)

## Local development

```bash
uv sync
uv run main.py   # currently prints "Hello from medicaid-mcp!"
```

`main.py` is `uv init` residue and gets deleted at step 1. Once the server exists, this section will cover `uv run` entrypoints for both transports, MCP Inspector usage, and the `claude mcp add --transport http` / claude.ai connector setup.

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

Planned, TDD throughout: `query.py` (table-driven, no network) → `client.py` error mapping (httpx `MockTransport` over fixtures captured during discovery) → tools and lenses (in-memory client↔server session). A manual `scripts/smoke.py` hits the live API; no live-API tests run in CI.

## Roadmap

0. **Verify the aged assumptions** — SDK, protocol, and API surface (gates everything below)
1. Scaffold `src/medicaid_mcp/`, pin dependencies, commit `uv.lock`
2. **Dataset discovery pass** against the live API — confirm lens targets, capture fixtures
3. `query.py` — filter DSL translator
4. `client.py` — DKAN client and typed error mapping
5. `cache.py`, `settings.py`, `models.py`
6. Generic tools
7. `server.py` — instructions, both transports, `Dockerfile`
8. Lenses
9. Deploy, smoke test, client setup docs *(the status banner above comes off here — not before)*
10. *(v1.1)* MCP Apps views for enrollment trend and NADAC price history

Steps 3 and 5 can run in parallel; everything else is sequential. Discovery sits at step 2 rather than late in the sequence because the fixtures it captures are what steps 4 and 8 are tested against.

See the [design document](.claude/docs/2026-07-21-mcp-plan.md) for non-goals and reasoning, and the [implementation plan](.claude/docs/2026-09-23-impl-plan.md) for per-step deliverables, done-when criteria, and risks.

## License

[MIT](LICENSE) — free to use, modify, and redistribute, including commercially. Copyright (c) 2026 Anna Lulushi.
