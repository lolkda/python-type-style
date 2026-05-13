# Typing Usage

This reference sets the rules for `typing` and `collections.abc` primitives across all FastAPI / Pydantic /
SQLAlchemy 2 code. Examples reference the shared anchor models (`User`, `UserDetailData`, `BaseResponse[T]`,
`PageData[T]`, `AsyncSession`, `Base`) so the rules read against real call sites. Target Python 3.12+; PEP 695
generic and `type` syntax is the default.

## Principles

- Always annotate. Avoid `Any` except at hard interop boundaries; convert to a strict type immediately after entry.
- Prefer built-in `list[T]`, `dict[K, V]`, `tuple[T, ...]`, `set[T]`, `frozenset[T]` over `typing.List` / `Dict`
  / `Tuple` / `Set` / `FrozenSet`.
- Prefer `collections.abc` for `Sequence` / `Mapping` / `Iterable` / `Iterator` / `AsyncIterator` / `Callable` /
  `Awaitable`.
- Prefer `X | Y` and `X | None` over `Union[X, Y]` / `Optional[X]`.
- Prefer PEP 695 syntax: `class Foo[T]:`, `def func[T](...)`, `type Alias = ...`.
- Use `Annotated[...]` for context-bearing metadata. Extract repeated chains to module-level aliases.
- Do **not** enable `from __future__ import annotations` project-wide. Pydantic v2 and FastAPI rely on runtime
  type introspection; use string annotations or `TYPE_CHECKING` surgically when needed.

## Built-in generics and `collections.abc`

- `list[int]`, not `List[int]`.
- `dict[str, User]`, not `Dict[str, User]`.
- `tuple[int, str]` for fixed shapes; `tuple[int, ...]` for variable-length homogeneous.
- Import `Sequence`, `Mapping`, `Iterable`, `Iterator`, `AsyncIterator`, `Callable`, `Awaitable` from
  `collections.abc`.

**Sequence vs list rule:**

- Function parameters that only iterate or index → `Sequence[T]` (permissive, accepts `list`, `tuple`, custom
  sequences).
- Return types and parameters that mutate → `list[T]` (concrete, callers can mutate).
- Repository return types use concrete `list[T]` since downstream code commonly appends or sorts.

Bad:

```python
from typing import Dict, List, Optional, Sequence


def index_users(users: List[User]) -> Dict[int, User]:
    return {u.id: u for u in users}


def find_admin(users: Sequence[User]) -> Optional[User]:
    ...
```

Good:

```python
from collections.abc import Sequence


def index_users(users: Sequence[User]) -> dict[int, User]:
    """根据用户实体序列构造按主键索引的字典。"""
    return {user.id: user for user in users}


def find_admin(users: Sequence[User]) -> User | None:
    """从用户序列中查找首个管理员用户。"""
    return next((user for user in users if user.is_admin), None)
```

## Union types and `X | None`

- `X | None` over `Optional[X]`.
- `X | Y` over `Union[X, Y]`.
- Discriminated unions: combine `Literal` tag fields with Pydantic `Field(discriminator="kind")`.

Example — webhook event with a discriminator:

```python
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class UserCreatedEvent(BaseModel):
    """用户创建事件载荷。"""

    kind: Literal["user_created"] = Field(description="事件类型标识")
    user_id: int = Field(description="新创建用户的唯一标识")


class UserUpdatedEvent(BaseModel):
    """用户更新事件载荷。"""

    kind: Literal["user_updated"] = Field(description="事件类型标识")
    user_id: int = Field(description="被更新用户的唯一标识")
    fields: list[str] = Field(description="本次更新涉及的字段名列表")


type WebhookEvent = Annotated[
    UserCreatedEvent | UserUpdatedEvent,
    Field(discriminator="kind"),
]
```

## `Literal` vs `Enum`

- `Literal` for narrow, local finite sets (status flags, mode switches, discriminator tags).
- `StrEnum` / `IntEnum` (3.12 native) when the value set is shared across modules and carries business semantics.
- Pydantic `Literal` fields render as enum schemas in OpenAPI automatically.

Good — `Literal` for a status field internal to a single model:

