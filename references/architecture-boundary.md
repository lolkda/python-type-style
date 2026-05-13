# Architecture Boundary

## Public and External Boundaries

Public or external boundaries include:

- FastAPI route handlers
- Public SDK interfaces
- Cross-module service facades with stable business contracts
- RPC, MQ, webhook, or plugin entrypoints
- Reusable application service methods exposed to other bounded contexts

Persistence-layer methods are **not** outward boundaries by default:

- SQLAlchemy repository methods
- ORM query builders
- Session-scoped data access helpers
- Internal unit-of-work utilities

Repository and ORM-layer methods may return ORM entities, scalar rows, tuples, or SQLAlchemy result wrappers
when the contract stays inside the application boundary. Convert to outward `BaseResponse[T]` contracts only
when data leaves the service boundary.

## Exceptions and Priorities

1. If project rules conflict, follow the stricter rule that keeps API contracts explicit.
2. If compatibility constraints exist, document the exception in code comments and keep outward contracts
   unchanged.
3. Do not relax outward response model requirements or route metadata completeness.
4. Do not introduce a per-endpoint envelope model that duplicates `BaseResponse[T]`. The unified envelope is
   load-bearing for documentation, error handling, and downstream codegen.

## When To Deviate

- Framework internals that enforce fixed callback signatures (middleware dispatch, framework event hooks) may
  be exempt from keyword-only rules. Any wrapper method exposed to business code must still keep keyword-only
  interfaces.
- Decorators typed with `Concatenate[X, P]` require the decorated business method to declare the first
  parameter positionally (e.g. `async def rename_user(session: AsyncSession, *, user_id: int, ...)`). The
  keyword-only rule is exempt for the decorator-injected first parameter only; all other business parameters
  remain keyword-only.
- Third-party integration boundaries may temporarily use permissive types (untyped SDK results, `Any`-typed
  payloads). Conversion to strict `BaseModel` contracts must happen immediately after ingress, inside an
  adapter at the boundary.
- Streaming and file responses may use `response_class` instead of `BaseResponse[T]`. The unified envelope rule
  applies only to JSON contract endpoints; metadata completeness and docstring requirements remain mandatory.

## Anti-patterns

- Routing-layer code returning raw ORM entities instead of `BaseModel` schemas wrapped by `BaseResponse[T]`.
- Repository methods returning ad hoc tuple shapes that bleed into service-layer code.
- Service facades that vary their return types across callers (some return `dict`, some return `BaseModel`).
- Exposing internal helper data structures (named tuples, dataclasses without semantic meaning) across module
  boundaries.
