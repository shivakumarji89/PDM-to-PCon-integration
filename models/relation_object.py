"""RelationObject domain model.

An OCD relation object (``tCOMd_RelObj`` bound to ``tCOMd_Relation`` via
``tCOMd_RelObjRel``): a named relation (``B_``/``A_``) with its type, domain,
evaluation order and OCD_4 logic ``body``. Fields only - no logic.
"""
from __future__ import annotations

from dataclasses import dataclass

#: OCD relation types (``tCOMd_RelObjRel.com_RelObjTypeCode``).
RELATION_TYPE_LABELS: dict[str, str] = {
    "1": "Precondition",
    "2": "Selection Condition",
    "3": "Action",
    "4": "Constraint",
    "5": "Reaction",
    "6": "Post-Reaction",
}

#: OCD relation domains (``tCOMd_RelObjRel.com_RelObjDomainCode``).
RELATION_DOMAIN_LABELS: dict[str, str] = {
    "C": "Configuration",
    "P": "Price",
    "BOI": "Bill of Items",
    "PCKG": "Packaging",
    "TAX": "Taxation",
}


@dataclass
class RelationObject:
    """One OCD relation object with its logic body."""

    name: str = ""
    type_code: str = "1"
    domain: str = "C"
    order: int = 100
    body: str = ""
    class_name: str = ""
    # The entity this relation binds to (the OCD ``RelObjID`` link), recorded at
    # derivation time: the property, plus the value for a value-level relation.
    property_id: str = ""
    value_id: str = ""
