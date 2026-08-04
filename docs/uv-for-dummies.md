# uv for dummies

Short guide to `uv` — the fast Python package manager used by this project.

## Add a package

Add a package to `pyproject.toml` and install it:

```bash
uv add pytest
```

This replaces manually editing `requirement.txt`.

Example: the project needs `pyjwt`. Run:

```bash
uv add pyjwt
```

## Run a script

Run a Python file with its dependencies from the toml file:

```bash
uv run main.py
```

Example:

```bash
uv run src/main.py
```

## Install everything

Download and install all dependencies and libraries for the project:

```bash
uv sync
```

Runs after cloning or when `pyproject.toml`/`uv.lock` changes.

## Shout out

Shout out to moaz.
