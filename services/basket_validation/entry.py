r"""Entry point behind QA → Article OBX Generator → *Basket Validation*.

Connects the button to the standalone pCon.basket CE automation (``C:\pcon_automation\step18_batch_obx.py``) through
:mod:`services.basket_validation.runner`. Independent of the OCD Engine and of OBX generation: it only receives OBX file
paths. The automation folder / interpreter are configurable (``MK_BASKET_AUTOMATION_ROOT`` / ``MK_BASKET_AUTOMATION_PYTHON``).
"""
from __future__ import annotations

from services.basket_validation.runner import (  # noqa: F401  (re-exported for the UI)
    AutomationConfig, BasketValidationUnavailable, CHECK_LABELS, ERROR, FAIL, FileResult, NOT_VERIFIED, PASS, PHASES,
    ValidationResult, run_validation)

BASKET_VALIDATION_ENABLED = True


def default_config() -> AutomationConfig:
    return AutomationConfig.from_environment()
