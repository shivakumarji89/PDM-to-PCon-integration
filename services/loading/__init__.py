"""Loading Engine package.

The single loading backend (skeleton). Establishes the frozen pipeline,
request/result models and progress hooks; bulk SQL stages are placeholders that
will be filled in later. Existing Load Product / Load Family are untouched.
"""
from __future__ import annotations

from services.loading.load_request import (
    LoadRequest,
    LoadResult,
    SelectionType,
)
from services.loading.loading_engine import LoadingEngine

__all__ = [
    "LoadRequest",
    "LoadResult",
    "LoadingEngine",
    "SelectionType",
]
