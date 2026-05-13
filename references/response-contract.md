# Unified Response Contract

All outward API responses must be wrapped by a single generic envelope `BaseResponse[T]`. Do not redefine
`code` / `message` / `data` per route. One envelope handles success, business failure, validation failure, and
protocol failure paths uniformly.

## Rules

- Define exactly one `BaseResponse[T]` envelope per project. Do not fork it per module.
- Business data models (e.g. `UserDetailData`) must stay pure: no `code`, no `message`, no protocol fields.
- Use `BaseResponse[T]` as the route `response_model` and return annotation. Instantiate with
  `BaseResponse.ok(data)` for success and `BaseResponse.fail(code=..., message=...)` for business failure.
- For list endpoints, compose with `PageData[T]`: `response_model=BaseResponse[PageData[UserDetailData]]`.
- Global exception handlers (`RequestValidationError`, `HTTPException`, business exceptions) must serialize
  through the same envelope. Do not introduce a separate `ErrorResponse` model.
- `data: T | None` with `default=None`. Failure responses, 204-style empty responses, and not-found cases all
  produce `data=None`. Forcing `T` non-null breaks the unified envelope.
- Do not stack nested envelope generics beyond two layers. `BaseResponse[PageData[UserDetailData]]` is the
  ceiling; deeper composition violates Model Layering Rules.
- The business `code` space is decoupled from HTTP status. HTTP status reflects protocol-level outcome;
  business `code` reflects business outcome. A 200 HTTP response may carry a non-zero business `code`.

## Envelope definition

```python
from pydantic import BaseModel, ConfigDict, Field


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
    """分页数据载荷,与 BaseResponse 组合使用。"""

    items: list[T] = Field(description="当前页数据项列表")
    total: int = Field(description="符合查询条件的总记录数")
    page: int = Field(description="当前页码,从 1 开始计数")
    size: int = Field(description="每页大小,与请求参数保持一致")
```

## Business data stays pure

Bad — protocol fields leak into business model:

```python
class UserDetailResponse(BaseModel):
    code: int = Field(default=0, description="业务状态码")
    message: str = Field(default="成功", description="业务处理结果说明")
    data: UserDetailData = Field(description="用户详情数据")
```

Good — business model holds only business fields; envelope wraps it:

```python
class UserDetailData(BaseModel):
    """用户详情数据模型。"""

    user_id: int = Field(description="用户唯一标识,用于定位账户")
    nickname: str = Field(description="用户展示昵称,用于页面展示")
    avatar_url: str | None = Field(default=None, description="用户头像地址,未设置时为空")
```

## Route using BaseResponse[T]

```python
@router.api_route(
    path="/users/{user_id}",
    methods=["GET"],
    response_model=BaseResponse[UserDetailData],
    tags=["用户中心"],
    summary="查询用户详情",
)
async def get_user_detail(*, user_id: UserId) -> BaseResponse[UserDetailData]:
    """
    用途:
        按用户标识查询详情信息并返回统一结构数据。

    Args:
        user_id: 路径参数,目标用户唯一标识。

    Returns:
        BaseResponse[UserDetailData]: 统一外壳包装的用户详情数据。
    """
    data = UserDetailData(user_id=user_id, nickname="示例用户", avatar_url=None)
    return BaseResponse.ok(data)


@router.api_route(
    path="/users",
    methods=["GET"],
    response_model=BaseResponse[PageData[UserDetailData]],
    tags=["用户中心"],
    summary="分页查询用户列表",
)
async def list_users(
    *,
    page: PageNum = 1,
    size: PageSize = 20,
) -> BaseResponse[PageData[UserDetailData]]:
    """分页查询用户列表并返回统一外壳包装的分页载荷。"""
    items: list[UserDetailData] = []
    total = 0
    return BaseResponse.ok(PageData(items=items, total=total, page=page, size=size))
```

## Exception handlers share the same envelope

```python
from typing import Final

_HTTP_PROTOCOL_BUSINESS_CODE: Final[dict[int, int]] = {
    401: 90401,
    403: 90403,
    404: 90404,
    405: 90405,
    500: 90500,
}
_DEFAULT_PROTOCOL_BUSINESS_CODE: Final[int] = 90000


async def user_not_found_handler(request: Request, exc: UserNotFoundError) -> JSONResponse:
    """将用户未找到业务异常转换为统一响应外壳。"""
    body = BaseResponse.fail(code=40401, message=f"用户 {exc.user_id} 不存在")
    return JSONResponse(status_code=404, content=body.model_dump())


async def validation_exception_handler(
    request: Request, exc: RequestValidationError,
) -> JSONResponse:
    """将参数校验失败转换为统一响应外壳。"""
    body = BaseResponse.fail(code=40000, message="请求参数校验失败")
    return JSONResponse(status_code=422, content=body.model_dump())


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """将协议层 HTTPException 转换为统一响应外壳。业务码独立于 HTTP 状态码。"""
    business_code = _HTTP_PROTOCOL_BUSINESS_CODE.get(
        exc.status_code, _DEFAULT_PROTOCOL_BUSINESS_CODE,
    )
    body = BaseResponse.fail(code=business_code, message=str(exc.detail))
    return JSONResponse(status_code=exc.status_code, content=body.model_dump())


def register_exception_handlers(*, app: FastAPI) -> None:
    """注册全局异常处理器,统一将异常序列化为 BaseResponse 外壳。"""
    app.add_exception_handler(UserNotFoundError, user_not_found_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
```

## OpenAPI schema naming

Pydantic v2 emits generic instantiations as schemas like `BaseResponse_UserDetailData_`. Downstream codegen
tools (openapi-typescript, openapi-generator) recognize this form. Override
`__get_pydantic_json_schema__` only if a project-wide naming convention requires it; default naming is usually
acceptable.

## Anti-patterns

- Defining a per-endpoint `XxxResponse` model that duplicates `code` / `message` / `data` — the unified envelope
  is load-bearing for documentation, error handling, and downstream codegen.
- Introducing a separate `ErrorResponse` model — failure paths use `BaseResponse[None]` from the same envelope.
- Stacking nested generics beyond `BaseResponse[PageData[T]]`.
- Tying business `code` to HTTP status one-to-one — they reflect different concerns and evolve independently.

## Runnable counterparts

- Envelope definition with factories + exception handlers — see `examples/base_response.py`.
- Routes consuming `BaseResponse[T]` and `BaseResponse[PageData[T]]` — see `examples/route.py`.
