"""Generate code clone variants from seed DSP/math functions.

Applies Type 1, Type 2, and Type 3 transformations to produce
equivalence-pair test data for ast-equiv.
"""

from __future__ import annotations

import ast
import copy
import textwrap
from typing import Any


# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------

SEEDS: dict[str, str] = {
    "moving_avg": textwrap.dedent("""\
        def algorithm(signal, window_size):
            n = len(signal)
            result = []
            for i in range(n):
                start = max(0, i - window_size + 1)
                window = signal[start:i + 1]
                avg = sum(window) / len(window)
                result.append(avg)
            return result
    """),

    "rms": textwrap.dedent("""\
        def algorithm(signal):
            n = len(signal)
            total = 0.0
            for i in range(n):
                total += signal[i] ** 2
            rms_val = (total / n) ** 0.5
            return rms_val
    """),

    "fir_filter": textwrap.dedent("""\
        def algorithm(signal, coeffs):
            n = len(signal)
            m = len(coeffs)
            output = []
            for i in range(n):
                acc = 0.0
                for j in range(m):
                    idx = i - j
                    if idx >= 0:
                        acc += coeffs[j] * signal[idx]
                output.append(acc)
            return output
    """),

    "hamming_window": textwrap.dedent("""\
        def algorithm(n):
            import math
            window = []
            for i in range(n):
                val = 0.54 - 0.46 * math.cos(2 * math.pi * i / (n - 1))
                window.append(val)
            return window
    """),

    "zero_crossing_rate": textwrap.dedent("""\
        def algorithm(signal):
            n = len(signal)
            crossings = 0
            for i in range(1, n):
                if signal[i] * signal[i - 1] < 0:
                    crossings += 1
            rate = crossings / (n - 1)
            return rate
    """),
}


# ---------------------------------------------------------------------------
# AST Transformers
# ---------------------------------------------------------------------------

class AlphaRenamer(ast.NodeTransformer):
    """Type 1: Rename all local variables systematically."""

    def __init__(self, prefix: str = "v"):
        self.mapping: dict[str, str] = {}
        self.counter = 0
        self.prefix = prefix
        # Names that should never be renamed
        self.protected = {
            "algorithm", "range", "len", "sum", "max", "min", "abs",
            "math", "cos", "sin", "pi", "append", "True", "False", "None",
            "print", "int", "float", "list", "dict", "set", "tuple",
        }

    def _rename(self, name: str) -> str:
        if name in self.protected:
            return name
        if name not in self.mapping:
            self.mapping[name] = f"{self.prefix}_{self.counter}"
            self.counter += 1
        return self.mapping[name]

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        # Rename parameters (except self)
        for arg in node.args.args:
            if arg.arg != "self":
                arg.arg = self._rename(arg.arg)
        self.generic_visit(node)
        return node

    def visit_Name(self, node: ast.Name) -> ast.Name:
        node.id = self._rename(node.id)
        return node

    def visit_arg(self, node: ast.arg) -> ast.arg:
        # Already handled in visit_FunctionDef
        return node


class ConstantUnfolder(ast.NodeTransformer):
    """Type 2: Unfold constants (e.g. 0.54 -> 27/50)."""

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        self.generic_visit(node)
        # Transform range(n) -> range(0, n, 1) handled separately
        return node

    def visit_Call(self, node: ast.Call) -> ast.Call:
        self.generic_visit(node)
        # range(n) -> range(0, n, 1)
        if (isinstance(node.func, ast.Name)
                and node.func.id == "range"
                and len(node.args) == 1
                and not node.keywords):
            node.args = [
                ast.Constant(value=0),
                node.args[0],
                ast.Constant(value=1),
            ]
        return node


class AugAssignExpander(ast.NodeTransformer):
    """Type 3: Convert augmented assignments to plain assignments.

    x += 1  ->  x = x + 1
    """

    _op_map = {
        ast.Add: ast.Add,
        ast.Sub: ast.Sub,
        ast.Mult: ast.Mult,
        ast.Div: ast.Div,
        ast.Pow: ast.Pow,
    }

    def visit_AugAssign(self, node: ast.AugAssign) -> ast.Assign:
        target = node.target
        value = ast.BinOp(
            left=copy.deepcopy(target),
            op=node.op,
            right=node.value,
        )
        new_node = ast.Assign(
            targets=[target],
            value=value,
        )
        return ast.copy_location(new_node, node)


class ForToWhile(ast.NodeTransformer):
    """Type 3: Convert for-range loops to while loops.

    Only handles simple `for x in range(n):` patterns.
    """

    def visit_For(self, node: ast.For) -> Any:
        self.generic_visit(node)

        # Only transform `for VAR in range(...):`
        if not (isinstance(node.iter, ast.Call)
                and isinstance(node.iter.func, ast.Name)
                and node.iter.func.id == "range"
                and isinstance(node.target, ast.Name)):
            return node

        var = node.target.id
        args = node.iter.args

        if len(args) == 1:
            start, stop, step = ast.Constant(value=0), args[0], ast.Constant(value=1)
        elif len(args) == 2:
            start, stop, step = args[0], args[1], ast.Constant(value=1)
        elif len(args) == 3:
            start, stop, step = args[0], args[1], args[2]
        else:
            return node

        # var = start
        init = ast.Assign(
            targets=[ast.Name(id=var, ctx=ast.Store())],
            value=start,
        )
        # var < stop
        test = ast.Compare(
            left=ast.Name(id=var, ctx=ast.Load()),
            ops=[ast.Lt()],
            comparators=[stop],
        )
        # var = var + step
        increment = ast.Assign(
            targets=[ast.Name(id=var, ctx=ast.Store())],
            value=ast.BinOp(
                left=ast.Name(id=var, ctx=ast.Load()),
                op=ast.Add(),
                right=step,
            ),
        )
        body = list(node.body) + [increment]
        while_node = ast.While(test=test, body=body, orelse=[])

        return [ast.copy_location(init, node), ast.copy_location(while_node, node)]


