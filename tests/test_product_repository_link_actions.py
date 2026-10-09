import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from models.product import Product
from ui.pages.product_page import ProductPage


def _page(repo_path, selected, loaded):
    page = SimpleNamespace(
        _repository_workspace=SimpleNamespace(
            repository_path=repo_path, _repository_status=MagicMock()
        ),
        _establish_repository_btn=MagicMock(),
        _selected_product=lambda: selected,
        _loaded_product=loaded,
        _context=MagicMock(),
    )
    page._repository_link_product = lambda: ProductPage._repository_link_product(page)
    return page


def _product(code="P1"):
    return Product(code=code, name="Prod")


class RepositoryLinkActionsTest(unittest.TestCase):
    def test_enabled_with_loaded_product_and_category_selected(self):
        page = _page("repo.mdb", None, _product())
        ProductPage._update_repository_actions(page)
        page._establish_repository_btn.setEnabled.assert_called_once_with(True)

    def test_disabled_without_loaded_product(self):
        page = _page("repo.mdb", None, None)
        ProductPage._update_repository_actions(page)
        page._establish_repository_btn.setEnabled.assert_called_once_with(False)

    def test_disabled_without_repository(self):
        page = _page("", None, _product())
        ProductPage._update_repository_actions(page)
        page._establish_repository_btn.setEnabled.assert_called_once_with(False)

    def test_establish_uses_loaded_product_when_group_selected(self):
        loaded = _product("LOADED")
        page = _page("repo.mdb", None, loaded)
        page._context.maintenance_repository_link_service.establish.return_value = {
            "pdm": {"product_code": "LOADED"},
            "repository": {"name": "repo"},
        }
        ProductPage._on_establish_repository(page)
        kwargs = page._context.maintenance_repository_link_service.establish.call_args.kwargs
        self.assertIs(kwargs["pdm_candidate"], loaded)

    def test_selected_leaf_still_preferred(self):
        leaf = _product("LEAF")
        page = _page("repo.mdb", leaf, _product("LOADED"))
        self.assertIs(ProductPage._repository_link_product(page), leaf)
        ProductPage._update_repository_actions(page)
        page._establish_repository_btn.setEnabled.assert_called_once_with(True)

    def test_status_message_reflects_loaded_product(self):
        for loaded, expected in (
            (_product(), "Ready to establish"),
            (None, "Load/select a PDM product"),
        ):
            page = _page("repo.mdb", None, loaded)
            page._update_repository_actions = MagicMock()
            page._context_module = ProductPage.__init__.__globals__["WorkbenchModule"].MAINTENANCE
            page.snapshot_changed = MagicMock()
            ProductPage._on_shared_repository_loaded(page, None)
            text = page._repository_workspace._repository_status.setText.call_args[0][0]
            self.assertIn(expected, text)


if __name__ == "__main__":
    unittest.main()


class RealProductPageLinkTest(unittest.TestCase):
    """Drive the real ProductPage tree/selection (not mocks)."""

    @classmethod
    def setUpClass(cls):
        import os
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        cls._app = QApplication.instance() or QApplication([])

    def _page(self):
        from core.application_context import ApplicationContext
        from core.modules import WorkbenchModule
        # Hermetic: never start the background navigator (registry cache / PDM).
        with patch.object(ProductPage, "_load_navigator", lambda *a, **k: None):
            page = ProductPage(ApplicationContext())
        page.set_module(WorkbenchModule.MAINTENANCE)
        products = [
            Product(id=str(i), code=f"AL{i}", name=f"P{i}", category="Bolster",
                    description="Cat", catalogue_id="C1", range_name="R")
            for i in range(3)
        ]
        page._populate_results(products, expand=True, lazy=False)
        return page

    def test_enablement_follows_repository_and_selected_leaf(self):
        page = self._page()
        btn = page._establish_repository_btn
        category = page._tree.topLevelItem(0).child(0)
        leaf = category.child(0)

        # No repository: disabled even with a leaf selected, reason says so.
        leaf.setSelected(True)
        self.assertFalse(btn.isEnabled())
        self.assertIn("repository", btn.toolTip().lower())

        # Repository loaded, but only a category (family) node selected and
        # nothing loaded: disabled, reason points at the missing product.
        page._repository_workspace._repository_path_value = "C:/repo"
        leaf.setSelected(False)
        category.setSelected(True)
        self.assertFalse(btn.isEnabled())
        self.assertIn("product", btn.toolTip().lower())

        # Leaf selected: enabled.
        category.setSelected(False)
        leaf.setSelected(True)
        self.assertTrue(btn.isEnabled())
        self.assertIn("Persist", btn.toolTip())

    def test_loaded_product_enables_link_with_category_selected(self):
        page = self._page()
        page._repository_workspace._repository_path_value = "C:/repo"
        page._tree.topLevelItem(0).child(0).setSelected(True)
        self.assertFalse(page._establish_repository_btn.isEnabled())
        page._loaded_product = _product("LOADED")
        page._update_repository_actions()
        self.assertTrue(page._establish_repository_btn.isEnabled())
