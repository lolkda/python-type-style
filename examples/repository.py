"""通用 ORM 仓储与具体读取示例,展示 PEP 695 受限泛型在持久化层的标准写法。"""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from _shared import AsyncSession, Base, User


class Repository[EntityT: Base]:
    """通用 ORM 仓储,泛型受 Base 约束以保证仅接受已声明的映射实体。"""

    def __init__(self, *, entity_type: type[EntityT]) -> None:
        """
        初始化通用仓储,绑定后续查询使用的 ORM 实体类型。

        Args:
            entity_type: 仓储管理的 ORM 实体类,用于构造查询语句。

        Returns:
            None: 构造函数无返回值,副作用为保存实体类型。
        """
        self._entity_type = entity_type

    async def get_by_id(
        self, *, session: AsyncSession, entity_id: int,
    ) -> EntityT | None:
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


def get_user_by_id(*, session: Session, user_id: int) -> User | None:
    """
    按主键查询同步会话下的用户实体。

    Args:
        session: 当前事务范围内的同步数据库会话。
        user_id: 用户唯一标识,用于定位数据库记录。

    Returns:
        User | None: 命中的用户实体;未命中时返回空值。
    """
    stmt = select(User).where(User.id == user_id)
    return session.scalar(stmt)


async def list_users_with_posts(*, session: AsyncSession) -> list[User]:
    """
    异步会话下加载用户列表并预加载其帖子,避免外向响应组装阶段触发 N+1 查询。

    Args:
        session: 当前请求范围内的异步数据库会话。

    Returns:
        list[User]: 含帖子数据的用户实体列表,按主键升序。
    """
    stmt = (
        select(User)
        .options(selectinload(User.posts))
        .order_by(User.id)
    )
    result = await session.scalars(stmt)
    return list(result)


__all__ = [
    "Repository",
    "get_user_by_id",
    "list_users_with_posts",
]
