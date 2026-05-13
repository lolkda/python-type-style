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

Remote install with the Codex skill installer:

```powershell
python C:\Users\Administrator\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py --repo lolkda/python-type-style --path . --name python-type-style
```

You can also install from the repository URL:

```powershell
python C:\Users\Administrator\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py --url https://github.com/lolkda/python-type-style --path . --name python-type-style
```

After installation, restart Codex to pick up the new skill.

## Usage

Typical prompt:

```text
Use $python-type-style to write or refactor this Python code in a FastAPI- and Pydantic-friendly, type-first style.
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
