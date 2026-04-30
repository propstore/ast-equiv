"""AST equivalence comparison for algorithm implementations."""
from .canonicalizer import (
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
from .comparison import (
    compare,
    ComparisonResult,
    Tier,
    partial_eval_match,
    structural_similarity,
)

__all__ = [
    "parse_algorithm",
    "extract_all_names",
    "extract_free_variables",
    "normalize_to_concepts",
    "canonicalize",
    "canonical_dump",
    "structural_match",
    "AlgorithmParseError",
    "KNOWN_BUILTINS",
    "compare",
    "ComparisonResult",
    "Tier",
    "partial_eval_match",
    "structural_similarity",
]
