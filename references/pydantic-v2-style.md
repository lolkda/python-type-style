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

## Default / Exception / Forbidden

| Area | Default | Allowed exception | Forbidden |
|---|---|---|---|
| Field docs | Chinese business description on every outward field. | Internal models not exposed in schema may stay lighter. | Missing descriptions, English placeholders, type-label descriptions. |
| Model layers | Reuse/configure the source model. | New layer only for changed contract, validation, permission, serialization, aggregation, or persistence semantics. | Mirror models with identical fields. |
| Call sites | Return existing `BaseModel` values directly. | Wrap with `BaseResponse.ok(...)` at outward boundaries. | Pass-through re-wrap with `model_dump()` / `model_validate()`. |
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

## Runnable Counterparts

- `BaseResponse[T]` + `PageData[T]` with `ok` / `fail` factories — see `examples/base_response.py`.
- Shared outward model definitions — see `examples/_shared.py`.
- `@computed_field` and setter anti-pattern comparisons — see `examples/property_usage.py`.

## Official Reference

For Pydantic v2 implementation details, prefer the official LLM index as the first documentation route:

- https://pydantic.dev/docs/validation/llms.txt

Use the index to choose the relevant official page, then load only that page for the current task. Keep this
skill focused on project policy; do not copy broad official documentation into it.
