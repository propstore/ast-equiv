# Import bindings in free-variable analysis

## Goal
Prerequisite for Propstore #26: imported names are Python bindings, not
undeclared concept inputs. Fix the existing owner; open a draft PR, no merge.

## State
- Isolated `fix/import-free-variable-bindings`, base `b742388` from freshly
  fetched ast-equiv master. GitHub resolves ctoth/ast-equiv to propstore/ast-equiv.
- Dirty main ast-equiv checkout untouched. No repository AGENTS.md/CLAUDE.md.
- Propstore integration currently rejects `def f(x): import math; return
  math.sqrt(x)` because the pinned collector has no Import/ImportFrom visitors.
- Implemented 9 production lines using the existing scope binder.
- Focused regression: 8 failed/6 passed before; 14 passed after.
- Full suite: 229 passed in 8.36s; package pyright: 0 errors.
- Logs: `logs/test-runs/ast-import-red-20261020-135641.log`,
  `ast-import-green-20261020-135727.log`, `ast-import-full-20261020-135811.log`.

## Decisions and why
- Smallest correction: two visitor methods (roughly 10 lines) using the existing
  scope binder, covering ordinary/dotted imports, aliases, and from imports.
- Python language reference section 7.11 specifies the names imports bind:
  https://docs.python.org/3.13/reference/simple_stmts.html#the-import-statement
- Reuse existing free-variable contract tests. No Propstore-local walker.

## Surprises
The missing import visitors were harmless while Propstore deferred the check;
enabling admission turns them into a false rejection, so fix before integration.

## Next step
Publish the draft owner PR, then pin Propstore to this owner commit and rerun
Propstore's admission and full tests. Parent arranges independent review.
