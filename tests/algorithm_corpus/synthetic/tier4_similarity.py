"""Tier 4 (Structural Similarity): Tree edit distance ratio.

Near-miss > 0.9, different < 0.5, intermediate ~0.7.
"""

PAIRS = [
    {
        "name": "near_miss_one_line_different",
        "body_a": (
            "def algorithm(data):\n"
            "    total = 0\n"
            "    for x in data:\n"
            "        total += x\n"
            "    return total"
        ),
        "body_b": (
            "def algorithm(data):\n"
            "    total = 0\n"
            "    for x in data:\n"
            "        total += x * x\n"
            "    return total"
        ),
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": False,
        "expected_min_tier": 4,
        "known_values": {},
    },
    {
        "name": "major_difference_low_similarity",
        "body_a": (
            "def algorithm(n):\n"
            "    if n <= 1:\n"
            "        return n\n"
            "    return algorithm(n - 1) + algorithm(n - 2)"
        ),
        "body_b": (
            "def algorithm(data):\n"
            "    result = {}\n"
            "    for item in data:\n"
            "        key = item[0]\n"
            "        if key not in result:\n"
            "            result[key] = []\n"
            "        result[key].append(item)\n"
            "    return result"
        ),
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": False,
        "expected_min_tier": 4,
        "known_values": {},
    },
    {
        "name": "intermediate_similarity_similar_structure",
        "body_a": (
            "def algorithm(data):\n"
            "    result = []\n"
            "    for x in data:\n"
            "        if x > 0:\n"
            "            result.append(x * 2)\n"
            "    return result"
        ),
        "body_b": (
            "def algorithm(data):\n"
            "    result = []\n"
            "    for x in data:\n"
            "        if x >= 0:\n"
            "            result.append(x + 1)\n"
            "        else:\n"
            "            result.append(0)\n"
            "    return result"
        ),
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": False,
        "expected_min_tier": 4,
        "known_values": {},
    },
    {
        "name": "same_structure_different_operations",
        "body_a": (
            "def algorithm(a, b):\n"
            "    c = a + b\n"
            "    d = a - b\n"
            "    return c * d"
        ),
        "body_b": (
            "def algorithm(a, b):\n"
            "    c = a * b\n"
            "    d = a / b\n"
            "    return c + d"
        ),
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": False,
        "expected_min_tier": 4,
        "known_values": {},
    },
    {
        "name": "near_miss_extra_guard_clause",
        "body_a": (
            "def algorithm(lst):\n"
            "    result = []\n"
            "    for x in lst:\n"
            "        result.append(x * 2)\n"
            "    return result"
        ),
        "body_b": (
            "def algorithm(lst):\n"
            "    if not lst:\n"
            "        return []\n"
            "    result = []\n"
            "    for x in lst:\n"
            "        result.append(x * 2)\n"
            "    return result"
        ),
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": False,
        "expected_min_tier": 4,
        "known_values": {},
    },
]
