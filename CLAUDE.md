# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A **skill bundle** — pure documentation plus illustrative Python examples that teach a strict, type-first style for FastAPI + Pydantic v2 + SQLAlchemy 2 on Python 3.12+. It is consumed by agent runtimes (Claude Code, Codex, etc.) that load `SKILL.md` and follow its rules when generating or refactoring Python.

There is no build system, package manifest, dependency pin file, or test runner. `test/` exists but is empty. The Python files in `examples/` are illustrative — they import from a local `_shared.py` and are not packaged or executed by CI. Do not invent `pip install`, `pytest`, or `ruff` invocations; none are wired up.

To sanity-check that an example still parses under Python 3.12+ syntax (PEP 695 generics, `type` aliases):

```powershell
python -m py_compile examples/<file>.py
```

That is the closest thing to a "test" in this repo.

## Identifier mapping

- **Folder / repo name:** `python-type-style`
- **Skill frontmatter `name:` in `SKILL.md`:** `python-typed-development-standards` (this is what skill loaders register)
- **Invocation prefix in prompts / `agents/openai.yaml`:** `$python-typed-development-standards`

When editing `SKILL.md` frontmatter, the README, or `agents/openai.yaml`, keep the registered skill name and user-facing `$` trigger aligned. Keep the folder / repo name stable unless the repository itself is intentionally renamed.

## Architecture: how the three layers fit together

```
SKILL.md                  ← daily-driver rules, ~150 lines, loaded into every triggered session
├── references/           ← deep dives, one file per topic, linked from SKILL.md
└── examples/             ← runnable counterparts, all importing from _shared.py
```

- **`SKILL.md`** holds "Quick Rules" sections (Class vs Function, Object API, Typing, Response, FastAPI, SQLAlchemy 2, Pydantic v2, Property, Async) plus an Anti-patterns list and a References Index table mapping each topic to its reference file and example file. Treat it as the index; don't inline deep treatments here.
- **`references/*.md`** are the source of truth for *why* and edge cases. Every Quick Rules section in `SKILL.md` ends with a "Full treatment:" link to one of these. When updating a rule, update the SKILL.md summary **and** the corresponding reference file in lockstep so the two do not drift.
- **`examples/*.py`** are the runnable counterparts cited by the References Index. They all import anchor models from `examples/_shared.py` (`User`, `Post`, `UserDetailData`, `BaseResponse[T]`, `PageData[T]`, `UserNotFoundError`). Add new examples by extending `_shared.py` rather than redefining anchor types per file — the shared file is the deliberate single point of truth so cross-example references read consistently.

The References Index table at the bottom of `SKILL.md` is load-bearing — every reference and example should appear in it. When adding a new reference or example, add the row.

## Reference writing policy

`references/*.md` must read like behavior constraints, not library tutorials:

- Prefer rule tables, `Default / Allowed exception / Forbidden` matrices, anti-pattern lists, and runnable counterpart links.
- Do not add tutorial sections that explain general FastAPI, Pydantic, SQLAlchemy, or typing mechanics.
- Rationale is allowed only as one short failure-mode clause attached to a rule.
- Do not duplicate full code examples already present in `examples/`; link to the runnable counterpart instead.
- Add catalogue entries only when this skill has a project-specific opinion that differs from ordinary modern Python practice.

## Load-bearing conventions inside the skill content

These are content conventions to preserve when editing rules, references, or examples — not generic Python style suggestions:

- **Bilingual on purpose.** Prose and code comments are English; function and class docstrings are Chinese;
  `Field(description=...)`, route `summary=...`, and docstring sections (用途/Args/Returns) use Chinese (中文).
  This is one of the rules the skill enforces — do not "normalize" example code to all-English descriptions.
- **Docstrings are exhaustive.** Every function-like definition in examples needs a Chinese docstring with
  `Args` and `Returns`, including `__init__`, properties, overload stubs, protocol stubs, decorator inner
  wrappers, and private helpers.
- **`BaseResponse[T]` envelope is singular.** The skill repeatedly forbids per-endpoint `XxxResponse` models that duplicate `code`/`message`/`data`. When adding examples, route handlers must wrap with `BaseResponse[T]` or `BaseResponse[PageData[T]]` — never introduce a parallel envelope.
- **Outward vs. persistence boundary** is the central architectural distinction (see `references/architecture-boundary.md`). Route handlers and public service facades return `BaseModel` contracts; repository methods may return ORM entities. Don't blur this in examples.
- **PEP 695 syntax is default.** `class Foo[T]:`, `def fn[T](...)`, `type Alias = ...`. The skill explicitly forbids `from __future__ import annotations` project-wide because Pydantic v2 / FastAPI rely on runtime introspection.
- **Keyword-only by default.** Every example function uses `*` to force keyword-only arguments unless a framework signature forbids it (decorator-injected first params via `Concatenate[X, P]` are the documented exception).
- **No shorthand route decorators.** Examples use `@router.api_route(path=..., methods=[...], response_model=..., tags=..., summary=...)`, never `@router.get(...)`.
- **Object API examples prefer one public request/config object.** When illustrating object API style, show the
  recommended C-shape (`Request.create().model_settings()`), not multiple competing A/B/C variants.

## Editing workflow

- **Adding a new rule:** add a Quick Rules bullet to `SKILL.md`, write the deep treatment in `references/<topic>.md`, link from SKILL.md, add an Anti-patterns bullet if there's a clear failure mode, and add/extend a runnable counterpart in `examples/` cited from the References Index.
- **Adding a new example:** put shared types in `examples/_shared.py`, import them in the new file, and add a row to the References Index in `SKILL.md`.
- **Renaming an anchor model:** update `examples/_shared.py` and every example that imports it; references that quote example code paths should be updated too.
- **Updating object API style:** keep `SKILL.md`, `references/object-api-style.md`, and
  `examples/object_api_style.py` aligned so the quick rule, deep treatment, and runnable shape do not drift.
