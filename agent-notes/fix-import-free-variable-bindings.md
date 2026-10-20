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
Push the reviewed correction to existing draft #4, pin Propstore to that exact
commit, rerun Propstore's focused/full checks and final-head CI, and return full
SHAs to the parent for re-review. No PR-description edits, merges, or ready action.

## Review correction: lexical scope owner
- Draft PR #4 at `f27924d993ac91d469f52bae08707b5b2afde89b` and Propstore
  #327 at `8f3d87945d6606d106250c31cb154f35578fa02e` received read-only findings.
- Reproduced all five categories: class imports leaking outward, ignored store
  subscripts, late closure/module bindings, except aliases, and omitted builtins.
  `review-bindings-red-20261020-141525.log`: 11 failed, 1 passed.
- Re-read Pierce definition 5.3.2 visually and Python 3.13 execution-model,
  exception, and symtable references. Block bindings are lexical, independent
  of statement order; class namespaces do not enclose method bodies.
- Target: Python's compiler-owned `symtable.SymbolTable` determines scopes;
  ast-equiv retains its public AST-to-external-name query and builtin exclusion.
- Disposition: `_FreeVariableCollector` is duplicated Python binding machinery;
  delete it. Rewrite `extract_free_variables` to query the existing compiler
  owner. Derive exported `KNOWN_BUILTINS` from `builtins`, rather than keeping
  incomplete duplicated metadata. Other canonicalization/comparison code stays.
- Smallest replacement: about 30 production lines instead of ~160 visitor lines.
  No new scope model, statement-order simulation, or runtime/dataflow checker.
- Active cleanup slice is these binding symbols only, as required by the user's
  bounded correctness-fix scope; do not delete unrelated canonicalization.
- Forbidden search: `_FreeVariableCollector`, `_visit_target_loads`, `_bind_target`
  must have zero production hits. Runtime gates: existing owner API/property/full
  tests, new reproductions, package typing, and Propstore compiler admission.
- Symtable syntax failures must use AlgorithmParseError and normal Propstore
  body diagnostics; no compiler exception may escape admission.
- Replacement owner validation: 30 focused API/property/reproducer tests passed;
  after adding a typed invalid-nonlocal test, full suite: 242 passed in 8.84s.
  Package pyright: 0 errors. Forbidden production-symbol searches have zero hits.
- Logs: `review-bindings-green-20261020-141709.log` and
  `review-bindings-full-20261020-141842.log` in `logs/test-runs/`.
- The old private collector was deleted and its only caller rewritten to the
  compiler owner. No replacement hand-written scope walker survives. The public
  extraction API and all earlier import/API/property/comparison tests remain.
