"""共享桩定义,集中放置所有示例文件复用的 ORM、Pydantic、业务异常锚点。"""

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import ForeignKey, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """ORM 声明基类,提供所有持久化实体共享的主键列。"""

    id: Mapped[int] = mapped_column(primary_key=True)


class User(Base):
    """用户持久化实体,聚合昵称、头像与其发布的帖子集合。"""

    __tablename__ = "user"

    nickname: Mapped[str] = mapped_column(String(64), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    posts: Mapped[list["Post"]] = relationship(
        "Post", back_populates="author", lazy="raise",
    )


class Post(Base):
    """帖子持久化实体,通过外键归属到一个用户。"""

    __tablename__ = "post"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    author: Mapped["User"] = relationship(
        "User", back_populates="posts", lazy="raise",
    )


class UserDetailData(BaseModel):
    """用户详情响应数据模型,外向接口业务载荷,不含协议字段。"""

    user_id: int = Field(description="用户唯一标识,用于定位账户")
    nickname: str = Field(description="用户展示昵称,用于页面展示")
    avatar_url: str | None = Field(default=None, description="用户头像地址,未设置时为空")


class BaseResponse[T](BaseModel):
    """统一接口响应外壳,所有外向 API 必须使用此模型包装数据。"""

    model_config = ConfigDict(arbitrary_types_allowed=False)

    code: int = Field(default=0, description="业务状态码,0 表示成功,其余表示业务错误")
    message: str = Field(default="成功", description="业务处理结果说明,面向调用方展示")
    data: T | None = Field(default=None, description="接口返回的业务数据,失败或空结果时为空")

    @classmethod
    def ok(cls, data: T) -> "BaseResponse[T]":
        """
        构造业务成功响应。

        Args:
            data: 业务数据载荷,类型由调用方在泛型参数中显式指定。

        Returns:
            BaseResponse[T]: 业务成功的统一响应对象,code 为 0。
        """
        return cls(code=0, message="成功", data=data)

    @classmethod
    def fail(cls, *, code: int, message: str) -> "BaseResponse[None]":
        """
        构造业务失败响应,data 留空。

        Args:
            code: 非零业务错误码,需与项目错误码空间约定保持一致。
            message: 面向调用方的错误说明文本。

        Returns:
            BaseResponse[None]: 业务失败的统一响应对象,data 为空。
        """
        return BaseResponse[None](code=code, message=message, data=None)


class PageData[T](BaseModel):
    """分页数据载荷,与 BaseResponse 组合使用形成列表接口响应外壳。"""

    items: list[T] = Field(description="当前页数据项列表")
    total: int = Field(description="符合查询条件的总记录数")
    page: int = Field(description="当前页码,从 1 开始计数")
    size: int = Field(description="每页大小,与请求参数保持一致")


class UserNotFoundError(Exception):
    """用户业务异常,表示按标识查询用户不存在,由全局异常处理器转换为统一外壳。"""

    def __init__(self, *, user_id: int) -> None:
        """
        Args:
            user_id: 未找到的用户主键,供处理器构造错误消息使用。
        """
        super().__init__(f"user {user_id} not found")
        self.user_id = user_id


__all__ = [
    "AsyncSession",
    "Base",
    "BaseResponse",
    "PageData",
    "Post",
    "User",
    "UserDetailData",
    "UserNotFoundError",
]
