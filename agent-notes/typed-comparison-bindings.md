# Typed comparison bindings

## Goal
Repair the upstream typing failure exposed by Propstore PR #353 without
suppressing strict checks or introducing downstream wrappers.

## State
Smallest change: four binding parameter annotations in comparison.py, from
bare dict to dict[str, str]. ConceptNormalizer, canonical_dump and the internal
normalization helpers already require precisely this mapping. Runtime behavior
does not change. Both public comparison entry points share the same contract.

## Decisions and why
Fix the actual signature at its owner; downstream annotations cannot prevent
the unknown-type diagnostic on the import itself. Keep the existing known_values
contract and test/CI policy. Parent publishes and merges after hosted CI.

## Surprises
Propstore's pinned revision and current master have identical source trees.

## Next step
Apply annotations, publish a PR, wait for CI, merge, then update Propstore's pin
and remove its now-unnecessary dependency narrowing code.
