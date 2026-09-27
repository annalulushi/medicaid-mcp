# Package Scaffolding — Steps 0 and 1

**Date:** 2026-09-27
**Status:** Done 2026-09-27. Phase A results are in the impl plan (step 0); Phase B passed every check under Verification
**Implements:** steps 0 and 1 of [2026-09-23-impl-plan.md](2026-09-23-impl-plan.md). Where this doc and the impl plan disagree, the impl plan wins. Layout follows the README's "Planned architecture" tree.
**Why step 0 is folded in:** step 1 needs "the step-0-verified `mcp` pin", and step 0 was still open. So Phase A closes step 0 and Phase B scaffolds. **Phase B does not start until Phase A passes.**

## Context

The repo is design-only. `pyproject.toml` has `dependencies = []` and no `[build-system]`, `main.py` is `uv init` residue, and there is no package. Step 0 gates all code, and CLAUDE.md forbids pinning `mcp` before step 0 is verified.

A read-only check of PyPI on 2026-09-27 found that `mcp` **2.0.0 shipped stable on 2026-07-28**, followed by 2.1.0 (2026-08-24) and 2.2.0 (2026-09-07). The design doc's `<2.1` upper bound was written for a beta and is now stale. Phase A confirms this from primary sources and chooses the real pin.

Outcome: step 0's table is closed and the pin is recorded. After that, an importable, empty `src/medicaid_mcp/` package builds with hatchling, has dev tooling wired up, and has a committed `uv.lock`. The README, impl plan, and CLAUDE.md all reflect the new state.

---

## Phase A — Step 0: verify the aged assumptions

Record each answer as **Yes/No + date + source URL** in the impl plan's step 0 table. Verify against primary sources and code, not blog posts.

| # | Check | How to verify |
|---|---|---|
| 1 | `mcp` v2 stable shipped | `https://pypi.org/pypi/mcp/json`: 2.x releases, upload dates, none yanked or pre-release. Cross-check the `modelcontextprotocol/python-sdk` GitHub release notes for 2.0.0. |
| 2 | 2026-07-28 protocol revision landed as specified | The spec at `modelcontextprotocol.io/specification/2026-07-28` plus its changelog. Confirm stateless request/response with no initialize handshake and no protocol-level session. |
| 3 | `MCPServer` class name; `stateless_http` / `json_response` are constructor kwargs | **Empirically**, in a throwaway env that leaves the project untouched: `uv run --no-project --with "mcp==2.2.0" python -c "…"`. Import `MCPServer`, record its import path, and print `inspect.signature(MCPServer.__init__)`. If the kwargs moved (e.g. to `run()` or an app factory), record where they live. |

**Also record, since the same scratch env is already open (these feed steps 6–7):** the import paths of `ToolError` and of the in-memory client↔server session helper used for tests.

**Pin rule.** Default to `mcp>=2.2.0,<2.3`. That tracks the latest stable minor and keeps the design doc's intent of holding back the next minor. Deviate only if checks 1–3 give a concrete reason (e.g. a regression in 2.2), and write the reason down.

**Stop condition.** If any check answers **No**: record it, amend the design doc (the impl plan requires this), report to the user, and **do not start Phase B**.

### Phase A doc updates (same commit, per the impl plan's sync table)

- **Impl plan:** fill in the step 0 table. Set decision 4 ("SDK version") to SETTLED with the pin and its rationale. Add "`mcp` pin" to the "Current overrides" list in the Basis line, since it overrides the design doc's `<2.1`. Update the Status/Updated lines.
- **README:** replace "Not yet verified" with a "Verified: SDK and protocol (2026-09-27)" subsection, or amend it if any answer was No. Add the SDK pin to "Settled decisions". Mark roadmap item 0 done.
- **CLAUDE.md:** drop "step 0 gates everything" and "do not pin `mcp`… until verified" from "Project state".

**Commit A:** `step 0: verify SDK, protocol, and MCPServer API; settle mcp pin`. It includes this doc.

---

## Phase B — Step 1: scaffold the package

### File tree (README "Planned architecture", settled package name)

```
src/medicaid_mcp/
  __init__.py
  server.py
  client.py
  query.py
  cache.py
  settings.py
  models.py
  tools/
    __init__.py
    generic.py
    lenses.py
  apps/
    __init__.py
tests/
  conftest.py
scripts/
  .gitkeep
```

