# Class vs Function

Default to module-level functions. A class is justified only when at least one checklist item below is true.
If every item is false, the class is structural overhead; flatten it to functions.

Declarative-shape classes (`BaseModel`, `BaseSettings`, SQLAlchemy ORM models, `dataclass`) stay classes because
class syntax declares schema rather than behavior.

This only decides class syntax vs module function. It does not allow `dataclass` to replace Pydantic
`BaseModel` for stable request/config/domain contracts.

## Existence Before Quality

Existence is the first gate. Decide whether a function or model should exist before you give it a docstring, a
type, or a Pydantic field. A fully documented, fully typed, keyword-only definition that should not exist is
still a violation; decoration never offsets an existence failure.

Write the flow inline first. Start every script, handler, or workflow as one straight-line body — setup, the one
external call, result handling, wait/retry — and do not pre-split it into named steps. Promote a span out of
that body only by one of two independent warrants.

**Single-use — the inlining counterfactual.** Paste the span back into its sole caller and read the result.

- If the caller reads the same or *easier*, the span was only "what happens next" — a call, a wait, a log, a
  construct, a serialize, a forward. Keep it inline.
- Promote it only when inlining makes the caller *harder* to follow, i.e. the span owns a real decision, a
  validation, an invariant, a retry/error boundary, or a protocol/serialization transform.

This test is symmetric, and the symmetry is the point. It rejects the thin helper — extracting a span that
inlines neutrally or more cleanly — and it equally rejects the god function — refusing to extract a span whose
inlined form genuinely obscures the caller. A long `main()` is not automatically correct: a span inside it that
owns a real decision, validation, or transform has already earned its own function. "Keep it inline" means keep
*trivial continuations* inline; it never means bury real behavior in a wall of code.

**Reuse — real shared behavior.** A span used at two or more call sites earns a function only when its body
carries policy, validation, error/retry handling, protocol adaptation, a non-trivial transform, or a project
invariant. Call count alone never earns it. A body that still only generates an ID/token/timestamp/default,
sleeps, logs, makes one external call, constructs, forwards, or serializes stays inline even when reused; lift a
shared value to a constant rather than mint a thin helper to produce it.

**External-boundary adapters.** An adapter is a warrant only when it *transforms* (maps a domain model to or
from the external shape) or *absorbs* (handles the boundary's errors, retries, or policy). A function that only
forwards one SDK/client call, renames its arguments, or wraps a single `run_sync` / `send` / `create` is not an
adapter — inline it.

**Count and batch parameters — behavior, not name.** A `count` / `size` / `batch` / `repeat` parameter and the
`for _ in range(n)` loop it drives are a trivial continuation, not an abstraction. Judge by behavior: inline the
span into its sole caller when it has one call site, the looped count is a literal or statically fixed constant
at the call site (a literal `1`, a module constant set to `1` such as `REQUESTS_PER_BATCH = 1`, or a default
constant not sourced from user/config/runtime input), the loop body only calls / waits / logs / constructs /
appends / prints / serializes / forwards, and any guard it carries only rejects an out-of-range value of a
parameter the span itself introduced (`if size < 1: raise`). That guard is not the validation warrant — a
validation warrant protects a real domain invariant, never a synthetic knob the function invented; a count that
is a fixed constant at the one call site is not a degree of freedom and proves nothing about batch abstraction.
The loop earns its own function only when its body owns real batch policy: chunking, rate limiting, concurrency,
retry, error aggregation, or two-or-more distinct call sites. None of this is changed by the name:
`send_batch_once`, `run_once`, and `process_batch` are common instances of the shape, and renaming to
`dispatch_many` rescues nothing.

**Models — the unwrap test.** Models earn existence the same way, by what they *constrain or guarantee* —
validation, an invariant, an outward contract, a serialization shape — not by what they *hold*. Drop the layer
and use the inner type directly; if no constraint or guarantee is lost, the layer must not exist. A model that
only wraps a local list/batch/grouping, mirrors another model's fields, or re-wraps a value already shaped by
its callee (`AModel(**b.model_dump())`) fails this test and is deleted.

**No grandfather right.** Existing helpers and models in the input code earn nothing by already existing. During
a rewrite, do not preserve or re-create a local batch/request/result model because the old code had one, because
Pydantic is the default for *real* contracts, or because words like "batch" or "result" sound contract-like. If a
list or result is consumed only inside one linear workflow and no API, framework, external boundary, validation
rule, invariant, or serialization shape depends on it, keep the plain value. A wrapper does not pass the unwrap
test by renaming itself `Batch` → `Request`, by moving the same linear loop into a method, or by gaining a result
model — the method must protect an invariant, expose a real outward contract, adapt a boundary, or own reusable
policy; otherwise inline the loop and return the plain value.

Judge by what a definition *decides, protects, constrains, or guarantees* — never by its name, its shape, or
whether it can be given a clean docstring. Renaming `build_*` to `make_*`, splitting a 3-deep chain into 2, or
adding a filler field to a wrapper does not change the verdict. The docstring requirement applies only after a
definition has earned its place; if a span fails this gate, inline it and document the containing function
instead.

Do not replace one linear script with layered one-use orchestration helpers. A chain such as
`main -> send_batch_once -> send_config_prompt_once -> send_prompt_once` is forbidden when each layer only
forwards arguments, creates one object, calls one dependency, or names a step. Keep the orchestration in `main()`
or the nearest high-level entrypoint unless a layer owns retry/error policy, protocol adaptation, validation,
state transition, or a reusable tested transformation. Parameterizing such a layer with a `size` / `count`
argument and a `if size < 1: raise` guard does not rescue it; a synthetic knob that is always a literal or
statically fixed constant at the one call site, driving a trivial loop, is still inlined.

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
- Thin helper functions kept only because they are called twice, even though the body is still simple
  ID/token/random/default generation, sleeping, printing, direct external calls, simple constructors,
  serialization, attribute forwarding, or one obvious return expression.
- A `for _ in range(n)` batch/once helper kept alive by a `count` / `size` parameter or a `if size < 1: raise`
  guard, while its sole call site passes a literal or statically fixed constant and the loop body only
  constructs, calls, appends, prints, or forwards.
- A script whose main flow is harder to follow because each linear step is moved into a separate helper.
- Layered one-use orchestration helpers where each function only forwards to the next function in a straight-line
  flow.
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