```python
class UserDetailData(BaseModel):
    """用户详情数据模型。"""

    user_id: int = Field(description="用户唯一标识,用于定位账户")
    nickname: str = Field(description="用户展示昵称,用于页面展示")
    status: Literal["active", "inactive", "frozen"] = Field(description="账户状态")
```

Good — `StrEnum` when status is referenced across services, routes, and repositories:

```python
from enum import StrEnum


class UserStatus(StrEnum):
    """用户账户状态枚举,跨服务共享。"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    FROZEN = "frozen"
```

## `Annotated` and reusable type aliases

`Annotated[...]` carries source and validation metadata into FastAPI parameter signatures and Pydantic fields.
Repeated `Annotated` chains across routes must be extracted to module-level aliases via PEP 695 `type`. Routes
then consume the alias directly, eliminating drift across handlers.

```python
from typing import Annotated

from fastapi import Path, Query
from pydantic import Field


type UserId = Annotated[int, Path(gt=0, description="用户唯一标识")]
type PageNum = Annotated[int, Query(ge=1, description="页码,从 1 开始")]
type PageSize = Annotated[int, Query(ge=1, le=100, description="每页大小,上限 100")]
type NonEmptyStr = Annotated[str, Field(min_length=1, description="非空字符串字段")]
```

## `TypeVar` and `Generic[T]` — PEP 695 syntax

PEP 695 is the default form for new generic classes and functions on 3.12+:

```python
class BaseResponse[T](BaseModel):
    """统一接口响应外壳。"""

    code: int = Field(default=0, description="业务状态码,0 表示成功")
    message: str = Field(default="成功", description="业务处理结果说明")
    data: T | None = Field(default=None, description="接口返回的业务数据")


class PageData[T](BaseModel):
    """分页数据载荷。"""

    items: list[T] = Field(description="当前页数据项列表")
    total: int = Field(description="符合查询条件的总记录数")
    page: int = Field(description="当前页码,从 1 开始")
    size: int = Field(description="每页大小")
```

Bounded type parameters tie a generic repository to the ORM declarative base:

```python
class Repository[EntityT: Base]:
    """通用 ORM 仓储,泛型受 Base 约束以保证只接受映射实体。"""

    def __init__(self, *, entity_type: type[EntityT]) -> None:
        """
        Args:
            entity_type: 仓储管理的 ORM 实体类,用于构造查询语句。
        """
        self._entity_type = entity_type

    async def get_by_id(self, *, session: AsyncSession, entity_id: int) -> EntityT | None:
        """
        按主键加载实体。

        Args:
            session: 当前请求范围内的异步数据库会话。
            entity_id: 目标实体主键值。

        Returns:
            EntityT | None: 命中的实体;未命中时返回空值。
        """
        stmt = select(self._entity_type).where(self._entity_type.id == entity_id)
        return await session.scalar(stmt)

    async def list_all(self, *, session: AsyncSession) -> list[EntityT]:
        """
        加载当前实体类的全部记录。

        Args:
            session: 当前请求范围内的异步数据库会话。

        Returns:
            list[EntityT]: 全部记录列表,顺序未指定。
        """
        stmt = select(self._entity_type)
        result = await session.scalars(stmt)
        return list(result)
```

## `Protocol` for DI and testing

Use `Protocol` to declare what a service depends on. Concrete implementations need not inherit — duck typing is
sufficient. This is the recommended way to decouple service layer from concrete repositories and to enable
in-memory test fakes without inheritance hierarchies.

```python
from typing import Protocol


class UserReader(Protocol):
    """用户读取依赖契约,描述任何能按主键加载用户实体的对象。"""

    async def get_by_id(self, *, session: AsyncSession, user_id: int) -> User | None: ...


async def get_user_detail_service(
    *,
    session: AsyncSession,
    reader: UserReader,
    user_id: int,
) -> UserDetailData:
    """构造用户详情数据,依赖 UserReader 协议而非具体仓储。"""
    user = await reader.get_by_id(session=session, user_id=user_id)
    if user is None:
        raise UserNotFoundError(user_id=user_id)
    return UserDetailData(user_id=user.id, nickname=user.nickname, status="active")
```

