# Unified Response Contract

All outward JSON API responses use one generic envelope: `BaseResponse[T]`. Do not redefine `code` /
`message` / `data` per route. The same envelope covers success, business failure, validation failure, and
protocol failure paths.

## Rules

- Define exactly one `BaseResponse[T]` envelope per project. Do not fork it per module.
- Business data models stay pure: no `code`, no `message`, no protocol fields.
- Use `BaseResponse[T]` as the route `response_model` and return annotation for JSON endpoints.
- Success returns `BaseResponse.ok(data)`.
- Failures are raised as typed business exceptions or protocol exceptions; global handlers serialize them with
  `BaseResponse.fail(code=..., message=...)`.
- List endpoints compose at one level: `BaseResponse[PageData[T]]`.
- `data` is `T | None` with `default=None`; failure and empty-result responses use `data=None`.
- Do not stack nested envelope generics beyond `BaseResponse[PageData[T]]`.
- Business `code` is independent from HTTP status. HTTP status carries protocol outcome; business `code`
  carries business outcome.

## Boundary Rules

| Boundary | Default | Allowed exception | Forbidden |
|---|---|---|---|
| JSON routes | `response_model=BaseResponse[T]` or `BaseResponse[PageData[T]]`. | None. | Raw `dict`, raw `list`, primitive payloads, or unwrapped `BaseModel` payloads. |
| File / streaming / HTML routes | Use concrete `response_class` and return the concrete response type. | Unified envelope does not apply because the endpoint is not a JSON contract endpoint. | Omitting route metadata or docstrings. |
| Exception handlers | Emit `BaseResponse[None]` through `BaseResponse.fail(...)`. | HTTP status may differ from business `code`. | Separate `ErrorResponse` models. |
| Business schemas | Only business fields. | None. | Per-endpoint `XxxResponse` models duplicating envelope fields. |

## Anti-patterns

- Defining a per-endpoint `XxxResponse` model that duplicates `code` / `message` / `data`.
- Introducing a separate `ErrorResponse` model.
- Returning ORM entities or business schemas directly from outward JSON routes.
- Stacking nested generics beyond `BaseResponse[PageData[T]]`.
- Tying business `code` to HTTP status one-to-one.

## Runnable Counterparts

- Envelope definition with `ok` / `fail` factories and global exception handlers — see `examples/base_response.py`.
- Routes consuming `BaseResponse[T]` and `BaseResponse[PageData[T]]` — see `examples/route.py`.
