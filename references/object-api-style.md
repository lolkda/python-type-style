# Object API Style

Use this rule when helper functions or one large function repeatedly use the same context/request/config object
to assemble related outputs. Prefer one cohesive domain object whose public methods match caller goals.

This reference owns one decision: how to collapse scattered assembly into a cohesive request/config/domain
object. Two adjacent doctrines live elsewhere and are deliberately not restated here:

- **Whether a function or model should exist at all** — thin-helper inlining, linear-flow orchestration,
  forwarding chains, and the model unwrap test — see [class-vs-function.md](class-vs-function.md).
- **Contract shape and serialization** — Pydantic state, no serialized fields, one final boundary dump — see
  [pydantic-v2-style.md](pydantic-v2-style.md).

## Rules

- Replace scattered `build_xxx(context=...)` helpers when two or more related payloads derive from the same
  state. If one function derives multiple stable payloads from the same request/config/domain state, split those
  payloads into Pydantic models behind one cohesive object API.
- Name the object after the domain concept, not the implementation pattern: `ResponsesRequest`,
  `WebhookDelivery`, `ReportExport`, `AuthSession`.
- Expose caller-goal methods such as `headers()`, `payload()`, `model_settings()`, `to_request()`, or
  `as_openai_settings()`. Those derived methods return Pydantic models, not raw dictionaries.
- Hide intermediate assembly details when the caller only needs the final object. Callers should not coordinate
  headers, body metadata, and model settings separately if `request.model_settings()` can do it.
- Do not use `build`, `build_`, or `Builder` in public function, method, class, or attribute names for
  request/config object APIs. Prefer `create`, `from_*`, `to_*`, `as_*`, or direct caller-goal method names.
  Internal local names, fixtures, and third-party names are not the target.
- Object API cleanup is not a license to mint a new thin-helper or forwarding layer. After replacing `build_xxx`
  helpers, audit the result against [class-vs-function.md](class-vs-function.md): do not recreate the same
  fragmentation under `create_xxx`, `new_xxx`, `send_once`, `default_xxx`, or `to_xxx` method names, and do not
  add methods that only forward to the next method.
- Store stable request/config/domain state as Pydantic models and serialize only at the final external boundary.
  The contract, serialized-state, and one-final-dump rules are owned by
  [pydantic-v2-style.md](pydantic-v2-style.md).
- Use Chinese docstrings with `Args` / `Returns` for every surviving method, including `create`, properties, and
  private helpers.

## Default / Exception / Forbidden

| Area | Default | Allowed exception | Forbidden |
|---|---|---|---|
| Related request/config assembly | One domain object with methods. | A single pure transform that derives one non-contract value. | Repeated `build_xxx(context=...)` calls or one large function deriving multiple stable payloads. |
| Naming | Domain noun plus caller-goal methods. | `to_*` / `as_*` when converting to an external-boundary shape. | Public names containing `build`, `build_`, or `Builder`; `XxxUtils`, `XxxHelpers`, or vague `Manager`. |
| Method results | Caller-goal methods return Pydantic models. | `to_*_dict()` / `as_*_dict()` inline at the final external call. | `body()` / `headers()` / `client_metadata()` / `model_settings()` returning raw dictionaries. |
| Cohesion vs fragmentation | One object exposing caller goals. | Extract a method only when it earns existence per [class-vs-function.md](class-vs-function.md). | Renamed `build_xxx` fragmentation under `create_xxx` / `send_once` / `to_xxx`, or methods that only forward. |

State ownership, factory behavior, serialized state, external-call kwargs, and the final dump follow
[pydantic-v2-style.md](pydantic-v2-style.md); existence and linear-orchestration verdicts follow
[class-vs-function.md](class-vs-function.md).

## Rewrite Pattern

Prefer:

```python
request = GatewayResponsesRequest.create()
settings = request.model_settings()
client.responses.create(**settings.as_external_call_dict())
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

These are the object-API-specific failures. Thin-helper, forwarding-chain, serialized-state, and final-dump
anti-patterns are not repeated here — see [class-vs-function.md](class-vs-function.md) and
[pydantic-v2-style.md](pydantic-v2-style.md).

- `build_headers(context)`, `build_body(context)`, and `build_settings(context)` all sharing the same state while
  callers only need settings.
- A class named `RequestBuilder` or a method named `build_settings()` that exposes assembly steps instead of
  caller intent.
- Object API rewrites that remove `build_xxx` names but keep the same fragmentation under `create_xxx`,
  `new_xxx`, `send_once`, `default_xxx`, or `to_xxx` names.
- Public methods named after implementation steps instead of caller intent.
- Methods named `body()`, `headers()`, `client_metadata()`, or `model_settings()` returning raw dictionaries
  instead of Pydantic models.

## Runnable Counterpart

- Cohesive gateway request object with `create()` and `model_settings()` — see `examples/object_api_style.py`.