Rules:

- `@runtime_checkable` only when callers need `isinstance(x, UserReader)` checks. Most projects never need it.
- Protocol vs ABC: Protocol when you do not own all implementations or want test fakes without inheritance.
  ABC when you need shared base behavior across implementations.

## `TypedDict` — narrow boundary use

`TypedDict` is static-only — it does not validate at runtime. Use it at interop boundaries where a dict shape
is required by an external contract. Do **not** substitute `TypedDict` for `BaseModel` at outward API boundaries.

```python
from typing import NotRequired, Required, TypedDict, Unpack


class WebhookPayloadTD(TypedDict):
    """外部 webhook 投递的原始字典形状,用于在 Pydantic 校验前显式标注。"""

    kind: Required[str]
    user_id: Required[int]
    fields: NotRequired[list[str]]


def receive_webhook(payload: WebhookPayloadTD) -> WebhookEvent:
    """校验并解析外部 webhook 字典为强类型事件模型。"""
    return WebhookEvent.model_validate(payload)
```

`**kwargs` typing via PEP 692 `Unpack`:

```python
class CreateUserKwargs(TypedDict):
    """用户创建可选参数集合。"""

    nickname: Required[str]
    avatar_url: NotRequired[str | None]


def build_user(**kwargs: Unpack[CreateUserKwargs]) -> User:
    """通过类型化关键字参数构造用户实体。"""
    return User(**kwargs)
```

## `Self` for fluent, builder, and Pydantic validator return

`Self` (3.11+) annotates methods that return an instance of their own class. Replaces the older
`T = TypeVar("T", bound="Foo")` pattern.

```python
from typing import Self

from pydantic import model_validator


class UserDetailData(BaseModel):
    """用户详情数据模型,包含跨字段一致性校验。"""

    user_id: int = Field(description="用户唯一标识,用于定位账户")
    nickname: str = Field(description="用户展示昵称,用于页面展示")
    status: Literal["active", "inactive", "frozen"] = Field(description="账户状态")
    frozen_reason: str | None = Field(default=None, description="冻结原因,仅冻结状态下应有值")

    @model_validator(mode="after")
    def validate_frozen_reason(self) -> Self:
        """校验冻结状态与冻结原因字段的一致性。"""
        if self.status == "frozen" and not self.frozen_reason:
            raise ValueError("冻结状态必须提供冻结原因")
        return self
```

## `@overload` for varying return types

Use `@overload` when a function's return type depends on argument value or shape. Only the overload stubs are
visible to callers; the implementation keeps a single permissive signature.

**Stub function bodies are `...` with no docstring.** SKILL.md's "every function must have Args /
Returns docstrings" rule is waived for `@overload` stubs — stubs serve only as signature
placeholders, and the full business docstring stays on the implementation. `Protocol` method stubs
are contract definitions read by consumers, so their docstrings remain mandatory (see the
`Protocol` section below).

```python
from typing import Literal, overload


@overload
async def get_user(
    *, session: AsyncSession, user_id: int, required: Literal[True],
) -> User: ...


@overload
async def get_user(
    *, session: AsyncSession, user_id: int, required: Literal[False] = False,
) -> User | None: ...


async def get_user(
    *, session: AsyncSession, user_id: int, required: bool = False,
) -> User | None:
    """按主键加载用户;required=True 时未命中抛出业务异常,否则返回 None。"""
    stmt = select(User).where(User.id == user_id)
    user = await session.scalar(stmt)
    if user is None and required:
        raise UserNotFoundError(user_id=user_id)
    return user
```

## `TYPE_CHECKING` for circular imports

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .order_service import OrderService


async def link_order_to_user(*, service: "OrderService", user_id: int) -> None:
    """将订单服务挂载到指定用户,通过 TYPE_CHECKING 避免循环导入。"""
    ...
