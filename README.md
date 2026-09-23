# medicaid-mcp

An MCP server that wraps the [data.medicaid.gov](https://data.medicaid.gov) API so Claude — and any MCP client — can explore US Medicaid and CHIP open data conversationally.

> **Status: design only. Not implemented.**
> This repository contains a `uv init` scaffold (`main.py` prints a greeting), a design document, and an
> implementation plan. None of the tools below exist yet, and nothing here is installable or runnable as an
> MCP server.
>
> - [`.claude/docs/2026-07-21-mcp-plan.md`](.claude/docs/2026-07-21-mcp-plan.md) — design: what and why
> - [`.claude/docs/2026-09-23-impl-plan.md`](.claude/docs/2026-09-23-impl-plan.md) — implementation: order and done-when. Where the two disagree, the implementation plan wins.

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

Numbered to match the design doc and implementation plan, which refer to lenses by number.

1. `get_state_enrollment_snapshot` — recent monthly Medicaid/CHIP enrollment for one state.
2. `compare_states_enrollment_trend` — multi-state trend, shaped for summarization or charting.
3. `get_state_eligibility_renewals` — renewal/termination churn.
4. `get_drug_price_nadac` — National Average Drug Acquisition Cost lookups.
5. `get_state_drug_utilization` — units, prescriptions, and amounts reimbursed.
6. `get_managed_care_enrollment` — enrollment by plan and program type.
7. `get_quality_measures` — Child/Adult Core Set performance measures.
8. `whats_new_medicaid` — recently modified datasets.

A ninth candidate, `list_1115_waivers`, is deferred: waiver data may not live on data.medicaid.gov at all.

Only lens #6 has a target verified against the live API so far. The rest assume dataset shapes that are still unconfirmed. The discovery pass that checks them runs early (step 2) because everything after it depends on the results. A lens with no backing dataset gets dropped and the gap documented, not faked with a weak proxy.

## Planned architecture

```
src/medicaid_mcp/
  server.py     # Server instance, instructions, ASGI app, http + stdio entrypoints
  client.py     # DKAN API client (httpx), typed error mapping
  query.py      # Friendly filter shape → DKAN query JSON (pure, no network)
  cache.py      # In-memory TTL cache
  settings.py   # Env-var configuration
  models.py     # Result shapes for structured output
  tools/        # generic.py, lenses.py
  apps/         # MCP Apps: ui:// resources (v1.1)
```

- **Transport:** streamable HTTP (stateless, JSON responses) at `/mcp`; stdio for local development. SSE is deprecated and will not be implemented.
- **Errors:** raised as `ToolError` with the recovery hint folded into the message, not returned as a fake-success payload.
- **Deployment:** single container on a scale-to-zero host (Cloud Run or Railway are the leading candidates). No secrets, no database, no session affinity.

### Settled decisions (2026-09-23)

These overrule the design doc; the implementation plan records the reasoning.

- **Package:** `medicaid_mcp`, not `cms_medicaid_mcp`.
- **Build backend:** `hatchling`.
- **Env-var prefix:** `MEDICAID_MCP_*`, not `CMS_MEDICAID_*`.

## What has and hasn't been verified

### Not yet verified

The design doc was written 2026-07-20 and targets dates that have since passed. These are **stated intentions, not confirmed facts**, and step 0 of the implementation plan gates all coding on checking them:

- **Protocol:** MCP revision 2026-07-28 (stateless request/response) — did it land as specified?
- **SDK:** official `mcp` Python SDK v2, pinned `<2.1` — stable was targeted for 2026-07-27; did it ship?
- **API surface:** `MCPServer` as the class name, with `stateless_http` / `json_response` kwargs.

If any of these turns out false, the design doc gets amended before code is written.

### Verified: upstream API (2026-09-23)

All three data.medicaid.gov DKAN endpoints are live and the catalog holds 277 datasets. Five findings correct the design doc:

- `search` returns an object, not an array.
- The id field is `identifier`, not `id`.
- Column schema needs a second request.
- `?show-reference-ids` is required to reach the datastore.
- The 500-row cap is ours to enforce, not the API's.

There is also one hazard: at least one dataset types every column as `text`, including counts, so a naive `>`/`<` filter would compare values as strings and return wrong rows. The filter DSL will cast or refuse those comparisons, never run them silently. Details are in the [implementation plan](.claude/docs/2026-09-23-impl-plan.md).

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

Planned environment variables. None are secrets — the upstream API is open. The design doc still lists these under the old `CMS_MEDICAID_*` prefix; the names below are the settled ones.

| Variable | Default | Purpose |
| --- | --- | --- |
| `MEDICAID_MCP_BASE_URL` | `https://data.medicaid.gov` | Upstream API root |
| `MEDICAID_MCP_TIMEOUT` | `30` | Request timeout, seconds |
| `MEDICAID_MCP_CACHE_TTL_SEARCH` | `900` | Search-result cache lifetime, seconds |
| `MEDICAID_MCP_CACHE_TTL_META` | `3600` | Dataset-metadata cache lifetime, seconds |
| `MEDICAID_MCP_LOG_LEVEL` | `INFO` | Log level |
| `PORT` | `8000` | HTTP listen port; unprefixed because hosting platforms set it |

Row data is never cached.

## Testing

Planned, TDD throughout: `query.py` (table-driven, no network) → `client.py` error mapping (httpx `MockTransport` over fixtures captured during discovery) → tools and lenses (in-memory client↔server session). A manual `scripts/smoke.py` hits the live API; no live-API tests run in CI.

## Roadmap

0. **Verify the aged assumptions** — SDK, protocol, and server API surface (gates everything below)
1. Scaffold `src/medicaid_mcp/`, pin dependencies, commit `uv.lock`
2. **Dataset discovery pass** against the live API — confirm lens targets, capture fixtures
3. `query.py` — filter DSL translator
4. `client.py` — DKAN client and typed error mapping
5. `cache.py`, `settings.py`, `models.py`
6. Generic tools
7. `server.py` — instructions, both transports, `Dockerfile`
8. Lenses
9. Deploy, smoke test, client setup docs *(the status banner above comes off here — not before)*
10. *(v1.1)* MCP Apps views for enrollment trend (lenses #1/#2) and NADAC price history (lens #4)

Steps 3 and 5 can run in parallel; everything else is sequential. Discovery comes at step 2 rather than near the end because steps 4 and 8 are tested against the fixtures it captures, and step 3's handling of `text`-typed columns depends on what it finds.

See the [design document](.claude/docs/2026-07-21-mcp-plan.md) for non-goals and reasoning, and the [implementation plan](.claude/docs/2026-09-23-impl-plan.md) for per-step deliverables, done-when criteria, and risks.

## License

[MIT](LICENSE) — free to use, modify, and redistribute, including commercially. Copyright (c) 2026 Anna Lulushi.
