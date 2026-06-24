# Object API Style

Use this rule when several helper functions repeatedly pass the same context/request/config object to assemble
related outputs. Prefer one cohesive domain object whose public methods match caller goals.

## Rules

- Replace scattered `build_xxx(context=...)` helpers when three or more helpers derive related outputs from the
  same state.
- Name the object after the domain concept, not the implementation pattern: `ResponsesRequest`,
  `WebhookDelivery`, `ReportExport`, `AuthSession`.
- Do not use `build` in public function, method, class, or variable names for request/config object APIs. Prefer
  `create`, `from_*`, `to_*`, `as_*`, or direct caller-goal method names.
- Expose caller-goal methods such as `headers()`, `payload()`, `model_settings()`, `to_request()`, or
  `as_openai_settings()`.
- Hide intermediate assembly details when the caller only needs the final object. For example, callers should not
  coordinate headers, body metadata, and model settings if `request.model_settings()` can do it.
- Store stable request/config/domain state as Pydantic `BaseModel` values by default. Dump dictionaries only at
  the final SDK/HTTP serialization boundary.
- Keep standalone pure transforms as module-level functions. The object API rule does not override the
  Class-vs-Function checklist.
- Use Chinese docstrings with `Args` / `Returns` for every method, including `create`, properties, and private
  helpers.

## Default / Exception / Forbidden

| Area | Default | Allowed exception | Forbidden |
|---|---|---|---|
| Related request/config assembly | One domain object with methods. | Module functions while there are only one or two simple transforms. | Repeated `build_xxx(context=...)` calls that force callers to orchestrate internals. |
| Naming | Domain noun plus caller-goal methods. | `to_*` / `as_*` when converting to an external SDK shape. | Public names containing `build`, `build_`, or `Builder`; `XxxUtils`, `XxxHelpers`, or vague `Manager`. |
| State ownership | Store stable state as Pydantic models and derive raw dictionaries only at SDK/HTTP boundaries. | Mutable state only with a documented invariant or lifecycle. | Dict aliases or `Mapping` objects passed through object methods as stable contracts. |

## Rewrite Pattern

Prefer:

```python
request = GatewayResponsesRequest.create()
settings = request.model_settings()
```

Avoid:

```python
context = create_gateway_request_context()
headers = build_gateway_headers(context=context)
metadata = build_gateway_client_metadata(context=context)
extra_body = build_gateway_extra_body(context=context)
settings = build_gateway_model_settings(context=context)
```

## Anti-patterns

- `build_headers(context)`, `build_body(context)`, and `build_settings(context)` all sharing the same state while
  callers only need settings.
- A class named `RequestBuilder` or a method named `build_settings()` that exposes assembly steps instead of
  caller intent.
- A frozen dataclass storing both mutable metadata and a serialized JSON copy of that metadata.
- Passing `Mapping`, `dict[str, object]`, or dict type aliases through object methods instead of modeling
  request/config/domain state with Pydantic.
- Returning a raw dictionary from one project method only for another project method to enrich or forward it.
- Public methods named after implementation steps instead of caller intent.

## Runnable Counterpart

- Cohesive gateway request object with `create()` and `model_settings()` — see `examples/object_api_style.py`.
