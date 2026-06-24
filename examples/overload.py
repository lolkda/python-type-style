"""@overload 示例,演示 required 参数控制返回类型的双重签名。"""

from typing import Literal, overload

from sqlalchemy import select

from _shared import AsyncSession, User, UserNotFoundError


@overload
async def get_user(
    *, session: AsyncSession, user_id: int, required: Literal[True],
) -> User:
    """
    required=True 的重载签名,声明未命中时抛出异常且返回值非空。

    Args:
        session: 当前请求范围内的异步数据库会话。
        user_id: 目标用户唯一标识。
        required: 固定为 True,表示调用方要求用户必须存在。

    Returns:
        User: 命中的用户实体;未命中由实现函数抛出 UserNotFoundError。
    """
    ...


@overload
async def get_user(
    *, session: AsyncSession, user_id: int, required: Literal[False] = False,
) -> User | None:
    """
    required=False 的重载签名,声明未命中时返回空值。

    Args:
        session: 当前请求范围内的异步数据库会话。
        user_id: 目标用户唯一标识。
        required: 固定为 False 或省略,表示允许用户不存在。

    Returns:
        User | None: 命中的用户实体;未命中时返回空值。
    """
    ...


async def get_user(
    *, session: AsyncSession, user_id: int, required: bool = False,
) -> User | None:
    """
    按主键加载用户;required=True 时未命中抛出业务异常,否则返回空值。

    Args:
        session: 当前请求范围内的异步数据库会话。
        user_id: 目标用户唯一标识。
        required: 为真时未命中触发 UserNotFoundError,否则返回空值。

    Returns:
        User | None: 命中的用户实体;未命中且 required=False 时返回空值。
    """
    stmt = select(User).where(User.id == user_id)
    user = await session.scalar(stmt)
    if user is None and required:
        raise UserNotFoundError(user_id=user_id)
    return user


async def demo_narrowing(*, session: AsyncSession, user_id: int) -> str:
    """
    演示调用方根据 required 参数自动收窄类型,无需手动空值判断。

    Args:
        session: 当前请求范围内的异步数据库会话。
        user_id: 目标用户主键。

    Returns:
        str: required=True 调用返回非空用户的昵称。
    """
    user = await get_user(session=session, user_id=user_id, required=True)
    return user.nickname


__all__ = [
    "demo_narrowing",
    "get_user",
]
