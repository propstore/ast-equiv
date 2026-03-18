"""SymPy-based expression comparison for algebraic equivalence.

Converts Python AST expressions to SymPy expressions and uses
sympy.simplify to check algebraic equivalence. Handles patterns
like x/d + y/d vs (x+y)/d, a*a vs a**2, -exp(-x) vs -exp(-(x)).

Strategy: walk both canonical ASTs in parallel. At each statement pair,
require structural equivalence for control flow and use SymPy for
expression comparison. When statement counts differ, inline assignments
on the longer side to try to match the shorter side's structure.
"""
import ast
import copy
from typing import Any

try:
    import sympy
    HAS_SYMPY = True
except ImportError:
    HAS_SYMPY = False


class AstToSympyError(Exception):
    """Raised when an AST node cannot be converted to SymPy."""
    pass


def ast_to_sympy(node: ast.expr) -> Any:
    """Convert a Python AST expression node to a SymPy expression.

    Returns a SymPy expression, or raises AstToSympyError if the node
    type is not supported.
    """
    if not HAS_SYMPY:
        raise AstToSympyError("sympy not installed")

    if isinstance(node, ast.Constant):
        v = node.value
        if isinstance(v, bool):
            raise AstToSympyError("boolean constants not supported")
        if isinstance(v, int):
            return sympy.Integer(v)
        if isinstance(v, float):
            return sympy.Float(v)
        raise AstToSympyError(f"unsupported constant type: {type(v)}")

    if isinstance(node, ast.Name):
        return sympy.Symbol(node.id)

    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.USub):
            operand = ast_to_sympy(node.operand)
            return -operand
        if isinstance(node.op, ast.UAdd):
            return ast_to_sympy(node.operand)
        raise AstToSympyError(f"unsupported unary op: {type(node.op).__name__}")

    if isinstance(node, ast.BinOp):
        left = ast_to_sympy(node.left)
        right = ast_to_sympy(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Pow):
            return left ** right
        raise AstToSympyError(f"unsupported binary op: {type(node.op).__name__}")

    # math.pi attribute access
    if isinstance(node, ast.Attribute):
        if (isinstance(node.value, ast.Name) and node.value.id == "math"
                and node.attr == "pi"):
            return sympy.pi
        raise AstToSympyError(f"unsupported attribute: {ast.unparse(node)}")

    # Function calls: math.exp, math.cos, math.sin, math.log, math.sqrt, abs
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            if node.func.value.id == "math":
                if len(node.args) != 1 or node.keywords:
                    raise AstToSympyError(
                        f"unsupported math call: {ast.unparse(node)}"
                    )
                arg = ast_to_sympy(node.args[0])
                fn = node.func.attr
                if fn == "exp":
                    return sympy.exp(arg)
                if fn == "cos":
                    return sympy.cos(arg)
                if fn == "sin":
                    return sympy.sin(arg)
                if fn == "log":
                    return sympy.log(arg)
                if fn == "sqrt":
                    return sympy.sqrt(arg)
                if fn == "log10":
                    return sympy.log(arg, 10)
                raise AstToSympyError(f"unsupported math function: {fn}")

        if isinstance(node.func, ast.Name) and node.func.id == "abs":
            if len(node.args) == 1 and not node.keywords:
                arg = ast_to_sympy(node.args[0])
                return sympy.Abs(arg)

        raise AstToSympyError(f"unsupported call: {ast.unparse(node)}")

    if isinstance(node, ast.Tuple):
        return tuple(ast_to_sympy(elt) for elt in node.elts)

    raise AstToSympyError(f"unsupported node type: {type(node).__name__}")


def _sympy_expr_equal(expr_a: ast.expr, expr_b: ast.expr) -> bool:
    """Check if two AST expressions are algebraically equivalent via SymPy."""
    try:
        sym_a = ast_to_sympy(expr_a)
        sym_b = ast_to_sympy(expr_b)
    except AstToSympyError:
        return False

    if isinstance(sym_a, tuple) and isinstance(sym_b, tuple):
        if len(sym_a) != len(sym_b):
            return False
        return all(sympy.simplify(a - b) == 0 for a, b in zip(sym_a, sym_b))
    if isinstance(sym_a, tuple) or isinstance(sym_b, tuple):
        return False

    return sympy.simplify(sym_a - sym_b) == 0


class _SubstituteNames(ast.NodeTransformer):
    """Substitute Name(Load) nodes with their mapped expressions."""

    def __init__(self, mapping: dict[str, ast.expr]):
        self.mapping = mapping

    def visit_Name(self, node: ast.Name) -> ast.AST:
        if isinstance(node.ctx, ast.Load) and node.id in self.mapping:
            return copy.deepcopy(self.mapping[node.id])
        return node


