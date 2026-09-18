from core.enums import WorkflowStep
from core.modules import MODULE_ITEMS, WorkbenchModule, module_title, module_workflows


def test_top_level_modules_are_defined_in_order():
    assert [item.module for item in MODULE_ITEMS] == [
        WorkbenchModule.DEVELOPMENT,
        WorkbenchModule.MAINTENANCE,
        WorkbenchModule.QA_VALIDATION,
        WorkbenchModule.METATYPE,
        WorkbenchModule.OAP,
    ]


def test_module_titles():
    assert module_title(WorkbenchModule.DEVELOPMENT) == "Development"
    assert module_title(WorkbenchModule.MAINTENANCE) == "Maintenance"
    assert module_title(WorkbenchModule.QA_VALIDATION) == "QA Validation"
    assert module_title(WorkbenchModule.METATYPE) == "Metatype"
    assert module_title(WorkbenchModule.OAP) == "OAP"


def test_module_workflow_mapping_uses_existing_workflows():
    assert module_workflows(WorkbenchModule.DEVELOPMENT) == (
        WorkflowStep.PRODUCT,
        WorkflowStep.ARTICLES,
        WorkflowStep.CLASS_CREATION,
        WorkflowStep.TEXT,
        WorkflowStep.RELATION,
        WorkflowStep.PRICING,
        WorkflowStep.PRICING_RELATION,
        WorkflowStep.REVIEW,
        WorkflowStep.ENGINEERING,
    )
    assert module_workflows(WorkbenchModule.MAINTENANCE) == (WorkflowStep.PRODUCT, WorkflowStep.MAINTENANCE)
    assert module_workflows(WorkbenchModule.QA_VALIDATION) == (
        WorkflowStep.PRODUCT,
        WorkflowStep.CET_SIF_VALIDATION,
        WorkflowStep.OBX_VALIDATION,
    )
    assert module_workflows(WorkbenchModule.METATYPE) == (WorkflowStep.PRODUCT,)
    assert module_workflows(WorkbenchModule.OAP) == (WorkflowStep.PRODUCT,)
