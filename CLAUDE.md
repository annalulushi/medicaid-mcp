# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project state

Design-only. No server code exists yet: `main.py` is a `uv init` greeting stub (deleted at step 1), and `pyproject.toml` has `dependencies = []` and no `[build-system]`. Work proceeds by the numbered steps in the implementation plan, and **step 0 gates everything** — do not pin `mcp` or write server code until its open checks are verified.

Three documents, in precedence order when they disagree:

1. `.claude/docs/2026-09-23-impl-plan.md` — order, done-when criteria, settled decisions, verified API findings. **Wins over the design doc.**
2. `.claude/docs/2026-07-21-mcp-plan.md` — what and why (tool signatures, lenses, error model, non-goals). Stale on package name (`cms_medicaid_mcp`), env-var prefix (`CMS_MEDICAID_*`), step numbering, and the API facts corrected in the plan. Don't edit it to fix these; the plan records the overrides.
3. `README.md` — public; restates parts of the plan.

**When plan content changes, update the matching README section in the same commit.** The plan's "Keeping the README in sync" table lists the pairs. The README's design-only banner comes off only after step 9's end-to-end check passes against the deployed URL.

## Commands

Available now:

```bash
uv sync
```

Planned from step 1 (dev deps `pytest`, `pytest-asyncio`, `ruff`, `mypy`; build backend `hatchling`):

```bash
uv run pytest                                        # all tests
uv run pytest tests/test_query.py::test_name         # single test
uv run ruff check . && uv run ruff format .
uv run mypy src
uv run python scripts/smoke.py                       # manual, hits the live API; never in CI
```

Commit `uv.lock` (it is intentionally not gitignored).

## Architecture (planned)

Package `src/medicaid_mcp/`, a hybrid MCP server over the data.medicaid.gov DKAN API (open, no auth). Four layers with strict boundaries:

- **`client.py`** knows HTTP only. Returns parsed JSON or raises `ApiTimeout` / `ApiHttpError` / `ApiPayloadError`.
- **`query.py`** is pure translation from the friendly filter DSL to DKAN query JSON. No network, no state, imports nothing from `client`.
- **`tools/generic.py`** is the MCP surface: `search_datasets`, `get_dataset`, `list_dataset_columns`, `query_dataset`. It validates input, calls query/client, shapes typed results (`models.py`) for structured output, and re-raises errors as `ToolError`.
- **`tools/lenses.py`** has eight curated tools, each composing the internal `_query` helper (one query-construction code path). A ninth, `list_1115_waivers`, is deferred until step 2's discovery.

Data flow: `query_dataset` (validate) → `query.translate` → `client.datastore_query` → shaped result. Caching (`cache.py`, in-memory): search 15 min, metadata 1 hour, rows never. `settings.py` reads `MEDICAID_MCP_*` env vars plus unprefixed `PORT`; README's Configuration table is the reference for names and defaults. Transport is stateless streamable HTTP with JSON responses at `/mcp`, plus stdio for local dev. No SSE.

## Non-obvious rules

- **Errors go through `ToolError` with the recovery hint in the message** (e.g. "Call list_dataset_columns(...)"). Never return a success-shaped error payload or an empty result where an error occurred.
- **Verified API facts that contradict the design doc** (full details in the plan, step 0):
  - `/api/1/search` returns `results` as an object keyed by URI, so iterate `.values()`.
  - The id field is `identifier`, not `id`.
  - Column schema is not in the metastore item. `get_dataset` makes two requests: metastore item → distribution `identifier` → `/api/1/datastore/query/{distributionId}`.
  - Metastore requests need `?show-reference-ids`, or the distribution has no id.
  - The API does not cap `limit`. The 500 cap is ours to enforce, and `limit=0` is an HTTP 400. Reject `limit < 1` or `> 500` with an error; never clamp. `list_dataset_columns` uses `limit=1`.
- **Columns are often typed `text`, including numeric counts and `year`.** `<`/`>` filters on them compare lexically (`"9" > "10"`). The filter DSL must cast or refuse these comparisons, never silently return wrong rows.
- **Lens targets are unverified except #6** (managed care, `0bef7b8a-c663-5b14-9a46-0b5c2b86b0fe`). A lens with no backing dataset is dropped and the gap documented. Don't substitute a weak proxy.
- Server `instructions` and tool descriptions must stay under 2KB (clients truncate), with critical details first.
- `query_dataset` defaults to `limit=50` and nudges pagination ("N of M rows; call again with offset=…") rather than dumping rows.
- Tests: `test_client.py` uses httpx `MockTransport` over real fixtures in `tests/fixtures/` captured during step 2 (don't hand-write them). Tools and lenses are tested through the SDK's in-memory client↔server session. Inject a clock for TTL tests instead of using `sleep`.
- Non-goals: analytics features and a standalone web frontend. UI is MCP Apps (`ui://` resources, v1.1 only), and every tool must stay fully useful as text.
