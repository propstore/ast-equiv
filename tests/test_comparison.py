"""Tests for ast_equiv.comparison -- TDD: all tests fail until implementation exists."""
import pytest
from ast_equiv.canonicalizer import canonical_dump
from ast_equiv.comparison import (
    compare,
    ComparisonResult,
    Tier,
    _normalize_and_canonicalize,
    partial_eval_match,
    structural_similarity,
)


class TestCanonicalComparison:
    def test_constant_fold_match(self):
        body_a = "def f(n):\n    return 2 * 3 * n"
        body_b = "def f(n):\n    return 6 * n"
        assert compare(body_a, {"n": "count"}, body_b, {"n": "count"}).equivalent

    def test_range_normalization(self):
        body_a = "def f(n):\n    for i in range(0, n, 1):\n        pass"
        body_b = "def f(n):\n    for i in range(n):\n        pass"
        assert compare(body_a, {"n": "count"}, body_b, {"n": "count"}).equivalent

    def test_different_logic_no_match(self):
        body_a = "def f(x):\n    return x + 1"
        body_b = "def f(x):\n    return x * 2"
        assert not compare(body_a, {"x": "val"}, body_b, {"x": "val"}).equivalent

    def test_augmented_assignment(self):
        body_a = "def f(x):\n    x = x + 1\n    return x"
        body_b = "def f(x):\n    x += 1\n    return x"
        assert compare(body_a, {"x": "val"}, body_b, {"x": "val"}).equivalent


class TestPartialEvaluation:
    def test_param_substituted(self):
        body_a = "def f(rate):\n    return rate / 4"
        body_b = "def f():\n    return 11025"
        assert partial_eval_match(
            body_a, {"rate": "sample_rate"}, body_b, {},
            known_values={"sample_rate": 44100},
        )

    def test_different_values_diverge(self):
        body_a = "def f(rate):\n    return rate / 4"
        body_b = "def f():\n    return 11025"
        assert not partial_eval_match(
            body_a, {"rate": "sample_rate"}, body_b, {},
            known_values={"sample_rate": 22050},
        )

    def test_no_values_falls_through(self):
        body_a = "def f(rate):\n    return rate / 4"
        body_b = "def f():\n    return 11025"
        # Without known_values, partial eval can't resolve -- should not match
        assert not partial_eval_match(
            body_a, {"rate": "sample_rate"}, body_b, {},
            known_values={},
        )


class TestComparisonLadder:
    def test_compare_pipeline_matches_canonical_dump_concept_names(self):
        import ast

        body = "def f(x):\n    return x + 1"
        bindings = {"x": "mass"}

        pipeline_dump = ast.dump(
            _normalize_and_canonicalize(body, bindings),
            include_attributes=False,
        )

        assert pipeline_dump
        assert canonical_dump(body, bindings).split(":", 1)[0] == "1"

    def test_sympy_tier_distinct_from_partial_eval_tier(self):
        sympy_a = "def f(x):\n    return x / 2 + x / 2"
        sympy_b = "def g(y):\n    return y"

        r_sym = compare(sympy_a, {"x": "val"}, sympy_b, {"y": "val"})

        r_partial = compare(
            "def f(rate):\n    return rate / 4",
            {"rate": "sample_rate"},
            "def g():\n    return 11025",
            {},
            known_values={"sample_rate": 44100},
        )

        assert r_sym.tier == Tier.SYMPY
        assert r_partial.tier == Tier.PARTIAL_EVAL
        assert r_sym.tier != r_partial.tier

    def test_tier1_match(self):
        body_a = "def f(x):\n    return x + 1"
        body_b = "def g(y):\n    return y + 1"
        result = compare(body_a, {"x": "val"}, body_b, {"y": "val"})
        assert result.equivalent is True
        assert result.tier == Tier.CANONICAL

    def test_sympy_match(self):
        body_a = "def f(x):\n    return x / 2 + x / 2"
        body_b = "def g(y):\n    return y"
        result = compare(body_a, {"x": "val"}, body_b, {"y": "val"})
        assert result.equivalent is True
        assert result.tier == Tier.SYMPY

    def test_tier3_match(self):
        body_a = "def f(rate):\n    return rate / 4"
        body_b = "def g():\n    return 11025"
        result = compare(
            body_a, {"rate": "sample_rate"}, body_b, {},
            known_values={"sample_rate": 44100},
        )
        assert result.equivalent is True
        assert result.tier == Tier.PARTIAL_EVAL

    def test_no_match_with_similarity(self):
        body_a = "def f(x):\n    return x + 1"
        body_b = "def g(x):\n    return x * x + x - 1"
        result = compare(body_a, {"x": "val"}, body_b, {"x": "val"})
        assert result.equivalent is False
        assert 0.0 <= result.similarity <= 1.0


class TestStructuralSimilarity:
    def test_identical_is_one(self):
        body = "def f(x):\n    return x + 1"
        import ast
        tree = ast.parse(body)
        assert structural_similarity(tree, tree) == pytest.approx(1.0)

    def test_different_below_half(self):
        import ast
        tree_a = ast.parse("def f(x):\n    return x + 1")
        tree_b = ast.parse("def g(a, b, c):\n    for i in range(a):\n        b += c * i\n    return b")
        assert structural_similarity(tree_a, tree_b) < 0.5

    def test_minor_variant_high(self):
        import ast
        tree_a = ast.parse("def f(x, y):\n    z = x + y\n    return z * 2")
        tree_b = ast.parse("def f(x, y):\n    z = x + y\n    return z * 3")
        assert structural_similarity(tree_a, tree_b) > 0.8


class TestComparisonResult:
    def test_fields(self):
        r = ComparisonResult(equivalent=True, tier=Tier.CANONICAL, similarity=1.0, details="match")
        assert r.equivalent is True
        assert r.tier == Tier.CANONICAL
        assert r.similarity == 1.0
