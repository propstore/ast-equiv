"""Negative cases: pairs that are NOT equivalent at any tier.

These test that the comparison engine correctly rejects non-equivalent code.
"""

PAIRS = [
    {
        "name": "different_arithmetic_add_vs_mul",
        "body_a": "def algorithm(a, b):\n    return a + b",
        "body_b": "def algorithm(a, b):\n    return a * b",
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": False,
        "expected_min_tier": 1,
        "known_values": {},
    },
    {
        "name": "off_by_one_range",
        "body_a": (
            "def algorithm(n):\n"
            "    total = 0\n"
            "    for i in range(n):\n"
            "        total += i\n"
            "    return total"
        ),
        "body_b": (
            "def algorithm(n):\n"
            "    total = 0\n"
            "    for i in range(n + 1):\n"
            "        total += i\n"
            "    return total"
        ),
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": False,
        "expected_min_tier": 1,
        "known_values": {},
    },
    {
        "name": "gt_vs_gte",
        "body_a": (
            "def algorithm(a, b):\n"
            "    if a > b:\n"
            "        return a\n"
            "    return b"
        ),
        "body_b": (
            "def algorithm(a, b):\n"
            "    if a >= b:\n"
            "        return a\n"
            "    return b"
        ),
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": False,
        "expected_min_tier": 1,
        "known_values": {},
    },
    {
        "name": "reversed_loop_direction",
        "body_a": (
            "def algorithm(data):\n"
            "    result = []\n"
            "    for i in range(len(data)):\n"
            "        result.append(data[i])\n"
            "    return result"
        ),
        "body_b": (
            "def algorithm(data):\n"
            "    result = []\n"
            "    for i in range(len(data) - 1, -1, -1):\n"
            "        result.append(data[i])\n"
            "    return result"
        ),
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": False,
        "expected_min_tier": 1,
        "known_values": {},
    },
    {
        "name": "missing_initialization",
        "body_a": (
            "def algorithm(data):\n"
            "    total = 0\n"
            "    for x in data:\n"
            "        total += x\n"
            "    return total"
        ),
        "body_b": (
            "def algorithm(data):\n"
            "    for x in data:\n"
            "        total += x\n"
            "    return total"
        ),
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": False,
        "expected_min_tier": 1,
        "known_values": {},
    },
    {
        "name": "different_return_values",
        "body_a": (
            "def algorithm(x, y):\n"
            "    return x + y"
        ),
        "body_b": (
            "def algorithm(x, y):\n"
            "    return x - y"
        ),
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": False,
        "expected_min_tier": 1,
        "known_values": {},
    },
    {
        "name": "bubble_sort_vs_selection_sort",
        "body_a": (
            "def algorithm(arr):\n"
            "    n = len(arr)\n"
            "    for i in range(n):\n"
            "        for j in range(0, n - i - 1):\n"
            "            if arr[j] > arr[j + 1]:\n"
            "                arr[j], arr[j + 1] = arr[j + 1], arr[j]\n"
            "    return arr"
        ),
        "body_b": (
            "def algorithm(arr):\n"
            "    n = len(arr)\n"
            "    for i in range(n):\n"
            "        min_idx = i\n"
            "        for j in range(i + 1, n):\n"
            "            if arr[j] < arr[min_idx]:\n"
            "                min_idx = j\n"
            "        arr[i], arr[min_idx] = arr[min_idx], arr[i]\n"
            "    return arr"
        ),
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": False,
        "expected_min_tier": 1,
        "known_values": {},
    },
    {
        "name": "same_names_different_logic",
        "body_a": (
            "def algorithm(data):\n"
            "    result = 0\n"
            "    for x in data:\n"
            "        result += x\n"
            "    return result"
        ),
        "body_b": (
            "def algorithm(data):\n"
            "    result = 1\n"
            "    for x in data:\n"
            "        result *= x\n"
            "    return result"
        ),
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": False,
        "expected_min_tier": 1,
        "known_values": {},
    },
    {
        "name": "different_condition_and_vs_or",
        "body_a": (
            "def algorithm(a, b):\n"
            "    if a > 0 and b > 0:\n"
            "        return True\n"
            "    return False"
        ),
        "body_b": (
            "def algorithm(a, b):\n"
            "    if a > 0 or b > 0:\n"
            "        return True\n"
            "    return False"
        ),
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": False,
        "expected_min_tier": 1,
        "known_values": {},
    },
    {
        "name": "different_slice_step",
        "body_a": "def algorithm(data):\n    return data[::2]",
        "body_b": "def algorithm(data):\n    return data[::3]",
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": False,
        "expected_min_tier": 1,
        "known_values": {},
    },
    {
        "name": "append_vs_extend",
        "body_a": (
            "def algorithm(lst, items):\n"
            "    for x in items:\n"
            "        lst.append(x)\n"
            "    return lst"
        ),
        "body_b": (
            "def algorithm(lst, items):\n"
            "    lst.extend(items)\n"
            "    return lst"
        ),
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": False,
        "expected_min_tier": 1,
        "known_values": {},
    },
]
