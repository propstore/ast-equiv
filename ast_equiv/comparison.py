"""Comparison ladder for algorithm equivalence."""
import ast
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from enum import Enum
from typing import Any

from .canonicalizer import (
    ConceptNormalizer,
    PositionalRenamer,
    TempVariableInliner,
    WhileToForNormalizer,
    canonical_dump,
    canonicalize,
    parse_algorithm,
    structural_match,
)
from .sympy_bridge import AstToSympyError, sympy_expressions_equivalent


class Tier(Enum):
    """Named comparison tiers with stable ordering for corpus expectations."""

    NONE = ("none", 0)
    CANONICAL = ("canonical", 1)
    SYMPY = ("sympy", 2)
    PARTIAL_EVAL = ("partial_eval", 4)

    def __init__(self, label: str, rank: int):
        self.label = label
        self.rank = rank

    def __le__(self, other: object) -> bool:
        if isinstance(other, Tier):
            return self.rank <= other.rank
        if isinstance(other, int):
            return self.rank <= other
        return NotImplemented

    def __lt__(self, other: object) -> bool:
        if isinstance(other, Tier):
            return self.rank < other.rank
        if isinstance(other, int):
            return self.rank < other
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        if isinstance(other, Tier):
            return self.rank >= other.rank
        if isinstance(other, int):
            return self.rank >= other
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        if isinstance(other, Tier):
            return self.rank > other.rank
        if isinstance(other, int):
            return self.rank > other
        return NotImplemented


@dataclass
class ComparisonResult:
    """Result of comparing two algorithm implementations."""

    equivalent: bool
    tier: Tier
    similarity: float
    details: str = ""
    tier_failures: dict[Tier, type[Exception]] = field(default_factory=dict)


def _normalize_and_canonicalize(body: str, bindings: dict[str, str]) -> ast.Module:
    """Parse, normalize to concepts, alpha-rename, and canonicalize."""
    tree = parse_algorithm(body)
    normalizer = ConceptNormalizer(bindings)
    tree = normalizer.visit(tree)
    ast.fix_missing_locations(tree)
    concept_names = frozenset(bindings.values())
    tree = PositionalRenamer.rename(tree, concept_names=concept_names)
    tree = WhileToForNormalizer().visit(tree)
    ast.fix_missing_locations(tree)
    tree = TempVariableInliner().visit(tree)
    ast.fix_missing_locations(tree)
    tree = canonicalize(tree)
    return tree


class ParameterSubstituter(ast.NodeTransformer):
    """Substitute known parameter values into the AST."""

    def __init__(self, known_values: dict[str, Any]):
        self.known_values = known_values

    def visit_Name(self, node: ast.Name) -> ast.AST:
        if isinstance(node.ctx, ast.Load) and node.id in self.known_values:
            return ast.Constant(value=self.known_values[node.id])
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        if node.args and node.args.args:
            node.args.args = [
                arg for arg in node.args.args
                if arg.arg not in self.known_values
            ]
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        return self.visit_FunctionDef(node)


def _partial_eval_tree(
    body: str,
    bindings: dict[str, str],
    known_values: dict[str, Any],
) -> ast.Module:
    tree = parse_algorithm(body)
    tree = ConceptNormalizer(bindings).visit(tree)
    ast.fix_missing_locations(tree)
    tree = ParameterSubstituter(known_values).visit(tree)
    ast.fix_missing_locations(tree)
    concept_names = frozenset(bindings.values())
    tree = PositionalRenamer.rename(tree, concept_names=concept_names)
    tree = WhileToForNormalizer().visit(tree)
    ast.fix_missing_locations(tree)
    tree = TempVariableInliner().visit(tree)
    ast.fix_missing_locations(tree)
    tree = canonicalize(tree)
    return tree


