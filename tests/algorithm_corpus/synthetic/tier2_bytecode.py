"""Tier 2 (Bytecode): After compilation, bytecode matches.

Constant folding, range normalization, boolean normalization, etc.
"""

PAIRS = [
    {
        "name": "constant_folding_multiply",
        "body_a": "def algorithm(n):\n    return 2 * 3 * n",
        "body_b": "def algorithm(n):\n    return 6 * n",
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": True,
        "expected_min_tier": 2,
        "known_values": {},
    },
    {
        "name": "constant_folding_addition",
        "body_a": "def algorithm(y):\n    return 1 + 2 + y",
        "body_b": "def algorithm(y):\n    return 3 + y",
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": True,
        "expected_min_tier": 2,
        "known_values": {},
    },
    {
        "name": "range_normalization_full_to_short",
        "body_a": (
            "def algorithm(n):\n"
            "    s = 0\n"
            "    for i in range(0, n, 1):\n"
            "        s += i\n"
            "    return s"
        ),
        "body_b": (
            "def algorithm(n):\n"
            "    s = 0\n"
            "    for i in range(n):\n"
            "        s += i\n"
            "    return s"
        ),
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": True,
        "expected_min_tier": 2,
        "known_values": {},
    },
    {
        "name": "boolean_equals_true",
        "body_a": "def algorithm(x):\n    if x == True:\n        return 1\n    return 0",
        "body_b": "def algorithm(x):\n    if x:\n        return 1\n    return 0",
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": True,
        "expected_min_tier": 2,
        "known_values": {},
    },
    {
        "name": "boolean_equals_false",
        "body_a": "def algorithm(x):\n    if x == False:\n        return 1\n    return 0",
        "body_b": "def algorithm(x):\n    if not x:\n        return 1\n    return 0",
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": True,
        "expected_min_tier": 2,
        "known_values": {},
    },
    {
        "name": "augmented_assignment",
        "body_a": (
            "def algorithm(data):\n"
            "    total = 0\n"
            "    for x in data:\n"
            "        total = total + x\n"
            "    return total"
        ),
        "body_b": (
            "def algorithm(data):\n"
            "    total = 0\n"
            "    for x in data:\n"
            "        total += x\n"
            "    return total"
        ),
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": True,
        "expected_min_tier": 2,
        "known_values": {},
    },
    {
        "name": "chained_comparison",
        "body_a": "def algorithm(x, a, b):\n    return a < x and x < b",
        "body_b": "def algorithm(x, a, b):\n    return a < x < b",
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": True,
        "expected_min_tier": 2,
        "known_values": {},
    },
    {
        "name": "dead_code_after_return",
        "body_a": (
            "def algorithm(x):\n"
            "    return x * 2\n"
            "    y = x + 1\n"
            "    return y"
        ),
        "body_b": "def algorithm(x):\n    return x * 2",
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": True,
        "expected_min_tier": 2,
        "known_values": {},
    },
    {
        "name": "string_concat_vs_format",
        "body_a": 'def algorithm(name):\n    return "hello " + name',
        "body_b": 'def algorithm(name):\n    return "hello " + name',
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": True,
        "expected_min_tier": 2,
        "known_values": {},
    },
    {
        "name": "constant_folding_power",
        "body_a": "def algorithm(x):\n    return x * x * x",
        "body_b": "def algorithm(x):\n    return x ** 3",
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": True,
        "expected_min_tier": 2,
        "known_values": {},
    },
    {
        "name": "identity_multiplication",
        "body_a": "def algorithm(x):\n    return 1 * x",
        "body_b": "def algorithm(x):\n    return x",
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": True,
        "expected_min_tier": 2,
        "known_values": {},
    },
    {
        "name": "identity_addition",
        "body_a": "def algorithm(x):\n    return x + 0",
        "body_b": "def algorithm(x):\n    return x",
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": True,
        "expected_min_tier": 2,
        "known_values": {},
    },
]
