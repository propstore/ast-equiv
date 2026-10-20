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
- Preservation correction: deriving the shared KNOWN_BUILTINS set changed the
  existing positional-renaming policy. A direct probe of `f(object): object+1`
  versus `f(x): x+1` changed CANONICAL equivalence to NONE; restoring the old set
  in the probe restored equivalence. Added a failing comparison regression.
  Keep that existing canonicalization policy unchanged and use `vars(builtins)`
  directly only at the free-name query. This supersedes the earlier plan to
  derive KNOWN_BUILTINS; no comparison behavior change belongs in this fix.
- Final owner suite with preservation regression: 243 passed in 8.00s;
  package pyright: 0 errors. Log `review-bindings-final-20261020-142512.log`.

## Anonymous namespace correction
- Reproduced the new review finding on b4efa217: a function child table named
  genexpr makes an unrelated referenced global genexpr report namespace=True,
  but assigned=False/imported=False. Python's __check_children only matches
  child names, so namespace metadata is not sufficient binding evidence.
- Smallest owner fix: remove is_namespace() from binding evidence. Named def
  and class declarations already carry assigned=True; imports carry imported.
- Added regressions for generator/list/set/dict comprehension labels and a
  lambda expression, plus real named functions/classes and assigned lambdas.
  The literal lambda label is a reserved keyword, so valid source coverage uses
  the external identifier lambda_ rather than inventing an invalid identifier.
- Separate CI draft #5 is complete at d6d6904aa5fe39265ee2e54efb084ee832bf81e9;
  hosted run 39494960286 passed typing, 220 existing tests, and sdist/wheel builds.
  This scope correction stays on #4, separate from the CI-only change.
- Red owner regression: 1 failed/5 passed, with genexpr incorrectly removed.
  Full green after the one-condition correction: 249 passed (7.35s), package
  typing 0 errors. Logs `namespace-label-red-20261020-145122.log` and
  `namespace-label-green-20261020-145222.log` in logs/test-runs.

## Reviewed CI baseline integration
- Parent authorized ready/merge of independently reviewed CI-only #5 at exact
  d6d6904aa5fe39265ee2e54efb084ee832bf81e9. It merged as
  470f0907018af5c15b95f9ae8709b3129eb5416e; source branch is preserved.
- Post-merge push run 39497808299 completed successfully at that merge SHA.
- Rebased this isolated branch onto that baseline. Range-diff confirms all four
  semantic commits are unchanged. Backup algorithm-bindings-before-ci retains
  the old a4680232b6e19c8952262501f80da7514af05332 head.
- Locked owner checks after rebase: 249 passed (20.71s), package typing zero
  errors, source distribution and wheel both built. One pytest cache ACL
  warning is local to this Windows workspace.
- Next: push for owner CI, then repin consumer #327 and rerun its checks.
  #4 and #327 remain drafts pending
  the parent's final semantic review; neither is authorized for merge here.
