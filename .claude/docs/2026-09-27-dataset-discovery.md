# Dataset Discovery Pass — Step 2

**Date:** 2026-09-27
**Status:** Ready to execute
**Implements:** step 2 of [2026-09-23-impl-plan.md](2026-09-23-impl-plan.md). Where this doc and the impl plan disagree, the impl plan wins.
**Prerequisite:** steps 0 and 1 are done (`37f273c`, `7487007`).

## Context

Every lens except #6 targets a dataset nobody has checked. Steps 3, 4 and 8 depend on what those datasets really look like:
- Step 4 tests the client against fixtures, and those must be captured from the live API, never hand-written.
- Step 3's handling of numeric filters on `text` columns depends on how widespread that typing is.
- Step 8 ships only the lenses that have a verified target.

Step 2 is read-only against an open API, so it is the cheapest point to find out.

A short read-only recon on 2026-09-27, done while writing this plan, already turned up things that change downstream code. **Step 2 must confirm each one and capture it as a fixture:**

1. **An empty `/api/1/search` returns `"results": []`, a list, not an object.** Step 0's finding 1 ("results is an object keyed by URI") holds only when there are hits, so `models.py` and `search_datasets` must handle both shapes.
2. **`total` is a JSON string** (`"total":"0"`), not a number.
3. **`/api/1/search?sort=modified&sort-order=desc` works.** That makes lens #8 viable with no dataset of its own.
4. **Many lens candidates are split into one dataset per year:** NADAC (2013–2026), State Drug Utilization (1991–2026), and the Core Set quality measures. A lens asked for `months_back=12` may have to query two datasets. That affects how lenses are designed, not just which dataset ids they use.
5. **Column typing is mixed, not uniformly `text`.** For example, in `6165f45b-…`, `total_medicaid_enrollment` is `int` but `total_adult_medicaid_enrollment` is `text`.
6. **Long column names are machine-truncated with a hash suffix** (e.g. `total_applications_for_financial_assistance_submitted_at_st_d6fa`). Lenses must use the verified names; they can't guess them.
7. **Candidate ids from recon, all unverified.** Candidates are not results: each one needs the checks below before it goes in the lens table.

| Lens | Recon candidate(s) |
|---|---|
| 1, 2 enrollment | `6165f45b-ca93-5bb5-9d06-db29c692a360` (State Medicaid and CHIP Applications, Eligibility Determinations, and Enrollment Data; `reporting_period` int, 11,118 rows); `4723da0d-4d04-46ce-8163-e4b58c8fe728` (Separate CHIP Enrollment by Month and State) |
| 3 renewals | `e6205a51-e6d7-4849-9882-4483b8a28c41` (Updated Renewal Outcomes; last modified 2024-11, so possibly frozen after unwinding); `5abea2e0-3f8e-4b49-a50d-d63d5fd9103c` (State Medicaid and CHIP Eligibility Processing Data; current) |
| 4 NADAC | Per-year "NADAC (National Average Drug Acquisition Cost) YYYY", e.g. 2026 = `fbb83258-11c7-47f5-8b18-5f8e79f7e704`; also "NADAC Comparison" `a217613c-…` and "First Time NADAC Rates" `e3af839d-…` |
| 5 SDUD | Per-year "State Drug Utilization Data YYYY" |
| 6 managed care | `0bef7b8a-c663-5b14-9a46-0b5c2b86b0fe` (confirmed at step 0) |
| 7 Core Set | Per-year "YYYY Child and Adult Health Care Quality Measures [Quality]", latest 2025 = `14bc26c3-5584-4032-9175-f3a0399cb206` |
| 8 what's new | `/api/1/search` sorted by `modified`, no dataset |
| 1115 waivers | `fulltext=1115` returns 0 results. `waiver` returns only "Section 1915(c) waiver program participants", which is a different waiver authority and would be exactly the weak proxy the design doc forbids |

---

## Deliverables

1. **`scripts/capture_fixtures.py`** (committed). It is the only way fixtures get written, so every fixture can be regenerated and none is hand-written.
2. **`tests/fixtures/*.json` plus `tests/fixtures/manifest.json`** (committed).
3. **A "Findings" subsection under step 2 in the impl plan:** the lens table, answers to the open questions, and new API findings.
4. **Sync updates to the README, CLAUDE.md and this doc**, in the same commit.

Exploration itself (ad-hoc queries, the catalog-wide type survey) runs in the scratchpad and is not committed. Its **method and results** go into the Findings subsection so someone else can reproduce them.

---

## A. Per-lens verification

For each of lenses 1–8, run these checks and fill one row of the Findings lens table.

