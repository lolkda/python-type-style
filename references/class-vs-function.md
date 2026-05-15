# Class vs Function

## Default

Default to module-level functions. A class is justified only when at least one of the conditions below
holds. If none of them holds, the class is structural overhead — flatten it to functions.

The deciding question is not "does this look object-oriented?" — it is "does this code own state, identity,
invariants, polymorphism, lifecycle, or runtime context that a function cannot represent honestly?"

Declarative-shape classes — Pydantic `BaseModel`, `pydantic_settings.BaseSettings`, SQLAlchemy ORM models,
`dataclass` — always stay class regardless of these rules. They use class syntax to declare schema, not as
behavior encapsulation.

## Three Families of Class

The conditions below cluster into three families. They overlap, but the family lens helps explain *why* a
given class exists:

- **Entity** — the class represents a thing in the domain. Identity is primary; state and behavior are
  secondary. Driven mainly by condition 3. Examples: `User`, `Order`, `Task`.
- **Context** — the class bundles a runtime scope or manages a lifecycle that callers must respect.
  Driven mainly by conditions 2 and 7. Examples: `RequestContext`, `CrawlerContext`, `FileLock`.
- **Capability** — the class provides a behavior backed by state, polymorphism, invariants, concurrency,
  or cache ownership. Driven mainly by conditions 1, 4, 5, 6, 8, 9. Examples: `HttpClient`, `Cart`,
  `BankAccount`, `StorageBackend`, `RateLimiter`, `FtpSession`.

A single class can sit in more than one family (a `Session` is both Entity and Capability). The family
label is descriptive, not prescriptive — the operative rule is still "any condition yes → class".

## When To Use Class

### 1. Long-lived state

The instance carries state across calls (cache, session, connection pool, cookie jar, in-memory index, or
any cache that owns its own invalidation policy). Threading the state through every function call would
lose the encapsulation and make multiple independent instances impossible.

```python
class HttpClient:
    """长连接 HTTP 客户端,持有连接池与共享 cookie。"""

    def __init__(self, *, base_url: str) -> None:
        self._client = httpx.AsyncClient(base_url=base_url)
        self._cookies: dict[str, str] = {}

    async def get(self, *, path: str) -> httpx.Response:
        return await self._client.get(path, cookies=self._cookies)
```

### 2. Lifecycle

The object has an `open → use → close` flow that callers must manage, typically via context-manager
protocols (`__enter__/__exit__`, `__aenter__/__aexit__`).

```python
class FileLock:
    """文件锁,需要显式获取与释放。"""

    async def __aenter__(self) -> Self:
        await self._acquire()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self._release()
```

### 3. Identity

The object represents a system entity. Equality, identity in the system, references-by-id, and lifecycle
in the domain all suggest entity status — even when the entity carries little behavior.

Examples: `User`, `Order`, `Session`, `Task`, `Connection`, `RequestContext`.

These typically end up as Pydantic / ORM / dataclass declarations, overlapping with declarative-shape
classes. The entity-ness is the reason they exist.

### 4. Behavior aggregated around one internal dataset

Multiple operations all read or mutate the same internal data. Splitting them into module-level functions
would force the dataset to be threaded through every signature, breaking the locality of the operations.

```python
class Cart:
    """购物车聚合,封装条目集合上的统一操作。"""

    def __init__(self) -> None:
        self._items: list[CartItem] = []

    def add_item(self, *, item: CartItem) -> None: ...
    def remove_item(self, *, item_id: str) -> None: ...
    def total_price(self) -> Decimal: ...
```

Counter-example — independent operations, no shared internal data:

```python
def send_sms(*, phone: str, body: str) -> None: ...
def hash_password(*, raw: str) -> str: ...
def parse_email(*, raw: str) -> EmailAddress: ...
```

These three have no common state. Putting them on `class SmsHashEmailUtils:` is namespace grouping (see
anti-patterns).

### 5. Invariants

State plus rules belong together. If callers can violate an invariant by touching attributes directly,
the invariant must move into methods that enforce it.

```python
class BankAccount:
    """账户,余额非负不变量在内部强制。"""

    def __init__(self, *, opening_balance: Decimal) -> None:
        self._balance = opening_balance

    def withdraw(self, *, amount: Decimal) -> None:
        if amount > self._balance:
            raise InsufficientBalanceError
        self._balance -= amount
```

State-machine transitions are the same shape: legal transitions live on the class, not in caller code.

### 6. Polymorphism

Multiple swappable implementations exist behind one interface. The interface is usually a `Protocol` or
abstract base; concrete implementations are classes that satisfy it.

