# Object API Style

Use this rule when helper functions or one large function repeatedly use the same context/request/config object
to assemble related outputs. Prefer one cohesive domain object whose public methods match caller goals.

## Rules

- Replace scattered `build_xxx(context=...)` helpers when two or more related payloads derive from the same
  state.
- If one function derives multiple stable payloads from the same request/config/domain state, split those payloads
  into Pydantic models behind one cohesive object API.
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
- `dataclass`, `TypedDict`, `Mapping`, and dict type aliases are not substitutes for stable request/config/domain
  models.
- Keep `create()` / `from_*()` factories narrow: normalize input, generate IDs, apply defaults, and return the
  object. Do not assemble derived dictionaries, serialized JSON, SDK kwargs, HTTP headers, or body payloads inside
  factories.
- Methods such as `headers()`, `payload()`, `body()`, `client_metadata()`, and `model_settings()` return Pydantic
  models. Only explicit final-boundary serializers named `to_*_dict()` or `as_*_dict()` may return raw
  dictionaries.
- Do not assign final serializer output to variables for later indexing. Prefer
  `responses.create(**request.sdk_create_params().to_sdk_dict())` at the SDK/HTTP call boundary.
- Do not rebuild nested SDK kwargs such as `extra_body` or `extra_headers` from an already serialized dictionary.
  Put those nested values on the final SDK/HTTP parameter model.
- Keep standalone pure transforms as module-level functions. The object API rule does not override the
  Class-vs-Function checklist.
- Use Chinese docstrings with `Args` / `Returns` for every method, including `create`, properties, and private
  helpers.

## Default / Exception / Forbidden

| Area | Default | Allowed exception | Forbidden |
|---|---|---|---|
| Related request/config assembly | One domain object with methods. | A single pure transform that derives one non-contract value. | Repeated `build_xxx(context=...)` calls or one large function deriving multiple stable payloads. |
| Naming | Domain noun plus caller-goal methods. | `to_*` / `as_*` when converting to an external SDK shape. | Public names containing `build`, `build_`, or `Builder`; `XxxUtils`, `XxxHelpers`, or vague `Manager`. |
| State ownership | Store stable state as Pydantic models and derive raw dictionaries only at SDK/HTTP boundaries. | Mutable state only with a documented invariant or lifecycle. | Dict aliases or `Mapping` objects passed through object methods as stable contracts. |
| Factory behavior | Factories only normalize inputs and return the object. | ID/time/default generation needed for construction. | `create()` assembling metadata dicts, JSON strings, headers, body payloads, or SDK kwargs. |
| Derived payload methods | Return Pydantic models. | `to_*_dict()` / `as_*_dict()` inline at the final SDK/HTTP call. | `body()` / `headers()` / `client_metadata()` / `model_settings()` returning raw dictionaries or serializers called far from the call site. |
| SDK kwargs | One final Pydantic parameter model serialized once. | Inline literal only when tiny and consumed by the same third-party call. | `body_args = body.to_sdk_dict()` followed by `body_args["..."]` indexing or `extra_body={...}` rebuilt from serialized data. |

## Rewrite Pattern

Prefer:

```python
request = GatewayResponsesRequest.create()
settings = request.model_settings()
client.responses.create(**settings.to_sdk_dict())
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
- Using `TypedDict` or `dataclass` as the stable request/config/domain object because the code is "just a script"
  or "internal".
- Returning a raw dictionary from one project method only for another project method to enrich or forward it.
- `create()` assembling `turn_metadata: dict[...]`, `turn_metadata_json`, headers, body payloads, or SDK kwargs
  before returning the object.
- Methods named `body()`, `headers()`, `client_metadata()`, or `model_settings()` returning dictionaries.
- A final dictionary serializer such as `to_sdk_dict()` being called far away from the actual SDK/HTTP call site
  and then passed through project helpers.
- Assigning serialized kwargs to `body_args`, `sdk_kwargs`, or `payload_dict` and indexing them to call the SDK.
- Rebuilding `extra_body`, `extra_headers`, or nested SDK kwargs from an already serialized dictionary instead of
  modeling the final SDK parameter shape.
- A single orchestration function deriving headers, metadata, body, and SDK kwargs as local dictionaries instead
  of modeling those payloads.
- Public methods named after implementation steps instead of caller intent.

## Runnable Counterpart

- Cohesive gateway request object with `create()` and `model_settings()` — see `examples/object_api_style.py`.
