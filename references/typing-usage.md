# Typing Usage

This reference records project-specific typing constraints for Python 3.12+ FastAPI / Pydantic v2 /
SQLAlchemy 2 code. It is not a typing catalog; if a primitive has no project-specific rule, use normal modern
Python typing.

## Core Rules

| Area | Default | Allowed exception | Forbidden |
|---|---|---|---|
| Containers | Use built-in generics: `list[T]`, `dict[K, V]`, `tuple[T, ...]`, `set[T]`. | None. | `typing.List`, `Dict`, `Tuple`, `Set`, `FrozenSet`. |
| ABC imports | Import `Sequence`, `Mapping`, `Iterable`, `Iterator`, `AsyncIterator`, `Callable`, `Awaitable` from `collections.abc`. | None. | Importing these ABCs from `typing`. |
| Nullable and unions | Use `X | None` and `X | Y`. | None. | `Optional[X]`, `Union[X, Y]`, nested `Optional[Optional[X]]`. |
| Generic syntax | Use PEP 695: `class Repo[T]:`, `def fn[T](...)`, `type Alias = ...`. | Legacy files may keep old syntax until refactored. | New `TypeVar` / `Generic[T]` scaffolding or `Alias: TypeAlias = ...` in Python 3.12+ code. |
| `Annotated` aliases | Extract repeated FastAPI / Pydantic metadata chains to module-level `type` aliases. | One-off local metadata may stay inline. | Repeating the same `Annotated[...]` chain across route signatures. |
| `Sequence[T]` vs `list[T]` | Use `Sequence[T]` for read-only iterable/indexable parameters; use `list[T]` for return values and mutation. | Repository methods may return concrete `list[T]` because callers often append, sort, or serialize. | `list[T]` parameters for read-only input, or abstract return types when callers need a concrete list. |
| `Protocol` dependencies | Service dependencies use `Protocol`; concrete implementations do not need to inherit the protocol. | Use ABC only when shared base behavior is required. Use `@runtime_checkable` only for real `isinstance` checks. | Coupling service code to concrete repository classes for test seams. |
| `TypedDict` | Use only for raw external `dict` ingress immediately before `BaseModel.model_validate(...)`. | `Unpack[TypedDict]` is allowed only inside a third-party adapter for typed kwargs passed directly to that SDK call. | `TypedDict` as request/config/domain state, outward API contract, or project-function contract; use `BaseModel`. |
| `Literal` vs enum | Use `Literal[...]` for single-model or single-module finite sets. | Upgrade to `StrEnum` / `IntEnum` only when the same value set is shared across modules or carries business behavior. | Creating an enum only for one local status field. |
| `ClassVar` | Wrap non-field Pydantic class attributes in `ClassVar[...]` because Pydantic collects annotated class attributes as fields. | None. | Class-level constants on Pydantic models without `ClassVar[...]`. |
| `cast` | Use only after verifying an untyped third-party value or a narrowing the checker cannot infer. | Prefer runtime checks (`isinstance`, validators) whenever runtime validation is required. | Using `cast` to bypass validation or replace runtime narrowing. |
| `NewType` | Use for service-layer nominal IDs when primitive ID mixups are a real risk. | Pydantic fields use `Annotated[int, ...]` instead. | Declaring Pydantic model fields directly as `NewType` IDs. |
| `from __future__ import annotations` | Do not enable project-wide. Pydantic v2 and FastAPI rely on runtime type introspection. | Use string annotations or `TYPE_CHECKING` surgically for circular imports. | Blanket future-annotations policy in FastAPI / Pydantic modules. |

## Required Details

- `@overload` stubs use `...` bodies but still require Chinese docstrings with `Args` / `Returns`.
- `Protocol` method stubs are consumer-facing contracts and still require business docstrings.
- `Concatenate[X, P]` decorators may inject the first positional parameter into the decorated business function
  (`async def rename_user(session: AsyncSession, *, user_id: int, ...)`). The keyword-only rule is waived only
  for that injected first parameter.

## Anti-patterns

- Using `Any` for stable contracts or outward response payloads.
- Bare `dict` / `list` without type parameters in new code.
- Importing legacy collection aliases from `typing`.
- Rebuilding old typing syntax in Python 3.12+ code instead of PEP 695 syntax.
- Substituting `TypedDict` for `BaseModel` at outward API boundaries.
- Substituting `TypedDict` or `Unpack[TypedDict]` for request/config/domain contracts between project functions.
- Casting values that should be validated.
- Re-declaring the same `Annotated[...]` chain across multiple route signatures.
- Class-level constants on Pydantic models without `ClassVar[...]`.

## Runnable Counterparts

- Generic repository with PEP 695 bounded type parameter — see `examples/repository.py`.
- `Protocol`-based dependency injection with an in-memory fake — see `examples/protocol.py`.
- `@overload` return narrowing — see `examples/overload.py`.
- `ParamSpec` / `Concatenate` typed decorators and keyword-only exception — see `examples/paramspec.py`.
