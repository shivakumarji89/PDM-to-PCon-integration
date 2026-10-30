"""QA → Article OBX Generator (pCon SDK).

Isolated pipeline that drives the official pCon.planner Plugin SDK through a
plugin hosted in pCon.planner:

    catalogue → base articles → live properties → generation plan
        → plugin enumerates configurations with pCon's OFML runtime
        → ``IArticleManager.ExportBasketToObx`` → independent OBX validation

See ``docs/04_Reference/pCon/SDK_Article_OBX_Generator.md`` for the SDK
evidence behind each step. Nothing here touches Development, Maintenance,
pricing, VARCOND, Metatype or the shared snapshot infrastructure.
"""
from services.pcon_sdk_obx.bridge import (
    BridgeSettings,
    PconPluginBridge,
    PluginTimeoutError,
    PluginUnavailableError,
)
from services.pcon_sdk_obx.catalog_service import PconCatalogService
from services.pcon_sdk_obx.configuration_service import PconConfigurationService, PlanValidationError
from services.pcon_sdk_obx.generation_service import GenerationOutcome, PconObxGenerationService
from services.pcon_sdk_obx.protocol import PluginProtocolError
from services.pcon_sdk_obx.validation_service import (
    ObxOutputValidator,
    ObxValidationSummary,
    ReferenceComparison,
    ReferenceObxComparer,
)

__all__ = [
    "BridgeSettings",
    "GenerationOutcome",
    "ObxOutputValidator",
    "ObxValidationSummary",
    "PconCatalogService",
    "PconConfigurationService",
    "PconObxGenerationService",
    "PconPluginBridge",
    "PlanValidationError",
    "PluginProtocolError",
    "PluginTimeoutError",
    "PluginUnavailableError",
    "ReferenceComparison",
    "ReferenceObxComparer",
]
