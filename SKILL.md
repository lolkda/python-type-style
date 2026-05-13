---
name: typed-fastapi
description: >
  Type-first Python writing, refactoring, and review guidance for FastAPI + Pydantic v2 + SQLAlchemy 2
  codebases on Python 3.12+. Enforces keyword-only signatures, docstrings with Args/Returns business
  meaning, `BaseResponse[T]` unified envelope, PEP 695 typing syntax, and strict outward contract /
  persistence boundary separation.

  TRIGGER when: file imports `fastapi` / `pydantic` / `sqlalchemy` (especially `sqlalchemy.orm`,
  `sqlalchemy.ext.asyncio`); user writes or modifies a FastAPI route, router, dependency, or middleware;
  user defines a Pydantic v2 `BaseModel` (request, response, or internal); user writes a SQLAlchemy 2 ORM
  model (`Mapped`, `mapped_column`, `DeclarativeBase`), repository, or query; user refactors untyped or
  loosely-typed Python functions; user adds docstrings, type annotations, or keyword-only signatures;
  user reviews Python code for contract, boundary, or async safety; user asks about `BaseResponse[T]` /
  `PageData[T]` / unified response envelope / business error code layout; user asks about typing
  primitives (`Protocol`, `TypedDict`, `Self`, `@overload`, generics, `Annotated` aliases, `Literal`,
  `Final`, `ClassVar`, `TYPE_CHECKING`, `NewType`, `TypeGuard` / `TypeIs`, `Never` / `assert_never`,
  `ParamSpec`, `Concatenate`, PEP 695 `type` / `class Foo[T]` syntax); user asks about async safety,
  blocking I/O in `async def`, `AsyncSession` management, `selectinload` / `joinedload` strategy, or
  model layering / mirror-model anti-patterns.

  SKIP: file imports `flask` / `django` / `starlette`-only web framework code without FastAPI; legacy
  SQLAlchemy 1.x `Query`-style code where the task is not migration; Pydantic v1 codebase
  (`from pydantic.v1 import ...`) without v2 upgrade intent; pure data science / numpy / pandas /
  notebook code; general Python questions (algorithms, scripts, CLI tools) not tied to the FastAPI +
  Pydantic + SQLAlchemy stack; Python 2 or pre-3.12 codebases that cannot use PEP 695 syntax.
---

# Python Type Style

## Overview

Enforce a strict, type-first engineering style on FastAPI + Pydantic v2 + SQLAlchemy 2 codebases targeting
Python 3.12+. The high-frequency daily rules live in this file; deep treatment, examples, and runnable
counterparts live under `references/` and `examples/`. Apply these rules to new code and to any code being
refactored or reviewed.

## Core Rules

- Use `from ... import ...` style imports consistently. Do not use wildcard imports.
- Do not use `lambda`. Replace with named functions, built-in callables, or explicit logic.
- Use keyword-only arguments for all function and method parameters by default with `*`.
- Apply the same keyword-only rule to async functions and dependency callables unless a framework signature
  forbids it.
- Require docstrings on every function, async function, and class.
- Every function docstring must include `Args` and `Returns` sections with business meaning, not type labels.
- Every class docstring must describe business responsibility and key behavior semantics.
- Write explicit parameter and return types for all public methods.
- Avoid `Any`. Use it only at hard interoperability boundaries; convert to strict models immediately after
  entry.
- Public or external API-facing methods must return explicit contract models, not raw `dict`, `list`, or
  primitives.
- Route handlers and stable outward service facades must use `BaseModel` response contracts wrapped by
  `BaseResponse[T]`.
- Repository methods, ORM accessors, and persistence-layer helpers may return ORM entities or SQLAlchemy result
  objects when they do not cross an outward API boundary.
- Internal helpers, local transforms, and module-private utilities may use lightweight structures when no
  stable outward contract exists.

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
- Every route function has a docstring with `用途`, `Args`, `Returns`.

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
- No mirror-model chains: do not add a `BaseModel` layer that does not change contract, validation,
  serialization, permission, aggregation, or persistence semantics.

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

