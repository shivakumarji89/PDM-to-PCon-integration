"""Reusable engineering engines.

Cross-workspace infrastructure that standardises common behaviour:
  * validation - shared result shape and readiness semantics
  * statistics - shared aggregate helpers
  * filtering  - shared search / filter / sort / group execution
  * status     - shared workspace-status formatting

These engines let each workspace supply its own rules while reusing one
execution pattern, reducing duplication across the application.
"""
