from __future__ import annotations

import ast
from pathlib import Path

import sympy

import ast_equiv.canonicalizer as canonicalizer
from ast_equiv import canonical_dump


BODY = "def f(x):\n    y = x + 1\n    return y * y"
BINDINGS = {"x": "value"}


def test_cache_key_sympy_version_independent(monkeypatch) -> None:
    """RD-3: canonical_dump cache keys do not depend on SymPy printers."""
    before = canonical_dump(BODY, BINDINGS)

    monkeypatch.setattr(sympy, "__version__", "1.99.0")
    monkeypatch.setattr(sympy, "srepr", lambda expr: f"perturbed:{expr!r}")

    after = canonical_dump(BODY, BINDINGS)

    assert before == after
    assert before.startswith(f"{canonicalizer.SEMANTIC_EQUIVALENCE_VERSION}:")
    canonicalizer_source = Path("ast_equiv/canonicalizer.py").read_text(encoding="utf-8")
    parsed = ast.parse(canonicalizer_source)
    imported_modules = {
        node.module
        for node in ast.walk(parsed)
        if isinstance(node, ast.ImportFrom)
    } | {
        alias.name
        for node in ast.walk(parsed)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert "sympy" not in imported_modules


def test_cache_key_invalidates_on_semantic_version_change(monkeypatch) -> None:
    """RD-3: our semantic version is the explicit cache invalidation knob."""
    cache = {canonical_dump(BODY, BINDINGS): "cached"}

    monkeypatch.setattr(canonicalizer, "SEMANTIC_EQUIVALENCE_VERSION", "2")
    new_key = canonical_dump(BODY, BINDINGS)

    assert new_key.startswith("2:")
    assert new_key not in cache


def test_pyproject_has_no_sympy_upper_bound() -> None:
    """RD-3: no SymPy upper bound hides cache-key fragility."""
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert '"sympy>=1.14.0"' in pyproject
    assert "sympy<" not in pyproject
    assert "sympy>=" in pyproject