## Anti-patterns

- `from module import *` or module-wide references that hide symbol ownership in business layers.
- `lambda` in service logic, route handlers, or model builders.
- Positional arguments in business functions; missing `*` separator.
- Missing docstrings, or docstrings without `Args` / `Returns` business context.
- `Any` for stable contracts or outward response payloads.
- Raw `dict` / `list` / primitive returns from outward API boundaries.
- Shorthand route decorators (`@router.get(...)`) lacking full metadata.
- Implicit parameter sources or `user_id: int = Path(...)` default-style; use `Annotated[int, Path(...)]`.
- Raising raw `HTTPException` for business validation failures.
- `BaseModel` fields without `Field(...)`; non-Chinese or placeholder `description`.
- Per-endpoint `XxxResponse` model duplicating `code` / `message` / `data` — use `BaseResponse[T]`.
- Mirror-model chains (`UserOrmSchema` → `UserResponse` with identical fields).
- Class-level constants on Pydantic v2 models without `ClassVar[...]`.
- Legacy `session.query(...)` in new SQLAlchemy 2 code; ORM columns without `Mapped[...]`.
- Sharing one `Session` / `AsyncSession` across unrelated request or task scopes.
- Sync ORM access inside async request flows; blocking I/O inside `async def`.
- Importing `typing.List` / `Dict` / `Tuple` / `Sequence` / `Mapping` — use built-in or `collections.abc`.
- Enabling `from __future__ import annotations` project-wide on a Pydantic / FastAPI codebase.
- Substituting `TypedDict` for `BaseModel` at outward API boundaries.
- `@property` on a `BaseModel` when the value must appear in `model_dump()` / OpenAPI — use `@computed_field` paired with `@property`.
- `@cached_property` on a mutable ORM entity or mutable Pydantic model without an invalidation strategy.
- `@xxx.setter` on Pydantic / ORM domain models for business validation — use validators or named methods.

## References Index

| Topic | Reference | Runnable example |
|---|---|---|
| Typing primitives (`Protocol`, `TypedDict`, `Self`, `@overload`, generics, `Annotated` aliases, `Literal`, `Final` / `ClassVar`, `TYPE_CHECKING`, `cast`, `NewType`, `TypeGuard` / `TypeIs`, `Never` / `assert_never`, `ParamSpec`, `@final` / `@override`, PEP 695 `type`) | [typing-usage.md](references/typing-usage.md) | [repository.py](examples/repository.py), [protocol.py](examples/protocol.py), [overload.py](examples/overload.py), [paramspec.py](examples/paramspec.py) |
| Unified response envelope `BaseResponse[T]` + `PageData[T]` + exception handlers | [response-contract.md](references/response-contract.md) | [base_response.py](examples/base_response.py), [route.py](examples/route.py) |
| FastAPI routes, parameter sources, error handling, deviations for streaming | [fastapi-style.md](references/fastapi-style.md) | [route.py](examples/route.py), [base_response.py](examples/base_response.py) |
| SQLAlchemy 2 ORM, async repository, relationship loading | [sqlalchemy2-style.md](references/sqlalchemy2-style.md) | [repository.py](examples/repository.py) |
| Pydantic v2 fields, validators, `ClassVar`, model layering | [pydantic-v2-style.md](references/pydantic-v2-style.md) | [base_response.py](examples/base_response.py) |
| `@property` / `@cached_property` / `@computed_field` / `@hybrid_property` usage discipline + setter ban | [property-usage.md](references/property-usage.md) | [property_usage.py](examples/property_usage.py) |
| Async safety, blocking I/O, sync-in-async anti-patterns | [async-concurrency.md](references/async-concurrency.md) | — |
| Outward vs persistence boundary, exceptions and priorities, deviation rules | [architecture-boundary.md](references/architecture-boundary.md) | — |

Historical versions of this skill are archived under `archive/`.
