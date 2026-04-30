from __future__ import annotations

import ast

import pytest

from ast_equiv.canonicalizer import WhileToForNormalizer
from ast_equiv.comparison import Tier, compare
from ast_equiv.sympy_bridge import ast_to_sympy


def _module_after_while_normalization(source: str) -> ast.Module:
    tree = ast.parse(source)
    tree = WhileToForNormalizer().visit(tree)
    ast.fix_missing_locations(tree)
    return tree


def _contains_node(tree: ast.AST, node_type: type[ast.AST]) -> bool:
    return any(isinstance(node, node_type) for node in ast.walk(tree))


def test_C1_identity_elimination_is_not_valid_for_untyped_addition() -> None:
    """C-1: `x + 0` must not canonicalize to `x` for untyped values."""
    left = "def f(x):\n    return x + 0"
    right = "def f(x):\n    return x"

    result = compare(left, {"x": "value"}, right, {"x": "value"})

    assert result.equivalent is False


def test_C2_repeated_mult_with_calls_preserves_call_count() -> None:
    """C-2: `g(x) * g(x)` is not equivalent to `g(x) ** 2` for unknown calls."""
    left = "def f(x):\n    return g(x) * g(x)"
    right = "def f(x):\n    return g(x) ** 2"

    result = compare(left, {"x": "value"}, right, {"x": "value"})

    assert result.equivalent is False


@pytest.mark.parametrize(
    "source",
    (
        "def f(n):\n"
        "    i = 0\n"
        "    while i < n:\n"
        "        if i == 2:\n"
        "            break\n"
        "        i = i + 1\n",
        "def f(n):\n"
        "    i = 0\n"
        "    while i < n:\n"
        "        if i % 2 == 0:\n"
        "            i = i + 1\n"
        "            continue\n"
        "        i = i + 1\n",
        "def f(n):\n"
        "    i = 0\n"
        "    while i < n:\n"
        "        n = n - 1\n"
        "        i = i + 1\n",
        "def f(n):\n"
        "    i = 0.0\n"
        "    while i < n:\n"
        "        i = i + 1\n",
    ),
)
def test_C3_while_to_for_refuses_control_flow_and_unsound_bounds(source: str) -> None:
    """C-3: while-to-for conversion must refuse unsafe loop shapes."""
    normalized = _module_after_while_normalization(source)

    assert _contains_node(normalized, ast.While)
    assert not _contains_node(normalized, ast.For)


def test_X1_compare_propagates_unexpected_sympy_tier_errors(monkeypatch) -> None:
    """X-1/RD-4: unexpected internal tier errors are not UNKNOWN results."""
    import ast_equiv.comparison as comparison

    def _boom(*_args, **_kwargs):
        raise RuntimeError("synthetic sympy tier failure")

    monkeypatch.setattr(comparison, "sympy_expressions_equivalent", _boom)

    with pytest.raises(RuntimeError, match="synthetic sympy tier failure"):
        compare(
            "def f(x):\n    return x + 1",
            {"x": "value"},
            "def f(x):\n    return 1 + x",
            {"x": "value"},
        )


def test_S1_math_log_two_arg_real_domain_equivalence() -> None:
    """S-1/RD-1: real finite symbols support `math.log(x, base)`."""
    left = "def f(x):\n    return math.log(x, 2)"
    right = "def f(x):\n    return math.log(x) / math.log(2)"

    symbol = ast_to_sympy(ast.parse("x").body[0].value)
    assert symbol.is_real is True
    assert symbol.is_finite is True

    result = compare(left, {"x": "value"}, right, {"x": "value"})

    assert result.equivalent is True
    assert result.tier is Tier.SYMPY


def test_S2_floordiv_and_mod_have_integer_domain_bridge() -> None:
    """S-2/RD-1: FloorDiv and Mod lower to SymPy over integer symbols."""
    floor_expr = ast_to_sympy(ast.parse("x // 2").body[0].value)
    mod_expr = ast_to_sympy(ast.parse("x % 2").body[0].value)
    x = next(iter(floor_expr.free_symbols | mod_expr.free_symbols))

    assert x.is_integer is True
    assert str(floor_expr) == "floor(x/2)"
    assert str(mod_expr) == "Mod(x, 2)"


def test_S3_positive_assertion_enables_sqrt_product_equivalence() -> None:
    """S-3/RD-1: positive assertions opt into sound sqrt product simplification."""
    no_assert = compare(
        "def f(x, y):\n    return math.sqrt(x * y)",
        {"x": "x", "y": "y"},
        "def f(x, y):\n    return math.sqrt(x) * math.sqrt(y)",
        {"x": "x", "y": "y"},
    )
    with_assert = compare(
        "def f(x, y):\n    assert x > 0\n    assert y > 0\n    return math.sqrt(x * y)",
        {"x": "x", "y": "y"},
        "def f(x, y):\n    assert x > 0\n    assert y > 0\n    return math.sqrt(x) * math.sqrt(y)",
        {"x": "x", "y": "y"},
    )

    assert no_assert.equivalent is False
    assert with_assert.equivalent is True
    assert with_assert.tier is Tier.SYMPY
