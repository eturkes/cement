"""Public error hierarchy."""


class CementError(Exception):
    """Base error for expected Cement failures."""


class ValidationError(CementError, ValueError):
    """Untrusted input failed a bounded structural check."""


class NotFoundError(CementError, LookupError):
    """Requested record does not exist in the caller's partition."""


class ConflictError(CementError):
    """A write conflicts with the ledger's current state: an identity already in use (a source id,
    an observation id) or a hash or plan that changed after the caller read it. Re-read the
    state; this is the one class where a retry is the intended recovery (CLI exit 4)."""


class StateError(CementError):
    """Requested state transition is invalid or stale."""


class IntegrityError(CementError):
    """Persisted content does not match its bound digest or ABI."""


class CandidateSourceError(CementError):
    """The candidate source failed to produce a usable candidate.

    A source adapter raises this error to declare its own failure.
    ``System.propose`` also raises it when the source fails. The instance that
    ``System.propose`` raises carries no detail from the source: no class, no
    message, no cause, no context, and no adapter frame.
    """
