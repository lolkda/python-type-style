# Property Usage

This reference sets the rules for `@property`, `@cached_property`, `@computed_field`, and
`@hybrid_property` across the FastAPI / Pydantic v2 / SQLAlchemy 2 stack. The four primitives have
overlapping use cases but distinct contracts — pick the one matching the layer and intent rather
than defaulting to plain `@property` everywhere. Examples reference the shared anchor models
(`User`, `Post`, `UserDetailData`, `BaseResponse[T]`) in `examples/_shared.py`.

## Principles

- `@property` only for **cheap**, **side-effect-free**, **read-only** derivations over instance state.
- No DB queries, no network calls, no business exceptions inside a `@property` body — that is a method.
- Mutability of the host object determines `@cached_property` legality. Frozen / immutable hosts: OK.
  Mutable hosts: only with documented invalidation.
- Pydantic v2 contract awareness: `@property` is invisible to `model_dump()` / OpenAPI. Use
  `@computed_field` when the derived value must cross the API boundary.
- SQLAlchemy 2 contract awareness: `@property` is invisible to SQL. Use `@hybrid_property` when the
  derived value must appear in `select(...).where(...)`.
- Setters (`@xxx.setter`) on domain models are nearly always anti-patterns. Use validators (Pydantic),
  direct field assignment (ORM), or named methods (plain Python) instead.

## Plain `@property`

Use for cheap derivations that read like an attribute. Always annotate the return type explicitly.

Good — service-layer DTO with a computed display name:

```python
class UserSummary:
    """用户摘要数据,服务层内部使用,不跨外向边界。"""

    def __init__(self, *, user_id: int, nickname: str) -> None:
        """
        Args:
            user_id: 用户唯一标识。
            nickname: 用户展示昵称。
        """
        self._user_id = user_id
        self._nickname = nickname

    @property
    def display_name(self) -> str:
        """返回拼接展示名,纯字符串拼接无副作用。"""
        return f"{self._nickname}#{self._user_id}"
```

Bad — `@property` triggers a DB query:

```python
class UserService:
    @property
    def latest_post(self) -> Post | None:
        stmt = select(Post).where(Post.author_id == self._user_id).order_by(Post.id.desc())
        return self._session.scalar(stmt)
```

The caller reads `service.latest_post` expecting an attribute access, but each read fires a database
round trip. Expose this as an explicit method `get_latest_post(*, session: Session)` so the cost
matches the signature.

## `@cached_property`

`@cached_property` writes the first-call result into `instance.__dict__`, bypassing the descriptor on
subsequent reads. **Precondition: the host instance must be treated as immutable for the cached
value's lifetime.**

Good — derived value over immutable attributes:

```python
from functools import cached_property


class UserSummary:
    """用户摘要数据,构造后视为不可变。"""

    def __init__(self, *, user_id: int, nickname: str) -> None:
        """
        Args:
            user_id: 用户唯一标识。
            nickname: 用户展示昵称,允许含前后空白。
        """
        self._user_id = user_id
        self._nickname = nickname

    @cached_property
    def normalized_nickname(self) -> str:
        """归一化昵称(去前后空白 + 转小写),计算一次后冻结在 __dict__ 中。"""
        return self._nickname.strip().lower()
```

Bad — mutable ORM entity without an invalidation strategy:

```python
class User(Base):
    nickname: Mapped[str] = mapped_column(String(64), nullable=False)

    @cached_property
    def normalized_nickname(self) -> str:
        return self.nickname.strip().lower()
```

`session.refresh(user)` or `session.merge` may rewrite `nickname`, but `normalized_nickname` keeps
returning the stale cached value with no error. If caching is required on a mutable entity, document
an explicit invalidation step (for instance `instance.__dict__.pop("normalized_nickname", None)` at
every mutation point); otherwise prefer a method.

## `@computed_field` on Pydantic v2

A plain `@property` on a `BaseModel` does **not** appear in `model_dump()` or the OpenAPI schema. To
expose a derived value through the API contract, stack `@computed_field` above `@property`
(`@computed_field` outermost, `@property` innermost).

Good:

```python
from typing import Literal

from pydantic import BaseModel, Field, computed_field


class UserDetailDataWithLabel(BaseModel):
    """用户详情数据 + OpenAPI 暴露的状态标签。"""

    user_id: int = Field(description="用户唯一标识")
    nickname: str = Field(description="用户展示昵称")
    status: Literal["active", "inactive", "frozen"] = Field(description="账户状态")

    @computed_field(description="账户状态对应的中文标签,出现在 OpenAPI schema 中")
    @property
    def status_label(self) -> str:
        """根据状态返回中文标签,同时进入 model_dump() 和响应 schema。"""
        return {"active": "正常", "inactive": "停用", "frozen": "冻结"}[self.status]
```

