"""Tier 1 (Canonical AST): Alpha-renaming + normalization pairs.

Two snippets differ only in variable names, whitespace, docstrings, comments.
"""

PAIRS = [
    {
        "name": "simple_alpha_rename_single_var",
        "body_a": "def algorithm(data):\n    x = 0\n    for i in data:\n        x += i\n    return x",
        "body_b": "def algorithm(data):\n    total = 0\n    for item in data:\n        total += item\n    return total",
        "bindings_a": {"x": "accumulator", "i": "element"},
        "bindings_b": {"total": "accumulator", "item": "element"},
        "expected_equivalent": True,
        "expected_min_tier": 1,
        "known_values": {},
    },
    {
        "name": "alpha_rename_nested_loops",
        "body_a": (
            "def algorithm(matrix):\n"
            "    result = []\n"
            "    for i in range(len(matrix)):\n"
            "        for j in range(len(matrix[i])):\n"
            "            result.append(matrix[i][j])\n"
            "    return result"
        ),
        "body_b": (
            "def algorithm(matrix):\n"
            "    flat = []\n"
            "    for row in range(len(matrix)):\n"
            "        for col in range(len(matrix[row])):\n"
            "            flat.append(matrix[row][col])\n"
            "    return flat"
        ),
        "bindings_a": {"result": "output_list", "i": "row_idx", "j": "col_idx"},
        "bindings_b": {"flat": "output_list", "row": "row_idx", "col": "col_idx"},
        "expected_equivalent": True,
        "expected_min_tier": 1,
        "known_values": {},
    },
    {
        "name": "alpha_rename_list_comprehension",
        "body_a": "def algorithm(nums):\n    return [x * x for x in nums if x > 0]",
        "body_b": "def algorithm(nums):\n    return [val * val for val in nums if val > 0]",
        "bindings_a": {"x": "element"},
        "bindings_b": {"val": "element"},
        "expected_equivalent": True,
        "expected_min_tier": 1,
        "known_values": {},
    },
    {
        "name": "alpha_rename_lambda",
        "body_a": "def algorithm(items):\n    return sorted(items, key=lambda x: x[1])",
        "body_b": "def algorithm(items):\n    return sorted(items, key=lambda elem: elem[1])",
        "bindings_a": {"x": "sort_key"},
        "bindings_b": {"elem": "sort_key"},
        "expected_equivalent": True,
        "expected_min_tier": 1,
        "known_values": {},
    },
    {
        "name": "alpha_rename_attribute_access",
        "body_a": (
            "def algorithm(data):\n"
            "    buf = []\n"
            "    for v in data:\n"
            "        buf.append(v * 2)\n"
            "    return buf"
        ),
        "body_b": (
            "def algorithm(data):\n"
            "    result = []\n"
            "    for item in data:\n"
            "        result.append(item * 2)\n"
            "    return result"
        ),
        "bindings_a": {"buf": "output_list", "v": "element"},
        "bindings_b": {"result": "output_list", "item": "element"},
        "expected_equivalent": True,
        "expected_min_tier": 1,
        "known_values": {},
    },
    {
        "name": "multiple_return_values_tuple",
        "body_a": (
            "def algorithm(a, b):\n"
            "    s = a + b\n"
            "    d = a - b\n"
            "    return s, d"
        ),
        "body_b": (
            "def algorithm(a, b):\n"
            "    total = a + b\n"
            "    diff = a - b\n"
            "    return total, diff"
        ),
        "bindings_a": {"s": "sum_val", "d": "diff_val"},
        "bindings_b": {"total": "sum_val", "diff": "diff_val"},
        "expected_equivalent": True,
        "expected_min_tier": 1,
        "known_values": {},
    },
    {
        "name": "early_return_renamed",
        "body_a": (
            "def algorithm(lst):\n"
            "    if not lst:\n"
            "        return None\n"
            "    m = lst[0]\n"
            "    for v in lst[1:]:\n"
            "        if v > m:\n"
            "            m = v\n"
            "    return m"
        ),
        "body_b": (
            "def algorithm(lst):\n"
            "    if not lst:\n"
            "        return None\n"
            "    best = lst[0]\n"
            "    for candidate in lst[1:]:\n"
            "        if candidate > best:\n"
            "            best = candidate\n"
            "    return best"
        ),
        "bindings_a": {"m": "max_val", "v": "candidate"},
        "bindings_b": {"best": "max_val", "candidate": "candidate"},
        "expected_equivalent": True,
        "expected_min_tier": 1,
        "known_values": {},
    },
    {
        "name": "docstring_presence_vs_absence",
        "body_a": (
            "def algorithm(n):\n"
            '    """Compute factorial of n."""\n'
            "    if n <= 1:\n"
            "        return 1\n"
            "    return n * algorithm(n - 1)"
        ),
        "body_b": (
            "def algorithm(n):\n"
            "    if n <= 1:\n"
            "        return 1\n"
            "    return n * algorithm(n - 1)"
        ),
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": True,
        "expected_min_tier": 1,
        "known_values": {},
    },
    {
        "name": "comment_differences",
        "body_a": (
            "def algorithm(x, y):\n"
            "    # compute the sum\n"
            "    return x + y"
        ),
        "body_b": (
            "def algorithm(x, y):\n"
            "    # add two numbers together\n"
            "    return x + y"
        ),
        "bindings_a": {},
        "bindings_b": {},
        "expected_equivalent": True,
        "expected_min_tier": 1,
        "known_values": {},
    },
    {
        "name": "completely_different_naming_scheme",
        "body_a": (
            "def algorithm(arr):\n"
            "    n = len(arr)\n"
            "    for i in range(n):\n"
            "        for j in range(i + 1, n):\n"
            "            if arr[i] > arr[j]:\n"
            "                arr[i], arr[j] = arr[j], arr[i]\n"
            "    return arr"
        ),
        "body_b": (
            "def algorithm(arr):\n"
            "    length = len(arr)\n"
            "    for outer in range(length):\n"
            "        for inner in range(outer + 1, length):\n"
            "            if arr[outer] > arr[inner]:\n"
            "                arr[outer], arr[inner] = arr[inner], arr[outer]\n"
            "    return arr"
        ),
        "bindings_a": {"n": "size", "i": "outer_idx", "j": "inner_idx"},
        "bindings_b": {"length": "size", "outer": "outer_idx", "inner": "inner_idx"},
        "expected_equivalent": True,
        "expected_min_tier": 1,
        "known_values": {},
    },
    {
        "name": "nested_comprehension_rename",
        "body_a": "def algorithm(grid):\n    return [c for r in grid for c in r]",
        "body_b": "def algorithm(grid):\n    return [cell for row in grid for cell in row]",
        "bindings_a": {"r": "row", "c": "cell"},
        "bindings_b": {"row": "row", "cell": "cell"},
        "expected_equivalent": True,
        "expected_min_tier": 1,
        "known_values": {},
    },
]
