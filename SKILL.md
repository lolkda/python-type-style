---
name: python-typed-development-standards
description: Mandatory for every Python task, including application code, scripts, CLI tools, tests, examples, one-off utilities, reviews, debugging, explanations, and design. Always use this skill when writing, refactoring, reviewing, debugging, fixing, explaining, or designing Python code. Enforce Python 3.12+ strict typing, keyword-only signatures, Chinese Args/Returns docstrings, Pydantic BaseModel-first request/config/domain contracts, no serialized contract state, one final boundary model dump, object API style over build_xxx helpers, no public build/build_/Builder names in request/config APIs, mandatory function extraction audit with one-use thin helpers inlined, FastAPI/Pydantic v2/SQLAlchemy 2 rules, and async safety.
---

# Python Type Style

## Overview

Enforce a strict, type-first engineering style on FastAPI + Pydantic v2 + SQLAlchemy 2 codebases targeting
Python 3.12+. Apply these rules when writing new Python and when refactoring or reviewing existing code.

This skill is gated by priority. Audit every definition in order: **Priority 0 — should it exist?** →
**Priority 1 — is its contract shaped right?** → **Priority 2 — is its surface clean?** A later priority never
offsets an earlier failure. The domain Quick Rules below (Class vs Function, Typing, Response, FastAPI,
SQLAlchemy 2, Pydantic v2, Property, Async) are orthogonal to the priority gate: they apply whenever that
technology appears, on top of P0/P1/P2. For edge cases and rationale, follow each `Full treatment:` link to
`references/`, and see `examples/` for runnable counterparts.

Apply this skill to every Python task and every Python output: application code, scripts, CLI tools, tests,
examples, one-off utilities, reviews, debugging, explanations, and design.

Apply it even when the user does not name the skill.

When rules conflict, keep the stricter rule unless the user explicitly requests a documented compatibility
deviation.

## Priority 0 — Existence Before Quality

Existence is the first gate. Decide whether a function or model should exist *before* you give it a docstring, a
type, or a Pydantic field. A perfectly documented, fully typed, keyword-only definition that should not exist is
still a violation — decoration never offsets a Priority 0 failure.

Write the flow inline first. Start every script, handler, or workflow as one straight-line body; do not
pre-split it into named steps.

Then promote a span to its own function only by one of two independent warrants:

- **Single-use — the inlining test.** Paste the span back into its sole caller. If the caller reads the same or
  *easier*, the span is only "what happens next" (a call, a wait, a log, a construct, a serialize, a forward) —
  keep it inline. Promote it only when inlining makes the caller *harder* to follow, i.e. the span owns a real
  decision, a validation, an invariant, a retry/error boundary, or a protocol/serialization transform.
- **Reuse — real shared behavior.** A span used at two or more call sites earns a function only when its body
  carries policy, validation, error/retry handling, protocol adaptation, a non-trivial transform, or a project
  invariant. Call count alone never earns it: a body that still only generates an ID/token/timestamp/default,
  sleeps, logs, makes one external call, constructs, forwards, or serializes stays inline even when reused.

