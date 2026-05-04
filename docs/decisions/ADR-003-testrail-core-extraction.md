---
number: 3
title: Extract testrail-core as a separately importable Python package
date: 2026-05-04
status: proposed
route: B
plan: plan-004-testrail-mcp-v2.md
---

# ADR-003: Extract `testrail-core` as a Separately Importable Python Package

**Deciders**: Eden Fridman (owner), konstruct (planning)

## Context

The TestRail MCP server today ships as a single Python package. The MCP
protocol surface and the TestRail integration logic (HTTP client, retry,
rate-limit, caches, schemas, exceptions, attachment handling) live in the
same source tree under `src/`. Anyone who wants to talk to TestRail from
Python in this codebase's idiom — same auth, same retry behavior, same field
caches, same Pydantic schemas — must either:

1. Spawn the MCP server as a subprocess and speak the MCP protocol to it, or
2. Vendor the integration code into their own project, taking on a
   maintenance fork.

Both options impose costs that are unrelated to the integration itself. The
MCP subprocess pays JSON-RPC overhead and forces the consumer to translate
their domain calls into tool invocations. Vendoring forks the very logic this
project exists to centralize. As v2.0.0 is shipping new server-side
capabilities (read-only mode, allowlist, aliases, preload), it is the right
moment to also offer the integration core as a first-class importable
library so consumers can pick the boundary that fits them.

The relevant forces:

- **Reuse**: the HTTP client, caches, rate limiter, schemas, and exceptions
  are protocol-agnostic. They have no dependency on the MCP runtime. Keeping
  them coupled to it is incidental, not essential.
- **Surface stability**: a published library has a public API contract that
  the MCP server is the first consumer of. That discipline is good for the
  code; it forces clean module boundaries.
- **Refactor blast radius**: the current dispatcher, tool definitions, and
  handlers import freely from any layer. Extraction will surface every
  illegal back-reference at once.
- **Version coordination**: two packages versioned and released together
  cost more than one.
- **Distribution**: PyPI publishing and OIDC trusted-publishing work cleanly
  with one or many packages; the cost is mostly the workflow, not the count.

## Decision

Split the repository into a **uv workspace with two packages**:

- `packages/testrail-core/` — protocol-agnostic integration library.
  Contains the HTTP client (`base_client.py`), per-resource clients
  (`cases.py`, `runs.py`, `plans.py`, …), Pydantic schemas, exceptions,
  rate limiter, retry logic, attachment handling, and the four caches
  (field, status, priority, case-type).
- `packages/testrail-mcp/` — thin MCP wrapper. Contains the stdio entry
  point, tool definitions, dispatcher, server-side gates (read-only,
  allowlist, aliases, preload), and the per-resource handlers that adapt
  MCP tool calls to `testrail-core` calls.

Both packages version together and release together at v2.0.0. The MCP
package depends on `testrail-core==2.0.0`. The public API of `testrail-core`
is treated as semver-stable from v2.0.0 onward — any breaking change to the
core requires a major bump of both packages.

The migration is incremental, one resource per PR, with `cases` shipping
first as a canary to surface shared-base coupling before nine more resources
follow the same pattern.

## Alternatives Considered

### Alternative 1: Keep a single package, expose internals as importable

- **Pros**: zero packaging churn; one version, one release, one changelog;
  no workspace to manage.
- **Cons**: the public-vs-private boundary is implicit (a `__all__` list at
  best); consumers who only want the integration logic still pull in MCP
  dependencies (`mcp` SDK, dispatcher modules) they will never use; refactors
  to MCP internals can silently break library consumers because nothing
  enforces the boundary.
- **Why not**: the boundary discipline only shows up when the package
  boundary is real. Without enforcement, every refactor risks breaking the
  implicit "this is the library" subset, and consumers learn by breakage.

### Alternative 2: Two separate repositories (`testrail-core` and `testrail-mcp`)

- **Pros**: strongest possible separation; independent release cadences;
  contributors can work on one without the other.
