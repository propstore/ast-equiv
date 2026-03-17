"""Tier 3 (Partial Eval): After substituting known parameter values, bytecode matches.

Pairs that become equivalent only when specific parameter values are known.
"""

PAIRS = [
    {
        "name": "parameter_substitution_division",
        "body_a": "def algorithm(samples, rate):\n    return len(samples) / (rate / 4)",
        "body_b": "def algorithm(samples, rate):\n    return len(samples) / 11025",
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": True,
        "expected_min_tier": 3,
        "known_values": {"rate": 44100},
    },
    {
        "name": "branch_collapse_debug_false",
        "body_a": (
            "def algorithm(x, debug):\n"
            "    result = x * 2\n"
            "    if debug:\n"
            "        print(result)\n"
            "    return result"
        ),
        "body_b": (
            "def algorithm(x, debug):\n"
            "    result = x * 2\n"
            "    return result"
        ),
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": True,
        "expected_min_tier": 3,
        "known_values": {"debug": False},
    },
    {
        "name": "loop_bound_substitution",
        "body_a": (
            "def algorithm(data, n):\n"
            "    total = 0\n"
            "    for i in range(n):\n"
            "        total += data[i]\n"
            "    return total"
        ),
        "body_b": (
            "def algorithm(data, n):\n"
            "    total = 0\n"
            "    for i in range(3):\n"
            "        total += data[i]\n"
            "    return total"
        ),
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": True,
        "expected_min_tier": 3,
        "known_values": {"n": 3},
    },
    {
        "name": "multi_parameter_substitution",
        "body_a": (
            "def algorithm(data, width, height):\n"
            "    area = width * height\n"
            "    return [d / area for d in data]"
        ),
        "body_b": (
            "def algorithm(data, width, height):\n"
            "    area = 200\n"
            "    return [d / area for d in data]"
        ),
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": True,
        "expected_min_tier": 3,
        "known_values": {"width": 10, "height": 20},
    },
    {
        "name": "same_bodies_equivalent_under_binding",
        "body_a": (
            "def algorithm(x, scale):\n"
            "    return x * scale"
        ),
        "body_b": (
            "def algorithm(x, scale):\n"
            "    return x * 2"
        ),
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": True,
        "expected_min_tier": 3,
        "known_values": {"scale": 2},
    },
    {
        "name": "same_bodies_divergent_under_different_binding",
        "body_a": (
            "def algorithm(x, scale):\n"
            "    return x * scale"
        ),
        "body_b": (
            "def algorithm(x, scale):\n"
            "    return x * 2"
        ),
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": False,
        "expected_min_tier": 3,
        "known_values": {"scale": 5},
    },
    {
        "name": "math_simplification_known_exponent",
        "body_a": (
            "def algorithm(base, exp):\n"
            "    return base ** exp"
        ),
        "body_b": (
            "def algorithm(base, exp):\n"
            "    return base * base"
        ),
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": True,
        "expected_min_tier": 3,
        "known_values": {"exp": 2},
    },
    {
        "name": "conditional_collapse_mode_select",
        "body_a": (
            "def algorithm(data, mode):\n"
            "    if mode == 'sum':\n"
            "        return sum(data)\n"
            "    elif mode == 'mean':\n"
            "        return sum(data) / len(data)\n"
            "    else:\n"
            "        return 0"
        ),
        "body_b": (
            "def algorithm(data, mode):\n"
            "    return sum(data) / len(data)"
        ),
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": True,
        "expected_min_tier": 3,
        "known_values": {"mode": "mean"},
    },
    {
        "name": "step_size_substitution",
        "body_a": (
            "def algorithm(data, step):\n"
            "    return data[::step]"
        ),
        "body_b": (
            "def algorithm(data, step):\n"
            "    return data[::4]"
        ),
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": True,
        "expected_min_tier": 3,
        "known_values": {"step": 4},
    },
    {
        "name": "threshold_substitution",
        "body_a": (
            "def algorithm(values, threshold):\n"
            "    return [v for v in values if v > threshold]"
        ),
        "body_b": (
            "def algorithm(values, threshold):\n"
            "    return [v for v in values if v > 0.5]"
        ),
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": True,
        "expected_min_tier": 3,
        "known_values": {"threshold": 0.5},
    },
    {
        "name": "offset_arithmetic_substitution",
        "body_a": (
            "def algorithm(x, offset):\n"
            "    return (x + offset) * 2 - offset"
        ),
        "body_b": (
            "def algorithm(x, offset):\n"
            "    return (x + 10) * 2 - 10"
        ),
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": True,
        "expected_min_tier": 3,
        "known_values": {"offset": 10},
    },
]
