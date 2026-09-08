---
paths:
  - "examples/**"
---

# Hospital OCR example + demo law

- `run_demo.py` prints exactly TWO per-run dynamic values, one `art_<32hex>` and one function hash; every other line is deterministic ⇒ mask both before diffing, and pin the occurrence COUNT of every mask beside the masked comparison. Masking erases equality along with the value: two different 64-hex tokens normalize to one string, so the count assertion is what catches an extra or missing token and makes substitution order provably irrelevant.
- The example README's `text` transcript block is that output verbatim under the same mask, pinned by `DemoTranscriptTests`. Rerun the demo and re-diff whenever either side moves.
- The demo refuses to run under `-O`/`-OO`, where Python strips the `assert` verdicts backing its `All checks passed.` line; re-derive the verdict count whenever the act structure moves. `assert` is not a binding mechanism for anything load-bearing — where the library offers a raising form (`parse_function(..., expected_function_hash=...)` raising `IntegrityError`), route the invariant through it and make the parameter REQUIRED so no caller reaches the weak form.
- The demo deletes its temporary ledger, so every producing step (set checkpoint, promotion, export) must run BEFORE teardown; the offline resolve then reads the exported bytes alone. When an example is the consumer of a new surface, check whether its own teardown makes it an unusable producer before costing alternatives.
- Two clean runs export different bundle bytes at a stable length: per-run evidence and verification-example IDs feed the digests that feed `function_hash`. Prove the loop self-consistently (export in-process, evaluate the bytes just written) rather than comparing against a committed bundle.
- A test that grades a helper's RESULT does not bind its CHANNEL: a mutant that decodes the JSON itself and returns the reference plan passes every hit/miss predicate. Spy the shipped API with `mock.patch.object(..., wraps=...)`, then assert call count and arguments — `wraps=` leaves `return_value` a sentinel, so bind through `call_args` and compare digests, never whole documents.
- An end-to-end script needs its own integration pin, or the unit tests certify an unused helper: record the temp directory by wrapping `tempfile.TemporaryDirectory` in the script's namespace, wrap the producing library call, then assert each helper invocation carries that exact produced text with the recorded path already absent.
- Example self-checks run only by hand ⇒ behavior worth protecting lives in `tests/test_hospital_ocr_example.py`, which puts the example dir on `sys.path` and then imports the modules.
- A probe copied into a worktree relocates its `__file__`, so a `parents[N]` root derivation breaks silently: derive the root by searching upward for `pyproject.toml`, or take it as an argument.
