# Locked ast-equiv owner CI

## Goal
Add the missing owner-package release gate in a separate draft PR. Preserve
ast-equiv #4 at b4efa217744b5dc93cb69dd18e15e50e0213374b and Propstore #327 at
80d741e62ce44a7d8e4d007c76ab675be73fb877. Parent reviews/merges CI first, then
arranges the fix rebase and re-review. No merge, ready, auth, or settings changes.

## State
- Separate `ci/locked-owner-checks` worktree from fetched ast-equiv master.
- GitHub API at exact owner head returned Actions runs total_count=0,
  check-runs total_count=0, and commit status total_count=0/statuses=[]. The
  combined status's pending label is empty evidence, not a queued test job.
- No tracked .github files at that head. Workflow listing contains only dynamic
  Dependabot Updates and Dependency Graph jobs, no project test workflow.
- Read repository manifest, lockfile, tests/typing configuration, actual global
  instructions and repository-ci skill. No repo AGENTS.md/CLAUDE.md exists.
- Implementation complete. actionlint 1.7.12: exit 0; zizmor 1.31.1 offline:
  no findings. Exact locked project commands: package typing 0 errors, all 220
  existing tests passed (17.24s), sdist and wheel builds succeeded.
- Lock update adds only Hatchling/editables and required backend dependencies;
  all pre-existing dependency versions remain unchanged. No source/tests/typing
  settings were changed.

## Decisions and why
- Smallest pipeline: one Python 3.13/Linux job on PRs and master pushes, existing
  pytest and package Pyright plus sdist/wheel build; bounded at 15 minutes.
- Add Hatchling and its editable-build requirement to the existing dev extra so
  the build backend and dynamic editable hook dependency are also locked.
  Bootstrap locked dev packages without installing this project; subsequent
  commands use no build isolation to build/install from that locked backend.
- Pin checkout v6.0.2, setup-python v6.2.0, setup-uv v8.1.0 to commit SHAs
  independently resolved from their official GitHub tag references.
- Read-only contents permission, no persisted checkout credentials, and no
  duplicate feature-branch push job. No tests or typing settings are weakened.
- Run actionlint 1.7.12 and zizmor 1.31.1, then actual locked project commands.

## Surprises
The first no-isolation editable install failed with ModuleNotFoundError for
editables. Hatchling's build/wheel source declares this dynamic editable-build
requirement; add it to the lock rather than letting build isolation fetch it.

## Next step
Publish separate draft CI PR from this branch and record exact-head hosted
results in the task handoff. Parent reviews/merges this CI first, then arranges
the #4 rebase and owner-head CI before dependency/consumer merges. Do not merge
or mark ready. Do not rebase or modify the existing fix branches in this task.
