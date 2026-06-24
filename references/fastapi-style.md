# FastAPI Style

## Rules

- Declare all routes with `@router.api_route(...)`. Do not use shorthand decorators like `@router.get(...)`.
- In every route decorator, explicitly set `path`, `methods`, `response_model` (or `response_class`), `tags`,
  and `summary`.
- JSON endpoint `response_model` is `BaseResponse[T]` or `BaseResponse[PageData[T]]`. Do not redefine envelope
  fields.
- Every route function has a Chinese docstring with `用途`, `Args`, and `Returns`.
- Every parameter source is explicit: `Path`, `Query`, `Body`, `Form`, `File`, `Header`, `Cookie`, `Depends`,
  or `Security`.
- Use `Annotated[...]` for parameter sources and validation metadata. Do not pass source objects as default
  values (`user_id: int = Path(...)` is forbidden).
- Return `BaseResponse.ok(data)` for success paths.
- Raise typed business exceptions for business failures; global handlers serialize them with
  `BaseResponse.fail(...)`.

## Default / Exception / Forbidden

| Area | Default | Allowed exception | Forbidden |
|---|---|---|---|
| Route decorator | `@router.api_route(path=..., methods=..., response_model=..., tags=..., summary=...)`. | None. | Shorthand decorators lacking full metadata. |
| JSON response | `BaseResponse[T]` or `BaseResponse[PageData[T]]`. | None. | Raw `dict`, raw `list`, primitives, or unwrapped outward models. |
| Non-JSON response | Concrete `response_class` and concrete return type. | Streaming, file, and HTML responses skip the unified envelope. | Dropping route metadata or docstrings. |
| Parameter source | `Annotated[T, Path|Query|Body|Header|Cookie|Depends|Security(...)]`. | Repeated source chains become module-level `type` aliases. | Implicit FastAPI inference or default-value source objects. |
| Exceptions | Typed business exceptions plus global handlers. | `HTTPException` only for protocol-level failures. | Raw `HTTPException` for business validation failures. |
| Keyword-only | Route and dependency callables follow the project keyword-only rule. | Framework-fixed callback signatures may keep the required positional shape. | Positional business parameters. |

## Error Handling

- Define typed business exception classes per bounded context.
- Register handlers for `RequestValidationError`, `HTTPException`, and each business exception family.
- Every handler emits `BaseResponse[None]` through `BaseResponse.fail(...)`.
- Business `code` space is decoupled from HTTP status and documented in one source of truth.

## Anti-patterns

- `@router.get(...)` / `@router.post(...)` shortcuts in new route code.
- Missing `response_model`, `tags`, or `summary`.
- Implicit parameter sources.
- `user_id: int = Path(...)` default-style parameter declarations.
- Raw `HTTPException` for business validation failures.
- Raw `dict` / `list` returns from JSON route handlers.
- Repeating the same `Annotated[...]` chain across multiple route signatures.

## Runnable Counterparts

- Full route with reusable `Annotated` aliases and `BaseResponse[T]` — see `examples/route.py`.
- Exception handler registration with `BaseResponse.fail(...)` — see `examples/base_response.py`.
