---
name: python-typed-development-standards
description: Mandatory for every Python task, including application code, scripts, CLI tools, tests, examples, one-off utilities, reviews, debugging, explanations, and design. Always use this skill when writing, refactoring, reviewing, debugging, fixing, explaining, or designing Python code. Enforce Python 3.12+ strict typing, keyword-only signatures, Chinese Args/Returns docstrings, Pydantic BaseModel-first request/config/domain contracts, object API style over build_xxx helpers, no public build/build_/Builder names in request/config APIs, FastAPI/Pydantic v2/SQLAlchemy 2 rules, and async safety.
---

# Python Type Style

## Overview

Enforce a strict, type-first engineering style on FastAPI + Pydantic v2 + SQLAlchemy 2 codebases targeting
Python 3.12+. Apply these rules when writing new Python and when refactoring or reviewing existing code. Each
section gives enforceable rules; for edge cases and rationale, follow the `Full treatment:` link to
`references/`, and see `examples/` for runnable counterparts.

## Mandatory Scope

Apply this skill to every Python output, not only production application code. Scripts, CLI tools, tests,
examples, notebooks converted to Python, one-off utilities, code review comments, debugging patches,
architecture sketches, and explanatory Python snippets all obey the same output gate.

If a user asks for Python code but does not mention this skill, still apply it. If a user asks to ignore part of
this style, keep the stricter rule unless they explicitly request a deliberate deviation for compatibility and
the deviation is documented next to the code.

## Mandatory Python Output Gate

Before producing any Python code or Python code review result, audit the output against this gate.
If any check fails, do not present the code. Rewrite it until all checks pass.

- Every class has a Chinese docstring describing business responsibility and key behavior semantics.
- Every function, async function, method, property, overload stub, protocol stub, decorator wrapper, and private
  helper has a Chinese docstring.
- Every function-like docstring contains `Args` and `Returns`.
- Public request/config object API names do not contain `build`, `build_`, or `Builder`.
- Scattered `build_xxx(context=...)` helpers are not used when the outputs belong to one request/config/domain
  object.
- Request/config/domain object APIs prefer `Request.create().model_settings()` or equivalent cohesive object
  methods, and those cohesive methods return Pydantic models rather than raw dictionaries.
- Function and method parameters are keyword-only by default.
- Stable request/config/domain contracts use Pydantic `BaseModel` by default.
- Do not pass raw dictionaries, `Mapping`, or dict type aliases between project functions as stable contracts.
- Raw dictionaries are allowed only as inline literals immediately consumed by a third-party, framework, or
  external I/O call boundary, or as tiny single-function local values that are not returned, stored, passed
  onward, or reused across branches.
- `create()` / `from_*()` factories for request/config/domain objects do not assemble derived dictionaries,
  JSON strings, external-call kwargs, headers, or body payloads.
- Request/config/domain methods return Pydantic models for derived payloads; only explicit final-boundary
  methods named `to_*_dict()` or `as_*_dict()` may return raw dictionaries.
- Do not assign `to_*_dict()` / `as_*_dict()` results to variables such as `body_args`, `external_kwargs`, or
  `payload_dict` for later indexing. Serialize inline at the actual external call boundary.
- Do not build `extra_body`, `headers`, command args, file payloads, database parameters, or framework kwargs by
  extracting pieces from an already serialized dict. Model the final external-boundary parameter shape and
  serialize it once at the call boundary.

Do not output Python code that violates this gate.

## Mandatory Contract Model Rule

For stable request/config/domain payloads, prefer Pydantic `BaseModel` by default.

Use raw `dict` only at final serialization boundaries. This includes any third-party, framework, or external I/O
call boundary, for example SDK, HTTP, CLI, database, message queue, file, subprocess, browser automation, or plugin
calls. These examples are not exhaustive.

- Header/metadata literals passed directly into the call that consumes them.
- JSON/body/argument literals passed directly into the sending or execution call.
- Tiny single-function local literals that are not returned, stored, passed onward, or reused across branches.

Do not pass raw dictionaries, `Mapping`, or dict type aliases between project functions as stable contracts.
Do not use `dict[str, object]` for request/config/domain state.
If a dictionary crosses more than one function boundary, convert it to a Pydantic model.
If a dictionary is assigned to a variable and then returned, stored on an object, passed to a project helper, or
shared across branches, it is no longer a local literal; model it with Pydantic.

