"""Tests for ast_equiv.canonicalizer -- TDD: all tests fail until implementation exists."""
import pytest
from ast_equiv.canonicalizer import (
    parse_algorithm,
    extract_all_names,
    extract_free_variables,
    normalize_to_concepts,
    canonicalize,
    canonical_dump,
    structural_match,
    AlgorithmParseError,
    KNOWN_BUILTINS,
)


class TestParseAlgorithm:
    def test_valid_function(self):
        tree = parse_algorithm("def f(x):\n    return x + 1")
        assert tree is not None

    def test_syntax_error_raises(self):
        with pytest.raises(AlgorithmParseError):
            parse_algorithm("def f(x:\n    return")

    def test_empty_body_raises(self):
        with pytest.raises(AlgorithmParseError):
            parse_algorithm("")

    def test_non_function_raises(self):
        with pytest.raises(AlgorithmParseError):
            parse_algorithm("x = 1")


class TestExtractNames:
    def test_simple_names(self):
        tree = parse_algorithm("def f(x, y):\n    z = x + y\n    return z")
        names = extract_all_names(tree)
        assert "x" in names
        assert "y" in names
        assert "z" in names

    def test_builtins_included(self):
        tree = parse_algorithm("def f(x):\n    return len(x)")
        names = extract_all_names(tree)
        assert "len" in names

    def test_attribute_base(self):
        tree = parse_algorithm("def f(x):\n    return x.append(1)")
        names = extract_all_names(tree)
        assert "x" in names

    def test_free_variables_exclude_builtins_and_locals(self):
        tree = parse_algorithm("def f(x):\n    y = len(x)\n    return y + external")
        assert extract_free_variables(tree) == {"external"}


class TestNormalizeToConcepts:
    def test_bound_replaced(self):
        body = "def f(x):\n    return x + 1"
        bindings = {"x": "input_signal"}
        result = normalize_to_concepts(body, bindings)
        assert "input_signal" in result
        assert "x" not in result or "x" in "input_signal"

    def test_unbound_preserved(self):
        body = "def f(x, y):\n    return x + y"
        bindings = {"x": "signal"}
        result = normalize_to_concepts(body, bindings)
        assert "signal" in result
        # y should still appear since it's not bound

    def test_nested_scope(self):
        body = "def f(items):\n    return [x*2 for x in items]"
        bindings = {"items": "data_list"}
        result = normalize_to_concepts(body, bindings)
        assert "data_list" in result

    def test_attribute_access(self):
        body = "def f(arr):\n    arr.append(1)\n    return arr"
        bindings = {"arr": "buffer"}
        result = normalize_to_concepts(body, bindings)
        assert "buffer" in result


class TestCanonicalize:
    def test_range_normalization(self):
        body_a = "def f(n):\n    for i in range(0, n, 1):\n        pass"
        body_b = "def f(n):\n    for i in range(n):\n        pass"
        dump_a = canonical_dump(body_a, {"n": "count"})
        dump_b = canonical_dump(body_b, {"n": "count"})
        assert dump_a == dump_b

    def test_docstring_stripped(self):
        body_a = 'def f(x):\n    """Docstring."""\n    return x'
        body_b = "def f(x):\n    return x"
        dump_a = canonical_dump(body_a, {"x": "val"})
        dump_b = canonical_dump(body_b, {"x": "val"})
        assert dump_a == dump_b

    def test_constant_fold(self):
        body_a = "def f(n):\n    return 2 * 3 * n"
        body_b = "def f(n):\n    return 6 * n"
        dump_a = canonical_dump(body_a, {"n": "count"})
        dump_b = canonical_dump(body_b, {"n": "count"})
        assert dump_a == dump_b

    def test_true_comparison_preserved_for_non_bool_annotation(self):
        import ast
        from ast_equiv.comparison import _normalize_and_canonicalize

        body = "def f(x: int):\n    return x == True"
        dump = ast.dump(_normalize_and_canonicalize(body, {}), include_attributes=False)

        assert "Compare" in dump
        assert "Eq" in dump
        assert "Constant(value=True" in dump

    def test_true_comparison_rewritten_for_bool_annotation(self):
        body_a = "def f(x: bool):\n    return x == True"
        body_b = "def f(x: bool):\n    return x"

        assert canonical_dump(body_a, {}) == canonical_dump(body_b, {})

    def test_temp_var_inlining_preserves_call_order(self):
        body = (
            "def f():\n"
            "    t = produce()\n"
            "    g()\n"
            "    return use(t)"
        )
        import ast
        from ast_equiv.comparison import _normalize_and_canonicalize

        tree_dump = ast.dump(
            _normalize_and_canonicalize(body, {"produce": "produce", "g": "g", "use": "use"}),
            include_attributes=False,
        )

        assert tree_dump.index("Name(id='produce'") < tree_dump.index("Name(id='g'")


class TestAlphaEquivalence:
    def test_same_names_match(self):
        body = "def f(x):\n    return x + 1"
        assert structural_match(
            canonical_dump(body, {"x": "val"}),
            canonical_dump(body, {"x": "val"}),
        )

    def test_different_names_same_concepts(self):
        body_a = "def f(x):\n    return x + 1"
        body_b = "def g(y):\n    return y + 1"
        assert structural_match(
            canonical_dump(body_a, {"x": "val"}),
            canonical_dump(body_b, {"y": "val"}),
        )

    def test_different_concepts_no_match(self):
        body_a = "def f(x):\n    return x + 1"
        body_b = "def g(y):\n    return y + 1"
        assert not structural_match(
            canonical_dump(body_a, {"x": "signal"}),
            canonical_dump(body_b, {"y": "frequency"}),
        )
