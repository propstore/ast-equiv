# ast-equiv

Python AST equivalence comparison.

## Tiers

- **NONE** -- no equivalence proof found
- **CANONICAL** -- alpha-renaming and structural normalization match
- **SYMPY** -- algebraic expression equivalence over the configured symbolic domain
- **PARTIAL_EVAL** -- known concept values are substituted before canonical/SymPy comparison