- **Cons**: changes that span both (e.g. adding a new TestRail resource)
  require two PRs in two repos; CI cannot atomically test the integration of
  the two; cross-cutting refactors are painful; the workspace's "atomic
  commit across both" property is lost.
- **Why not**: this project's velocity comes from being able to refactor
  across the protocol/integration boundary in a single change. Two repos
  multiplies coordination cost without paying for itself unless the
  packages have genuinely different audiences and release cadences — which
  v2.0.0 does not.

### Alternative 3: In-process import only, no PyPI release for `testrail-core`

- **Pros**: zero publishing overhead; consumers who happen to depend on the
  repo as a git submodule can already import it.
- **Cons**: external consumers cannot `pip install testrail-core` from PyPI;
  every consumer must pin to a git SHA; transitive consumers (a library that
  uses `testrail-core`) cannot publish to PyPI without inheriting the git
  dependency, which most index-hosted repositories reject.
- **Why not**: the goal is to make the library usable by external Python
  consumers. PyPI is the standard distribution. Skipping it negates most of
  the reuse benefit.

## Consequences

### Positive

- External Python consumers can `pip install testrail-core` and use the HTTP
  client, retry, rate-limit, caches, and schemas without ever loading the
  MCP runtime.
- The MCP package becomes a thin wrapper — small enough to read in one
  sitting — making the protocol surface easier to audit and evolve.
- A real package boundary forces the integration code to stop reaching into
  MCP internals (e.g. tool registries, dispatcher state). The first PR that
  tries to do so will fail import — early signal.
- Server-side hardening from Phases 1–4 stays cleanly in `testrail-mcp`,
  where it belongs. Library consumers do not pay for or reason about
  read-only mode, allowlists, or alias resolution.
- The workspace layout makes each per-resource extraction a small, reviewable
  PR rather than a single 30-file mega-diff.

### Negative

- Every internal import path changes from `src.client.api.cases` to
  `testrail_core.api.cases`. Phase 5 sub-PRs will touch hundreds of import
  statements. Reviewers must trust mechanical correctness.
- Two packages mean two `pyproject.toml` files, two changelogs, and two
  PyPI projects to register and maintain.
- Versions must move together until a clear divergence reason exists.
  Marketing this as "semver-stable from v2.0.0" means breaking changes cost
  a major bump on both packages, even if only one is actually breaking.
- The first consumer of `testrail-core` (the MCP package itself) is a weak
  test of API ergonomics — if the MCP package is the only caller, the public
  API will tend to overfit to its needs. Mitigated by writing at least one
  example consumer in the README.
- Workspace tooling (`uv sync`, editable installs) has more failure modes
  than a flat package. Phase 5.0 must explicitly verify local-path
  installs still work for existing consumers.

### Risks

- **Risk**: shared-state singletons (e.g. a module-level cache instance)
  that work in a flat package break when imported from two packages.
  **Mitigation**: the `cases` canary PR is explicitly the place to surface
  this. If the canary blows up, ADR-003 gets a follow-up amendment before
  the rest of the resources move.
- **Risk**: consumers who installed via `uvx --from /local/path` against the
  pre-split layout get a confusing error after upgrade.
  **Mitigation**: README install matrix at Phase 6 documents the new path
  (`packages/testrail-mcp`); release notes call it out as a breaking change
  to invocation only — runtime behavior unchanged.
- **Risk**: the public API of `testrail-core` calcifies around the MCP
  server's needs and is awkward for direct consumers.
  **Mitigation**: ship at least one non-MCP usage example in the
  `testrail-core` README at v2.0.0. Treat the first external bug report
  about API ergonomics as a real signal, not noise.
- **Risk**: workspace versioning drift — `testrail-mcp` accidentally
  depends on `testrail-core>=2.0.0` instead of `==2.0.0`, allowing a
  mismatched install.
  **Mitigation**: pin exactly until there's a documented reason to widen,
  and lockfile-check in CI.
