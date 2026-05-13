# SQLAlchemy 2 Style

## Rules

- Prefer SQLAlchemy 2.x native style: `DeclarativeBase`, `Mapped[...]`, `mapped_column(...)`.
- Do not introduce legacy `Query`-centric ORM code. Prefer `select(...)` with `Session.scalar(...)`,
  `Session.scalars(...)`, or `Session.execute(...)`.
- Every mapped attribute must use `Mapped[...]`. Do not use untyped `Column(...)` declarations in new code.
- Repository, DAO, and unit-of-work methods must keep keyword-only signatures.
- One ORM model per persistence representation. Do not create mirror ORM wrappers with no added semantics.
- Keep persistence concerns in ORM models; keep outward API contracts in `BaseModel` schemas wrapped by
  `BaseResponse[T]`. Do not expose ORM entities directly as outward response contracts.
- Declare relationship loading strategy explicitly. Do not rely on hidden lazy-loading in outward API assembly.
- Use `sessionmaker(...)` for sync sessions; `async_sessionmaker(...)` for async sessions.
- Do not share a `Session` or `AsyncSession` instance across unrelated request scopes.
- Manage sessions with context managers. Keep transaction boundaries explicit.
- In async code, use `AsyncSession` with async engine and async driver consistently.
- Use `selectinload`, `joinedload`, or other explicit loader options when assembling related entities.
- Keep SQLAlchemy statements composable. Build filters and eager-loading through statement composition.
- Repository return types must be explicit: ORM entity, `list[Entity]`, scalar value, or result type.
- Do not leak raw database rows or ad hoc tuple contracts into service or router layers.
- Use `@hybrid_property` (with both Python-side getter and SQL-side expression) when the derived attribute must appear in `select(...).where(...)`; use `@property` for Python-only access that does not touch lazy-loaded relationships. See [property-usage.md](property-usage.md).

## ORM model with relationship

```python
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """ORM 声明基类,提供所有持久化实体共享的主键列。"""

    id: Mapped[int] = mapped_column(primary_key=True)


class User(Base):
    """用户持久化实体。"""

    __tablename__ = "user"

    nickname: Mapped[str] = mapped_column(String(64), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    posts: Mapped[list["Post"]] = relationship("Post", back_populates="author", lazy="raise")


class Post(Base):
    """帖子持久化实体。"""

    __tablename__ = "post"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    author: Mapped["User"] = relationship("User", back_populates="posts", lazy="raise")
```

`lazy="raise"` is recommended as the default. It forces all relationship loading to be explicit at the query
site, preventing hidden N+1 queries in outward API assembly paths.

## Async repository with selectinload

Bad:

```python
async def list_users(db):
    return db.query(User).all()
```

Good:

```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession


async def list_users_with_posts(*, session: AsyncSession) -> list[User]:
    """
    查询用户列表并预加载其帖子数据。

    Args:
        session: 当前请求范围内的异步数据库会话。

    Returns:
        list[User]: 含帖子数据的用户实体列表。
    """
    stmt = (
        select(User)
        .options(selectinload(User.posts))
        .order_by(User.id)
    )
    result = await session.scalars(stmt)
    return list(result)
```

## Sync repository

Bad:

```python
def get_user(db, user_id):
    return db.query(User).filter(User.id == user_id).first()
```

Good:

```python
from sqlalchemy import select
from sqlalchemy.orm import Session


def get_user_by_id(*, session: Session, user_id: int) -> User | None:
    """
    按用户标识查询用户实体。

    Args:
        session: 当前事务范围内的同步数据库会话。
        user_id: 用户唯一标识。

    Returns:
        User | None: 命中的用户实体;未命中时返回空值。
    """
    stmt = select(User).where(User.id == user_id)
    return session.scalar(stmt)
```

## Anti-patterns

- Using legacy `session.query(...)` style in new SQLAlchemy 2 code.
- Declaring ORM columns without `Mapped[...]` type annotations.
- Sharing one `Session` or `AsyncSession` across unrelated request or task scopes.
- Mixing synchronous ORM access into asynchronous request flows.
- Returning anonymous tuple or row shapes from repository methods when a named ORM entity or explicit outward
  contract is available.
- Exposing ORM entities directly as outward response models (use `BaseModel` schemas wrapped by `BaseResponse[T]`).

## When To Deviate

- Legacy modules already built around SQLAlchemy 1.x `Query` style may keep existing code until the module is
  actively refactored. New repository code in those modules should still use SQLAlchemy 2 statement style.
- Small migration adapters may temporarily bridge old and new session APIs during a multi-step migration, but
  all newly written repository code must use SQLAlchemy 2 statement style.
- ORM model constructors may follow SQLAlchemy native mapped class behavior (positional keyword arguments per
  mapped column) even when business-layer functions are keyword-only.

## Runnable counterparts

- Generic `Repository[EntityT: Base]`, sync + async user accessors, eager-loading with `selectinload` — see
  `examples/repository.py`.
- `@hybrid_property` dual-signature example (Python + SQL) — see `examples/property_usage.py`.
