"""property 家族 (@property / @cached_property / @computed_field / @hybrid_property) 示例。

复用 _shared.py 中的 User / Post / UserDetailData / BaseResponse 作为锚点;Article 为新增演示实体,
专门承载 @hybrid_property 演示(给 Post 添加会引入单表继承的不必要复杂度)。每节末尾给出反例对照,
说明 property 家族选错时的具体后果。
"""

from functools import cached_property
from typing import Any, Literal

from pydantic import BaseModel, Field, computed_field
from sqlalchemy import String, func, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column

from _shared import AsyncSession, Base


class UserSummary:
    """用户摘要数据,服务层内部使用,不跨外向边界。

    构造后被视为不可变 — 字段一旦设置不再修改,这是 @cached_property 在此合法的前提。
    """

    def __init__(self, *, user_id: int, nickname: str) -> None:
        """
        Args:
            user_id: 用户唯一标识。
            nickname: 用户展示昵称,允许含前后空白。
        """
        self._user_id = user_id
        self._nickname = nickname

    @property
    def display_name(self) -> str:
        """
        返回拼接展示名,纯字符串拼接无副作用。

        Returns:
            str: 形如 "alice#42" 的展示字符串。
        """
        return f"{self._nickname.strip()}#{self._user_id}"

    @cached_property
    def normalized_nickname(self) -> str:
        """
        归一化昵称(去前后空白 + 转小写),计算一次后冻结在 __dict__ 中。

        合法前提:实例的 _nickname 在缓存生命周期内不变;UserSummary 被设计为不可变,故满足。

        Returns:
            str: 归一化后的昵称字符串。
        """
        return self._nickname.strip().lower()


class UserDetailDataWithLabel(BaseModel):
    """用户详情数据 + OpenAPI 暴露的中文状态标签,演示 @computed_field。

    继承自 UserDetailData 在示例代码中会增加锚点依赖,此处直接平铺定义业务字段以聚焦
    @computed_field 主题。
    """

    user_id: int = Field(description="用户唯一标识,用于定位账户")
    nickname: str = Field(description="用户展示昵称,用于页面展示")
    status: Literal["active", "inactive", "frozen"] = Field(description="账户状态")

    @computed_field(description="账户状态对应的中文标签,出现在 OpenAPI schema 中")
    @property
    def status_label(self) -> str:
        """
        根据 status 字段返回中文标签;同时进入 model_dump() 和响应 schema。

        Returns:
            str: 状态对应的中文短语。
        """
        return {"active": "正常", "inactive": "停用", "frozen": "冻结"}[self.status]


class Article(Base):
    """文章 ORM 实体,演示 @hybrid_property 的 Python 侧 + SQL 侧双签。"""

    __tablename__ = "article"

    title: Mapped[str] = mapped_column(String(255), nullable=False)

    @hybrid_property
    def title_length(self) -> int:
        """
        Python 侧:返回标题字符长度,等价于 len(self.title)。

        Returns:
            int: 标题字符长度。
        """
        return len(self.title)

    @title_length.expression
    @classmethod
    def title_length(cls) -> Any:
        """
        SQL 侧:返回 char_length(title) 表达式,可用于 select / where / order_by。

        Returns:
            Any: SQLAlchemy ColumnElement,代表 SQL 函数表达式。
        """
        return func.char_length(cls.title)


async def find_long_articles(*, session: AsyncSession, threshold: int) -> list[Article]:
    """
    演示 @hybrid_property 在 SQL 子句中的可查询性。

    Args:
        session: 当前请求范围内的异步数据库会话。
        threshold: 标题长度下限,严格大于此值的记录会被返回。

    Returns:
        list[Article]: 标题长度超过阈值的文章列表。
    """
    stmt = select(Article).where(Article.title_length > threshold)
    result = await session.scalars(stmt)
    return list(result)


# ----------------------------------------------------------------------
# Anti-pattern reference (comment-only, not executable) — listing common
# misuses of the property family for quick cross-checking during review.
# ----------------------------------------------------------------------
#
# BAD-1: @property triggers a DB query
#
#     class UserService:
#         @property
#         def latest_post(self) -> Post | None:
#             return self._session.scalar(select(Post).where(...))
#
# Problem: caller expects field access; each read fires a database round trip.
# Fix: expose as `async def get_latest_post(*, session) -> Post | None`.
#
# BAD-2: @property on BaseModel expected to appear in OpenAPI
#
#     class UserResp(BaseModel):
#         status: Literal["active", "frozen"] = Field(...)
#
#         @property
#         def status_label(self) -> str:
#             return {"active": "正常"}[self.status]
#
# Problem: `model_dump()` omits `status_label`; OpenAPI schema lacks the field;
# frontend / codegen cannot see it.
# Fix: stack `@computed_field` over `@property` (see UserDetailDataWithLabel).
#
# BAD-3: @property on an ORM entity used in select.where
#
#     class Article(Base):
#         @property
#         def title_length(self) -> int:
#             return len(self.title)
#
#     select(Article).where(Article.title_length > 50)  # TypeError / wrong behavior
#
# Problem: `Article.title_length` on the class is a plain descriptor; the SQL
# layer cannot interpret it.
# Fix: dual-sign with `@hybrid_property` + `@title_length.expression` (see Article).
#
# BAD-4: @cached_property on a mutable entity
#
#     class User(Base):
#         @cached_property
#         def normalized_nickname(self) -> str:
#             return self.nickname.strip().lower()
#
# Problem: after `session.refresh` / `merge` rewrites `nickname`, the cached value
# diverges from the source without raising.
# Fix: avoid `@cached_property` here, or explicitly
# `user.__dict__.pop("normalized_nickname", None)` at every mutation point.
#
# BAD-5: setter used for business validation
#
#     class User(Base):
#         @property
#         def status(self) -> str: ...
#
#         @status.setter
#         def status(self, value: str) -> None:
#             if value not in {"active", "frozen"}:
#                 raise ValueError(...)
#             self._status = value
#
# Problem: the assignment line hides validation side effects and bypasses the
# Pydantic validator mechanism.
# Fix: in Pydantic use `@field_validator`; in ORM use an explicit service-layer
# method such as `freeze_user(...)`.
# ----------------------------------------------------------------------


__all__ = [
    "Article",
    "UserDetailDataWithLabel",
    "UserSummary",
    "find_long_articles",
]
