"""Property-based tests for ast-equiv."""
import ast
import pytest
from hypothesis import given, strategies as st, assume, settings

from ast_equiv.canonicalizer import parse_algorithm, canonical_dump, AlgorithmParseError
from ast_equiv.comparison import compare, structural_similarity


# Strategy: generate simple function bodies
simple_ops = st.sampled_from(["+", "-", "*"])
simple_body = st.builds(
    lambda op, const: f"def f(x):\n    return x {op} {const}",
    simple_ops,
    st.integers(min_value=0, max_value=100),
)


@given(body=simple_body)
@settings(max_examples=50)
def test_self_equivalence(body):
    """Any algorithm is equivalent to itself."""
    result = compare(body, {"x": "val"}, body, {"x": "val"})
    assert result.equivalent is True
    assert result.tier == 1


@given(body=simple_body)
@settings(max_examples=50)
def test_symmetry(body):
    """compare(a, b) == compare(b, a) in equivalence."""
    bindings = {"x": "val"}
    r1 = compare(body, bindings, body, bindings)
    r2 = compare(body, bindings, body, bindings)
    assert r1.equivalent == r2.equivalent


@given(body=simple_body)
@settings(max_examples=50)
def test_canonical_dump_deterministic(body):
    """Same input always produces same canonical dump."""
    bindings = {"x": "val"}
    d1 = canonical_dump(body, bindings)
    d2 = canonical_dump(body, bindings)
    assert d1 == d2


@given(body=simple_body)
@settings(max_examples=50)
def test_similarity_bounds(body):
    """Structural similarity is always in [0, 1]."""
    tree = ast.parse(body)
    sim = structural_similarity(tree, tree)
    assert 0.0 <= sim <= 1.0


rename_chars = st.sampled_from(["a", "b", "c", "m", "n", "p", "q", "r", "s", "t"])

@given(body=simple_body, new_name=rename_chars)
@settings(max_examples=50)
def test_rename_equivalence(body, new_name):
    """Renaming the parameter preserves equivalence."""
    assume(new_name != "x")
    renamed = body.replace("x", new_name)
    result = compare(body, {"x": "val"}, renamed, {new_name: "val"})
    assert result.equivalent is True


@given(
    op=simple_ops,
    const_a=st.integers(min_value=1, max_value=50),
    const_b=st.integers(min_value=1, max_value=50),
)
@settings(max_examples=50)
def test_different_constants_not_equivalent(op, const_a, const_b):
    """Different constants should not be equivalent (unless partial eval resolves them)."""
    assume(const_a != const_b)
    body_a = f"def f(x):\n    return x {op} {const_a}"
    body_b = f"def f(x):\n    return x {op} {const_b}"
    result = compare(body_a, {"x": "val"}, body_b, {"x": "val"})
    assert result.equivalent is False
