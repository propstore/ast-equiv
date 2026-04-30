"""AST canonicalization for algorithm equivalence comparison."""
import ast
import hashlib
import operator
from typing import Any

SEMANTIC_EQUIVALENCE_VERSION = "1"


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


def extract_all_names(tree: ast.Module) -> set[str]:
    """Walk AST and collect all Name node ids, plus function argument names."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
    return names


class _FreeVariableCollector(ast.NodeVisitor):
    """Collect load names not bound by Python local binding constructs."""

    def __init__(self):
        self.free: set[str] = set()
        self._scopes: list[set[str]] = [set()]

    def _is_bound(self, name: str) -> bool:
        return any(name in scope for scope in reversed(self._scopes))

    def _bind(self, name: str) -> None:
        self._scopes[-1].add(name)

    def _bind_target(self, node: ast.AST) -> None:
        if isinstance(node, ast.Name):
            self._bind(node.id)
            return
        if isinstance(node, (ast.Tuple, ast.List)):
            for elt in node.elts:
                self._bind_target(elt)
            return
        if isinstance(node, ast.Starred):
            self._bind_target(node.value)

    def _visit_target_loads(self, node: ast.AST) -> None:
        if isinstance(node, (ast.Attribute, ast.Subscript)):
            self.visit(node.value)
        elif isinstance(node, (ast.Tuple, ast.List)):
            for elt in node.elts:
                self._visit_target_loads(elt)
        elif isinstance(node, ast.Starred):
            self._visit_target_loads(node.value)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._bind(node.name)
        for decorator in node.decorator_list:
            self.visit(decorator)
        for default in node.args.defaults:
            self.visit(default)
        for default in node.args.kw_defaults:
            if default is not None:
                self.visit(default)
        self._scopes.append(set())
        self._bind_arguments(node.args)
        for stmt in node.body:
            self.visit(stmt)
        self._scopes.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        for default in node.args.defaults:
            self.visit(default)
        for default in node.args.kw_defaults:
            if default is not None:
                self.visit(default)
        self._scopes.append(set())
        self._bind_arguments(node.args)
        self.visit(node.body)
        self._scopes.pop()

    def _bind_arguments(self, args: ast.arguments) -> None:
        for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs):
            self._bind(arg.arg)
        if args.vararg is not None:
            self._bind(args.vararg.arg)
        if args.kwarg is not None:
            self._bind(args.kwarg.arg)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            if node.id not in KNOWN_BUILTINS and not self._is_bound(node.id):
                self.free.add(node.id)
        elif isinstance(node.ctx, (ast.Store, ast.Del)):
            self._bind(node.id)

    def visit_Assign(self, node: ast.Assign) -> None:
        self.visit(node.value)
        for target in node.targets:
            self._visit_target_loads(target)
            self._bind_target(target)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is not None:
            self.visit(node.value)
        self.visit(node.annotation)
        self._visit_target_loads(node.target)
        self._bind_target(node.target)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self.visit(node.target)
        self.visit(node.value)
        self._bind_target(node.target)

    def visit_For(self, node: ast.For) -> None:
        self.visit(node.iter)
        self._bind_target(node.target)
        for stmt in node.body:
            self.visit(stmt)
        for stmt in node.orelse:
            self.visit(stmt)

    def visit_With(self, node: ast.With) -> None:
        for item in node.items:
            self.visit(item.context_expr)
            if item.optional_vars is not None:
                self._bind_target(item.optional_vars)
        for stmt in node.body:
            self.visit(stmt)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        self.visit(node.iter)
        self._bind_target(node.target)
        for condition in node.ifs:
            self.visit(condition)

    def _visit_comprehension(
        self,
        elt: ast.AST,
        generators: list[ast.comprehension],
        extra: list[ast.AST] | None = None,
    ) -> None:
        self._scopes.append(set())
        for generator in generators:
            self.visit_comprehension(generator)
        if extra:
            for node in extra:
                self.visit(node)
        self.visit(elt)
        self._scopes.pop()

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._visit_comprehension(node.elt, node.generators)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        self._visit_comprehension(node.elt, node.generators)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        self._visit_comprehension(node.elt, node.generators)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self._visit_comprehension(node.value, node.generators, [node.key])

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        self.visit(node.value)
        self._bind_target(node.target)


def extract_free_variables(tree: ast.Module) -> set[str]:
    """Return load names that are not bound locally and are not builtins."""
    collector = _FreeVariableCollector()
    collector.visit(tree)
    return collector.free


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


class _NameCollector(ast.NodeVisitor):
    """Collect variable names in order of first appearance."""

    def __init__(self, preserve: frozenset[str] | None = None):
        self.seen: set[str] = set()
        self.order: list[str] = []
        # Names used as attribute roots (e.g. math in math.pi) but never assigned
        self._attr_only_names: set[str] = set()
        # Concept names (binding values) that should not be positionally renamed
        self._preserve: frozenset[str] = preserve or frozenset()

    def _record(self, name: str) -> None:
        if (name not in self.seen and name not in KNOWN_BUILTINS
                and name not in self._attr_only_names and name not in self._preserve):
            self.seen.add(name)
            self.order.append(name)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Pre-scan: find names used as attribute roots that are never assigned.
        # These are module-like names (e.g. math, os) that should not be renamed.
        attr_roots: set[str] = set()
        assigned_names: set[str] = set()
        param_names = {a.arg for a in (node.args.args or [])}
        for child in ast.walk(node):
            if isinstance(child, ast.Attribute):
                root = child
                while isinstance(root, ast.Attribute):
                    root = root.value
                if isinstance(root, ast.Name):
                    attr_roots.add(root.id)
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
                assigned_names.add(child.id)
        # Only exclude names that are attribute roots but never assigned and not params
        self._attr_only_names = attr_roots - assigned_names - param_names

        # Parameters first, in declaration order
        for arg_node in (node.args.args or []):
            self._record(arg_node.arg)
        # Then walk body for locals
        for child in node.body:
            self.visit(child)

    def visit_Name(self, node: ast.Name) -> None:
        self._record(node.id)
        self.generic_visit(node)

    def visit_arg(self, node: ast.arg) -> None:
        self._record(node.arg)
        self.generic_visit(node)


class PositionalRenamer(ast.NodeTransformer):
    """Rename all variables by position-of-first-use.

    Each side of a comparison gets its own positional mapping so that
    different variable names map to the same canonical names (_v0, _v1, ...).
    """

    def __init__(self):
        self.mapping: dict[str, str] = {}

    @classmethod
    def rename(cls, tree: ast.Module, concept_names: frozenset[str] | None = None) -> ast.Module:
        """Build positional mapping and apply to tree."""
        collector = _NameCollector(preserve=concept_names)
        collector.visit(tree)
        mapping = {name: f"_v{i}" for i, name in enumerate(collector.order)}
        renamer = cls()
        renamer.mapping = mapping
        tree = renamer.visit(tree)
        ast.fix_missing_locations(tree)
        return tree

    def visit_Name(self, node: ast.Name) -> ast.Name:
        if node.id in self.mapping:
            node.id = self.mapping[node.id]
        return node

    def visit_arg(self, node: ast.arg) -> ast.arg:
        if node.arg in self.mapping:
            node.arg = self.mapping[node.arg]
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        # Don't rename the function name itself
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


def _collect_mult_power_chain(node: ast.BinOp) -> tuple[ast.AST | None, int]:
    """Detect repeated multiplication of the same base in a Mult BinOp chain.

    Handles both pure chains (x * x * x) and already-collapsed ones (x**2 * x).
    Returns (base_node, total_count) if all operands share the same base,
    or (None, 0) otherwise.
    """
    # Collect (base_dump, count, base_node) for each leaf in the mult chain
    parts: list[tuple[str, int, ast.AST]] = []

    def _walk(n: ast.AST) -> None:
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mult):
            _walk(n.left)
            _walk(n.right)
        elif (isinstance(n, ast.BinOp) and isinstance(n.op, ast.Pow)
              and isinstance(n.right, ast.Constant) and isinstance(n.right.value, int)):
            parts.append((ast.dump(n.left), n.right.value, n.left))
        else:
            parts.append((ast.dump(n), 1, n))

    _walk(node)
    if len(parts) < 2:
        return None, 0
    first_dump = parts[0][0]
    if all(d == first_dump for d, _, _ in parts) and _is_pure_algebraic(parts[0][2]):
        total = sum(c for _, c, _ in parts)
        return parts[0][2], total
    return None, 0


_PURE_ALGEBRAIC_BUILTINS = frozenset({"abs", "pow"})


def _is_pure_algebraic(node: ast.AST) -> bool:
    if isinstance(node, (ast.Constant, ast.Name)):
        return True
    if isinstance(node, ast.UnaryOp):
        return _is_pure_algebraic(node.operand)
    if isinstance(node, ast.BinOp):
        return _is_pure_algebraic(node.left) and _is_pure_algebraic(node.right)
    if isinstance(node, ast.Attribute):
        return isinstance(node.value, ast.Name) and node.value.id == "math"
    if isinstance(node, ast.Call):
        if node.keywords:
            return False
        if isinstance(node.func, ast.Attribute):
            safe_func = isinstance(node.func.value, ast.Name) and node.func.value.id == "math"
        elif isinstance(node.func, ast.Name):
            safe_func = node.func.id in _PURE_ALGEBRAIC_BUILTINS
        else:
            safe_func = False
        return safe_func and all(_is_pure_algebraic(arg) for arg in node.args)
    return False


class Canonicalizer(ast.NodeTransformer):
    """Apply canonical transformations to normalize AST structure."""

    def __init__(self):
        self._bool_names_stack: list[frozenset[str]] = []
        self._numeric_names_stack: list[frozenset[str]] = []

    @staticmethod
    def _annotation_is_bool(annotation: ast.AST | None) -> bool:
        return isinstance(annotation, ast.Name) and annotation.id == "bool"

    @staticmethod
    def _annotation_is_numeric(annotation: ast.AST | None) -> bool:
        return isinstance(annotation, ast.Name) and annotation.id in {"int", "float"}

    def _function_bool_names(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> frozenset[str]:
        bool_names = {
            arg.arg
            for arg in node.args.args
            if self._annotation_is_bool(arg.annotation)
        }
        for child in ast.walk(node):
            if (
                isinstance(child, ast.AnnAssign)
                and isinstance(child.target, ast.Name)
                and self._annotation_is_bool(child.annotation)
            ):
                bool_names.add(child.target.id)
        return frozenset(bool_names)

    def _function_numeric_names(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> frozenset[str]:
        numeric_names = {
            arg.arg
            for arg in node.args.args
            if self._annotation_is_numeric(arg.annotation)
        }
        for child in ast.walk(node):
            if (
                isinstance(child, ast.AnnAssign)
                and isinstance(child.target, ast.Name)
                and self._annotation_is_numeric(child.annotation)
            ):
                numeric_names.add(child.target.id)
        return frozenset(numeric_names)

    def _expression_is_bool_typed(self, node: ast.AST) -> bool:
        return (
            isinstance(node, ast.Name)
            and bool(self._bool_names_stack)
            and node.id in self._bool_names_stack[-1]
        )

    def _expression_is_numeric_typed(self, node: ast.AST) -> bool:
        return (
            isinstance(node, ast.Name)
            and bool(self._numeric_names_stack)
            and node.id in self._numeric_names_stack[-1]
        )

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

        self._bool_names_stack.append(self._function_bool_names(node))
        self._numeric_names_stack.append(self._function_numeric_names(node))
        try:
            self.generic_visit(node)
        finally:
            self._bool_names_stack.pop()
            self._numeric_names_stack.pop()
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
        # Boolean normalization is semantics-preserving only for expressions
        # statically annotated as bool; int == True is an equality to 1.
        if (len(node.ops) == 1 and len(node.comparators) == 1):
            op = node.ops[0]
            comp = node.comparators[0]
            if isinstance(op, ast.Eq) and self._expression_is_bool_typed(node.left):
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
            if _is_constant_value(node.right, 0) and self._expression_is_numeric_typed(node.left):
                return node.left
            if _is_constant_value(node.left, 0) and self._expression_is_numeric_typed(node.right):
                return node.right
        # Identity elimination: x * 1 -> x, 1 * x -> x
        elif op_type is ast.Mult:
            if _is_constant_value(node.right, 1) and self._expression_is_numeric_typed(node.left):
                return node.left
            if _is_constant_value(node.left, 1) and self._expression_is_numeric_typed(node.right):
                return node.right
        # Identity elimination: x - 0 -> x
        elif op_type is ast.Sub:
            if _is_constant_value(node.right, 0) and self._expression_is_numeric_typed(node.left):
                return node.left
        # Identity elimination: x ** 1 -> x
        elif op_type is ast.Pow:
            if _is_constant_value(node.right, 1) and self._expression_is_numeric_typed(node.left):
                return node.left

        # Repeated multiplication -> power: x * x * x -> x ** 3
        # Also handles post-child-transform case: x**n * x -> x**(n+1)
        if op_type is ast.Mult:
            base, count = _collect_mult_power_chain(node)
            if base is not None and count >= 2:
                import copy
                result = ast.BinOp(
                    left=copy.deepcopy(base),
                    op=ast.Pow(),
                    right=ast.Constant(value=count),
                )
                return ast.copy_location(result, node)

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


class WhileToForNormalizer(ast.NodeTransformer):
    """Convert `init; while cond: body; incr` patterns to `for var in range(...)`.

    Detects statement sequences like:
        var = init_val
        while var < bound:
            ...body...
            var = var + 1
    And converts to:
        for var in range([init_val,] bound):
            ...body...  (without the increment)
    """

    def _transform_stmts(self, stmts: list[ast.stmt]) -> list[ast.stmt]:
        """Scan a statement list for init+while patterns and convert them."""
        result = []
        i = 0
        while i < len(stmts):
            # Check for init+while pattern: stmts[i] is Assign, stmts[i+1] is While
            if (i + 1 < len(stmts)
                    and isinstance(stmts[i], ast.Assign)
                    and len(stmts[i].targets) == 1
                    and isinstance(stmts[i].targets[0], ast.Name)
                    and isinstance(stmts[i].value, ast.Constant)
                    and isinstance(stmts[i].value.value, int)
                    and not isinstance(stmts[i].value.value, bool)
                    and isinstance(stmts[i + 1], ast.While)):
                assign = stmts[i]
                while_node = stmts[i + 1]
                var_name = assign.targets[0].id
                init_val = assign.value.value
                converted = self._try_convert(var_name, init_val, while_node)
                if converted is not None:
                    result.append(converted)
                    i += 2
                    continue
            result.append(stmts[i])
            i += 1
        return result

    def _try_convert(self, var_name: str, init_val, while_node: ast.While) -> ast.For | None:
        """Try to convert a while loop to a for loop."""
        # Check test: var < bound
        test = while_node.test
        if not (isinstance(test, ast.Compare)
                and len(test.ops) == 1
                and isinstance(test.ops[0], ast.Lt)
                and len(test.comparators) == 1
                and isinstance(test.left, ast.Name)
                and test.left.id == var_name):
            return None

        bound = test.comparators[0]
        if self._has_unsafe_control_flow(while_node.body):
            return None
        if self._mutates_loop_or_bound(var_name, bound, while_node.body[:-1]):
            return None

        # Check last statement in body: var = var + 1 OR var += 1
        if not while_node.body:
            return None
        last_stmt = while_node.body[-1]
        is_assign_incr = (isinstance(last_stmt, ast.Assign)
                and len(last_stmt.targets) == 1
                and isinstance(last_stmt.targets[0], ast.Name)
                and last_stmt.targets[0].id == var_name
                and isinstance(last_stmt.value, ast.BinOp)
                and isinstance(last_stmt.value.op, ast.Add)
                and isinstance(last_stmt.value.left, ast.Name)
                and last_stmt.value.left.id == var_name
                and isinstance(last_stmt.value.right, ast.Constant)
                and last_stmt.value.right.value == 1)
        is_aug_incr = (isinstance(last_stmt, ast.AugAssign)
                and isinstance(last_stmt.target, ast.Name)
                and last_stmt.target.id == var_name
                and isinstance(last_stmt.op, ast.Add)
                and isinstance(last_stmt.value, ast.Constant)
                and last_stmt.value.value == 1)
        if not (is_assign_incr or is_aug_incr):
            return None

        # Build the for loop body (without the increment)
        for_body = while_node.body[:-1]

        # Recursively transform nested while loops in the body
        for_body = self._transform_stmts(for_body)

        if not for_body:
            for_body = [ast.Pass()]

        # Build range args
        import copy
        if init_val == 0:
            range_args = [copy.deepcopy(bound)]
        else:
            range_args = [ast.Constant(value=init_val), copy.deepcopy(bound)]

        for_node = ast.For(
            target=ast.Name(id=var_name, ctx=ast.Store()),
            iter=ast.Call(
                func=ast.Name(id='range', ctx=ast.Load()),
                args=range_args,
                keywords=[],
            ),
            body=for_body,
            orelse=[],
        )
        return ast.copy_location(for_node, while_node)

    @staticmethod
    def _has_unsafe_control_flow(stmts: list[ast.stmt]) -> bool:
        return any(isinstance(node, (ast.Break, ast.Continue)) for stmt in stmts for node in ast.walk(stmt))

    @staticmethod
    def _mutates_loop_or_bound(var_name: str, bound: ast.AST, stmts: list[ast.stmt]) -> bool:
        protected = {var_name}
        if isinstance(bound, ast.Name):
            protected.add(bound.id)
        for stmt in stmts:
            for node in ast.walk(stmt):
                if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)) and node.id in protected:
                    return True
        return False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        self.generic_visit(node)
        node.body = self._transform_stmts(node.body)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        self.generic_visit(node)
        node.body = self._transform_stmts(node.body)
        return node

    def visit_For(self, node: ast.For) -> ast.For:
        self.generic_visit(node)
        node.body = self._transform_stmts(node.body)
        return node

    def visit_While(self, node: ast.While) -> ast.While:
        self.generic_visit(node)
        node.body = self._transform_stmts(node.body)
        return node

    def visit_If(self, node: ast.If) -> ast.If:
        self.generic_visit(node)
        node.body = self._transform_stmts(node.body)
        if node.orelse:
            node.orelse = self._transform_stmts(node.orelse)
        return node

    def visit_With(self, node: ast.With) -> ast.With:
        self.generic_visit(node)
        node.body = self._transform_stmts(node.body)
        return node


class _VarCounter(ast.NodeVisitor):
    """Count Store (assignment) and Load (use) occurrences of each variable."""

    def __init__(self):
        self.stores: dict[str, int] = {}
        self.loads: dict[str, int] = {}
        self.in_loop = False

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Store):
            self.stores[node.id] = self.stores.get(node.id, 0) + 1
        elif isinstance(node.ctx, ast.Load):
            self.loads[node.id] = self.loads.get(node.id, 0) + 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        old = self.in_loop
        self.in_loop = True
        self.generic_visit(node)
        self.in_loop = old

    def visit_While(self, node: ast.While) -> None:
        old = self.in_loop
        self.in_loop = True
        self.generic_visit(node)
        self.in_loop = old


class _VarSubstituter(ast.NodeTransformer):
    """Replace Name(id=var, ctx=Load) with the inlined expression."""

    def __init__(self, mapping: dict[str, ast.AST]):
        self.mapping = mapping

    def visit_Name(self, node: ast.Name) -> ast.AST:
        if isinstance(node.ctx, ast.Load) and node.id in self.mapping:
            import copy
            return copy.deepcopy(self.mapping[node.id])
        return node


class TempVariableInliner(ast.NodeTransformer):
    """Inline single-assignment single-use local variables.

    For variables with exactly 1 Store and 1 Load, not inside a loop body:
    substitute the RHS at the use site and remove the assignment.
    Iterates until stable.
    """

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        self.generic_visit(node)
        node.body = self._inline_stmts(node.body)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        self.generic_visit(node)
        node.body = self._inline_stmts(node.body)
        return node

    def visit_For(self, node: ast.For) -> ast.For:
        self.generic_visit(node)
        node.body = self._inline_stmts(node.body)
        return node

    def visit_While(self, node: ast.While) -> ast.While:
        self.generic_visit(node)
        node.body = self._inline_stmts(node.body)
        return node

    def visit_If(self, node: ast.If) -> ast.If:
        self.generic_visit(node)
        node.body = self._inline_stmts(node.body)
        if node.orelse:
            node.orelse = self._inline_stmts(node.orelse)
        return node

    def _inline_stmts(self, stmts: list[ast.stmt]) -> list[ast.stmt]:
        """Iteratively inline single-use temps until stable."""
        changed = True
        while changed:
            changed = False
            candidates = self._find_inline_candidates(stmts)
            if not candidates:
                break

            # Inline one candidate at a time (its RHS may reference other candidates)
            var_name, stmt_idx, rhs = candidates[0]
            mapping: dict[str, ast.AST] = {var_name: rhs}
            remove_indices: set[int] = {stmt_idx}

            # Apply substitutions and remove assignments
            new_stmts = []
            for i, stmt in enumerate(stmts):
                if i in remove_indices:
                    changed = True
                    continue
                stmt = _VarSubstituter(mapping).visit(stmt)
                new_stmts.append(stmt)
            stmts = new_stmts

        return stmts

    def _find_inline_candidates(
        self, stmts: list[ast.stmt],
    ) -> list[tuple[str, int, ast.AST]]:
        """Find single-assignment single-use vars suitable for inlining.

        Returns list of (var_name, stmt_index, rhs_expr).
        """
        # Count stores and loads across all statements at this level
        stores: dict[str, int] = {}
        loads: dict[str, int] = {}
        for node in ast.walk(ast.Module(body=stmts, type_ignores=[])):
            if isinstance(node, ast.Name):
                if isinstance(node.ctx, ast.Store):
                    stores[node.id] = stores.get(node.id, 0) + 1
                elif isinstance(node.ctx, ast.Load):
                    loads[node.id] = loads.get(node.id, 0) + 1

        # Find single-store single-load assignments at this level
        candidates = []
        for i, stmt in enumerate(stmts):
            if (isinstance(stmt, ast.Assign)
                    and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)):
                var_name = stmt.targets[0].id
                if (stores.get(var_name, 0) == 1
                        and loads.get(var_name, 0) == 1
                        and not self._rhs_references(stmt.value, var_name)
                        and self._rhs_is_safe_to_inline(stmt.value)):
                    candidates.append((var_name, i, stmt.value))
        return candidates

    @staticmethod
    def _rhs_references(rhs: ast.AST, var_name: str) -> bool:
        """Check if the RHS expression references var_name (self-referential / accumulator)."""
        for node in ast.walk(rhs):
            if isinstance(node, ast.Name) and node.id == var_name:
                return True
        return False

    @staticmethod
    def _rhs_is_safe_to_inline(rhs: ast.AST) -> bool:
        """Return True only for RHS forms that can be moved to the use site."""
        return _is_safe_inline_expr(rhs)


_PURE_INLINE_BUILTINS = frozenset({"abs", "min", "max", "sum", "round", "pow", "int", "float"})


def _is_safe_inline_expr(node: ast.AST) -> bool:
    if isinstance(node, (ast.Constant, ast.Name)):
        return True
    if isinstance(node, ast.UnaryOp):
        return _is_safe_inline_expr(node.operand)
    if isinstance(node, ast.BinOp):
        return _is_safe_inline_expr(node.left) and _is_safe_inline_expr(node.right)
    if isinstance(node, ast.BoolOp):
        return all(_is_safe_inline_expr(value) for value in node.values)
    if isinstance(node, ast.Compare):
        return _is_safe_inline_expr(node.left) and all(
            _is_safe_inline_expr(comparator) for comparator in node.comparators
        )
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return all(_is_safe_inline_expr(elt) for elt in node.elts)
    if isinstance(node, ast.Dict):
        return all(
            (key is None or _is_safe_inline_expr(key)) and _is_safe_inline_expr(value)
            for key, value in zip(node.keys, node.values)
        )
    if isinstance(node, ast.Attribute):
        return isinstance(node.value, ast.Name) and node.value.id == "math"
    if isinstance(node, ast.Call):
        return _is_safe_inline_call(node)
    return isinstance(
        node,
        (
            ast.Load,
            ast.operator,
            ast.unaryop,
            ast.boolop,
            ast.cmpop,
        ),
    )


def _is_safe_inline_call(node: ast.Call) -> bool:
    if node.keywords:
        return False
    if isinstance(node.func, ast.Name):
        safe_func = node.func.id in _PURE_INLINE_BUILTINS
    elif isinstance(node.func, ast.Attribute):
        safe_func = isinstance(node.func.value, ast.Name) and node.func.value.id == "math"
    else:
        safe_func = False
    if not safe_func:
        return False
    # Unknown calls are blocked because inlining can reorder effects across
    # intervening statements; whitelisted math/builtin calls keep algebraic
    # corpus normalization without moving user code.
    return all(_is_safe_inline_expr(arg) for arg in node.args)


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

    # Re-run temp inlining: dead branch elimination may expose new single-use vars
    tree = TempVariableInliner().visit(tree)
    ast.fix_missing_locations(tree)

    return tree


def canonical_dump(body: str, bindings: dict[str, str]) -> str:
    """Parse, normalize, canonicalize, and return the versioned AST cache key."""
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
    canonical = ast.dump(tree, include_attributes=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"{SEMANTIC_EQUIVALENCE_VERSION}:{digest}"


def structural_match(dump_a: str, dump_b: str) -> bool:
    """Compare two canonical dumps for structural equality."""
    return dump_a == dump_b
