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
