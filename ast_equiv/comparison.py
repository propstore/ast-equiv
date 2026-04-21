"""Five-tier comparison ladder for algorithm equivalence."""
import ast
import dis
from dataclasses import dataclass
from difflib import SequenceMatcher
from enum import Enum
from typing import Any

from .canonicalizer import (
    parse_algorithm,
    ConceptNormalizer,
    PositionalRenamer,
    WhileToForNormalizer,
    TempVariableInliner,
    canonicalize,
    canonical_dump,
    structural_match,
)
from .sympy_bridge import sympy_expressions_equivalent


# Opcodes to skip: vary by source layout, not semantics
SKIP_OPS = frozenset({
    "RESUME", "NOP", "CACHE", "PRECALL", "COPY_FREE_VARS",
    "PUSH_NULL",  # Python 3.11+
})

# Augmented assignment BINARY_OP args are offset by 13 from plain ones.
# e.g. + is 0, += is 13; * is 5, *= is 18
_INPLACE_OFFSET = 13


class Tier(Enum):
    """Named comparison tiers with stable ordering for corpus expectations."""

    NONE = ("none", 0)
    CANONICAL = ("canonical", 1)
    SYMPY = ("sympy", 2)
    BYTECODE = ("bytecode", 3)
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
    similarity: float  # 0.0-1.0 structural similarity
    details: str = ""


def _normalize_and_canonicalize(body: str, bindings: dict[str, str]) -> ast.Module:
    """Parse, normalize to concepts, alpha-rename, and canonicalize."""
    tree = parse_algorithm(body)
    normalizer = ConceptNormalizer(bindings)
    tree = normalizer.visit(tree)
    ast.fix_missing_locations(tree)
    tree = PositionalRenamer.rename(tree)
    tree = WhileToForNormalizer().visit(tree)
    ast.fix_missing_locations(tree)
    tree = TempVariableInliner().visit(tree)
    ast.fix_missing_locations(tree)
    tree = canonicalize(tree)
    return tree


