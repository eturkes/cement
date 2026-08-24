"""Red regression probes for the M3.3 post-implementation review."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
import pathlib
import tempfile
import unittest

from cement_runtime import (
    Candidate,
    CandidateSourceError,
    CompilePolicy,
    System,
    ValidationError,
)


class _Source:
    def __init__(self, candidate: Candidate) -> None:
        self.candidate = candidate

    def propose(self, _request):
        return self.candidate


class _IterationBomb(Mapping[str, object]):
    def __getitem__(self, _key: str) -> object:
        raise RuntimeError("ITERATION-SECRET-42")

    def __iter__(self) -> Iterator[str]:
        raise RuntimeError("ITERATION-SECRET-42")

    def __len__(self) -> int:
        return 1


class _ItemsBomb(Mapping[str, object]):
    def __getitem__(self, key: str) -> object:
        if key != "model":
            raise KeyError(key)
        return "review-probe"

    def __iter__(self) -> Iterator[str]:
        return iter(("model",))

    def __len__(self) -> int:
        return 1

    def items(self):
        raise RuntimeError("ITEMS-SECRET-42")


class M3U3ReviewProbeTests(unittest.TestCase):
    def _make_system(self, *, source=None) -> System:
        temporary = tempfile.TemporaryDirectory(dir=".")
        self.addCleanup(temporary.cleanup)
        system = System(
            pathlib.Path(temporary.name) / "cement.db", candidate_source=source
        )
        system.register_operation(
            "tenant_a", "echo_1", policy=CompilePolicy(2, 1, 0)
        )
        return system

    def test_direct_submission_rejects_pair_iterable_provenance(self):
        system = self._make_system()
        candidate = Candidate(
            output={"v": 1},
            provenance=[("model", "review-probe")],  # type: ignore[arg-type]
        )

        with self.assertRaisesRegex(
            ValidationError, "^candidate provenance must be a mapping$"
        ):
            system.submit_proposal(
                "tenant_a", "echo_1", {"k": 1}, candidate=candidate
            )

    def test_direct_submission_normalizes_mapping_iteration_failure(self):
        system = self._make_system()
        candidate = Candidate(output={"v": 1}, provenance=_IterationBomb())

        with self.assertRaises(ValidationError):
            system.submit_proposal(
                "tenant_a", "echo_1", {"k": 1}, candidate=candidate
            )

    def test_source_return_rejects_pair_iterable_provenance(self):
        candidate = Candidate(
            output={"v": 1},
            provenance=[("model", "review-probe")],  # type: ignore[arg-type]
        )
        system = self._make_system(source=_Source(candidate))

        with self.assertRaisesRegex(
            CandidateSourceError, "^candidate source failed$"
        ):
            system.propose("tenant_a", "echo_1", {"k": 1})

    def test_source_return_contains_items_iteration_failure(self):
        system = self._make_system(
            source=_Source(Candidate(output={"v": 1}, provenance=_ItemsBomb()))
        )

        with self.assertRaisesRegex(
            CandidateSourceError, "^candidate source failed$"
        ):
            system.propose("tenant_a", "echo_1", {"k": 1})


if __name__ == "__main__":
    unittest.main()
