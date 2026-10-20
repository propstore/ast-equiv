from __future__ import annotations

import ast
from pathlib import Path

import pytest

import ast_equiv
from ast_equiv.canonicalizer import parse_algorithm
from ast_equiv.comparison import Tier, compare


def test_D14_bytecode_tier_deleted_from_public_surface() -> None:
    """D-14: the bytecode tier is deleted, not deprecated."""
    assert {tier.name for tier in Tier} == {
        "NONE",
        "CANONICAL",
        "SYMPY",
        "PARTIAL_EVAL",
    }
    assert not hasattr(Tier, "BYTECODE")

    comparison_source = Path("ast_equiv/comparison.py").read_text(encoding="utf-8")
    assert "_compile_to_bytecode" not in comparison_source
    assert "Tier.BYTECODE" not in comparison_source


def test_X4_readme_tier_names_match_enum() -> None:
    """X-4: README and enum name the same post-D-14 tier set."""
    readme = Path("README.md").read_text(encoding="utf-8")

    for tier_name in ("NONE", "CANONICAL", "SYMPY", "PARTIAL_EVAL"):
        assert tier_name in readme
    assert "BYTECODE" not in readme
    assert "STRUCTURAL_SIMILARITY" not in readme


def test_RD2_extract_names_split_public_api() -> None:
    """RD-2: broad names and free variables are separate APIs."""
    assert hasattr(ast_equiv, "extract_all_names")
    assert hasattr(ast_equiv, "extract_free_variables")
    assert not hasattr(ast_equiv, "extract_names")


def test_RD2_extract_free_variables_respects_python_binders() -> None:
    """RD-2: bound names, builtins, and locals are not free variables."""
    tree = parse_algorithm(
        "def f(x):\n"
        "    local = len(x)\n"
        "    pairs = [item + y for item in x]\n"
        "    func = lambda z: z + y\n"
        "    with manager as handle:\n"
        "        inside = handle.read()\n"
        "    return local + pairs[0] + func(1) + external + inside\n"
    )

    assert ast_equiv.extract_free_variables(tree) == {"manager", "y", "external"}
    assert {"x", "local", "pairs", "item", "func", "z", "handle", "inside", "len"}.isdisjoint(
        ast_equiv.extract_free_variables(tree)
    )


@pytest.mark.parametrize(
    ("imports", "expression"),
    [
        ("import math", "math.sqrt(x)"),
        ("import math as m", "m.sqrt(x)"),
        ("import os.path", "os.path.basename(x)"),
        ("import os.path as path", "path.basename(x)"),
        ("from math import sqrt", "sqrt(x)"),
        ("from math import sqrt as root", "root(x)"),
    ],
)
def test_free_variables_exclude_import_bindings(imports: str, expression: str) -> None:
    tree = parse_algorithm(f"def f(x):\n    {imports}\n    return {expression} + external\n")

    assert ast_equiv.extract_free_variables(tree) == {"external"}


def test_import_alias_does_not_bind_original_name() -> None:
    tree = parse_algorithm(
        "def f(x):\n    import math as m\n    return m.sqrt(x) + math.pi\n"
    )

    assert ast_equiv.extract_free_variables(tree) == {"math"}


def test_nested_function_import_does_not_bind_enclosing_scope() -> None:
    tree = parse_algorithm(
        "def f(x):\n"
        "    def inner(y):\n"
        "        import math\n"
        "        return math.sqrt(y)\n"
        "    return inner(x) + math.pi\n"
    )

    assert ast_equiv.extract_free_variables(tree) == {"math"}


def test_module_import_binds_function_global_name() -> None:
    tree = parse_algorithm("import math\ndef f(x):\n    return math.sqrt(x)\n")

    assert ast_equiv.extract_free_variables(tree) == set()


def test_compare_result_records_tier_failures() -> None:
    """RD-4: compare exposes typed tier failures for expected tier refusal."""
    result = compare(
        "def f(x):\n    return [x]",
        {"x": "value"},
        "def f(x):\n    return tuple([x])",
        {"x": "value"},
    )

    assert result.equivalent is False
    assert result.tier is Tier.NONE
    assert Tier.SYMPY in result.tier_failures
    assert result.tier_failures[Tier.SYMPY].__name__ == "AstToSympyError"
