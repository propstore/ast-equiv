"""Parametrized tests over the full corpus."""
import pytest
from tests.algorithm_corpus import load_corpus
from ast_equiv.comparison import compare


CORPUS = load_corpus()


@pytest.mark.parametrize(
    "pair",
    CORPUS,
    ids=lambda p: f"{p.get('source', 'unknown')}/{p['name']}",
)
def test_corpus_pair(pair):
    result = compare(
        pair["body_a"], pair["bindings_a"],
        pair["body_b"], pair["bindings_b"],
        known_values=pair.get("known_values", {}),
    )
    assert result.equivalent == pair["expected_equivalent"], (
        f"Expected equivalent={pair['expected_equivalent']} but got {result.equivalent} "
        f"(tier={result.tier}, similarity={result.similarity:.3f})"
    )
    if pair.get("expected_min_tier") and result.equivalent:
        assert result.tier <= pair["expected_min_tier"], (
            f"Expected tier <= {pair['expected_min_tier']} but got tier {result.tier}"
        )
