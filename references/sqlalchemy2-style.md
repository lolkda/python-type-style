# SQLAlchemy 2 Style

## Rules

- Use SQLAlchemy 2.x native style: `DeclarativeBase`, `Mapped[...]`, `mapped_column(...)`.
- Do not introduce legacy `Query`-centric ORM code. Use `select(...)` with `Session.scalar(...)`,
  `Session.scalars(...)`, or `Session.execute(...)`.
- Every mapped attribute uses `Mapped[...]`; no untyped `Column(...)` declarations in new code.
- Repository, DAO, and unit-of-work methods keep keyword-only signatures.
- One ORM model per persistence representation. Do not create mirror ORM wrappers with no added semantics.
- Persistence concerns stay in ORM models; outward API contracts stay in `BaseModel` schemas wrapped by
  `BaseResponse[T]`.
- Declare relationship loading strategy explicitly. Default to `lazy="raise"`; opt in at query sites with
  `selectinload`, `joinedload`, or another explicit loader.
- Manage sessions with context managers. Do not share `Session` / `AsyncSession` instances across unrelated
  request or task scopes.
- Async paths use `AsyncSession`, async engine, and async driver consistently.
- Repository return types are explicit: ORM entity, `list[Entity]`, scalar value, or named result type.
- Do not leak raw database rows or ad hoc tuple contracts into service or router layers.
- Use `@hybrid_property` when a derived attribute must appear in SQL clauses; use `@property` only for
  Python-side access that does not touch lazy-loaded relationships.

## Default / Exception / Forbidden

| Area | Default | Allowed exception | Forbidden |
|---|---|---|---|
| Query style | `select(...)` statements. | Legacy modules may keep existing `Query` code until actively refactored. | New `session.query(...)` calls. |
| New code in legacy modules | SQLAlchemy 2 statement style. | Small migration adapters may bridge old and new session APIs temporarily. | Expanding the legacy query style. |
| Constructors | Business functions are keyword-only. | ORM model constructors may follow SQLAlchemy mapped-class behavior. | Business-layer positional APIs. |
| Relationship loading | `lazy="raise"` plus explicit loader options at query sites. | A relationship may use another explicit strategy when the access pattern is documented. | Hidden lazy loads during outward response assembly. |

## Anti-patterns

- Legacy `session.query(...)` style in new SQLAlchemy 2 code.
- ORM columns without `Mapped[...]` type annotations.
- One `Session` or `AsyncSession` shared across unrelated request or task scopes.
- Synchronous ORM access inside asynchronous request flows.
- Anonymous tuple or row shapes leaking from repository methods into services or routers.
- ORM entities exposed directly as outward response models.

## Runnable Counterparts

- Generic `Repository[EntityT: Base]`, sync + async accessors, and eager loading with `selectinload` — see
  `examples/repository.py`.
- `@hybrid_property` with Python + SQL forms — see `examples/property_usage.py`.
