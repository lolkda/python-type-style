"""ParamSpec / Concatenate 示例,演示 PEP 695 装饰器签名透传与首位参数注入。"""

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Concatenate

from _shared import AsyncSession


def with_logging[**P, R](
    fn: Callable[P, Awaitable[R]],
) -> Callable[P, Awaitable[R]]:
    """
    异步函数装饰器,记录调用入口与异常并透传签名,保留类型推断。

    Args:
        fn: 被装饰的异步函数,任意签名与返回类型。

    Returns:
        Callable[P, Awaitable[R]]: 包装后的异步函数,签名与原函数完全一致。
    """

    @wraps(fn)
    async def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        """
        实际包装实现,记录日志后调用原函数。

        Args:
            args: 被装饰函数的原始位置参数,由 ParamSpec 保持类型。
            kwargs: 被装饰函数的原始关键字参数,由 ParamSpec 保持类型。

        Returns:
            R: 原始异步函数返回的业务结果。
        """
        return await fn(*args, **kwargs)

    return wrapped


def transactional[**P, R](
    fn: Callable[Concatenate[AsyncSession, P], Awaitable[R]],
) -> Callable[P, Awaitable[R]]:
    """
    服务方法事务包装,自动注入异步会话并提交事务,对外契约移除首位参数。

    Args:
        fn: 期望首位参数为 AsyncSession 的异步业务方法。

    Returns:
        Callable[P, Awaitable[R]]: 移除首位参数后的对外调用契约。
    """

    @wraps(fn)
    async def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        """
        实际包装实现,构造会话后委派调用并提交事务。

        Args:
            args: 对外调用方传入的原始位置参数。
            kwargs: 对外调用方传入的原始关键字参数。

        Returns:
            R: 被事务包装的业务方法返回值。
        """
        session = await _open_session()
        try:
            result = await fn(session, *args, **kwargs)
            await session.commit()
            return result
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    return wrapped


async def _open_session() -> AsyncSession:
    """
    占位会话工厂,真实工程应注入 async_sessionmaker 构造的会话。

    Args:
        无。

    Returns:
        AsyncSession: 待业务使用的异步数据库会话。
    """
    raise NotImplementedError("connect to real async_sessionmaker in production code")


@with_logging
async def fetch_nickname(*, user_id: int) -> str:
    """
    演示被 with_logging 装饰的异步函数,签名透传后类型推断保留。

    Args:
        user_id: 目标用户主键。

    Returns:
        str: 占位昵称,真实工程应查询数据库。
    """
    _ = user_id
    return "示例用户"


@transactional
async def rename_user(
    session: AsyncSession, *, user_id: int, new_nickname: str,
) -> None:
    """
    演示被 transactional 装饰的服务方法,首位会话由装饰器注入。

    Args:
        session: 装饰器注入的异步会话,业务侧透明使用。
        user_id: 目标用户主键。
        new_nickname: 新昵称。

    Returns:
        None: 副作用为更新用户昵称,无返回值。
    """
    _ = session, user_id, new_nickname


__all__ = [
    "fetch_nickname",
    "rename_user",
    "transactional",
    "with_logging",
]
