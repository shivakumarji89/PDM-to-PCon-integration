"""Application-wide enumerations.

Single source of truth for shared enums. Pure metadata - no logic.
"""
from __future__ import annotations

from enum import Enum


class WorkflowStep(Enum):
    """Identifiers for each workspace step, in workflow order."""

    PRODUCT = "product"
    ARTICLES = "articles"
    PROPERTIES = "properties"
    VALUES = "values"
    OPTIONS = "options"
    OPTION_VALUES = "option_values"
    CLASS_CREATION = "class_creation"
    TEXT = "text"
    RELATION = "relation"
    PRICING = "pricing"
    PRICING_RELATION = "pricing_relation"
    REVIEW = "review"
    ENGINEERING = "engineering"
    MAINTENANCE = "maintenance"
    #: Standalone CET SIF validation tool (self-contained, disconnectable).
    CET_SIF_VALIDATION = "cet_sif_validation"
    #: Standalone OBX validation tool.
    OBX_VALIDATION = "obx_validation"


class SnapshotStatus(Enum):
    """Lifecycle state of a product snapshot."""

    NOT_CREATED = "not_created"
    CREATING = "creating"
    READY = "ready"
    MODIFIED = "modified"
