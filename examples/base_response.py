"""统一响应外壳异常处理器示例,展示 BaseResponse[T] 与三类异常的全局协同。"""

from typing import Final

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from _shared import BaseResponse, UserNotFoundError

_HTTP_PROTOCOL_BUSINESS_CODE: Final[dict[int, int]] = {
    401: 90401,
    403: 90403,
    404: 90404,
    405: 90405,
    500: 90500,
}
_DEFAULT_PROTOCOL_BUSINESS_CODE: Final[int] = 90000


async def user_not_found_handler(
    request: Request, exc: UserNotFoundError,
) -> JSONResponse:
    """
    将用户未找到业务异常转换为统一响应外壳。

    Args:
        request: 当前请求对象,保留以供日志或链路追踪扩展使用。
        exc: 触发的用户未找到异常实例。

    Returns:
        JSONResponse: 携带业务码 40401 的统一外壳响应。
    """
    _ = request
    body = BaseResponse.fail(code=40401, message=f"用户 {exc.user_id} 不存在")
    return JSONResponse(status_code=404, content=body.model_dump())


async def validation_exception_handler(
    request: Request, exc: RequestValidationError,
) -> JSONResponse:
    """
    将参数校验失败转换为统一响应外壳。

    Args:
        request: 当前请求对象,保留以供日志或链路追踪扩展使用。
        exc: Pydantic 抛出的请求参数校验异常。

    Returns:
        JSONResponse: 携带业务码 40000 的统一外壳响应。
    """
    _ = request, exc
    body = BaseResponse.fail(code=40000, message="请求参数校验失败")
    return JSONResponse(status_code=422, content=body.model_dump())


async def http_exception_handler(
    request: Request, exc: HTTPException,
) -> JSONResponse:
    """
    将协议层 HTTPException 转换为统一响应外壳。

    Args:
        request: 当前请求对象,保留以供日志或链路追踪扩展使用。
        exc: 触发的 HTTPException 实例,仅用于鉴权或路由级协议错误。

    Returns:
        JSONResponse: 携带协议层业务码的统一外壳响应;业务码独立于 HTTP 状态码,
            HTTP 状态码仍按原值返回。
    """
    _ = request
    business_code = _HTTP_PROTOCOL_BUSINESS_CODE.get(
        exc.status_code, _DEFAULT_PROTOCOL_BUSINESS_CODE,
    )
    body = BaseResponse.fail(code=business_code, message=str(exc.detail))
    return JSONResponse(status_code=exc.status_code, content=body.model_dump())


def register_exception_handlers(*, app: FastAPI) -> None:
    """
    注册全局异常处理器,统一将三类异常序列化为 BaseResponse 外壳。

    Args:
        app: 当前 FastAPI 应用实例。

    Returns:
        None: 无返回值,副作用为完成处理器注册。
    """
    app.add_exception_handler(UserNotFoundError, user_not_found_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)


__all__ = [
    "http_exception_handler",
    "register_exception_handlers",
    "user_not_found_handler",
    "validation_exception_handler",
]