Factory methods such as `create()` and `from_*()` may normalize constructor inputs, generate IDs, and choose
defaults, but they must not assemble derived dictionaries, serialized JSON, external-call kwargs, headers,
request bodies, command arguments, file payloads, or database parameters. Put each derived contract in its own
Pydantic `BaseModel`.

Request/config/domain methods such as `headers()`, `payload()`, `body()`, `client_metadata()`, and
`model_settings()` return Pydantic models by default. Raw dictionary returns are legal only in final boundary
methods whose names make serialization explicit, such as `as_external_call_dict()`, `to_headers_dict()`, or
`as_json_body_dict()`. Call those serializers adjacent to the actual external invocation; do not pass those
dictionaries to other project functions.

The serializer call must be inline or immediately inside the external call expression:

```python
external_client.send(**request.external_call_params().as_external_call_dict())
```

Forbidden:

```python
body_args = body.as_external_call_dict()
responses.create(
    model=body_args["model"],
    extra_body={"client_metadata": body_args["client_metadata"]},
)
```

Do not index into serialized dictionaries to rebuild external-call arguments. If the boundary needs nested
payloads such as `extra_body`, `extra_headers`, command arguments, file metadata, database parameters, or similar
kwargs, define those nested values as Pydantic models on one final boundary parameter model and dump that final
model once at the call boundary.

Low-level external I/O or framework helper functions do not read request credentials such as `API_KEY` from module globals.
Independent scripts may define a top-level `API_KEY`, but the high-level entrypoint must pass it explicitly into
the request/config object or helper call.

## Mandatory Object API Rewrite

When the input code contains two or more public functions named `build_*`, or several functions pass the same
`context`, `request`, `config`, `metadata`, or `settings` value, rewrite the design into one cohesive object.
Read [references/object-api-style.md](references/object-api-style.md) and follow
[examples/object_api_style.py](examples/object_api_style.py) before writing code.

Required shape:

```python
request = DomainRequest.create()
settings = request.model_settings()
client.responses.create(**settings.as_external_call_dict())
```

Forbidden public shapes:

```python
build_context(...)
build_headers(...)
build_body(...)
build_settings(...)
RequestBuilder
```

## Core Rules

- Use `from ... import ...` style imports consistently. Do not use wildcard imports.
- Do not use `lambda`. Replace with named functions, built-in callables, or explicit logic.
- Use keyword-only arguments for all function and method parameters by default with `*`.
- Apply the same keyword-only rule to async functions and dependency callables unless a framework signature
  forbids it.
- Require docstrings on every function, async function, and class.
- Every function docstring must be written in Chinese and include `Args` and `Returns` sections with business
  meaning, not type labels.
- This docstring rule applies to all function-like definitions, including `__init__`, `@property`,
  `@cached_property`, `@computed_field`, `@hybrid_property`, `@overload` stubs, `Protocol` method stubs,
  decorator inner wrappers, and private helpers.
- Every class docstring must be written in Chinese and describe business responsibility and key behavior semantics.
- Write explicit parameter and return types for all public methods.
- Avoid `Any`. Use it only at hard interoperability boundaries; convert to strict models immediately after
  entry.
- Public or external API-facing methods must return explicit contract models, not raw `dict`, `list`, or
  primitives.
- Stable request/config/domain payloads use Pydantic `BaseModel` by default; dataclasses, type aliases,
  `TypedDict`, and `Mapping` are not substitutes when the value crosses project function boundaries.
- Request/config/domain classes use Pydantic `BaseModel` by default. Use `dataclass` only for pure internal
  algorithm state with no aliases, validation, serialization, derived payloads, or stable boundary semantics.
- Route handlers and stable outward service facades must use `BaseModel` response contracts wrapped by
  `BaseResponse[T]`.
- Repository methods, ORM accessors, and persistence-layer helpers may return ORM entities or SQLAlchemy result
  objects when they do not cross an outward API boundary.
- Internal helpers, local transforms, and module-private utilities may use lightweight structures only inside one
  function body. Once a value is returned, stored, passed to another project function, or shared across modules,
  it is a contract and must follow the stricter model rules.

## Class vs Function Quick Rules