An external-boundary adapter is a warrant only when it *transforms* (maps a domain model to or from the external
shape) or *absorbs* (handles the boundary's errors, retries, or policy). A function that only forwards one
SDK/client call, renames its arguments, or wraps a single `run_sync` / `send` / `create` is not an adapter —
inline it.

A `count` / `size` / `batch` / `repeat` parameter earns no function. Judge the behavior, not the name: inline a
span into its sole caller when **all** hold — it has one call site, the looped count is a literal or statically
fixed constant at the call site (a literal `1`, a module constant set to `1`, or a default constant not sourced
from user/config/runtime input), the loop body only calls / waits / logs / constructs / appends / prints /
serializes / forwards, and any guard it carries only rejects an out-of-range value of a parameter the span itself
introduced (`if size < 1: raise`). That guard is not the validation warrant. The loop earns its own function only
with real batch policy: chunking, rate limiting, concurrency, retry, error aggregation, or two-or-more call
sites. `send_batch_once` / `run_once` / `process_batch` are instances of this shape, not the test — a rename
rescues nothing.

Models earn existence the same way, by what they *constrain or guarantee* — validation, an invariant, an outward
contract, a serialization shape — not by what they *hold*. Apply the unwrap test: drop the layer and use the
inner type directly; if no constraint or guarantee is lost, the layer must not exist. A model that only wraps a
local list/batch/grouping, mirrors another model's fields, or re-wraps a value already shaped by its callee
(`AModel(**b.model_dump())`) fails this test. Input code earns no grandfather right: a rewrite inlines such a
wrapper instead of preserving it, and renaming it (`Batch` → `Request`) or hosting its one linear loop in a
method does not save it.

Judge by what a definition *decides, protects, constrains, or guarantees* — never by its name, its shape, or
whether it can be given a clean docstring. Renaming `build_*` to `make_*`, splitting a 3-deep chain into 2, or
adding a filler field to a wrapper does not change the verdict.

Audit order, per definition: existence (this gate) → contract shape (Priority 1) → surface (Priority 2). A
definition that fails this gate is inlined or deleted; do not document, type, or model it to make it look
compliant.

Full treatment: [references/class-vs-function.md](references/class-vs-function.md).

## Priority 1 — Contract Shape

A definition that survives Priority 0 must carry its state in the right contract shape before you touch its
surface.

Stable request/config/domain state uses Pydantic `BaseModel` by default. Do not pass raw `dict`, `Mapping`,
dict aliases, or `dict[str, object]` between project functions as stable contracts. `dataclass`, `TypedDict`,
and `Mapping` are not substitutes; reserve `dataclass` for pure internal algorithm state with no aliases,
validation, serialization, derived payloads, or boundary semantics. Raw `dict` is allowed only as an inline
literal consumed immediately by an external boundary, or as a tiny local value that is never returned, stored,
passed onward, or reused across branches.

Avoid `Any` for stable contracts and outward payloads; use it only at hard interop boundaries and convert
immediately. Public or external API-facing methods return explicit contract models, not raw `dict`, `list`, or
primitives.

Store semantic models, not serialized state. Fields such as `*_json`, `*_dict`, `*_payload`, `*_body`,
`*_headers`, `metadata_user_id`, or `external_kwargs` are boundary artifacts unless they are literal source
values from the external domain. `create()` / `from_*()` factories normalize inputs, generate IDs, and choose
defaults; they do not assemble derived dictionaries, JSON, headers, or external-call kwargs. `create()` and
value-named factories (`from_dict` / `from_orm` / `from_cli_metadata`, naming an in-hand value) perform no I/O.
Only a source-named ingress factory (`from_os` / `from_env` / `from_file`, naming an external source) reads, and
only the one source its name declares — never a second source. The name is a contract the factory must honor, not
a label to evade.

Default provenance must be visible. When a stable request/config/domain default comes from a file, env, network,
DB, or SDK, the high-level entrypoint resolves it and passes it in. A factory must not backfill external state in
an optional parameter's `None` fallback: `device_id: str | None = None` then `device_id or read_device_id()`
hides the read from every caller of the signature. Explicit ingress factories are selected by the high-level
caller; `create()` or value-named `from_*` must not call them as a fallback (`device_id or cls.from_file()` is
forbidden). The only allowed `None` fallback is pure in-process generation — dependency-free UUID / token /
timestamp / constant default — excluding files, env, caches, SDK / plugin / browser state, process-global mutable
config, or any value derived from a prior external read.

Serialize only at the final external boundary. Dump one complete boundary model once; do not stitch several
child `model_dump()` / `to_*_dict()` results into a parent dictionary. Derived payload methods return Pydantic
models; only an explicit final-boundary serializer named `to_*_dict()` / `as_*_dict()` may return a raw dict,
and it is called inline at the actual external call — never assigned to `body_args` / `external_kwargs` and
indexed.

Multiple `build_*`, `make_*`, `compose_*`, or similar helpers that share one `context`, `request`, `config`, or
`settings` object are a fragmentation smell: collapse them into one cohesive object API whose caller-goal
methods (`Request.create().model_settings()`) return Pydantic models. Cosmetic renames do not satisfy this rule.

Public request/config/domain APIs do not use `build`, `build_`, or `Builder` in function, method, class, or
public attribute names. Internal local names, fixtures, and third-party names are not the target.

Full treatment: [references/pydantic-v2-style.md](references/pydantic-v2-style.md),
[references/object-api-style.md](references/object-api-style.md),
[references/architecture-boundary.md](references/architecture-boundary.md).

## Priority 2 — Surface

After Priority 0 and Priority 1 pass, every surviving class and every surviving function-like definition has a
Chinese docstring. Function-like definitions include functions, async functions, methods, properties, overload
stubs, protocol stubs, decorator wrappers, and private helpers that are already necessary. Their docstrings
include `Args` and `Returns` with business meaning, not type labels. Class docstrings describe business
responsibility and key behavior semantics.

Do not create or preserve a definition merely to document it. The list above prevents skipping obscure surviving
definitions; it is not permission to create those helpers.

Every surviving definition also obeys these surface rules:

- Keyword-only signatures by default with a leading `*`, including async functions and dependency callables
  unless a framework signature forbids it.
- Explicit parameter and return types for all public methods.
- No `lambda`; replace with named functions, built-in callables, or explicit logic.
- `from ... import ...` style imports; no wildcard imports.
- Outward `BaseModel` fields use `Field(description="中文业务说明")`.

## Never Output These Shapes

This is a non-exhaustive rejection index. Each item points back to Priority 0 or Priority 1; the real verdict
comes from what the definition decides, protects, constrains, or guarantees, not from matching names or shapes.

- Thin helper that only calls, waits, logs, constructs, serializes, or forwards. → P0
- Forwarding chain where each layer only calls the next layer. → P0
- Pydantic model that only wraps a local list/batch/grouping, mirrors another model's fields, or pass-through re-wraps a callee's already-shaped value. → P0
- Raw `dict` / `Mapping` / dict alias passed between project functions as request/config/domain state. → P1
- Stable serialized state such as `*_json`, `*_dict`, `*_payload`, `metadata_user_id`, or `external_kwargs`. → P1
- Final serializer that stitches child dumps instead of dumping one boundary model once. → P1
- Public request/config/domain `build_*` / `Builder` API or cosmetic rename preserving the same fragmentation. → P1
- `dataclass` / `TypedDict` / `Mapping` used as a stable request/config/domain contract. → P1
- Count/batch helper kept alive only by a `count` / `size` parameter or a `if size < 1: raise` guard, while its sole call site passes a literal or statically fixed constant and the loop body is trivial. → P0
- Factory performing hidden file/env/network/DB/subprocess/SDK I/O, an optional parameter whose `None` fallback fetches external state (`x or load_x()`), or a persisted-value read named `new_*` / `generate_*`. → P1

## Class vs Function Quick Rules

- Default to module-level functions. Promote to a class only for long-lived state, lifecycle, identity, shared
  dataset behavior, invariants, polymorphism, runtime context, concurrency ownership, or a sequenced protocol.
- Declarative-shape classes (Pydantic `BaseModel`, `pydantic_settings.BaseSettings`, SQLAlchemy ORM,
  `dataclass`) always stay classes — class syntax for schema, not behavior. This does not make `dataclass` valid
  for stable request/config/domain contracts; those use Pydantic `BaseModel`.
- Forbidden: `class XxxUtils:` / `class XxxHelpers:` whose body is only `@staticmethod` / `@classmethod` with no
  shared state — Python modules are namespaces; flatten to module-level functions.

Full treatment: [references/class-vs-function.md](references/class-vs-function.md).

## Typing Quick Rules

- Avoid `Any` except at hard interop boundaries.
- Prefer built-in `list` / `dict` / `tuple` / `set` over `typing.List` / `Dict` / `Tuple` / `Set`.
- Import `Sequence` / `Mapping` / `Iterable` / `Callable` / `Awaitable` from `collections.abc`.
- Prefer `X | Y` and `X | None` over `Union[X, Y]` / `Optional[X]`.
- Prefer PEP 695 syntax: `class Foo[T]:`, `def func[T](...)`, `type Alias = ...`.
- Extract repeated `Annotated[...]` chains to module-level aliases (`type UserId = Annotated[int, Path(...)]`).
- Do **not** enable `from __future__ import annotations` project-wide — Pydantic v2 + FastAPI rely on runtime
  type introspection.

Full treatment: [references/typing-usage.md](references/typing-usage.md).

## Unified Response Quick Rules

- One `BaseResponse[T]` envelope per project, used as the `response_model` and return annotation of every JSON
  route.
- Business data models stay pure — no `code` / `message` / `data` fields on business schemas.
- Success: `BaseResponse.ok(data)`. Failure: raise a typed business exception; a global handler emits
  `BaseResponse.fail(code=..., message=...)`.
- Business `code` is decoupled from HTTP status. Document the project error code layout (module × sub-code) in
  one source of truth.

Full treatment: [references/response-contract.md](references/response-contract.md).

## FastAPI Quick Rules

- Declare routes with `@router.api_route(path=..., methods=..., response_model=..., tags=..., summary=...)`.
  Do not use shorthand decorators.
- `response_model` is always `BaseResponse[T]` or `BaseResponse[PageData[T]]` for JSON endpoints.
- Every parameter source is explicit via `Annotated[T, Path|Query|Body|Header|Cookie|Depends|Security(...)]`.
  Do not pass source objects as default values.
- Reserve `HTTPException` for protocol-level failures. Define typed business exceptions and register global
  handlers that emit through `BaseResponse[None]`.
- Every route function has a Chinese docstring with `用途`, `Args`, `Returns`.

Full treatment: [references/fastapi-style.md](references/fastapi-style.md).

## SQLAlchemy 2 Quick Rules

- ORM models use `DeclarativeBase` + `Mapped[...]` + `mapped_column(...)`. Every mapped attribute is typed.
- Queries use `select(...)` + `session.scalar(...)` / `session.scalars(...)`. No legacy `session.query(...)`.
- Repository / DAO methods are keyword-only with explicit return types.
- `AsyncSession` with async engine and async driver in async paths. Sessions are context-managed.
- Declare relationship loading strategy explicitly (`lazy="raise"` default; opt in via `selectinload` /
  `joinedload` at the query site).

Full treatment: [references/sqlalchemy2-style.md](references/sqlalchemy2-style.md).

## Pydantic v2 Quick Rules

- Every outward `BaseModel` field has `Field(description="中文业务说明")`. Optional fields explicitly set
  `default` or `default_factory`.
- Outward business models do not include `code` / `message` / `data` — those belong to `BaseResponse[T]`.
- Non-field class attributes use `ClassVar[...]` to opt out of Pydantic field collection.
- Use `@computed_field` paired with `@property` when a derived value must appear in `model_dump()` or OpenAPI.
- Model existence — mirror-model chains, local-list/batch wrappers, pass-through re-wrap, and config-first
  layering (a difference expressible via `ConfigDict` / `Field(...)` / a validator) — is decided at Priority 0.

Full treatment: [references/pydantic-v2-style.md](references/pydantic-v2-style.md).

## Property Quick Rules

- `@property` only for cheap, side-effect-free, read-only derivations over instance state; no DB
  queries, network calls, or business exceptions in the body.
- Pydantic v2: stack `@computed_field` over `@property` when the derived value must appear in
  `model_dump()` or OpenAPI; use plain `@property` for internal-only computations.
- SQLAlchemy 2: use `@hybrid_property` when the derived value must appear in `select(...).where(...)`;
  otherwise use `@property`, and never trigger a `lazy="raise"` relationship inside the body.
- `@cached_property` is legal only when the host object is treated as immutable for the cached
  value's lifetime; on mutable entities it requires a documented invalidation strategy.
- Setters (`@xxx.setter`) on Pydantic / ORM domain models are forbidden; state changes go through
  named methods or validators.

Full treatment: [references/property-usage.md](references/property-usage.md).

## Async Quick Rules

- No blocking I/O inside `async def`. Use `httpx.AsyncClient`, `AsyncSession`, async drivers.
- Async boundaries propagate through service layers — do not call sync repository methods from async services.
- Avoid `run_in_executor` as a default escape hatch; diagnose the root cause first.

Full treatment: [references/async-concurrency.md](references/async-concurrency.md).

## References Index

| Topic | Reference | Runnable example |
|---|---|---|
| Existence gate, class vs function decision, linear-flow / thin-helper anti-patterns | [class-vs-function.md](references/class-vs-function.md) | [linear_flow.py](examples/linear_flow.py) |
| Typing defaults, project exceptions, and forbidden legacy forms | [typing-usage.md](references/typing-usage.md) | [repository.py](examples/repository.py), [protocol.py](examples/protocol.py), [overload.py](examples/overload.py), [paramspec.py](examples/paramspec.py) |
| Unified response envelope `BaseResponse[T]` + `PageData[T]` + exception handlers | [response-contract.md](references/response-contract.md) | [base_response.py](examples/base_response.py), [route.py](examples/route.py) |
| FastAPI routes, parameter sources, error handling, deviations for streaming | [fastapi-style.md](references/fastapi-style.md) | [route.py](examples/route.py), [base_response.py](examples/base_response.py) |
| SQLAlchemy 2 ORM, async repository, relationship loading | [sqlalchemy2-style.md](references/sqlalchemy2-style.md) | [repository.py](examples/repository.py) |
| Pydantic v2 fields, validators, `ClassVar`, model layering | [pydantic-v2-style.md](references/pydantic-v2-style.md) | [base_response.py](examples/base_response.py) |
| `@property` / `@cached_property` / `@computed_field` / `@hybrid_property` usage discipline + setter ban | [property-usage.md](references/property-usage.md) | [property_usage.py](examples/property_usage.py) |
| Object API style for replacing scattered `build_xxx(context=...)` helpers with cohesive request/config objects | [object-api-style.md](references/object-api-style.md) | [object_api_style.py](examples/object_api_style.py) |
| Async safety, blocking I/O, sync-in-async anti-patterns | [async-concurrency.md](references/async-concurrency.md) | — |
| Outward vs persistence boundary, exceptions and priorities, deviation rules | [architecture-boundary.md](references/architecture-boundary.md) | — |
