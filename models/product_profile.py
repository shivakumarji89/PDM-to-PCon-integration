"""ProductProfile model.

The detected structural traits of a loaded product, produced by
:class:`~services.product_profile_service.ProductProfileService` after the
snapshot is fully loaded and persisted with the project. Pure data - fields
only, no logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class VariantGroup:
    """A property that appears as instance variants (e.g. 'Desk type' -> A,B)."""

    base: str = ""
    variants: list[str] = field(default_factory=list)


@dataclass
class ProductProfile:
    """Structural traits detected from a loaded snapshot (workflow classifier).

    Extensible: new detectors add new fields here and a rule in
    ``ProductProfileService``. ``traits`` is a flat summary tag list for quick
    downstream branching.
    """

    super_product: bool = False
    component_bucket: bool = False
    total_properties: int = 0
    coded_properties: int = 0
    uncoded_properties: int = 0
    dependent_option_properties: int = 0
    model_suffix_properties: int = 0
    instance_variant_groups: list[VariantGroup] = field(default_factory=list)
    traits: list[str] = field(default_factory=list)
