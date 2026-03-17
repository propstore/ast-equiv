"""Test corpus loader for ast-equiv."""
import importlib
import importlib.util
import ast
from pathlib import Path

CORPUS_DIR = Path(__file__).parent


def load_pairs(source: str) -> list[dict]:
    """Load all pairs from a specific source directory (e.g., 'dsp', 'synthetic')."""
    pairs = []
    source_dir = CORPUS_DIR / source
    if not source_dir.exists():
        return pairs
    for py_file in sorted(source_dir.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        module_name = f"tests.algorithm_corpus.{source}.{py_file.stem}"
        spec = importlib.util.spec_from_file_location(module_name, py_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, "PAIRS"):
            for pair in module.PAIRS:
                pair["source"] = source
                pair["source_file"] = py_file.name
                pairs.append(pair)
    return pairs


def load_corpus() -> list[dict]:
    """Load all pairs from all sources."""
    pairs = []
    for source_dir in sorted(CORPUS_DIR.iterdir()):
        if source_dir.is_dir() and not source_dir.name.startswith("_"):
            pairs.extend(load_pairs(source_dir.name))
    return pairs
