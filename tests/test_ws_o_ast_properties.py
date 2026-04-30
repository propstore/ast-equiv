from __future__ import annotations

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

import ast_equiv
from ast_equiv import canonical_dump, compare
from ast_equiv.comparison import Tier


IDENTIFIERS = st.sampled_from(("a", "b", "c", "n", "total", "item"))
CONSTANTS = st.integers(min_value=0, max_value=20)
OPS = st.sampled_from(("+", "-", "*"))


@pytest.mark.property
@given(name=IDENTIFIERS, const=CONSTANTS, op=OPS)
@settings(max_examples=80)
def test_X6_property_canonicalize_idempotent(name: str, const: int, op: str) -> None:
    """X-6: canonicalization is a fixed point for generated arithmetic."""
    body = f"def f({name}):\n    return ({name} {op} {const})"
    bindings = {name: "value"}

    once = canonical_dump(body, bindings)
    canonical_source = ast_equiv.normalize_to_concepts(body, bindings)
    twice = canonical_dump(canonical_source, {"value": "value"})

    assert once == twice


@pytest.mark.property
@given(name=IDENTIFIERS, const_a=CONSTANTS, const_b=CONSTANTS)
@settings(max_examples=80)
def test_X6_property_compare_transitive_for_generated_renames(
    name: str,
    const_a: int,
    const_b: int,
) -> None:
    """X-6: generated true-equivalence comparisons are transitive."""
    body_a = f"def f({name}):\n    y = {name} + {const_a}\n    return y + {const_b}"
    body_b = f"def f(q):\n    z = q + {const_a}\n    return z + {const_b}"
    body_c = f"def f(r):\n    return r + {const_a} + {const_b}"

    ab = compare(body_a, {name: "value"}, body_b, {"q": "value"})
    bc = compare(body_b, {"q": "value"}, body_c, {"r": "value"})
    ac = compare(body_a, {name: "value"}, body_c, {"r": "value"})

    if ab.equivalent and bc.equivalent:
        assert ac.equivalent is True


@pytest.mark.property
@given(local=IDENTIFIERS, free=IDENTIFIERS.filter(lambda value: value != "x"))
@settings(max_examples=50)
def test_generated_free_variable_extraction_excludes_binders(local: str, free: str) -> None:
    """RD-2 property: generated locals and comprehension targets are not free."""
    assume(free != local)

    body = (
        "def f(x):\n"
        f"    {local} = x + 1\n"
        f"    values = [{local} + {free} for {local} in x]\n"
        f"    return values[0] + {free}\n"
    )

    free_variables = ast_equiv.extract_free_variables(ast_equiv.parse_algorithm(body))

    assert free in free_variables
    assert "x" not in free_variables
    assert local not in free_variables
    assert "values" not in free_variables


@pytest.mark.property
@given(name=IDENTIFIERS, const=CONSTANTS)
@settings(max_examples=50)
def test_generated_tier_contract_accepts_true_equivalence_and_none_is_undecided(
    name: str,
    const: int,
) -> None:
    """WS-P contract: true tiers prove equivalence; NONE is undecided."""
    equivalent = compare(
        f"def f({name}):\n    return {name} + {const}",
        {name: "value"},
        f"def f(other):\n    return other + {const}",
        {"other": "value"},
    )
    different = compare(
        f"def f({name}):\n    return {name} + {const}",
        {name: "value"},
        f"def f(other):\n    return other + {const + 1}",
        {"other": "value"},
    )

    assert equivalent.tier in {Tier.CANONICAL, Tier.SYMPY, Tier.PARTIAL_EVAL}
    assert equivalent.equivalent is True
    assert different.tier is Tier.NONE
    assert different.equivalent is False