1. **Metastore check.** Fetch `GET /api/1/metastore/schemas/dataset/items/{id}?show-reference-ids`. Record the title, `modified`, the number of distributions, and each distribution's `identifier` and media type.
2. **Datastore check.** Query `GET /api/1/datastore/query/{distributionId}?limit=1&schema=true`. Record `count`, then each column the lens needs, with its schema type and a sample value.
3. **Query the lens would actually run.** Run it as the **POST JSON** that `query.py` will emit (`POST /api/1/datastore/query/{distributionId}` with `conditions` / `properties` / `sort` / `limit`). Confirm it returns the expected rows. If POST doesn't behave like GET, record that; it becomes a new API finding.
4. **Granularity and freshness.** Record time grain (monthly, quarterly, annual), latest period present, row-level duplicates (e.g. `preliminary_or_updated` giving two rows per state-month for #1/#2), and whether the dataset is still being updated.
5. **Verdict.** Either **verified** (dataset id, distribution id(s), exact column names, the lens query, and any signature change) or **dropped** (a written rationale). **No weak proxies.** If the only candidate answers a different question, drop the lens.

Lens-specific questions that must be answered in writing:

- **#1/#2:**
  - Is the data monthly (the design's `months_back` assumes it)?
  - Which column is the headline enrollment figure?
  - How should the lens handle preliminary vs updated rows so it doesn't double-count?
  - Does CHIP-only enrollment need the second dataset, or is it already covered?
- **#3:** Which candidate is live? If only the frozen unwinding-era dataset has renewal outcomes, decide between shipping it (with the date range stated in the tool description) and dropping it, and write down why.
- **#4 NADAC:**
  - Confirm each year is a separate dataset with one distribution.
  - Record the NDC format (11-digit, dashes or not, zero-padding).
  - Does the drug-name column need `like`, and is it case-sensitive?
  - Does the current-year dataset update weekly?
  - How can a lens find the current-year dataset id: a stable title pattern via search, or a hardcoded registry? Record the evidence, not the decision; the design is step 8's.
- **#5 SDUD:**
  - Latest year available.
  - NDC format, whether it's one column or split into labeler/product/package, and whether it joins against NADAC's NDC.
  - Suppression flags or suppressed values.
  - Quarterly grain.
  - Same per-year discovery question as #4.
- **#6:** Capture fixtures and confirm step 0's column list and `text` typing still hold.
- **#7:** Is child vs adult a column or separate datasets? Is the "YYYY … Quality" title suffix consistent (it already isn't in recon)? Where is the measure identifier and the state rate?
- **#8:**
  - Confirm `sort`/`sort-order` and pagination (`page`, `page-size`).
  - Is `modified` filterable server-side, or must a `since` cutoff be applied client-side over sorted pages?
  - Are there `theme` / `keyword` facets usable as `categories`?

## B. `list_1115_waivers`

Search more before concluding. Try `fulltext` for "1115", "demonstration", "section 1115" and "waiver", and scan the full `keyword` and `theme` facet lists from one search response for anything waiver-like. If nothing on data.medicaid.gov carries 1115 demonstration data, **drop the lens** and record:
- the queries tried,
- that 1915(c) is a different authority, not a substitute,
- where 1115 data does live (medicaid.gov's state waivers list), as a pointer for a future non-DKAN source. This is out of scope for v1.

## C. Open questions (the impl plan's list)

Answer each in the Findings subsection with evidence (dataset id, column, observed value):

- Is enrollment monthly? (#1/#2 above.)
- NADAC and SDUD column shapes, NDC formats, `like` vs exact matching, and whether NADAC history spans multiple datasets or distributions. (#4 and #5 above.)
- 1115 waivers present? (B above.)
- **How widespread is `text` typing?** This one is answered with a catalog-wide survey:
  - For every dataset, via `/api/1/search` paged through all 277: follow each distribution with a datastore to `?limit=1&schema=true`, and tally column types.
  - Specifically count **numeric-looking `text` columns**: `text` columns whose sampled values (e.g. 20 rows) all parse as numbers.
  - Record datasets with no datastore distribution separately; don't count them as zero.
  - Run it sequentially, with a descriptive `User-Agent`.
- **Can the server compare numerically on a `text` column?** Empirically run a `>` condition against a known numeric-looking `text` column (e.g. `total_adult_medicaid_enrollment` in `6165f45b`) and check whether the results are lexically or numerically ordered. Also check whether DKAN's query API has any cast or type option.
  - This decides step 3: if the server can't cast, the DSL must **refuse** `<`/`<=`/`>`/`>=` on `text` columns, with a `ToolError` hint.
  - Record the evidence and the resulting step-3 rule.

## D. Fixtures

### `scripts/capture_fixtures.py`

- **Capture table:** a declarative list of captures, each `{name, method, path, params, json_body, expect_status}`. It uses `httpx` (already a runtime dependency) with a 30 s timeout and `User-Agent: medicaid-mcp-fixture-capture`.
- **Fail loud, all-or-nothing:** if any response's status differs from `expect_status`, or a body that should be JSON isn't, the script aborts **without writing anything**. Results are collected in memory and written only after every capture succeeds, so a half-updated fixture set can't exist.
- **Faithful bodies:** each body is written as parsed JSON re-serialized with `indent=2` for readable diffs. Content is never edited, filtered or trimmed after the fact. Keep fixtures small **by request parameters** (`limit=3`, a narrow condition) instead.
- **Manifest:** `tests/fixtures/manifest.json` records for each fixture the method, URL, params or body, status, and `captured_at`. Tests later assert that the fixture they load is one the manifest knows about.
- **Checks:** passes `ruff check` and `mypy --strict`.
- **Not in CI:** the script never runs in CI, and nothing under `tests/` imports it.

### Fixture set

**Client (step 4):**

| Name | Captures |
|---|---|
| `search_hits` | `fulltext=managed care`, `page-size=3`: the object-keyed `results` |
| `search_empty` | `fulltext=1115`: the `[]` results, string `total` |
| `search_sorted_modified` | `sort=modified&sort-order=desc&page-size=3` |
| `metastore_item` | `0bef7b8a` with `?show-reference-ids` |
| `metastore_item_no_refs` | Same item **without** the flag: the "distribution has no `identifier`" case from real data |
| `metastore_not_found` | Nonexistent dataset id, capturing the real error status and body |
| `datastore_schema` | `0bef7b8a`'s distribution, `limit=1&schema=true` |
| `datastore_query_post` | POST JSON with one condition, `limit=3` |
| `datastore_limit_zero` | `limit=0`: the real HTTP 400 body |
| `datastore_bad_column` | Condition on a nonexistent column, capturing the real error status and body |

**Lenses (step 8):** one fixture per **verified** lens, captured with exactly the query recorded in A.3, `limit ≤ 5`. Dropped lenses get none.

**Not captured:** malformed payloads and timeouts. Step 4 builds those in-test with `MockTransport`, because the real API won't produce them on demand. That is constructing a transport failure, not hand-writing a fixture of API data.

## E. Doc updates (same commit)

- **Impl plan:**
  - Add a "Findings (2026-09-27)" subsection under step 2 holding:
    - the lens table (lens, verdict, dataset id, distribution id(s), key columns and types, grain, latest period, signature changes or drop rationale),
    - the `list_1115_waivers` verdict,
    - open-question answers with evidence,
    - the type-survey method and numbers,
    - the step-3 rule for numeric ops on `text` columns.
  - Add **new API findings** (empty search is `[]`, `total` is a string, plus anything found in A–C) to the step 0 findings as items 6+, since step 4 and step 5 consume them.
  - Update step 3's third bullet from "cast or raise" to whichever was decided.
  - Mark step 2 done and update Status/Updated.
  - Adjust the Risks table if a lens drops.
- **README:**
  - "Planned lenses": mark each lens verified or dropped (one-line reason), and say whether `list_1115_waivers` is in or out. Replace "Only lens #6 has a target verified…".
  - "Verified: upstream API": add the new findings, and replace "at least one dataset types every column as `text`" with the measured prevalence.
  - Roadmap: mark item 2 done.
- **CLAUDE.md:**
  - Replace "Lens targets are unverified except #6" with the outcome.
  - Add the empty-search `[]` / string `total` rule under the verified API facts.
  - Replace the "cast or refuse" line with the decided rule.
  - Update "Project state" (step 3 is next; steps 3 and 5 can run in parallel).
- **Design doc:** no edits. Step 8 records dropped lenses there; the impl plan records overrides.
- **This doc:** Status → Done.

**Commit:** `step 2: dataset discovery — lens verdicts, fixtures, text-typing survey`.

## Verification

- **Lens coverage:** every lens row in the Findings table holds either a verified dataset id plus distribution id(s), or a drop rationale. `list_1115_waivers` has an explicit verdict.
- **Open questions:** each one in C has a written answer that cites a dataset id and column.
- **Fixtures:**
  - `uv run python scripts/capture_fixtures.py` exits 0.
  - Every fixture file is listed in `manifest.json` and vice versa. Check this with a one-liner comparing `ls tests/fixtures/*.json` against the manifest keys.
  - Each non-200 fixture's status matches its `expect_status`.
- **Failure path:** temporarily set one `expect_status` wrong and rerun. The script must exit non-zero and leave `tests/fixtures/` unchanged (`git status` clean). Then revert the change.
- **Tooling still clean:** `uv run ruff check . && uv run ruff format --check .`, `uv run mypy src scripts`, and `uv run pytest` still exit 5 (no tests yet).
- **Docs:** `grep -n "unverified except #6\|Only lens #6" README.md CLAUDE.md` returns no hits.

## Out of scope

- Any `src/` code: the step-3 rule is decided here but implemented in step 3.
- Lens implementations and final lens signatures: step 8, informed by the Findings.
- Tests.
- A non-DKAN source for 1115 waivers.
