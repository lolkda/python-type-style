# FastAPI Style

## Rules

- Declare all routes with `@router.api_route(...)`. Do not use shorthand decorators like `@router.get(...)`.
- In every route decorator, explicitly set `path`, `methods`, `response_model` (or `response_class`), `tags`,
  and `summary`.
- `response_model` must be `BaseResponse[T]` or `BaseResponse[PageData[T]]`. Do not redefine envelope fields.
- Require docstrings for every route function with `用途`, `Args`, and `Returns` sections.
- Make every parameter source explicit: `Path`, `Query`, `Body`, `Form`, `File`, `Header`, `Cookie`, `Depends`,
  or `Security`. Never rely on FastAPI's implicit inference.
- Use `Annotated[...]` to attach source and validation metadata in signatures. Do not pass source objects as
  default values (e.g. `user_id: int = Path(...)` is wrong; use `user_id: Annotated[int, Path(...)]` or a
  module-level `UserId` alias).
- Return via `BaseResponse.ok(data)` for success paths and raise typed business exceptions for failure paths.
- When `response_class` is used (file download, streaming, HTML), annotate with the concrete response type and
  keep route metadata explicit. The unified envelope rule applies only to JSON contract endpoints.

## Error Handling

- Define typed business exception classes per bounded context. Do not raise raw `HTTPException` for business
  errors.
- Reserve `HTTPException` for protocol-level failures (auth, not found at routing level, method not allowed).
- Register global handlers for `RequestValidationError`, `HTTPException`, and each business exception. All
  handlers must emit `BaseResponse[None]` via `BaseResponse.fail(...)`.
- Business `code` space is decoupled from HTTP status. Define and document the project error code layout
  (e.g. module number × sub-code) in a single source of truth.

Bad:

```python
@router.get("/users/{user_id}")
async def get_user(user_id: int):
    user = await fetch_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="not found")
    return {"id": user_id}
```

Good:

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
        按用户标识查询详情,用户不存在时抛出业务异常,由全局处理器转换为统一外壳。

    Args:
        user_id: 路径参数,目标用户唯一标识。

    Returns:
        BaseResponse[UserDetailData]: 统一外壳包装的用户详情数据。
    """
    user = await fetch_user(user_id=user_id)
    if user is None:
        raise UserNotFoundError(user_id=user_id)
    return BaseResponse.ok(UserDetailData(user_id=user.id, nickname=user.nickname))
```

## Anti-patterns

- Shorthand decorators (`@router.get(...)`) lacking `response_model` / `tags` / `summary`.
- Implicit parameter sources — relying on FastAPI to infer between `Path`, `Query`, and `Body`.
- Passing source objects as default values: `user_id: int = Path(...)`. Use `Annotated[int, Path(...)]`.
- Raising raw `HTTPException` for business validation failures.
- Returning raw `dict` / `list` from a route handler.
- Repeating the same `Annotated[...]` chain across multiple route signatures — extract to a `type` alias.

## When To Deviate

- Streaming and file responses may use `response_class` (`StreamingResponse`, `FileResponse`). Route metadata
  completeness and docstring requirements remain mandatory. The unified envelope rule does not apply.
- Framework internals that enforce fixed callback signatures (e.g. middleware dispatch) may be exempt from
  keyword-only rules, but any wrapper method exposed to business code must keep keyword-only interfaces.

## Runnable counterparts

- Full FastAPI route with reusable `Annotated` aliases and `BaseResponse[T]` — see `examples/route.py`.
- Exception handler registration with `BaseResponse.fail(...)` — see `examples/base_response.py`.
