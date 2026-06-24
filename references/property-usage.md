# Property Usage

Rules for `@property`, `@cached_property`, `@computed_field`, and `@hybrid_property` across FastAPI /
Pydantic v2 / SQLAlchemy 2 code.

## Selection Rules

| Primitive | Use when | Allowed exception | Forbidden |
|---|---|---|---|
| `@property` | Cheap, side-effect-free, read-only derivation over instance state. | Internal-only convenience aliases with no I/O and no validation side effects. | DB queries, network calls, business exceptions, lazy relationship access, or values expected in OpenAPI / `model_dump()`. |
| `@cached_property` | Host object is treated as immutable for the cached value's lifetime. | Mutable hosts only with a documented invalidation step at every mutation point. | Mutable ORM / Pydantic entities with no invalidation strategy; stale cached values will not fail loudly. |
| `@computed_field` + `@property` | Pydantic derived value must appear in `model_dump()` or OpenAPI. | Internal-only derivations stay plain `@property`. | Plain `@property` for outward response fields. |
| `@hybrid_property` | SQLAlchemy derived value must appear in `select(...).where(...)`, ordering, or aggregation. | Python-only derivations stay plain `@property`. | Plain `@property` in SQL clauses; relationship loads inside the body. |
| `@xxx.setter` | Avoid by default. | Third-party ABC / Protocol requires a setter; keep it a thin wrapper around a named method. Test fakes are unconstrained. | Business validation hidden behind assignment on Pydantic, ORM, or domain models. |

## Setter Replacements

| Scenario | Wrong | Right |
|---|---|---|
| Pydantic cross-field consistency | Raise `ValueError` inside a setter. | `@model_validator(mode="after")`. |
| Pydantic single-field transform | Normalize inside a setter. | `@field_validator("field_name")`. |
| ORM entity | `@xxx.setter` plus business validation. | Direct assignment plus explicit service-layer check. |
| Domain state change | `entity.status = "frozen"` with hidden effects. | Named method such as `entity.freeze(*, reason: str)`. |

## Required Details

- Every `@property` return type is explicit.
- Every `@property`, `@cached_property`, `@computed_field`, and `@hybrid_property` function still has a Chinese
  docstring with `Args` and `Returns`; use `Args: 无。` when the property has no business parameters.
- `@computed_field` must be paired with `@property`.
- `@hybrid_property` must provide a SQL expression when it is used in SQL clauses.
- A property alias for an ORM column is allowed only when it has no side effects and performs no database access.

## Anti-patterns

- `@property` body triggers a DB query, network call, or business exception.
- `@cached_property` on mutable ORM / Pydantic models without invalidation.
- `@property` on a `BaseModel` when the value must cross the API boundary.
- `@property` on an ORM entity when callers write `select(Entity).where(Entity.derived > 0)`.
- `@property` or `@hybrid_property` body accesses a `lazy="raise"` relationship.
- `@xxx.setter` replaces a named state-change method.
- Missing return type annotation on `@property`.

## Runnable Counterpart

Full positive and negative examples for all four primitives live in `examples/property_usage.py`. Treat its
`BAD-*` comment block as the source for review-time anti-pattern comparisons.