```

**Pydantic gotcha**: if a model field references a `TYPE_CHECKING`-only import, Pydantic v2 cannot resolve the
forward reference at class build time. Call `Model.model_rebuild()` once the referenced model is importable, or
restructure modules to avoid the cycle entirely. Prefer restructuring over heavy `TYPE_CHECKING` use.

## `Final` and `ClassVar`

`Final` marks names that should not be reassigned. `ClassVar` marks class-level attributes that are **not**
Pydantic fields. Pydantic v2 collects every annotated class attribute as a field by default; wrap non-field
attributes in `ClassVar[...]` to opt out.

```python
from typing import ClassVar, Final

MAX_PAGE_SIZE: Final[int] = 100
DEFAULT_PAGE_SIZE: Final[int] = 20


class UserDetailData(BaseModel):
    """用户详情数据模型,包含类级别的静态查找表。"""

    STATUS_LABEL: ClassVar[dict[str, str]] = {
        "active": "正常",
        "inactive": "停用",
        "frozen": "冻结",
    }

    user_id: int = Field(description="用户唯一标识,用于定位账户")
    nickname: str = Field(description="用户展示昵称,用于页面展示")
    status: Literal["active", "inactive", "frozen"] = Field(description="账户状态")
```

Without `ClassVar`, Pydantic would treat `STATUS_LABEL` as a serialized field and emit it into the OpenAPI
schema.

## `cast` — escape hatch rules

`cast(T, value)` is a static-only escape hatch with zero runtime effect. Use only when:

- A third-party API is untyped (returns `Any`) but you have verified the actual shape.
- The type checker cannot follow a narrowing you can prove safe from surrounding context.

Do **not** use `cast` as a substitute for `isinstance`, `TypeIs`, or runtime `assert` when runtime validation is
required.

```python
import json
from typing import cast


def parse_webhook_body(*, raw: bytes) -> WebhookEvent:
    """将原始字节解析为强类型 webhook 事件。"""
    payload = cast(WebhookPayloadTD, json.loads(raw))
    return WebhookEvent.model_validate(payload)
```

## `NewType` for nominal IDs

`NewType` creates a nominal alias over a primitive — preventing accidental mixing of semantically distinct IDs
at the type level. Runtime stays the original type.

```python
from typing import NewType

UserIdInt = NewType("UserIdInt", int)
OrderIdInt = NewType("OrderIdInt", int)


def transfer_credits(
    *, from_user: UserIdInt, to_user: UserIdInt, order_id: OrderIdInt,
) -> None:
    """根据订单在两个用户之间转移积分,主键类型互不兼容防止参数颠倒。"""
    ...
```

Pydantic field caveat: `NewType` is not directly recognized by Pydantic for field declarations. For Pydantic
models, prefer `Annotated[int, ...]` aliases. Reserve `NewType` for service-layer function signatures.

## `TypeGuard` and `TypeIs`

User-defined predicates that narrow types. On Python 3.12 target, use `TypeGuard`; migrate to `TypeIs` (3.13+)
when upgrading — `TypeIs` narrows both true and false branches symmetrically.

```python
from typing import TypeGuard


class AdminUser(User):
    """管理员用户实体,继承用户基类。"""


def is_admin(user: User) -> TypeGuard[AdminUser]:
    """判断用户是否为管理员;返回真值时将类型收窄为 AdminUser。"""
    return getattr(user, "is_admin", False) is True
```

## `Never` and `assert_never` for exhaustiveness

`Never` annotates functions that always raise. `assert_never` enforces exhaustive `match` over `Literal` or
`Enum` unions — pyright / mypy flag missing cases at the call site.

```python
from typing import Literal, Never, assert_never


def raise_business_error(*, code: int, message: str) -> Never:
    """抛出业务异常并标注永不返回。"""
    raise BusinessError(code=code, message=message)


def status_label(*, status: Literal["active", "inactive", "frozen"]) -> str:
    """根据账户状态返回中文标签,缺漏分支触发静态检查报错。"""
    match status:
        case "active":
            return "正常"
        case "inactive":
            return "停用"
        case "frozen":
            return "冻结"
        case _ as unreachable:
            assert_never(unreachable)
```

## `ParamSpec` and `Concatenate` for typed decorators

Use PEP 695 syntax on 3.12+:

```python
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Concatenate


