from core.modules import MODULE_ITEMS, WorkbenchModule, module_title


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