```python
class StorageBackend(Protocol):
    async def put(self, *, key: str, blob: bytes) -> None: ...
    async def get(self, *, key: str) -> bytes: ...


class S3Storage:
    async def put(self, *, key: str, blob: bytes) -> None: ...
    async def get(self, *, key: str) -> bytes: ...


class LocalFsStorage:
    async def put(self, *, key: str, blob: bytes) -> None: ...
    async def get(self, *, key: str) -> bytes: ...
```

A single function with `if backend == "s3": ... elif backend == "local": ...` is the wrong shape — the
branching belongs at construction time, not in every call.

### 7. Runtime context

A single execution scope binds several related values that downstream code reads. The class exists so the
bundle can be passed as one argument and helpers can read its fields without each function re-deriving
them.

```python
class RequestContext:
    """单次请求上下文,绑定追踪、用户、会话、locale。"""

    trace_id: str
    current_user: User | None
    locale: str
    db_session: AsyncSession
```

### 8. Concurrency ownership

The class owns synchronization primitives or coordination state — locks, queues, semaphores, rate
limiters, dedup windows, retry controllers. State plus concurrency rules form one inseparable system
semantic; pulling them apart leaks invariants across call sites and makes multiple independent instances
impossible.

```python
class RateLimiter:
    """异步限流器,持有计数窗口与互斥锁。"""

    def __init__(self, *, max_per_second: int) -> None:
        self._max = max_per_second
        self._tokens = max_per_second
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            ...
```

A module-level `_lock` plus free functions can replicate the behavior, but loses the "this lock belongs
to this resource" coupling and forecloses multiple independent limiters in the same process.

### 9. Protocol / sequenced operations

Multiple operations must occur in a strict order; calling them out of sequence is a bug. The class
enforces the sequence as an internal state machine, turning what would be implicit temporal coupling
between free functions into an explicit, checkable transition graph.

```python
class FtpSession:
    """FTP 会话,按 connect → authenticate → transfer → quit 顺序执行。"""

    def __init__(self, *, host: str) -> None:
        self._host = host
        self._state: Literal["new", "connected", "authenticated", "closed"] = "new"

    async def connect(self) -> None:
        if self._state != "new":
            raise InvalidStateError
        ...
        self._state = "connected"

    async def authenticate(self, *, user: str, password: str) -> None:
        if self._state != "connected":
            raise InvalidStateError
        ...
        self._state = "authenticated"
```

Free functions `connect()`, `authenticate()`, `send()` cannot enforce order — every caller must remember
the protocol. The class makes the protocol part of the type.

## When NOT To Use Class

### Namespace grouping (anti-pattern)

```python
class JsonUtils:
    @staticmethod
    def loads(raw: str) -> JsonValue: ...

    @staticmethod
    def dumps(value: JsonValue) -> str: ...
```

Wrong. Python modules are namespaces. Move both functions to a module:

```python
# json_utils.py
def loads(*, raw: str) -> JsonValue: ...
def dumps(*, value: JsonValue) -> str: ...
```

The same rule applies to any class whose body is only `@staticmethod` / `@classmethod` with no shared
state — it is a function bag wearing class clothes.

### Pure transforms

Input → output, no shared state, no identity, no invariant. Function is the honest shape.

```python
def parse_email(*, raw: str) -> EmailAddress: ...
def hash_password(*, raw: str) -> str: ...
def slugify(*, text: str) -> str: ...
```

### Framework-prescribed function shapes

FastAPI route handlers, dependency callables, Pydantic validators, decorator factories — the framework
expects a function. Wrapping these in a class without one of the seven justifications above creates a
shape the framework cannot use directly.

## Decision Procedure

For any new piece of code, ask in order:

1. Does it hold state across calls?
2. Does it have a lifecycle the caller must manage?
3. Does it represent a system entity (identity)?
4. Do multiple operations all act on one shared internal dataset?
5. Does it own invariants that must stay valid across mutations?
6. Does it have multiple swappable implementations behind one interface?
7. Does it bundle a runtime context shared by downstream code?
8. Does it own synchronization primitives or coordination state?
9. Does it enforce a strict order between multiple operations?

Any **yes** → class. All **no** → module-level function. Declarative-shape (`BaseModel` / ORM / `dataclass`
/ `BaseSettings`) is class regardless.

## Anti-patterns

- `class XxxUtils:` / `class XxxHelpers:` whose body is only `@staticmethod` / `@classmethod` with no
  shared state — Python modules are namespaces; flatten to module-level functions.
- Class wrapping a single pure transform (`class Slugifier: def slugify(...)`) — write a function.
- "Service" class that holds no state, has no swappable implementations, and owns no invariants — collapse
  to module functions or merge with the actual stateful collaborator.
- Class purely to "look OOP" or to mirror Java / C# conventions — Python is multi-paradigm; pick the shape
  that matches the responsibility.
- FastAPI route handler, Pydantic validator, or dependency callable wrapped in a class without one of the
  seven class-justifying conditions — the framework expects a function.
