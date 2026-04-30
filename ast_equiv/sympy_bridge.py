"""SymPy-based expression comparison for algebraic equivalence."""
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


class SympyContext:
    """Symbol assumption context used while lowering AST nodes."""

    def __init__(
        self,
        *,
        assumptions: dict[str, dict[str, bool]] | None = None,
        assume_complex: bool = False,
        integer_default: bool = False,
    ):
        self.assumptions = assumptions or {}
        self.assume_complex = assume_complex
        self.integer_default = integer_default

    def for_integer_domain(self) -> "SympyContext":
        return SympyContext(
            assumptions=self.assumptions,
            assume_complex=self.assume_complex,
            integer_default=True,
        )

    def symbol(self, name: str) -> Any:
        explicit = dict(self.assumptions.get(name, {}))
        if self.integer_default and "integer" not in explicit:
            explicit["integer"] = True
        if not self.assume_complex:
            explicit.setdefault("real", True)
            explicit.setdefault("finite", True)
        return sympy.Symbol(name, **explicit)


def ast_to_sympy(
    node: ast.expr,
    *,
    context: SympyContext | None = None,
    assume_complex: bool = False,
) -> Any:
    """Convert a Python AST expression node to a SymPy expression."""
    if not HAS_SYMPY:
        raise AstToSympyError("sympy not installed")
    if context is None:
        context = SympyContext(assume_complex=assume_complex)

    if isinstance(node, ast.Constant):
        value = node.value
        if isinstance(value, bool):
            raise AstToSympyError("boolean constants not supported")
        if isinstance(value, int):
            return sympy.Integer(value)
        if isinstance(value, float):
            return sympy.Float(value)
        raise AstToSympyError(f"unsupported constant type: {type(value)}")

    if isinstance(node, ast.Name):
        return context.symbol(node.id)

    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.USub):
            return -ast_to_sympy(node.operand, context=context)
        if isinstance(node.op, ast.UAdd):
            return ast_to_sympy(node.operand, context=context)
        raise AstToSympyError(f"unsupported unary op: {type(node.op).__name__}")

    if isinstance(node, ast.BinOp):
        if isinstance(node.op, (ast.FloorDiv, ast.Mod)):
            op_context = context.for_integer_domain()
        else:
            op_context = context
        left = ast_to_sympy(node.left, context=op_context)
        right = ast_to_sympy(node.right, context=op_context)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.FloorDiv):
            return sympy.floor(left / right)
        if isinstance(node.op, ast.Mod):
            return sympy.Mod(left, right)
        if isinstance(node.op, ast.Pow):
            return left**right
        raise AstToSympyError(f"unsupported binary op: {type(node.op).__name__}")

    if isinstance(node, ast.Attribute):
        if (
            isinstance(node.value, ast.Name)
            and node.value.id == "math"
            and node.attr == "pi"
        ):
            return sympy.pi
        raise AstToSympyError(f"unsupported attribute: {ast.unparse(node)}")

    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            if node.func.value.id == "math":
                return _math_call_to_sympy(node, context)
        if isinstance(node.func, ast.Name) and node.func.id == "abs":
            if len(node.args) == 1 and not node.keywords:
                return sympy.Abs(ast_to_sympy(node.args[0], context=context))
        if isinstance(node.func, ast.Name) and node.func.id == "len":
            if len(node.args) == 1 and not node.keywords:
                symbol_name = f"len({ast.dump(node.args[0], include_attributes=False)})"
                return sympy.Symbol(symbol_name, integer=True, nonnegative=True)
        raise AstToSympyError(f"unsupported call: {ast.unparse(node)}")

    if isinstance(node, ast.Tuple):
        return tuple(ast_to_sympy(elt, context=context) for elt in node.elts)

    raise AstToSympyError(f"unsupported node type: {type(node).__name__}")


def _math_call_to_sympy(node: ast.Call, context: SympyContext) -> Any:
    if node.keywords:
        raise AstToSympyError(f"unsupported math call: {ast.unparse(node)}")
    function = node.func.attr
    args = [ast_to_sympy(arg, context=context) for arg in node.args]
    if function == "exp" and len(args) == 1:
        return sympy.exp(args[0])
    if function == "cos" and len(args) == 1:
        return sympy.cos(args[0])
    if function == "sin" and len(args) == 1:
        return sympy.sin(args[0])
    if function == "sqrt" and len(args) == 1:
        return sympy.sqrt(args[0])
    if function == "log" and len(args) in {1, 2}:
        return sympy.log(*args)
    if function == "log2" and len(args) == 1:
        return sympy.log(args[0], 2)
    if function == "log10" and len(args) == 1:
        return sympy.log(args[0], 10)
    raise AstToSympyError(f"unsupported math function: {function}")


def _sympy_expr_equal(expr_a: ast.expr, expr_b: ast.expr, context: SympyContext) -> bool:
    sym_a = ast_to_sympy(expr_a, context=context)
    sym_b = ast_to_sympy(expr_b, context=context)

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
    stmts = [copy.deepcopy(s) for s in stmts]
    while len(stmts) > target_count:
        inlined = False
        for i, stmt in enumerate(stmts):
            if (
                isinstance(stmt, ast.Assign)
                and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Name)
            ):
                var_name = stmt.targets[0].id
                rhs = stmt.value
                if _references_var(rhs, var_name):
                    continue
                mapping = {var_name: rhs}
                new_stmts = stmts[:i]
                for j in range(i + 1, len(stmts)):
                    new_stmt = _SubstituteNames(mapping).visit(copy.deepcopy(stmts[j]))
                    ast.fix_missing_locations(new_stmt)
                    new_stmts.append(new_stmt)
                stmts = new_stmts
                inlined = True
                break
        if not inlined:
            return None
    if len(stmts) == target_count:
        return stmts
    return None


