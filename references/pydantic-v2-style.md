# Pydantic v2 Style

## Rules

- All outward-facing `BaseModel` fields include `Field(description="中文业务说明")`.
- Outward business data models do not include `code` / `message` / `data`; those belong to `BaseResponse[T]`.
- Optional fields explicitly define `default` or `default_factory`, and include `description`.
- Every `description` is Chinese and explains business meaning, not a type label or placeholder.
- Internal lightweight models may omit validation constraints, but still include useful `Field(description=...)`
  when they surface in generated schemas.
- Use `Field(...)` constraints only when validation is required.
- Non-field class attributes on Pydantic v2 models use `ClassVar[...]`; otherwise Pydantic collects them as
  fields.
- `@model_validator(mode="after")` returns `Self`; `@field_validator` returns the validated value.
- Use `@computed_field` paired with `@property` when a derived value must appear in `model_dump()` or OpenAPI.
- Setters on Pydantic models are forbidden; use validators or named methods.
- Stable request/config/domain payloads use Pydantic `BaseModel` by default.
- Raw dictionaries are allowed only as inline literals immediately consumed by a third-party, framework, or
  external I/O call boundary, or as tiny single-function local values that are not returned, stored, passed
  onward, or reused across branches. External boundaries include SDK, HTTP, CLI, database, message queue, file,
  subprocess, browser automation, and plugin calls; this list is not exhaustive.
- Do not pass `dict`, `Mapping`, `dict[str, object]`, or dict type aliases between project functions as stable
  request/config/domain contracts.
- Stable request/config/domain objects use Pydantic `BaseModel`, not `dataclass`, `TypedDict`, `Mapping`, or dict
  type aliases. `dataclass` is only for pure internal algorithm state with no aliases, validation,
  serialization, derived payloads, or stable boundary semantics.
- Factory methods create models only; they do not assemble derived dictionaries, serialized JSON,
  external-call kwargs, headers, body payloads, command arguments, file payloads, or database parameters.
- Stable request/config/domain models store semantic Pydantic values, not serialized artifacts such as
  `metadata_json`, `metadata_user_id`, `headers_dict`, `body_dict`, `payload_json`, `request_body`, or
  `external_kwargs`.
- Derived payload methods return Pydantic models. Raw dictionaries are produced only by explicit final-boundary
  serializers named `to_*_dict()` or `as_*_dict()` and consumed adjacent to the actual external call.
- Final serializer output is not assigned to variables and indexed later. Serialize the final external-boundary
  parameter model inline at the third-party, framework, or external I/O call boundary.
- Nested boundary kwargs such as `extra_body`, `extra_headers`, command args, file metadata, or database
  parameters are modeled as nested Pydantic fields; do not rebuild them from pieces of an already serialized
  dictionary.
- Final-boundary serializers dump one complete Pydantic boundary model once. Use aliases, `exclude_none`,
  `@field_serializer`, `@model_serializer`, and nested models instead of manual dictionary assembly through
  repeated child `model_dump()` calls.

## Model Layering Rules

Do not introduce mirror-model chains that duplicate the same fields across layers with no change in semantics.

Before adding a new `BaseModel` layer, configure the source model when the difference is expressible through:

- `model_config = ConfigDict(...)`
- `Field(serialization_alias=..., validation_alias=..., exclude=..., default_factory=..., ...)`
- `@field_validator` / `@model_validator(mode="after")`

Add a new `BaseModel` layer only when it changes at least one of:

- Outward API contract
- Validation behavior that cannot live on the source model
- Permission visibility
- Serialization behavior that cannot live in `ConfigDict` or `Field(...)`
- Aggregation semantics
- Persistence representation

Prefer direct transformation from ORM / domain objects into outward response models. Do not stack generic
envelopes beyond `BaseResponse[PageData[T]]`.

## Call-site Rule: No Pass-through Re-wrap

If a function's return shape and semantics equal its callee's `BaseModel` return value, return the callee's
result directly. Do not reconstruct a structurally equivalent model via `AModel(**value.model_dump())` or
`AModel.model_validate(value)`.

The only allowed wrap at an outward boundary is `BaseResponse.ok(...)`, because it adds `code` / `message`
semantics.

## Serialized State Rule

Serialized values are boundary artifacts, not state. If an external boundary requires a JSON string, header
string, command argument string, or other rendered payload, keep the semantic source as a Pydantic model and
render it only inside the final boundary serializer.

Do not keep both a semantic model and a serialized copy on the same request/config/domain object. Do not replace a
semantic model with a string field merely because the downstream API eventually wants a string.

Use `@field_serializer` or `@model_serializer` when one field must render differently at the boundary.

## Default / Exception / Forbidden

