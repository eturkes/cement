"""Public error hierarchy."""


class CementError(Exception):
    """Base error for expected Cement failures."""


class ValidationError(CementError, ValueError):
    """Untrusted input failed a bounded structural check."""


class NotFoundError(CementError, LookupError):
    """Requested record does not exist in the caller's partition."""


class ConflictError(CementError):
    """A unique identity was reused for different immutable content."""


class StateError(CementError):
    """Requested state transition is invalid or stale."""


class IntegrityError(CementError):
    """Persisted content does not match its bound digest or ABI."""


class CandidateSourceError(CementError):
    """The supervised fallback source failed before creating a proposal."""
