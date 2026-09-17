"""Engineering services package.

Engineering-domain services operate on an already-populated Snapshot. The
PDM reduction bridge is loaded here so the existing ArticleSet workflow can
consume validated PDM reduction lengths without moving PDM access into the
engineering reduction engine itself.
"""

from services.engineering import pdm_reduction_integration  # noqa: F401,E402
from services.engineering import engineering_class_decode_fix  # noqa: F401,E402
