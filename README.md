# ast-equiv

Python AST equivalence comparison -- four-tier ladder.

## Tiers

1. **Canonical AST** -- alpha-rename + normalize
2. **Bytecode** -- compile and compare instruction sequences
3. **Partial evaluation** -- substitute known values, then bytecode compare
4. **Structural similarity** -- tree edit distance ratio