def partial_eval_match(
    body_a: str,
    bindings_a: dict,
    body_b: str,
    bindings_b: dict,
    known_values: dict[str, Any] | None = None,
) -> bool:
    """Compare canonical ASTs after substituting known concept values."""
    if not known_values:
        return False
    tree_a = _partial_eval_tree(body_a, bindings_a, known_values)
    tree_b = _partial_eval_tree(body_b, bindings_b, known_values)
    if ast.dump(tree_a, include_attributes=False) == ast.dump(tree_b, include_attributes=False):
        return True
    return sympy_expressions_equivalent(tree_a, tree_b)


def _ast_node_signatures(tree: ast.AST) -> list[str]:
    """Extract sequence of node signatures from an AST via walk."""
    sigs = []
    for node in ast.walk(tree):
        sig = type(node).__name__
        if isinstance(node, ast.Constant):
            sig += f"={node.value!r}"
        elif isinstance(node, ast.Name):
            sig += f"={node.id}"
        elif isinstance(
            node,
            (
                ast.Add,
                ast.Sub,
                ast.Mult,
                ast.Div,
                ast.FloorDiv,
                ast.Mod,
                ast.Pow,
                ast.BitAnd,
                ast.BitOr,
                ast.BitXor,
                ast.LShift,
                ast.RShift,
                ast.Eq,
                ast.NotEq,
                ast.Lt,
                ast.LtE,
                ast.Gt,
                ast.GtE,
                ast.Is,
                ast.IsNot,
                ast.In,
                ast.NotIn,
                ast.And,
                ast.Or,
                ast.Not,
                ast.USub,
                ast.UAdd,
                ast.Invert,
            ),
        ):
            pass
        elif isinstance(node, ast.Attribute):
            sig += f"={node.attr}"
        sigs.append(sig)
    return sigs


def structural_similarity(tree_a: ast.Module, tree_b: ast.Module) -> float:
    """Compute structural similarity between two ASTs."""
    sigs_a = _ast_node_signatures(tree_a)
    sigs_b = _ast_node_signatures(tree_b)
    return SequenceMatcher(None, sigs_a, sigs_b).ratio()


def compare(
    body_a: str,
    bindings_a: dict,
    body_b: str,
    bindings_b: dict,
    known_values: dict[str, Any] | None = None,
) -> ComparisonResult:
    """Compare two algorithms through canonical, SymPy, and partial-eval tiers."""
    tier_failures: dict[Tier, type[Exception]] = {}
    tree_a = _normalize_and_canonicalize(body_a, bindings_a)
    tree_b = _normalize_and_canonicalize(body_b, bindings_b)
    similarity = structural_similarity(tree_a, tree_b)

    dump_a = canonical_dump(body_a, bindings_a)
    dump_b = canonical_dump(body_b, bindings_b)
    if structural_match(dump_a, dump_b):
        return ComparisonResult(
            equivalent=True,
            tier=Tier.CANONICAL,
            similarity=1.0,
            details="Canonical AST match",
            tier_failures=tier_failures,
        )

    try:
        if sympy_expressions_equivalent(tree_a, tree_b):
            return ComparisonResult(
                equivalent=True,
                tier=Tier.SYMPY,
                similarity=similarity,
                details="SymPy algebraic equivalence",
                tier_failures=tier_failures,
            )
    except AstToSympyError as exc:
        tier_failures[Tier.SYMPY] = type(exc)

    if known_values:
        try:
            if partial_eval_match(body_a, bindings_a, body_b, bindings_b, known_values):
                return ComparisonResult(
                    equivalent=True,
                    tier=Tier.PARTIAL_EVAL,
                    similarity=similarity,
                    details="Partial evaluation match",
                    tier_failures=tier_failures,
                )
        except AstToSympyError as exc:
            tier_failures[Tier.PARTIAL_EVAL] = type(exc)

    return ComparisonResult(
        equivalent=False,
        tier=Tier.NONE,
        similarity=similarity,
        details="No equivalence found",
        tier_failures=tier_failures,
    )
