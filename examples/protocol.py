"""Protocol 解耦示例,演示 UserReader 协议、SQLA 实现与内存态测试桩。"""

from typing import Protocol

from sqlalchemy import select

from _shared import AsyncSession, User, UserDetailData, UserNotFoundError


class UserReader(Protocol):
    """用户读取依赖契约,任何能按主键加载用户实体的对象均满足。"""

    async def get_by_id(
        self, *, session: AsyncSession, user_id: int,
    ) -> User | None:
        """
        协议方法签名,实现方必须按主键返回用户实体或空值。

        Args:
            session: 当前请求范围内的异步数据库会话。
            user_id: 目标用户主键。

        Returns:
            User | None: 命中的用户实体;未命中时返回空值。
        """
        ...


class SqlaUserReader:
    """基于 SQLAlchemy AsyncSession 的真实仓储实现,满足 UserReader 协议。"""

    async def get_by_id(
        self, *, session: AsyncSession, user_id: int,
    ) -> User | None:
        """
        通过 select 语句按主键加载用户实体。

        Args:
            session: 当前请求范围内的异步数据库会话。
            user_id: 目标用户主键。

        Returns:
            User | None: 命中的用户实体;未命中时返回空值。
        """
        stmt = select(User).where(User.id == user_id)
        return await session.scalar(stmt)


class InMemoryUserReader:
    """测试用内存态用户读取实现,无需数据库即可满足 UserReader 协议。"""

    def __init__(self, *, users: dict[int, User]) -> None:
        """
        Args:
            users: 以主键为键的预置用户字典,供测试断言使用。
        """
        self._users = users

    async def get_by_id(
        self, *, session: AsyncSession, user_id: int,
    ) -> User | None:
        """
        从预置字典中查找用户,异步签名以匹配 UserReader 协议。

        Args:
            session: 协议要求的会话参数,内存实现忽略不使用。
            user_id: 目标用户主键。

        Returns:
            User | None: 字典中匹配的用户;未命中时返回空值。
        """
        _ = session
        return self._users.get(user_id)


async def get_user_detail_service(
    *,
    session: AsyncSession,
    reader: UserReader,
    user_id: int,
) -> UserDetailData:
    """
    构造用户详情数据,依赖 UserReader 协议而非具体仓储,便于测试替换。

    Args:
        session: 当前请求范围内的异步数据库会话。
        reader: 用户读取依赖,满足 UserReader 协议的任意实现。
        user_id: 目标用户唯一标识。

    Returns:
        UserDetailData: 用户详情业务数据。
    """
    user = await reader.get_by_id(session=session, user_id=user_id)
    if user is None:
        raise UserNotFoundError(user_id=user_id)
    return UserDetailData(
        user_id=user.id, nickname=user.nickname, avatar_url=user.avatar_url,
    )


__all__ = [
    "InMemoryUserReader",
    "SqlaUserReader",
    "UserReader",
    "get_user_detail_service",
]
