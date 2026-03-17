"""Validate all corpus pairs: parse bodies, check required keys, generate manifest."""
import ast
import json
import sys
from pathlib import Path

# Add project root to path so we can import the corpus loader
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.algorithm_corpus import load_corpus, CORPUS_DIR

REQUIRED_KEYS = {"name", "body_a", "body_b", "bindings_a", "bindings_b", "expected_equivalent"}


def validate():
    pairs = load_corpus()
    errors = []
    stats = {
        "total_pairs": 0,
        "by_source": {},
        "by_expected_equivalent": {"true": 0, "false": 0},
        "by_expected_min_tier": {"1": 0, "2": 0, "3": 0, "4": 0, "null": 0},
    }

    for i, pair in enumerate(pairs):
        source = pair.get("source", "unknown")
        name = pair.get("name", f"pair_{i}")
        label = f"{source}/{pair.get('source_file', '?')}::{name}"

        # Check required keys
        missing = REQUIRED_KEYS - set(pair.keys())
        if missing:
            errors.append(f"  MISSING KEYS in {label}: {missing}")
            continue

        # Try parsing body_a
        try:
            ast.parse(pair["body_a"])
        except SyntaxError as e:
            errors.append(f"  PARSE ERROR body_a in {label}: {e}")

        # Try parsing body_b
        try:
            ast.parse(pair["body_b"])
        except SyntaxError as e:
            errors.append(f"  PARSE ERROR body_b in {label}: {e}")

        # Stats
        stats["total_pairs"] += 1
        stats["by_source"][source] = stats["by_source"].get(source, 0) + 1

        if pair["expected_equivalent"]:
            stats["by_expected_equivalent"]["true"] += 1
        else:
            stats["by_expected_equivalent"]["false"] += 1

        tier = pair.get("expected_min_tier")
        if tier is None:
            stats["by_expected_min_tier"]["null"] += 1
        else:
            stats["by_expected_min_tier"][str(tier)] = stats["by_expected_min_tier"].get(str(tier), 0) + 1

    # Print results
    if errors:
        print("VALIDATION ERRORS:")
        for e in errors:
            print(e)
    else:
        print("ALL PAIRS VALID")

    print(f"\nTotal pairs: {stats['total_pairs']}")
    print(f"By source: {json.dumps(stats['by_source'], indent=2)}")
    print(f"By equivalent: {json.dumps(stats['by_expected_equivalent'], indent=2)}")
    print(f"By min tier: {json.dumps(stats['by_expected_min_tier'], indent=2)}")

    # Write manifest
    manifest_path = CORPUS_DIR / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(stats, f, indent=4)
    print(f"\nManifest written to {manifest_path}")

    return len(errors)


if __name__ == "__main__":
    sys.exit(validate())
