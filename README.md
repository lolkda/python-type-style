# Python Type Style

Type-first engineering guidance for Python 3.12+ projects built with FastAPI, Pydantic v2, and SQLAlchemy 2.

This skill is designed for code generation, refactoring, and review workflows where API contracts, typing discipline, async safety, and persistence boundaries need to stay consistent.

## What It Enforces

- Keyword-only function signatures by default
- Required docstrings with business-focused `Args` and `Returns`
- Explicit public types and strict contract models
- `BaseResponse[T]`-style unified API envelopes
- PEP 695 typing syntax on Python 3.12+
- Clear separation between outward API contracts and persistence-layer models
- FastAPI, Pydantic v2, and SQLAlchemy 2 usage conventions

## Repository Layout

```text
.
├── SKILL.md
├── agents/
│   └── openai.yaml
├── examples/
└── references/
```

## Installation

This repository is a plain skill bundle. Clone or download it, then place the folder in whatever skill search path your agent runtime uses.

Recommended method with `git`:

```bash
git clone https://github.com/lolkda/python-type-style.git
```

If you do not want to use `git`, download the repository archive from GitHub and extract it locally.

The runtime should see a folder named `python-type-style` containing:

```text
python-type-style/
├── SKILL.md
├── agents/
├── examples/
└── references/
```

If your runtime loads skills from a dedicated directory, copy or symlink this folder into that directory with the name `python-type-style`.

## Usage

Typical prompt:

```text
Use $python-typed-development-standards to write or refactor this Python code in a FastAPI- and Pydantic-friendly, type-first style.
```

## Contents

- `SKILL.md`: core rules and trigger guidance
- `references/`: detailed style references
- `examples/`: runnable examples for common patterns
- `agents/openai.yaml`: display metadata for agent integration

## Requirements

- Python 3.12+
- FastAPI-oriented Python codebase
- Pydantic v2
- SQLAlchemy 2

## Status

This repository currently publishes the skill content only. It does not include a packaging or installer script.