def with_logging[**P, R](fn: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
    """异步函数装饰器,记录调用入口与异常,签名透传以保留类型推断。"""

    @wraps(fn)
    async def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        return await fn(*args, **kwargs)

    return wrapped


def transactional[**P, R](
    fn: Callable[Concatenate[AsyncSession, P], Awaitable[R]],
) -> Callable[P, Awaitable[R]]:
    """服务方法事务包装,自动注入异步会话并提交事务。"""
    ...
```

**Keyword-only exemption**: a business method decorated by `Concatenate[X, P]` must declare its
first parameter positionally (`async def rename_user(session: AsyncSession, *, user_id: int, ...)`);
otherwise the `Concatenate` type does not match. This is an inherent constraint of `ParamSpec` +
`Concatenate`; the keyword-only rule is waived for the decorator-injected first parameter only,
while all other business parameters remain keyword-only.

## PEP 695 `type` statement

Three options for naming types, each with a distinct purpose:

- `type Alias = ...` — transparent rename (3.12+). Use for `Annotated[...]` composition, union shortcuts, and
  any case where the alias is purely cosmetic.
- `NewType("Alias", int)` — nominal alias. Use to prevent mixing semantically distinct primitives.
- `Alias: TypeAlias = ...` — legacy form (3.10 / 3.11). Do not use on 3.12+.

```python
type UserId = Annotated[int, Path(gt=0, description="用户唯一标识")]
InvoiceIdInt = NewType("InvoiceIdInt", int)
type AccountStatus = Literal["active", "inactive", "frozen"]
```

## `@final` and `@override`

`@final` on a class prevents subclassing; on a method prevents override. `@override` (3.12+) asserts a method
overrides a parent — pyright / mypy flag accidental typo overrides.

```python
from typing import final, override


class BaseUserService:
    """用户服务基类。"""

    async def get_detail(self, *, session: AsyncSession, user_id: int) -> UserDetailData:
        """子类必须重写以提供具体加载逻辑。"""
        raise NotImplementedError


@final
class StandardUserService(BaseUserService):
    """标准用户服务实现,不再允许进一步派生。"""

    @override
    async def get_detail(self, *, session: AsyncSession, user_id: int) -> UserDetailData:
        """按主键加载用户详情数据。"""
        ...
```

## Typing anti-patterns

- Using `Any` for sloppy typing.
- Bare `dict` / `list` without parameters in new code.
- Importing `typing.List` / `Dict` / `Tuple` / `Set` / `FrozenSet`.
- Importing `Sequence` / `Mapping` / `Iterable` from `typing` — use `collections.abc`.
- Enabling `from __future__ import annotations` project-wide in a Pydantic / FastAPI codebase.
- Using `cast` for runtime narrowing instead of `isinstance` / `TypeIs`.
- `def f(x: list = None)` — use `x: list[T] | None = None` (or a default factory at the call site).
- Stacking `Optional[Optional[X]]` — just `X | None`.
- Substituting `TypedDict` for `BaseModel` at outward API boundaries.
- Declaring class-level constants on Pydantic v2 models without `ClassVar[...]` wrapper.
- Re-declaring the same `Annotated[...]` chain across multiple route signatures — extract to a `type` alias.

## Tooling

- `pyright` strict mode (or `mypy --strict`) on the entire project. The rules above are designed to be
  machine-verifiable.
- `ruff` rule families to enforce mechanically:
  - `UP` (pyupgrade): collapses `List` → `list`, `Optional[X]` → `X | None`, etc.
  - `TCH`: moves type-only imports under `TYPE_CHECKING`.
  - `ANN`: requires annotations on every function signature.
  - `FA`: enforces project future-annotations policy (default: off).
- Pydantic v2 ships native pyright / mypy integration. No plugin required.

## Runnable counterparts

- Generic repository with `class Repository[EntityT: Base]:` — see `examples/repository.py`.
- `Protocol`-based dependency injection with in-memory test fake — see `examples/protocol.py`.
- `@overload` narrowing pattern — see `examples/overload.py`.
- `ParamSpec` / `Concatenate` typed decorators — see `examples/paramspec.py`.