class DeadCodeInserter(ast.NodeTransformer):
    """Type 3: Insert dead code after return statements."""

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        self.generic_visit(node)
        new_body = []
        for stmt in node.body:
            new_body.append(stmt)
            if isinstance(stmt, ast.Return):
                # Add unreachable code after return
                dead = ast.Assign(
                    targets=[ast.Name(id="_dead", ctx=ast.Store())],
                    value=ast.Constant(value=0),
                )
                ast.copy_location(dead, stmt)
                new_body.append(dead)
        node.body = new_body
        return node


# ---------------------------------------------------------------------------
# Transformation application
# ---------------------------------------------------------------------------

def apply_transform(source: str, transformer_cls: type) -> str:
    """Parse source, apply AST transformer, unparse back to source."""
    tree = ast.parse(source)
    transformer = transformer_cls()
    new_tree = transformer.visit(tree)
    ast.fix_missing_locations(new_tree)
    return ast.unparse(new_tree)


# ---------------------------------------------------------------------------
# Pair generation
# ---------------------------------------------------------------------------

TRANSFORMS: list[dict[str, Any]] = [
    {
        "suffix": "type1_rename",
        "cls": AlphaRenamer,
        "expected_equivalent": True,
        "expected_min_tier": 1,
        "desc": "Alpha-rename all locals",
    },
    {
        "suffix": "type2_range_expand",
        "cls": ConstantUnfolder,
        "expected_equivalent": True,
        "expected_min_tier": 2,
        "desc": "Expand range(n) to range(0,n,1)",
    },
    {
        "suffix": "type3_augassign",
        "cls": AugAssignExpander,
        "expected_equivalent": True,
        "expected_min_tier": 3,
        "desc": "Expand augmented assignments to plain assignments",
    },
    {
        "suffix": "type3_for_to_while",
        "cls": ForToWhile,
        "expected_equivalent": True,
        "expected_min_tier": 3,
        "desc": "Convert for-range loops to while loops",
    },
    {
        "suffix": "type3_dead_code",
        "cls": DeadCodeInserter,
        "expected_equivalent": True,
        "expected_min_tier": 3,
        "desc": "Insert unreachable code after return",
    },
]


def generate_pairs() -> list[dict[str, Any]]:
    """Generate all seed x transformation pairs."""
    pairs = []
    for seed_name, seed_src in SEEDS.items():
        for xform in TRANSFORMS:
            try:
                transformed = apply_transform(seed_src, xform["cls"])
            except Exception as exc:
                print(f"SKIP {seed_name} x {xform['suffix']}: {exc}")
                continue

            pairs.append({
                "name": f"{seed_name}_{xform['suffix']}",
                "body_a": seed_src.strip(),
                "body_b": transformed.strip(),
                "bindings_a": {},
                "bindings_b": {},
                "expected_equivalent": xform["expected_equivalent"],
                "expected_min_tier": xform["expected_min_tier"],
                "known_values": {},
            })
    return pairs


def format_pairs_module(pairs: list[dict[str, Any]]) -> str:
    """Format pairs as a Python module string."""
    lines = [
        '"""Auto-generated clone variant pairs for ast-equiv testing.',
        '',
        'Generated by scripts/generate_clones.py',
        '"""',
        '',
        'PAIRS = [',
    ]
    for p in pairs:
        lines.append('    {')
        lines.append(f'        "name": {p["name"]!r},')
        lines.append(f'        "body_a": {p["body_a"]!r},')
        lines.append(f'        "body_b": {p["body_b"]!r},')
        lines.append(f'        "bindings_a": {p["bindings_a"]!r},')
        lines.append(f'        "bindings_b": {p["bindings_b"]!r},')
        lines.append(f'        "expected_equivalent": {p["expected_equivalent"]!r},')
        lines.append(f'        "expected_min_tier": {p["expected_min_tier"]!r},')
        lines.append(f'        "known_values": {p["known_values"]!r},')
        lines.append('    },')
    lines.append(']')
    lines.append('')
    return '\n'.join(lines)


if __name__ == "__main__":
    pairs = generate_pairs()
    print(f"Generated {len(pairs)} pairs")
    module_src = format_pairs_module(pairs)

    import pathlib
    out_dir = pathlib.Path(__file__).resolve().parent.parent / "tests" / "algorithm_corpus" / "pyclone"
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "__init__.py").write_text("")
    (out_dir / "clone_pairs.py").write_text(module_src, encoding="utf-8")
    print(f"Wrote {out_dir / 'clone_pairs.py'}")

    for p in pairs:
        print(f"  {p['name']}: tier={p['expected_min_tier']}")