- Default to module-level functions. Promote to a class only when at least one of:
  1. **Long-lived state** carried across calls (cache / session / pool / cookies / in-memory index / caches with their own invalidation policy).
  2. **Lifecycle** the caller must manage (`open → use → close`, `__aenter__/__aexit__`).
  3. **Identity** — the object represents a system entity (`User`, `Order`, `Task`, `Session`, `Connection`).
  4. **Behavior aggregated** around one shared internal dataset (`Cart.add_item` / `Cart.total_price`).
  5. **Invariants** that must stay valid across mutations (`BankAccount` balance ≥ 0, state machine).
  6. **Polymorphism** — multiple swappable implementations behind one interface (`StorageBackend`, `PaymentProvider`).
  7. **Runtime context** binding several values for one execution scope (`RequestContext`, `CrawlerContext`).
  8. **Concurrency ownership** — the object owns synchronization primitives or coordination state (lock, queue, semaphore, rate limiter, dedup window, retry controller).
  9. **Protocol / sequenced operations** — multiple operations must occur in a strict order and the class enforces sequence correctness as an internal state machine (`connect → authenticate → send`).
- Declarative-shape `class` (Pydantic `BaseModel`, `pydantic_settings.BaseSettings`, SQLAlchemy ORM,
  `dataclass`) always stays class — class syntax used for schema, not for behavior.
- This class-vs-function allowance does not make `dataclass` valid for stable request/config/domain contracts;
  those use Pydantic `BaseModel` by default.
- Forbidden: `class FooUtils:` / `class XxxHelpers:` whose body is only `@staticmethod` / `@classmethod`
  with no shared state — Python modules are namespaces; flatten to module-level functions.

Full treatment: [references/class-vs-function.md](references/class-vs-function.md).

## Object API Quick Rules

- When two or more related payloads are derived from the same context/request/config object, or one function
  derives multiple stable payloads from that state, use one cohesive domain object with named methods.
- Prefer `request = GatewayResponsesRequest.create(); settings = request.model_settings();
  client.responses.create(**settings.as_external_call_dict())` over `context = create_context();
  settings = build_model_settings(context=context)`.
- Use domain nouns for the object (`GatewayResponsesRequest`, `WebhookDelivery`, `ReportExport`) and caller-goal
  method names (`headers()`, `payload()`, `model_settings()`, `to_request()`).
- Do not use `build` in public function, method, class, or variable names for request/config object APIs. Prefer
  `create`, `from_*`, `to_*`, `as_*`, or direct caller-goal method names.
- Keep pure standalone transforms as module-level functions. Do not create a class just to wrap one trivial
  function.
- Avoid public `build_xxx(...)` helpers when they only expose intermediate assembly details that callers should
  not coordinate.

Full treatment: [references/object-api-style.md](references/object-api-style.md).

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
- No mirror-model chains: do not add a `BaseModel` layer that does not change contract, validation,
  serialization, permission, aggregation, or persistence semantics.
- No pass-through re-wrap at call sites: if a function's return shape and semantics equal its callee's
  `BaseModel` return value, return that value directly. Do not reconstruct via `AModel(**b.model_dump())`
  or `AModel.model_validate(b)`. The only allowed wrap is `BaseResponse.ok(...)` at an outward boundary,
  because the envelope adds `code` / `message` semantics.
- Config-first over new models: if a proposed new `BaseModel` differs from the source only by something
  configurable on the source — `model_config = ConfigDict(...)`, `Field(serialization_alias=...,
  validation_alias=..., exclude=..., default_factory=..., ...)`, or `@field_validator` /
  `@model_validator` — configure the source model. Do not introduce a new layer to express a difference
  that is really a config switch.

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
- Missing docstrings, non-Chinese function or class docstrings, or docstrings without `Args` / `Returns` business
  context.
- Scattered `build_xxx(context=...)` helpers that repeatedly pass the same context to assemble one conceptual
  request/config object.
- Public names containing `build`, `build_`, or `Builder` in request/config object APIs.
- `Any` for stable contracts or outward response payloads.
- Passing request/config/domain data through functions as `dict`, `Mapping`, `dict[str, object]`, or dict type
  aliases instead of defining a Pydantic `BaseModel`.
- Hiding stable contract dictionaries behind type aliases such as `type Headers = dict[str, str]` or
  `type Body = dict[str, object]`.
- `create()` or `from_*()` factories that assemble `turn_metadata: dict[...]`, `body: dict[...]`, headers,
  JSON strings, external-call kwargs, or other derived payloads.