def _reduce_stmts(stmts: list[ast.stmt], target_count: int) -> list[ast.stmt] | None:
    """Try to reduce a statement list to target_count by inlining assignments.

    Inlines simple local assignments (var = expr) into subsequent statements,
    removing the assignment. Only inlines non-self-referencing assignments.
    Stops when the target count is reached.

    Returns the reduced list, or None if reduction to target_count is impossible.
    """
    stmts = [copy.deepcopy(s) for s in stmts]
    while len(stmts) > target_count:
        # Find the first inlinable assignment
        inlined = False
        for i, stmt in enumerate(stmts):
            if (isinstance(stmt, ast.Assign)
                    and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)):
                var_name = stmt.targets[0].id
                rhs = stmt.value
                # Don't inline self-referencing (accumulator) assignments
                if _references_var(rhs, var_name):
                    continue
                # Inline: substitute into all subsequent statements, remove this one
                mapping = {var_name: rhs}
                new_stmts = stmts[:i]
                for j in range(i + 1, len(stmts)):
                    s = _SubstituteNames(mapping).visit(copy.deepcopy(stmts[j]))
                    ast.fix_missing_locations(s)
                    new_stmts.append(s)
                stmts = new_stmts
                inlined = True
                break
        if not inlined:
            return None  # Can't reduce further
    if len(stmts) == target_count:
        return stmts
    return None


def _references_var(node: ast.AST, var_name: str) -> bool:
    """Check if an AST node references a variable by name."""
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and child.id == var_name:
            return True
    return False


def _expr_equiv(a: ast.expr, b: ast.expr) -> bool:
    """Check expression equivalence: first exact AST, then SymPy."""
    if ast.dump(a) == ast.dump(b):
        return True
    return _sympy_expr_equal(a, b)


def _stmts_equivalent(stmts_a: list[ast.stmt], stmts_b: list[ast.stmt]) -> bool:
    """Check if two statement lists are structurally equivalent with SymPy for expressions.

    If lengths differ, tries to reduce the longer list by inlining assignments.
    """
    # Try to match lengths by reducing the longer side
    if len(stmts_a) != len(stmts_b):
        if len(stmts_a) > len(stmts_b):
            reduced = _reduce_stmts(stmts_a, len(stmts_b))
            if reduced is None:
                return False
            stmts_a = reduced
        else:
            reduced = _reduce_stmts(stmts_b, len(stmts_a))
            if reduced is None:
                return False
            stmts_b = reduced

    if len(stmts_a) != len(stmts_b):
        return False

    return all(_stmt_equivalent(sa, sb) for sa, sb in zip(stmts_a, stmts_b))


def _stmt_equivalent(sa: ast.stmt, sb: ast.stmt) -> bool:
    """Check if two statements are equivalent (structural + SymPy for expressions)."""
    if type(sa) != type(sb):
        return False

    if isinstance(sa, ast.Import):
        return ast.dump(sa) == ast.dump(sb)

    if isinstance(sa, ast.Return):
        if sa.value is None and sb.value is None:
            return True
        if sa.value is None or sb.value is None:
            return False
        return _expr_equiv(sa.value, sb.value)

    if isinstance(sa, ast.Assign):
        if len(sa.targets) != len(sb.targets):
            return False
        for ta, tb in zip(sa.targets, sb.targets):
            if ast.dump(ta) != ast.dump(tb):
                return False
        return _expr_equiv(sa.value, sb.value)

    if isinstance(sa, ast.AugAssign):
        if ast.dump(sa.target) != ast.dump(sb.target):
            return False
        if type(sa.op) != type(sb.op):
            return False
        return _expr_equiv(sa.value, sb.value)

    if isinstance(sa, ast.For):
        if ast.dump(sa.target) != ast.dump(sb.target):
            return False
        if ast.dump(sa.iter) != ast.dump(sb.iter):
            return False
        if not _stmts_equivalent(sa.body, sb.body):
            return False
        return _stmts_equivalent(sa.orelse, sb.orelse)

    if isinstance(sa, ast.While):
        if ast.dump(sa.test) != ast.dump(sb.test):
            return False
        if not _stmts_equivalent(sa.body, sb.body):
            return False
        return _stmts_equivalent(sa.orelse, sb.orelse)

    if isinstance(sa, ast.If):
        if ast.dump(sa.test) != ast.dump(sb.test):
            return False
        if not _stmts_equivalent(sa.body, sb.body):
            return False
        return _stmts_equivalent(sa.orelse, sb.orelse)

    if isinstance(sa, ast.Expr):
        return _expr_equiv(sa.value, sb.value)

    if isinstance(sa, (ast.Break, ast.Continue, ast.Pass)):
        return True

    return ast.dump(sa) == ast.dump(sb)


def _extract_function(tree: ast.Module) -> ast.FunctionDef:
    """Extract the first function definition from a module."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return node
    raise ValueError("No function definition found")


def sympy_expressions_equivalent(tree_a: ast.Module, tree_b: ast.Module) -> bool:
    """Check if two canonicalized ASTs are algebraically equivalent using SymPy.

    Walks both function bodies in parallel. If statement counts differ at
    any level, tries to reduce the longer side by inlining assignments
    (only on the side with more statements). Uses SymPy to compare
    expression subtrees that differ.

    Returns True only if:
    1. Function signatures match
    2. Statement structures can be aligned (possibly with targeted inlining)
    3. All expression differences are algebraically equivalent per SymPy
    """
    if not HAS_SYMPY:
        return False

    func_a = _extract_function(tree_a)
    func_b = _extract_function(tree_b)

    if ast.dump(func_a.args) != ast.dump(func_b.args):
        return False

    return _stmts_equivalent(func_a.body, func_b.body)
