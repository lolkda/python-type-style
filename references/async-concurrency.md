# Async and Concurrency

## Rules

- Never block the event loop with synchronous I/O inside async functions.
- Prefer async database and HTTP clients (`AsyncSession`, `httpx.AsyncClient`) in async routes and services.
- Propagate async boundaries consistently through service layers. Do not call sync repository methods from
  async service methods.
- Avoid implicit threadpool fallbacks (`run_in_executor`) unless explicitly documented and justified.

## Examples

Bad — blocking I/O inside an async route:

```python
import requests

@router.api_route(path="/proxy", methods=["GET"], ...)
async def proxy_request() -> BaseResponse[ProxyData]:
    # requests.get blocks the event loop
    resp = requests.get("https://external-api.example.com/data")
    return BaseResponse.ok(ProxyData(payload=resp.json()))
```

Good — async HTTP client:

```python
import httpx

@router.api_route(path="/proxy", methods=["GET"], ...)
async def proxy_request() -> BaseResponse[ProxyData]:
    """
    用途:
        通过异步 HTTP 客户端代理请求外部数据接口。

    Args:
        无。

    Returns:
        BaseResponse[ProxyData]: 外部接口返回数据的统一外壳包装。
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://external-api.example.com/data")
        resp.raise_for_status()
    return BaseResponse.ok(ProxyData(payload=resp.json()))
```

Bad — sync ORM inside async service:

```python
async def get_user_service(*, user_id: int) -> UserSummary:
    # session.execute(...) without await blocks the event loop
    stmt = select(User).where(User.id == user_id)
    user = session.execute(stmt).scalar_one_or_none()
    ...
```

Good:

```python
async def get_user_service(*, session: AsyncSession, user_id: int) -> UserSummary:
    stmt = select(User).where(User.id == user_id)
    user = await session.scalar(stmt)
    ...
```

## Anti-patterns

- Using `requests`, `time.sleep`, blocking `open()`, or any sync I/O inside `async def`.
- Calling `session.execute(...)` without `await` on an `AsyncSession`.
- Mixing sync `Session` with async route handlers.
- Wrapping sync code in `run_in_executor` as a default — diagnose root cause first.
- Sharing one `AsyncSession` across concurrent tasks or unrelated request scopes.