- Request/config/domain methods named `headers()`, `payload()`, `body()`, `client_metadata()`, or
  `model_settings()` returning raw dictionaries instead of Pydantic models.
- Passing a dictionary returned by a final serializer such as `as_external_call_dict()` into another project helper for
  filtering, enrichment, or retry orchestration.
- Assigning `body_args = body.to_boundary_dict()` or `external_kwargs = settings.as_external_call_dict()` and then
  indexing that dictionary to call an external dependency.
- Building `extra_body={"client_metadata": body_args["client_metadata"]}` or similar nested boundary kwargs from
  an already serialized dictionary.
- Low-level external I/O or framework helpers reading `API_KEY`, tokens, or request credentials from module globals instead of
  receiving them explicitly from the high-level entrypoint or config model.
- Stable request/config/domain objects implemented as `@dataclass` while holding dictionaries or serialized
  copies of dictionaries.
- Claiming a value is an internal helper or local literal while returning it, storing it, passing it to another
  project function, or sharing it across branches/modules.
- Treating scripts, tests, examples, one-off utilities, or explanatory snippets as exempt from this style.
- Raw `dict` / `list` / primitive returns from outward API boundaries.
- Shorthand route decorators (`@router.get(...)`) lacking full metadata.
- Implicit parameter sources or `user_id: int = Path(...)` default-style; use `Annotated[int, Path(...)]`.
- Raising raw `HTTPException` for business validation failures.
- `BaseModel` fields without `Field(...)`; non-Chinese or placeholder `description`.
- Per-endpoint `XxxResponse` model duplicating `code` / `message` / `data` — use `BaseResponse[T]`.
- Mirror-model chains (`UserOrmSchema` → `UserResponse` with identical fields).
- Pass-through re-wrap at call sites: `return AModel(**b.model_dump())` or `return AModel.model_validate(b)` when no field, validation, permission, serialization, or aggregation change happens between caller and callee.
- Spinning up a new `BaseModel` layer to express a difference that could be set on the source model via `ConfigDict`, `Field(...)` options, or a validator (alias / `by_alias` / `extra` / `frozen` / `exclude` / serialization shape, etc.) — configure the source model instead.
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
- `class XxxUtils:` / `class XxxHelpers:` whose body is only `@staticmethod` / `@classmethod` with no shared state — Python modules are namespaces; flatten to module-level functions.

## References Index

| Topic | Reference | Runnable example |
|---|---|---|
| Typing defaults, project exceptions, and forbidden legacy forms | [typing-usage.md](references/typing-usage.md) | [repository.py](examples/repository.py), [protocol.py](examples/protocol.py), [overload.py](examples/overload.py), [paramspec.py](examples/paramspec.py) |
| Unified response envelope `BaseResponse[T]` + `PageData[T]` + exception handlers | [response-contract.md](references/response-contract.md) | [base_response.py](examples/base_response.py), [route.py](examples/route.py) |
| FastAPI routes, parameter sources, error handling, deviations for streaming | [fastapi-style.md](references/fastapi-style.md) | [route.py](examples/route.py), [base_response.py](examples/base_response.py) |
| SQLAlchemy 2 ORM, async repository, relationship loading | [sqlalchemy2-style.md](references/sqlalchemy2-style.md) | [repository.py](examples/repository.py) |
| Pydantic v2 fields, validators, `ClassVar`, model layering | [pydantic-v2-style.md](references/pydantic-v2-style.md) | [base_response.py](examples/base_response.py) |
| `@property` / `@cached_property` / `@computed_field` / `@hybrid_property` usage discipline + setter ban | [property-usage.md](references/property-usage.md) | [property_usage.py](examples/property_usage.py) |
| Object API style for replacing scattered `build_xxx(context=...)` helpers with cohesive request/config objects | [object-api-style.md](references/object-api-style.md) | [object_api_style.py](examples/object_api_style.py) |
| Async safety, blocking I/O, sync-in-async anti-patterns | [async-concurrency.md](references/async-concurrency.md) | — |
| Outward vs persistence boundary, exceptions and priorities, deviation rules | [architecture-boundary.md](references/architecture-boundary.md) | — |
| Class vs Function decision checklist and namespace-grouping anti-patterns | [class-vs-function.md](references/class-vs-function.md) | — |
