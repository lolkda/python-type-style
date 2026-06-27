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
- Third-party, framework, or external I/O boundaries may temporarily use permissive types (untyped results,
  `Any`-typed payloads). Conversion to strict `BaseModel` contracts must happen immediately after ingress, inside
  an adapter at the boundary.
- Raw dictionaries, `TypedDict`, dataclasses, and named tuples are temporary boundary adapters only when consumed
  in the same function. If the value is returned, stored, or passed into project code, convert it to the relevant
  Pydantic model first.
- Low-level external I/O or framework helpers do not read request credentials such as `API_KEY`, bearer tokens,
  tenant IDs, or session IDs from module globals. Standalone scripts may define top-level constants, but
  high-level entrypoints must pass credential/config values explicitly into request/config models or helper calls.
- `create()` and value-named `from_*` factories (naming an in-hand value, e.g. `from_dict` / `from_cli_metadata`)
  perform no I/O during construction. Only a source-named ingress factory (`from_os` / `from_env` / `from_file`)
  reads, and only the one source its name declares — never a second. The name is a contract it must honor.
- Explicit ingress factories are selected by the high-level entrypoint and their result passed in as a semantic
  value; `create()` or a value-named `from_*` must not call them as an optional-parameter fallback. An optional
  parameter's `None` fallback must not reach for external state — allow only dependency-free in-process
  generation (UUID / token / timestamp / constant default), never a file / env / cache / SDK / global-mutable
  read.
- Streaming and file responses may use `response_class` instead of `BaseResponse[T]`. The unified envelope rule
  applies only to JSON contract endpoints; metadata completeness and docstring requirements remain mandatory.

## Anti-patterns

- Routing-layer code returning raw ORM entities instead of `BaseModel` schemas wrapped by `BaseResponse[T]`.
- Repository methods returning ad hoc tuple shapes that bleed into service-layer code.
- Service facades that vary their return types across callers (some return `dict`, some return `BaseModel`).
- Exposing internal helper data structures (named tuples, dataclasses without semantic meaning) across module
  boundaries.
- Hidden global credential reads inside low-level external I/O or framework helpers.
- `create()` or a value-named `from_*` factory that reads a config file, environment, or SDK to fill a field or
  default; or a source-named ingress (`from_os` / `from_file`) that reaches a second, undeclared source.
- Optional parameter whose `None` fallback fetches external state, hiding the read from callers.
- A read-of-existing-value named `new_*` / `generate_*` instead of `read_*` / `load_*`.