**Content rule: every module is a docstring only.** No functions, classes, imports, or `NotImplementedError` stubs. Each docstring states the module's responsibility and boundary, taken from CLAUDE.md's Architecture section. Examples: `query.py`: "pure translation; imports nothing from `client`". `client.py`: "HTTP only; raises `ApiTimeout`/`ApiHttpError`/`ApiPayloadError`". `apps/__init__.py`: "v1.1, step 10". Real code arrives at the step that owns each module, test-first.

**Deliberately not created now:**
- `tests/fixtures/`: step 2 captures it from the live API and hand-writing fixtures is forbidden.
- `test_*.py` files: each arrives with its step.
- `scripts/smoke.py`: step 9.
- `apps/ui/`: step 10.
- `Dockerfile`: step 7.
- `[project.scripts]` entry point: step 7. Pointing one at a `main` that doesn't exist would give a broken console script.

### `pyproject.toml`

Use `uv add`, not hand edits, so that versions resolve to current releases:

```bash
uv add "mcp>=2.2.0,<2.3" httpx          # pin exactly as Phase A recorded
uv add --dev pytest pytest-asyncio ruff mypy
```

Then edit by hand:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- Replace the "Empty on purpose" comment above `dependencies` with: `# mcp pin settled at step 0 (2026-09-27) — see .claude/docs/2026-09-23-impl-plan.md. httpx is declared directly because client.py uses it, not just transitively via mcp.`
- No `[tool.hatch]` config. The impl plan verified that `src/` autodetection and `LICENSE` inclusion work with zero config.
- Tool config:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"                          # tools/lenses tests run over async in-memory sessions
asyncio_default_fixture_loop_scope = "function"

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "BLE", "SIM"]   # BLE = blind except: enforces fail-loud

[tool.mypy]
python_version = "3.12"
strict = true
```

### Other changes

- `git rm main.py`.
- `uv sync` regenerates `uv.lock`. Commit it; it is intentionally not gitignored.

### Phase B doc updates (same commit)

- **README**
  - Status banner: replace "a `uv init` scaffold (`main.py` prints a greeting)" with "an empty package skeleton (`src/medicaid_mcp/`, no tools yet)". Keep the rest of the banner; it comes off only at step 9.
  - "Local development": replace the `main.py` block with `uv sync`, `uv run pytest`, `uv run ruff check . && uv run ruff format .`, and `uv run mypy src`, and remove the `main.py` sentence.
  - Roadmap: mark item 1 done.
- **Impl plan:** update the "Current state" table (`pyproject.toml` and `main.py` rows), mark step 1 done, and update the Status line.
- **CLAUDE.md:** "Project state" should say the package skeleton exists and `main.py` is gone. Merge "Available now" and "Planned from step 1" under Commands, leaving `scripts/smoke.py` marked planned.

**Commit B:** `step 1: scaffold medicaid_mcp package, pin deps, commit uv.lock`.

---

## Verification

Phase A:
- Every step 0 table row holds Yes/No with a date and a source.
- The recorded `MCPServer` signature came from an actual import run, not from docs.

Phase B (step 1 done-when, plus tooling sanity):

```bash
uv sync                                          # succeeds
uv run python -c "import medicaid_mcp, medicaid_mcp.tools, medicaid_mcp.apps"
uv run pytest; test $? -eq 5                     # exit 5 = "no tests collected": the expected result
uv run ruff check . && uv run ruff format --check .
uv run mypy src                                  # strict, clean on docstring-only modules
uv build --wheel && unzip -l dist/*.whl          # medicaid_mcp/tools/*, apps/*, LICENSE present
grep -n "main.py" README.md CLAUDE.md            # no hits
git ls-files uv.lock                             # tracked
```

About the `pytest` check: with zero tests, pytest exits 5. That is "zero tests collected without error", which is exactly what step 1 asks for. Check for exit code 5 explicitly. Don't add a placeholder test to get exit 0. A collection error would be exit 2 or 4 and fails the check.

## Out of scope

Everything from step 2 onward: discovery, fixtures, any real module logic, `Dockerfile`, entry points, and the README "Configuration" or "Planned lenses" sections.