| Area | Default | Allowed exception | Forbidden |
|---|---|---|---|
| Field docs | Chinese business description on every outward field. | Internal models not exposed in schema may stay lighter. | Missing descriptions, English placeholders, type-label descriptions. |
| Model layers | Reuse/configure the source model. | New layer only for changed contract, validation, permission, serialization, aggregation, or persistence semantics. | Mirror models with identical fields. |
| Call sites | Return existing `BaseModel` values directly. | Wrap with `BaseResponse.ok(...)` at outward boundaries. | Pass-through re-wrap with `model_dump()` / `model_validate()`. |
| Contract state | Pydantic `BaseModel` for stable request/config/domain payloads. | Raw `dict` only as inline external-boundary literals or tiny single-function local values. | Dict aliases, `Mapping`, `TypedDict`, dataclasses, or `dict[str, object]` passed between project functions. |
| Factory behavior | Create and return Pydantic models only. | ID/time/default generation needed for construction. | Factories assembling dictionaries, JSON strings, headers, body payloads, command args, database parameters, or external-call kwargs. |
| Serialized state | Store semantic Pydantic models. | Boundary-only field serializers for APIs that require rendered strings. | Stable fields named like `*_json`, `*_dict`, `*_payload`, `metadata_user_id`, `request_body`, or `external_kwargs`. |
| Serialization boundary | `to_*_dict()` / `as_*_dict()` inline at final external calls. | Tiny local literals that are not returned, stored, passed onward, or reused across branches. | Assigning serialized dictionaries to `body_args` / `external_kwargs` and indexing them later. |
| Nested boundary kwargs | Nested Pydantic fields on one final external-boundary parameter model. | Tiny inline literals consumed by the same third-party, framework, or external I/O call. | `extra_body={"client_metadata": body_args["client_metadata"]}` built from serialized data. |
| Final dump | One complete boundary model dumped once. | `@field_serializer` / `@model_serializer` for special field rendering. | Child `to_*_dict()` calls or repeated child `model_dump()` calls stitched into a parent dict. |
| Derived fields | `@computed_field` + `@property` for API-visible derived values. | Plain `@property` for internal-only computation. | Expecting plain `@property` to appear in `model_dump()` / OpenAPI. |
| Mutation hooks | Validators or named methods. | None for business validation. | `@xxx.setter` on Pydantic business models. |

## Anti-patterns

- `BaseModel` fields without `Field(...)`.
- Non-Chinese or placeholder field descriptions.
- `code` / `message` / `data` fields on business data models.
- Optional fields without explicit defaults.
- Mirror-model chains such as `UserOrmSchema` -> `UserResponse` with identical fields.
- Chained `model_validate()` / `model_dump()` between structurally equivalent models.
- Pass-through re-wrap at call sites.
- Creating a new model for a difference that `ConfigDict`, `Field(...)`, or validators can express.
- Class-level constants without `ClassVar[...]`.
- Passing request/config/domain state as `dict`, `Mapping`, or dict type aliases across project function
  boundaries.
- Type aliases such as `type Headers = dict[str, str]` or `type Body = dict[str, object]` used as stable
  contracts instead of Pydantic models.
- `@dataclass`, `TypedDict`, or `Mapping` request/config/domain objects used as stable contracts.
- Calling a dictionary a local literal while returning it, storing it, passing it to a project helper, or sharing
  it across branches.
- `create()` / `from_*()` factories that assemble metadata dictionaries, request bodies, headers,
  external-call kwargs, command arguments, file payloads, database parameters, or JSON strings.
- Stable request/config/domain fields storing serialized derivatives such as `metadata_json`,
  `metadata_user_id`, `headers_dict`, `body_dict`, `payload_json`, `request_body`, or `external_kwargs`.
- Derived payload methods returning dictionaries instead of Pydantic models.
- `body_args = body.as_external_call_dict()` followed by `body_args["model"]`, `body_args["input"]`, or similar
  boundary argument indexing.
- Rebuilding nested boundary kwargs from an already serialized dict instead of serializing one final model at the
  call boundary.
- Final serializers that call child `to_*_dict()` methods or repeated child `model_dump()` calls to stitch
  together the parent payload.

## Runnable Counterparts

- `BaseResponse[T]` + `PageData[T]` with `ok` / `fail` factories — see `examples/base_response.py`.
- Shared outward model definitions — see `examples/_shared.py`.
- `@computed_field` and setter anti-pattern comparisons — see `examples/property_usage.py`.

## Official Reference

For Pydantic v2 implementation details, prefer the official LLM index as the first documentation route:

- https://pydantic.dev/docs/validation/llms.txt

Use the index to choose the relevant official page, then load only that page for the current task. Keep this
skill focused on project policy; do not copy broad official documentation into it.
