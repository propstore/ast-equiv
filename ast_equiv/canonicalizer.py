"""AST canonicalization for algorithm equivalence comparison."""
import ast
import operator
from typing import Any


class AlgorithmParseError(Exception):
    """Raised when algorithm source cannot be parsed into a valid function."""
    pass


KNOWN_BUILTINS = frozenset({
    "len", "range", "print", "min", "max", "sum", "abs",
    "int", "float", "str", "list", "dict", "set", "tuple",
    "enumerate", "zip", "map", "filter", "sorted", "reversed",
    "any", "all", "isinstance", "type", "round", "pow",
    "bool", "bytes", "bytearray", "complex", "frozenset",
    "hash", "hex", "id", "input", "iter", "next", "oct",
    "open", "ord", "chr", "repr", "super", "vars",
    "hasattr", "getattr", "setattr", "delattr",
    "callable", "classmethod", "staticmethod", "property",
    "ValueError", "TypeError", "KeyError", "IndexError",
    "AttributeError", "RuntimeError", "StopIteration",
    "Exception", "True", "False", "None",
})


def parse_algorithm(body: str) -> ast.Module:
    """Parse source into an AST Module containing exactly one function definition."""
    if not body or not body.strip():
        raise AlgorithmParseError("Empty body")
    try:
        tree = ast.parse(body)
    except SyntaxError as e:
        raise AlgorithmParseError(f"Syntax error: {e}") from e

    func_defs = [
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    if not func_defs:
        raise AlgorithmParseError("No function definition found at module level")

    return tree


def extract_names(tree: ast.Module) -> set[str]:
    """Walk AST and collect all Name node ids, plus function argument names."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
    return names


class ConceptNormalizer(ast.NodeTransformer):
    """Replace local names with concept names per bindings dict."""

    def __init__(self, bindings: dict[str, str]):
        self.bindings = bindings

    def visit_Name(self, node: ast.Name) -> ast.Name:
        if node.id in self.bindings:
            node.id = self.bindings[node.id]
        return node

    def visit_arg(self, node: ast.arg) -> ast.arg:
        if node.arg in self.bindings:
            node.arg = self.bindings[node.arg]
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        # Normalize function name to a canonical name
        node.name = "algorithm"
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        node.name = "algorithm"
        self.generic_visit(node)
        return node


def normalize_to_concepts(body: str, bindings: dict[str, str]) -> str:
    """Parse, apply concept normalization, return unparsed source."""
    tree = parse_algorithm(body)
    normalizer = ConceptNormalizer(bindings)
    tree = normalizer.visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


# Safe operators for constant folding
_SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.BitAnd: operator.and_,
    ast.BitOr: operator.or_,
    ast.BitXor: operator.xor,
    ast.LShift: operator.lshift,
    ast.RShift: operator.rshift,
}

_COMMUTATIVE_OPS = (ast.Add, ast.Mult)


class Canonicalizer(ast.NodeTransformer):
    """Apply canonical transformations to normalize AST structure."""

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        # Strip docstrings
        if (node.body and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)):
            node.body = node.body[1:]

        # Dead code removal: remove statements after Return
        new_body = []
        for stmt in node.body:
            new_body.append(stmt)
            if isinstance(stmt, ast.Return):
                break
        node.body = new_body

        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        return self.visit_FunctionDef(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> ast.AST:
        """Normalize x += y to x = x + y."""
        self.generic_visit(node)
        # Build x = x op y
        target_copy = ast.Name(id=node.target.id, ctx=ast.Load()) if isinstance(node.target, ast.Name) else node.target
        binop = ast.BinOp(left=target_copy, op=node.op, right=node.value)
        # Visit the new BinOp so commutative sort / constant folding applies
        binop = self.visit_BinOp(binop)
        assign = ast.Assign(
            targets=[node.target],
            value=binop,
        )
        return ast.copy_location(assign, node)

    def visit_Call(self, node: ast.Call) -> ast.AST:
        self.generic_visit(node)
        # Range normalization
        if isinstance(node.func, ast.Name) and node.func.id == "range":
            args = node.args
            if len(args) == 3:
                # range(0, N, 1) -> range(N)
                start, stop, step = args
                if (_is_constant(start, 0) and _is_constant(step, 1)):
                    node.args = [stop]
            elif len(args) == 2:
                # range(0, N) -> range(N)
                start, stop = args
                if _is_constant(start, 0):
                    node.args = [stop]
        return node

    def visit_Compare(self, node: ast.Compare) -> ast.AST:
        self.generic_visit(node)
        # Boolean normalization: x == True -> x, x == False -> not x
        if (len(node.ops) == 1 and len(node.comparators) == 1):
            op = node.ops[0]
            comp = node.comparators[0]
            if isinstance(op, ast.Eq):
                if _is_constant(comp, True):
                    return node.left
                if _is_constant(comp, False):
                    return ast.UnaryOp(op=ast.Not(), operand=node.left)
        return node

    def visit_BoolOp(self, node: ast.BoolOp) -> ast.AST:
        self.generic_visit(node)
        # Chained comparison collapse:
        # BoolOp(And, [Compare(left, [op1], [mid]), Compare(mid2, [op2], [right])])
        # where ast.dump(mid) == ast.dump(mid2)
        # -> Compare(left, [op1, op2], [mid, right])
        if (isinstance(node.op, ast.And) and len(node.values) == 2
                and isinstance(node.values[0], ast.Compare)
                and isinstance(node.values[1], ast.Compare)):
            cmp1, cmp2 = node.values
            if (len(cmp1.ops) == 1 and len(cmp1.comparators) == 1
                    and len(cmp2.ops) == 1 and len(cmp2.comparators) == 1):
                mid1 = cmp1.comparators[0]
                mid2 = cmp2.left
                if ast.dump(mid1) == ast.dump(mid2):
                    return ast.Compare(
                        left=cmp1.left,
                        ops=[cmp1.ops[0], cmp2.ops[0]],
                        comparators=[mid1, cmp2.comparators[0]],
                    )
        return node

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        self.generic_visit(node)
        # Constant folding
        if isinstance(node.left, ast.Constant) and isinstance(node.right, ast.Constant):
            op_type = type(node.op)
            if op_type in _SAFE_OPS:
                try:
                    result = _SAFE_OPS[op_type](node.left.value, node.right.value)
                    return ast.Constant(value=result)
                except (ZeroDivisionError, OverflowError, ValueError):
                    pass

        # Identity elimination: x + 0 -> x, 0 + x -> x
        op_type = type(node.op)
        if op_type is ast.Add:
            if _is_constant_value(node.right, 0):
                return node.left
            if _is_constant_value(node.left, 0):
                return node.right
        # Identity elimination: x * 1 -> x, 1 * x -> x
        elif op_type is ast.Mult:
            if _is_constant_value(node.right, 1):
                return node.left
            if _is_constant_value(node.left, 1):
                return node.right
        # Identity elimination: x - 0 -> x
        elif op_type is ast.Sub:
            if _is_constant_value(node.right, 0):
                return node.left
        # Identity elimination: x ** 1 -> x
        elif op_type is ast.Pow:
            if _is_constant_value(node.right, 1):
                return node.left

        # Commutative sort: for *, sort operands by ast.dump()
        # Note: Add is excluded because + is overloaded for lists/strings (not commutative)
        if op_type is ast.Mult:
            left_dump = ast.dump(node.left)
            right_dump = ast.dump(node.right)
            if left_dump > right_dump:
                node.left, node.right = node.right, node.left

        return node


_COMPARE_OPS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.Is: lambda a, b: a is b,
    ast.IsNot: lambda a, b: a is not b,
}


class ConstantComparisonFolder(ast.NodeTransformer):
    """Evaluate Compare nodes where all operands are constants.

    E.g. 'mean' == 'sum' -> Constant(False), 'mean' == 'mean' -> Constant(True).
    """

    def visit_Compare(self, node: ast.Compare) -> ast.AST:
        self.generic_visit(node)
        # All operands must be constants
        if not isinstance(node.left, ast.Constant):
            return node
        if not all(isinstance(c, ast.Constant) for c in node.comparators):
            return node

        # Evaluate the chain: left op1 comp1 op2 comp2 ...
        left_val = node.left.value
        for op, comparator in zip(node.ops, node.comparators):
            op_type = type(op)
            if op_type not in _COMPARE_OPS:
                return node
            try:
                if not _COMPARE_OPS[op_type](left_val, comparator.value):
                    return ast.Constant(value=False)
            except TypeError:
                return node
            left_val = comparator.value
        return ast.Constant(value=True)


class DeadBranchEliminator(ast.NodeTransformer):
    """Eliminate If nodes where the test is a constant True/False.

    - If(test=Constant(True)) -> replace with body statements
    - If(test=Constant(False)) with orelse -> replace with orelse statements
    - If(test=Constant(False)) without orelse -> remove entirely
    """

    def visit_If(self, node: ast.If) -> Any:
        self.generic_visit(node)
        if isinstance(node.test, ast.Constant):
            if node.test.value:
                # True branch: replace with body
                return node.body
            else:
                # False branch: replace with orelse or remove
                if node.orelse:
                    return node.orelse
                return []  # remove entirely
        return node


def _is_constant(node: ast.AST, value: Any) -> bool:
    """Check if node is a Constant with the given value (identity check)."""
    return isinstance(node, ast.Constant) and node.value is value


def _is_constant_value(node: ast.AST, value: Any) -> bool:
    """Check if node is a Constant with the given value (equality check)."""
    return isinstance(node, ast.Constant) and node.value == value and type(node.value) == type(value)


def canonicalize(tree: ast.Module) -> ast.Module:
    """Apply canonical transformations to an AST."""
    canonicalizer = Canonicalizer()
    tree = canonicalizer.visit(tree)
    ast.fix_missing_locations(tree)

    # Constant comparison folding + dead branch elimination
    tree = ConstantComparisonFolder().visit(tree)
    ast.fix_missing_locations(tree)
    tree = DeadBranchEliminator().visit(tree)
    ast.fix_missing_locations(tree)

    return tree


def canonical_dump(body: str, bindings: dict[str, str]) -> str:
    """Parse, normalize to concepts, canonicalize, and dump the AST."""
    tree = parse_algorithm(body)
    normalizer = ConceptNormalizer(bindings)
    tree = normalizer.visit(tree)
    ast.fix_missing_locations(tree)
    tree = canonicalize(tree)
    return ast.dump(tree)


def structural_match(dump_a: str, dump_b: str) -> bool:
    """Compare two canonical dumps for structural equality."""
    return dump_a == dump_b
