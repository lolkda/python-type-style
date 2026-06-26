# Class vs Function

Default to module-level functions. A class is justified only when at least one checklist item below is true.
If every item is false, the class is structural overhead; flatten it to functions.

Declarative-shape classes (`BaseModel`, `BaseSettings`, SQLAlchemy ORM models, `dataclass`) stay classes because
class syntax declares schema rather than behavior.

This only decides class syntax vs module function. It does not allow `dataclass` to replace Pydantic
`BaseModel` for stable request/config/domain contracts.

## Linear Flow Rule

For scripts, examples, one-off utilities, and small CLI tools, keep a simple straight-line workflow in one
readable top-level function when the logic is used once.

Keep setup -> call -> print/result -> wait/retry together when there is no meaningful branch or reusable
abstraction. Do not extract a helper merely to name every step.

When rewriting existing Python, do not preserve the old function layout by default. First audit every top-level
function and method that is introduced or preserved. A function must be one of:

1. An entrypoint such as `main`.
2. A framework callback or protocol-required hook.
3. A function used by two or more call sites.
4. A non-trivial parser, validator, transformer, retry/error boundary, or external-boundary adapter.
5. A cohesive Pydantic request/config/domain model method that exposes a real caller goal.

Inline any one-use helper that does not pass this audit before adding docstrings, type annotations, or Pydantic
models. The docstring requirement applies only after a function has earned its place.

Extract a function only when it has at least one of:

1. It is used by two or more call sites.
2. It contains meaningful branching, validation, parsing, retry, or error handling.
3. It adapts a protocol, serialization, framework, or external I/O boundary.
4. It encodes a project invariant that would be easy to misuse inline.
5. It makes a large block materially easier to test or review.

A thin helper is a helper whose body only delegates to one obvious operation, returns one simple expression, or
forwards arguments without adding validation, branching, boundary adaptation, invariants, or test value. Inline
thin helpers for simple ID/token/timestamp/random/default generation, waiting/sleeping, logging/printing/result
display, a single SDK/client/framework call with no retry or error policy, simple constructors, simple copies,
simple attribute/property access, simple `model_dump()` / `json.dumps()` / string formatting / alias conversion,
or one obvious return expression.

The docstring requirement is not a reason to extract or preserve a helper. If the helper fails the audit, inline
it and document the containing function instead.

## Class Checklist

Promote code to a class only when it has at least one of:

1. **Long-lived state**: cache, session, pool, cookie jar, in-memory index, or invalidation policy carried across calls.
2. **Lifecycle**: caller must respect `open -> use -> close`, `__enter__/__exit__`, or `__aenter__/__aexit__`.
3. **Identity**: object represents a system entity such as `User`, `Order`, `Task`, `Session`, or `Connection`.
4. **Shared dataset behavior**: several operations read or mutate the same internal dataset.
5. **Invariants**: state can become invalid unless mutations pass through methods that enforce rules.
6. **Polymorphism**: multiple swappable implementations sit behind one interface or `Protocol`.
7. **Runtime context**: one execution scope bundles several values consumed downstream.
8. **Concurrency ownership**: object owns locks, queues, semaphores, rate limiters, retry state, or dedup windows.
9. **Sequenced protocol**: operations must occur in a strict order and the class enforces that state machine.

Any **yes** means class is allowed. All **no** means module-level function.

## Forbidden Shapes

- `class XxxUtils:` / `class XxxHelpers:` with only `@staticmethod` or `@classmethod` and no shared state.
- A class wrapping one pure transform, such as `class Slugifier: def slugify(...)`.
- A "service" class with no state, no lifecycle, no swappable implementation, and no invariant.
- A class created only to mirror Java / C# style.
- FastAPI route handlers, dependency callables, Pydantic validators, or decorator factories wrapped in a class
  without one of the checklist justifications.
- Thin one-use functions that wrap a single obvious standard-library, framework, or SDK call without adding
  validation, boundary adaptation, retry, invariants, or readability.
- A script whose main flow is harder to follow because each linear step is moved into a separate helper.
- Preserving one-use thin helpers during a rewrite only because the input file already had them.
- Giving a thin helper a Chinese Args/Returns docstring and treating that docstring as evidence that the helper
  should remain.

## Default Rewrite

When no checklist item applies, move behavior to module functions:

```python
def parse_email(*, raw: str) -> EmailAddress: ...
def hash_password(*, raw: str) -> str: ...
def slugify(*, text: str) -> str: ...
```

Use modules as namespaces; do not create function bags wearing class syntax.
