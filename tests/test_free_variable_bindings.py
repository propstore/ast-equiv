"""Lexical binding regressions for the algorithm admission consumer."""

from __future__ import annotations

import pytest

from ast_equiv import AlgorithmParseError, compare, extract_free_variables, parse_algorithm


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        pytest.param(
            "def f(x):\n    class C:\n        import math\n    return math.sqrt(x)\n",
            {"math"},
            id="class-import-does-not-bind-enclosing-function",
        ),
        pytest.param(
            "def f(xs):\n    xs[missing] = 0\n    return xs\n",
            {"missing"},
            id="subscript-store-index-is-a-load",
        ),
        pytest.param(
            "def f(x):\n    def inner():\n        return offset\n"
            "    offset = x\n    return inner()\n",
            set(),
            id="closure-sees-later-enclosing-binding",
        ),
        pytest.param(
            "def f(x):\n    return math.sqrt(x)\nimport math\n",
            set(),
            id="function-sees-later-module-import",
        ),
        pytest.param(
            "def f(x):\n    try:\n        return int(x)\n"
            "    except ValueError as exc:\n        return str(exc)\n",
            set(),
            id="except-target-is-bound",
        ),
        pytest.param(
            "def f(x):\n    class C:\n        import math\n"
            "        def method(self):\n            return math.sqrt(x)\n"
            "    return C().method()\n",
            {"math"},
            id="class-bindings-are-not-method-closures",
        ),
    ],
)
def test_lexical_scope_binding_rules(body: str, expected: set[str]) -> None:
    assert extract_free_variables(parse_algorithm(body)) == expected


@pytest.mark.parametrize("name", ["divmod", "slice", "object", "issubclass", "OSError"])
def test_python_builtins_are_not_external_inputs(name: str) -> None:
    assert extract_free_variables(parse_algorithm(f"def f():\n    return {name}\n")) == set()


def test_uninitialized_local_is_outside_lexical_free_name_analysis() -> None:
    assert extract_free_variables(parse_algorithm("def f():\n    x += 1\n    return x\n")) == set()


def test_invalid_nonlocal_binding_has_a_typed_parse_error() -> None:
    tree = parse_algorithm("def f():\n    nonlocal missing\n    return missing\n")

    with pytest.raises(AlgorithmParseError, match="Invalid binding syntax"):
        extract_free_variables(tree)


def test_free_name_builtin_lookup_preserves_existing_comparison_policy() -> None:
    result = compare(
        "def f(object):\n    return object + 1\n", {},
        "def f(x):\n    return x + 1\n", {},
    )

    assert result.equivalent