`model_dump()` now includes `status_label`, and the OpenAPI schema lists it as a readOnly field so
frontend and downstream codegen pick it up automatically.

**Return type**: pyright infers from the `@property` annotation, but for large modules prefer
declaring it explicitly via `@computed_field(return_type=str)` so schema generation does not depend
on runtime introspection.

## `@hybrid_property` on SQLAlchemy 2

A `@property` defined on an ORM entity is accessible only on the Python side; it cannot appear in
`select(...).where(...)`. When the derived value must participate in SQL (filtering, ordering,
aggregation), use `sqlalchemy.ext.hybrid.hybrid_property` to register both a Python-side getter and a
SQL-side expression.

Good:

```python
from typing import Any

from sqlalchemy import func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column


class Article(Base):
    """文章实体,演示 @hybrid_property 的 Python + SQL 双签。"""

    __tablename__ = "article"

    title: Mapped[str] = mapped_column(String(255), nullable=False)

    @hybrid_property
    def title_length(self) -> int:
        """Python 侧:返回标题字符长度。"""
        return len(self.title)

    @title_length.expression
    @classmethod
    def title_length(cls) -> Any:
        """SQL 侧:返回 char_length(title) 表达式,可用于 select / where / order_by。"""
        return func.char_length(cls.title)


stmt = select(Article).where(Article.title_length > 50)
```

**Forbidden**: triggering a lazy-loaded relationship inside a `@property` or `@hybrid_property` body.
This conflicts with the `lazy="raise"` default and hides N+1 risk.

Bad — property triggers a relationship load:

```python
class User(Base):
    posts: Mapped[list["Post"]] = relationship(lazy="raise")

    @property
    def post_count(self) -> int:
        return len(self.posts)
```

Under `lazy="raise"` this raises directly; under `lazy="select"` it loads every post just to count
them. The correct approach is a SQL-level aggregate
(`select(func.count(Post.id)).where(Post.author_id == user_id)`) exposed through a repository
method.

## Setters

`@xxx.setter` on Pydantic / ORM / domain models is almost always an anti-pattern.

| Scenario | Wrong | Right |
|---|---|---|
| Pydantic cross-field consistency | Raise `ValueError` inside a setter | `@model_validator(mode="after")` returning `Self` |
| Pydantic single-field transform | Normalize inside a setter | `@field_validator("xxx")` |
| ORM entity | `@xxx.setter` + business validation | Direct assignment + explicit service-layer check |
| Domain state change | `entity.status = "frozen"` with hidden side effects | Named method `entity.freeze(*, reason: str)` |

Setters **look transparent** at the call site (`obj.x = y` reads as a field assignment) but they
hide state-change side effects and bypass Pydantic / SQLA contract validation. Readers cannot see
the risk from the assignment line alone.

## Typing `@property`

- The return type must be explicit: `def display_name(self) -> str:`.
- When the return type narrows based on other state, stack `@overload` on the getter:

```python
from typing import Literal, overload


class UserSummary:
    @overload
    @property
    def role_display(self) -> Literal["admin"]: ...

    @overload
    @property
    def role_display(self) -> str: ...

    @property
    def role_display(self) -> str:
        """根据内部状态返回展示字符串,管理员返回特定 literal。"""
        ...
```

`@property` + `@overload` is rare in practice; in most cases a single return type is sufficient.

## Anti-patterns

- `@property` body triggers a DB query, network call, or raises a business exception — the caller
  expects field access.
- `@cached_property` on a mutable ORM entity or mutable Pydantic model without an invalidation
  strategy.
- `@property` on a `BaseModel` when the value must appear in `model_dump()` / OpenAPI — use
  `@computed_field` paired with `@property`.
- `@property` on an ORM entity when the call site writes `select(Entity).where(Entity.derived > 0)`
  — use `@hybrid_property`.
- `@property` or `@hybrid_property` body that accesses a `lazy="raise"` relationship.
- `@xxx.setter` on a Pydantic / ORM domain model for business validation.
- Setter replacing a named state-change method (e.g. `entity.status = "frozen"` instead of
  `entity.freeze()`).
- Missing return type annotation on `@property`.
- `@computed_field` not paired with `@property` — Pydantic v2 requires the stack.

## When To Deviate

- When a third-party ABC / Protocol demands a setter interface, keep the setter as a thin wrapper
  that delegates to a named method internally.
- When an ORM column name conflicts with a Python keyword or framework attribute, a `@property`
  alias is acceptable (no side effects, no DB).
- Setters on test fakes / mocks are unconstrained — they are plain data carriers.

## Runnable counterparts

- Full demonstration of all four primitives + anti-pattern comparison — see
  `examples/property_usage.py`.