def _extract_function(tree: ast.Module) -> ast.FunctionDef:
    """Extract the first function definition from a module."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return node
    raise ValueError("No function definition found")


def _compile_to_bytecode(tree: ast.Module) -> list[tuple]:
    """Compile an AST to bytecode instruction sequence."""
    source = ast.unparse(tree)
    code = compile(source, "<ast-equiv>", "exec")
    # Find the function code object
    func_code = None
    for const in code.co_consts:
        if hasattr(const, 'co_code'):
            func_code = const
            break
    if func_code is None:
        func_code = code

    instructions = []
    for instr in dis.get_instructions(func_code):
        if instr.opname not in SKIP_OPS:
            argval = instr.argval
            # Normalize augmented assignment ops to plain ops
            # e.g. += (13) -> + (0), *= (18) -> * (5)
            if instr.opname == "BINARY_OP" and isinstance(argval, int) and argval >= _INPLACE_OFFSET:
                argval = argval - _INPLACE_OFFSET
            instructions.append((instr.opname, argval))
    return instructions


def normalized_bytecode(body: str, bindings: dict[str, str]) -> list[tuple]:
    """Normalize and compile to bytecode instruction sequence."""
    tree = _normalize_and_canonicalize(body, bindings)
    return _compile_to_bytecode(tree)


def bytecode_match(body_a: str, bindings_a: dict, body_b: str, bindings_b: dict) -> bool:
    """Compare normalized bytecode of two implementations."""
    bc_a = normalized_bytecode(body_a, bindings_a)
    bc_b = normalized_bytecode(body_b, bindings_b)
    return bc_a == bc_b


class ParameterSubstituter(ast.NodeTransformer):
    """Substitute known parameter values into the AST."""

    def __init__(self, known_values: dict[str, Any]):
        self.known_values = known_values

    def visit_Name(self, node: ast.Name) -> ast.AST:
        if node.id in self.known_values:
            return ast.Constant(value=self.known_values[node.id])
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        # Remove substituted parameters from function signature
        if node.args and node.args.args:
            node.args.args = [
                arg for arg in node.args.args
                if arg.arg not in self.known_values
            ]
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        return self.visit_FunctionDef(node)


def partial_eval_bytecode(body: str, bindings: dict[str, str], known_values: dict[str, Any]) -> list[tuple]:
    """Parse, normalize, substitute known values, canonicalize, compile to bytecode."""
    tree = parse_algorithm(body)
    normalizer = ConceptNormalizer(bindings)
    tree = normalizer.visit(tree)
    ast.fix_missing_locations(tree)

    # Apply parameter substitution using concept names
    substituter = ParameterSubstituter(known_values)
    tree = substituter.visit(tree)
    ast.fix_missing_locations(tree)

    tree = PositionalRenamer.rename(tree)
    tree = WhileToForNormalizer().visit(tree)
    ast.fix_missing_locations(tree)
    tree = TempVariableInliner().visit(tree)
    ast.fix_missing_locations(tree)
    tree = canonicalize(tree)
    return _compile_to_bytecode(tree)


def partial_eval_match(
    body_a: str, bindings_a: dict,
    body_b: str, bindings_b: dict,
    known_values: dict[str, Any] | None = None,
) -> bool:
    """Compare bytecode after partial evaluation with known values."""
    if not known_values:
        return bytecode_match(body_a, bindings_a, body_b, bindings_b)
    bc_a = partial_eval_bytecode(body_a, bindings_a, known_values)
    bc_b = partial_eval_bytecode(body_b, bindings_b, known_values)
    return bc_a == bc_b


def _ast_node_signatures(tree: ast.AST) -> list[str]:
    """Extract sequence of node signatures from an AST via walk.

    Includes node type plus distinguishing values (constants, names, ops)
    to prevent purely structural matches between semantically different trees.
    """
    sigs = []
    for node in ast.walk(tree):
        sig = type(node).__name__
        if isinstance(node, ast.Constant):
            sig += f"={node.value!r}"
        elif isinstance(node, ast.Name):
            sig += f"={node.id}"
        elif isinstance(node, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv,
                               ast.Mod, ast.Pow, ast.BitAnd, ast.BitOr, ast.BitXor,
                               ast.LShift, ast.RShift, ast.Eq, ast.NotEq, ast.Lt,
                               ast.LtE, ast.Gt, ast.GtE, ast.Is, ast.IsNot,
                               ast.In, ast.NotIn, ast.And, ast.Or, ast.Not,
                               ast.USub, ast.UAdd, ast.Invert)):
            pass  # type name is enough for operators
        elif isinstance(node, ast.Attribute):
            sig += f"={node.attr}"
        sigs.append(sig)
    return sigs


def structural_similarity(tree_a: ast.Module, tree_b: ast.Module) -> float:
    """Compute structural similarity between two ASTs.

    Returns 1.0 for identical trees, values based on SequenceMatcher ratio
    for differing trees.
    """
    sigs_a = _ast_node_signatures(tree_a)
    sigs_b = _ast_node_signatures(tree_b)
    return SequenceMatcher(None, sigs_a, sigs_b).ratio()


def compare(
    body_a: str, bindings_a: dict,
    body_b: str, bindings_b: dict,
    known_values: dict[str, Any] | None = None,
) -> ComparisonResult:
    """Comparison ladder.

    Tier 1: Canonical AST match (structural_match on canonical_dump)
    Tier 2: SymPy algebraic equivalence or bytecode match
    Tier 3: Bytecode match
    Tier 4: Partial evaluation match (if known_values provided)
    """
    # Compute similarity for all paths
    tree_a = _normalize_and_canonicalize(body_a, bindings_a)
    tree_b = _normalize_and_canonicalize(body_b, bindings_b)
    similarity = structural_similarity(tree_a, tree_b)

    # Tier 1: Canonical AST match
    dump_a = canonical_dump(body_a, bindings_a)
    dump_b = canonical_dump(body_b, bindings_b)
    if structural_match(dump_a, dump_b):
        return ComparisonResult(
            equivalent=True, tier=Tier.CANONICAL, similarity=1.0,
            details="Canonical AST match",
        )

    # Tier 1.5: SymPy algebraic equivalence on canonical trees
    try:
        if sympy_expressions_equivalent(tree_a, tree_b):
            return ComparisonResult(
                equivalent=True, tier=Tier.SYMPY, similarity=similarity,
                details="SymPy algebraic equivalence",
            )
    except Exception:
        pass

    # Tier 2: Bytecode match
    try:
        if bytecode_match(body_a, bindings_a, body_b, bindings_b):
            return ComparisonResult(
                equivalent=True, tier=Tier.BYTECODE, similarity=similarity,
                details="Bytecode match",
            )
    except Exception:
        pass

    # Tier 3: Partial evaluation match
    if known_values:
        try:
            if partial_eval_match(body_a, bindings_a, body_b, bindings_b, known_values):
                return ComparisonResult(
                    equivalent=True, tier=Tier.PARTIAL_EVAL, similarity=similarity,
                    details="Partial evaluation match",
                )
        except Exception:
            pass

    # Tier 4: Reserved for future runtime-based comparison
    # Structural similarity alone is unreliable for equivalence claims
    # (e.g., `a and b` vs `a or b` have near-identical ASTs but different semantics)

    return ComparisonResult(
        equivalent=False, tier=Tier.NONE, similarity=similarity,
        details="No equivalence found",
    )
