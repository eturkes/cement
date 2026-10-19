"""Provider-neutral candidate source boundary."""

from __future__ import annotations

from typing import Protocol

from .models import Candidate, CandidateRequest


class CandidateSource(Protocol):
    """An LLM adapter. Implementations return a proposal, never an applied result."""

    def propose(self, request: CandidateRequest) -> Candidate: ...