def _references_var(node: ast.AST, var_name: str) -> bool:
    return any(isinstance(child, ast.Name) and child.id == var_name for child in ast.walk(node))


def _expr_equiv(a: ast.expr, b: ast.expr, context: SympyContext) -> bool:
    if ast.dump(a) == ast.dump(b):
        return True
    return _sympy_expr_equal(a, b, context)


def _stmts_equivalent(
    stmts_a: list[ast.stmt],
    stmts_b: list[ast.stmt],
    context: SympyContext,
) -> bool:
    stmts_a = _strip_asserts(stmts_a)
    stmts_b = _strip_asserts(stmts_b)
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
    return all(_stmt_equivalent(sa, sb, context) for sa, sb in zip(stmts_a, stmts_b))


def _stmt_equivalent(sa: ast.stmt, sb: ast.stmt, context: SympyContext) -> bool:
    if type(sa) is not type(sb):
        return False
    if isinstance(sa, ast.Import):
        return ast.dump(sa) == ast.dump(sb)
    if isinstance(sa, ast.Return):
        if sa.value is None and sb.value is None:
            return True
        if sa.value is None or sb.value is None:
            return False
        return _expr_equiv(sa.value, sb.value, context)
    if isinstance(sa, ast.Assign):
        if len(sa.targets) != len(sb.targets):
            return False
        for ta, tb in zip(sa.targets, sb.targets):
            if ast.dump(ta) != ast.dump(tb):
                return False
        return _expr_equiv(sa.value, sb.value, context)
    if isinstance(sa, ast.AugAssign):
        if ast.dump(sa.target) != ast.dump(sb.target) or type(sa.op) is not type(sb.op):
            return False
        return _expr_equiv(sa.value, sb.value, context)
    if isinstance(sa, ast.For):
        if ast.dump(sa.target) != ast.dump(sb.target) or ast.dump(sa.iter) != ast.dump(sb.iter):
            return False
        return _stmts_equivalent(sa.body, sb.body, context) and _stmts_equivalent(sa.orelse, sb.orelse, context)
    if isinstance(sa, ast.While):
        if ast.dump(sa.test) != ast.dump(sb.test):
            return False
        return _stmts_equivalent(sa.body, sb.body, context) and _stmts_equivalent(sa.orelse, sb.orelse, context)
    if isinstance(sa, ast.If):
        if ast.dump(sa.test) != ast.dump(sb.test):
            return False
        return _stmts_equivalent(sa.body, sb.body, context) and _stmts_equivalent(sa.orelse, sb.orelse, context)
    if isinstance(sa, ast.Expr):
        return _expr_equiv(sa.value, sb.value, context)
    if isinstance(sa, (ast.Break, ast.Continue, ast.Pass)):
        return True
    return ast.dump(sa) == ast.dump(sb)


def _extract_function(tree: ast.Module) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return node
    raise ValueError("No function definition found")


def _strip_asserts(stmts: list[ast.stmt]) -> list[ast.stmt]:
    return [stmt for stmt in stmts if not isinstance(stmt, ast.Assert)]


def _collect_positive_assertions(func: ast.FunctionDef) -> dict[str, dict[str, bool]]:
    assumptions: dict[str, dict[str, bool]] = {}
    for stmt in func.body:
        if not isinstance(stmt, ast.Assert):
            continue
        if (
            isinstance(stmt.test, ast.Compare)
            and isinstance(stmt.test.left, ast.Name)
            and len(stmt.test.ops) == 1
            and isinstance(stmt.test.ops[0], ast.Gt)
            and len(stmt.test.comparators) == 1
            and isinstance(stmt.test.comparators[0], ast.Constant)
            and stmt.test.comparators[0].value == 0
        ):
            assumptions.setdefault(stmt.test.left.id, {})["positive"] = True
    return assumptions


def _merge_assumptions(
    left: dict[str, dict[str, bool]],
    right: dict[str, dict[str, bool]],
) -> dict[str, dict[str, bool]]:
    merged: dict[str, dict[str, bool]] = {}
    for name in set(left) | set(right):
        values = {**left.get(name, {}), **right.get(name, {})}
        if values:
            merged[name] = values
    return merged


def sympy_expressions_equivalent(tree_a: ast.Module, tree_b: ast.Module) -> bool:
    """Check whether two canonicalized ASTs are algebraically equivalent."""
    if not HAS_SYMPY:
        return False

    func_a = _extract_function(tree_a)
    func_b = _extract_function(tree_b)
    if ast.dump(func_a.args) != ast.dump(func_b.args):
        return False

    context = SympyContext(
        assumptions=_merge_assumptions(
            _collect_positive_assertions(func_a),
            _collect_positive_assertions(func_b),
        )
    )
    return _stmts_equivalent(func_a.body, func_b.body, context)
