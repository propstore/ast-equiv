"""AST equivalence comparison for algorithm implementations."""
from .canonicalizer import (
    parse_algorithm,
    extract_names,
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
    normalized_bytecode,
    bytecode_match,
    partial_eval_bytecode,
    partial_eval_match,
    structural_similarity,
)

__all__ = [
    "parse_algorithm",
    "extract_names",
    "normalize_to_concepts",
    "canonicalize",
    "canonical_dump",
    "structural_match",
    "AlgorithmParseError",
    "KNOWN_BUILTINS",
    "compare",
    "ComparisonResult",
    "Tier",
    "normalized_bytecode",
    "bytecode_match",
    "partial_eval_bytecode",
    "partial_eval_match",
    "structural_similarity",
]
