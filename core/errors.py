"""PDM integration error types.

These give the service and UI layers meaningful, non-crashing failure modes
for connection problems, query failures, and invalid/empty results.
"""
from __future__ import annotations


class PDMError(Exception):
    """Base class for all PDM integration errors."""


class PDMConnectionError(PDMError):
    """Raised when a connection to the PDM database cannot be established."""


class PDMQueryError(PDMError):
    """Raised when a PDM query fails to execute."""


class ProductNotFoundError(PDMError):
    """Raised when a requested product cannot be found in PDM."""
