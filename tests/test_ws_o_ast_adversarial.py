from __future__ import annotations

import pytest

from ast_equiv import compare


ADVERSARIAL_NEGATIVES = [
    ("def f(x):\n    return x + 0", "def f(x):\n    return x"),
    ("def f(x):\n    return x * 1", "def f(x):\n    return x"),
    ("def f(x):\n    return x - 0", "def f(x):\n    return x"),
    ("def f(x):\n    return g(x) * g(x)", "def f(x):\n    return g(x) ** 2"),
    ("def f(x):\n    return fetch() * fetch()", "def f(x):\n    return fetch() ** 2"),
    ("def f(x):\n    return x // 2", "def f(x):\n    return x / 2"),
    ("def f(x):\n    return x % 2", "def f(x):\n    return x - 2"),
    ("def f(x):\n    return math.sqrt(x * x)", "def f(x):\n    return x"),
    ("def f(x):\n    return math.log(x, 10)", "def f(x):\n    return math.log(x)"),
    ("def f(x):\n    return x and True", "def f(x):\n    return x"),
    ("def f(x):\n    return x or False", "def f(x):\n    return x"),
    ("def f(x):\n    return [x] + []", "def f(x):\n    return [x]"),
    ("def f(x):\n    return [] + [x]", "def f(x):\n    return [x]"),
    ("def f(x):\n    return [x] * 1", "def f(x):\n    return [x]"),
    ("def f(x):\n    return (x,)", "def f(x):\n    return x"),
    ("def f(x):\n    return str(x) + ''", "def f(x):\n    return str(x)"),
    ("def f(x):\n    return int(x) * 1", "def f(x):\n    return int(x)"),
    ("def f(x):\n    return x + True", "def f(x):\n    return x + 1"),
    ("def f(x):\n    return x == True", "def f(x):\n    return x"),
    ("def f(x):\n    return x is True", "def f(x):\n    return x == True"),
]


@pytest.mark.parametrize("left,right", ADVERSARIAL_NEGATIVES)
def test_corpus_adversarial_negative_pairs(left: str, right: str) -> None:
    result = compare(left, {"x": "value"}, right, {"x": "value"})

    assert result.equivalent is False
