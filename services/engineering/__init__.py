"""Engineering services package.

Pure engineering-domain services that operate on an already-populated Snapshot.
They never access PDM, the UI, or signals.
"""

# Load the PDM-reduction bridge after the engineering package is available.  The
# bridge keeps the existing ArticleSet/UI workflow while supplying its base
# lengths from the validated PDM filter reduction.
from services.engineering import pdm_reduction_integration  # noqa: F401,E402
