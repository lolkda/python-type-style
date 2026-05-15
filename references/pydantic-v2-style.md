# Pydantic v2 Style

## Rules

- All outward-facing `BaseModel` fields must include `Field(description="中文业务说明")`.
- Outward business data models do **not** include `code` / `message` / `data` fields. Those belong to
  `BaseResponse[T]` (see `references/response-contract.md`).
- Internal lightweight models may omit validation constraints, but must still include `Field(description=...)`
  for schema readability.
- Use `Field(...)` constraint parameters (`gt`, `min_length`, `max_length`, etc.) only when validation is
  required.
- Optional fields must explicitly define `default` or `default_factory`, and must include `description`.
- Every `description` must be Chinese and explain business meaning. Do not use type labels or placeholders.
- Keep model intent explicit and stable for API contracts and downstream consumers.
- Non-field class attributes on Pydantic v2 models must be wrapped in `ClassVar[...]` to opt out of field
  collection.
- `@model_validator(mode="after")` returns `Self`. `@field_validator` returns the validated value.
- Use `@computed_field` paired with `@property` when the derived value must appear in `model_dump()` or the OpenAPI schema; use plain `@property` for internal-only computation. See [property-usage.md](property-usage.md).
- Setters (`@xxx.setter`) on Pydantic models are forbidden; use `model_validator(mode="after")` for cross-field constraints and `field_validator` for single-field transforms.

## Model Layering Rules

Do not introduce mirror-model chains that duplicate the same fields across layers with no change in semantics.

**Config-first over new models.** Before adding a new layer, check whether the desired difference can be set
on the source model itself:

- `model_config = ConfigDict(serialize_by_alias=True, populate_by_name=True, extra="ignore", frozen=True, ...)`
- `Field(serialization_alias=..., validation_alias=..., exclude=..., repr=..., default_factory=..., ...)`
- `@field_validator` / `@model_validator(mode="after")`

If the difference is expressible this way, configure the source model. The criteria below justify a new
model only when one model genuinely cannot carry both behaviors — for example, the same data must be
exposed to multiple consumers with incompatible serialization or validation forms, or the new behavior
depends on context (permission, tenant, caller identity) that the source model cannot see.

Add a new `BaseModel` layer only when it changes at least one of:

- Outward API contract
- Validation behavior (and the validation cannot be expressed via validators on the source model)
- Permission visibility
- Serialization behavior (and the serialization cannot be expressed via `ConfigDict` / `Field(...)` on the source model)
- Aggregation semantics
- Persistence representation

Prefer direct transformation from ORM or domain objects into outward response models. Do not stack generic
envelopes beyond `BaseResponse[PageData[T]]` — deeper nesting violates layering rules.

Bad — pointless intermediate model:

```python
class UserOrmSchema(BaseModel):
    id: int
    nickname: str

class UserResponse(BaseModel):
    id: int
    nickname: str

orm_schema = UserOrmSchema.model_validate(user)
return UserResponse.model_validate(orm_schema.model_dump())  # identical structure, zero value added
```

Good — direct transformation, envelope at the edge:

```python
class UserDetailData(BaseModel):
    """用户详情响应数据模型。"""

    user_id: int = Field(description="用户唯一标识,用于定位账户")
    nickname: str = Field(description="用户展示昵称,用于页面展示")

# In service:
return BaseResponse.ok(UserDetailData(user_id=user.id, nickname=user.nickname))
```

## Call-site rule: no pass-through re-wrap

The layering rule above governs *definitions*. The same principle applies at *call sites*: if a function's
return shape and semantics equal its callee's `BaseModel` return value, return the callee's result directly.
Do not reconstruct a structurally equivalent model. The only allowed wrap at an outward boundary is
`BaseResponse.ok(...)`, which adds `code` / `message` semantics.

Bad — caller re-wraps a structurally equivalent model:

```python
def build_user_detail(*, user_id: int) -> UserDetailData:
    user = repo.get_user(user_id=user_id)
    return UserDetailData(user_id=user.id, nickname=user.nickname)


def get_user_detail(*, user_id: int) -> UserDetailData:
    detail = build_user_detail(user_id=user_id)
    return UserDetailData(**detail.model_dump())   # identical shape, wasted construction
    # equivalent and equally bad:
    # return UserDetailData.model_validate(detail)
```

Good — return the callee's value directly; only wrap when the boundary adds semantics:

```python
def get_user_detail(*, user_id: int) -> UserDetailData:
    return build_user_detail(user_id=user_id)


@router.api_route(
    path="/users/{user_id}",
    methods=["GET"],
    response_model=BaseResponse[UserDetailData],
    tags=["users"],
    summary="获取用户详情",
)
async def read_user(*, user_id: int) -> BaseResponse[UserDetailData]:
    detail = build_user_detail(user_id=user_id)
    return BaseResponse.ok(detail)   # envelope adds code / message semantics
```

The rule applies symmetrically:

- If `AModel` and `BModel` are structurally equivalent, the definition itself is a mirror-model chain — collapse the duplicate.
- If only one model exists but a caller still re-constructs it from a callee's return value, the call site is a pass-through re-wrap — return the callee's value directly.

## Model with ClassVar and validator

```python
from typing import ClassVar, Literal, Self

from pydantic import BaseModel, Field, model_validator


class UserDetailData(BaseModel):
    """用户详情数据模型,包含类级别的静态查找表与跨字段一致性校验。"""

    STATUS_LABEL: ClassVar[dict[str, str]] = {
        "active": "正常",
        "inactive": "停用",
        "frozen": "冻结",
    }

    user_id: int = Field(description="用户唯一标识,用于定位账户")
    nickname: str = Field(description="用户展示昵称,用于页面展示")
    avatar_url: str | None = Field(default=None, description="用户头像地址,未设置时为空")
    status: Literal["active", "inactive", "frozen"] = Field(description="账户状态")
    frozen_reason: str | None = Field(default=None, description="冻结原因,仅冻结状态下应有值")

    @model_validator(mode="after")
    def validate_frozen_reason(self) -> Self:
        """校验冻结状态与冻结原因字段的一致性。"""
        if self.status == "frozen" and not self.frozen_reason:
            raise ValueError("冻结状态必须提供冻结原因")
        return self
```

## Anti-patterns

- Declaring `BaseModel` fields without `Field(...)`.
- Writing field descriptions in non-Chinese text or with non-business placeholders.
- Including `code` / `message` / `data` fields on business data models — those belong to `BaseResponse[T]`.
- Optional fields without explicit `default` or `default_factory`.
- Mirror-model chains (`UserOrmSchema` → `UserResponse` with identical fields).
- Chained `model_validate()` / `model_dump()` calls between structurally equivalent models.
- Pass-through re-wrap at call sites: `return AModel(**b.model_dump())` or `return AModel.model_validate(b)` where the caller's return shape and semantics already equal the callee's `BaseModel` return value — return the callee's value directly instead.
- Spinning up a new `BaseModel` layer to express a difference that could be set on the source model via `ConfigDict`, `Field(...)` options, or a validator (alias / `by_alias` / `extra` / `frozen` / `exclude` / serialization shape, etc.) — configure the source model instead.
- Class-level constants declared without `ClassVar[...]` wrapper — Pydantic will treat them as fields.

## Runnable counterparts

- `BaseResponse[T]` + `PageData[T]` with `ok` / `fail` factories — see `examples/base_response.py`.
- `UserDetailData` definition consumed by route and service code — see `examples/_shared.py`.
- `@computed_field` model example + setter anti-pattern comparison — see `examples/property_usage.py`.
