"""Main application window.

Assembles the four sections of the workbench:
  * Left:   Workflow Navigator
  * Center: QStackedWidget of workspace pages
  * Right:  PDM Explorer
  * Plus a menu bar and status bar.

All panels are resizable via QSplitter. Phase 1 is UI only - the only
behavior is page navigation.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QSettings, QProcess
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QDockWidget,
    QLabel,
    QMainWindow,
    QMenuBar,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QTableWidget,
    QTreeWidget,
    QWidget,
)

from core.application_context import ApplicationContext
from core.workflow import WORKFLOW_ITEMS, WorkflowStep
from ui import theme
from ui.navigation.workflow_navigator import WorkflowNavigator
from core.modules import WorkbenchModule, module_title, module_workflows
from ui.pages.articles_page import ArticlesPage
from ui.pages.base_page import BasePage
from ui.pages.class_creation_page import ClassCreationPage
from ui.pages.engineering_page import EngineeringPage
from ui.pages.pricing_page import PricingPage
from ui.pages.pricing_relation_page import PricingRelationPage
from ui.pages.product_page import ProductPage
from ui.pages.relation_page import RelationPage
from ui.pages.review_page import ReviewPage
from ui.pages.text_page import TextPage
from ui.pages.maintenance_page import MaintenancePage
from ui.pages.cet_sif_validation_page import CetSifValidationPage  # CET SIF (disconnectable)
from ui.pages.obx_validation_page import ObxValidationPage
from ui.pages.module_home_page import ModuleHomePage
from ui.pages.module_placeholder_page import ModulePlaceholderPage
from workflow.host import WorkspaceHost
from workflow.manager import WorkflowManager
from ui.widgets.activity_panel import ActivityPanel
from ui.widgets.assistant_panel import AssistantPanel
from ui.widgets.background_status import BackgroundStatusIndicator
from ui.widgets.data_table import standardize_table
from ui.widgets.explorer_tree import standardize_tree


class MainWindow(QMainWindow):
    """Top-level window hosting the workbench shell and workflow framework."""

    #: Default horizontal sizes for [navigator, workspace] when no saved layout.
    _DEFAULT_SPLITTER_SIZES = [260, 1040]
    #: Default width of the Engineering Assistant dock.
    _DEFAULT_ASSISTANT_WIDTH = 300

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MK Product Workbench")
        self.resize(1360, 860)

        # Shared application context (services + state) for the whole window.
        self._context = ApplicationContext()
        saved_xocd = QSettings().value("xocd/svnPath", "", type=str)
        if saved_xocd:
            self._context.config.xocd_svn_path = saved_xocd

        self._pages: dict[WorkflowStep, BasePage] = {}
        self._navigator = WorkflowNavigator(self)
        self._active_module: WorkbenchModule | None = None
        self._stack = QStackedWidget(self)
        self._module_home = ModuleHomePage(self)
        self._module_placeholder = ModulePlaceholderPage(self)
        self._stack.addWidget(self._module_home)
        self._stack.addWidget(self._module_placeholder)
        self._module_home.module_selected.connect(self._on_module_selected)
        self._module_placeholder.back_button.clicked.connect(self._show_module_home)

        self._build_pages()

        # Workflow framework: host owns page lifecycle, manager owns navigation.
        self._host = WorkspaceHost(self._stack, self._pages)
        self._manager = WorkflowManager(
            self._context, self._host, [item.step for item in WORKFLOW_ITEMS]
        )

        self._build_central_layout()
        self._build_assistant_dock()
        self._build_activity_dock()
        self._build_menu_bar()
        self._build_status_bar()
        self._apply_design_standards()

        self._navigator.set_manager(self._manager)
        self._manager.step_changed.connect(self._on_step_changed)

        # Restore the user's saved layout (panel sizes, dock positions,
        # collapse state) before activating the first workspace.
        self._restore_layout()

        # Start at Level 1. No workflow is shown until a module is selected.
        self._show_module_home()


    def _on_step_changed(self, step: WorkflowStep) -> None:
        title = self._manager.title(step)
        if step != WorkflowStep.PRODUCT and not self._product_page.is_snapshot_ready():
            self.statusBar().showMessage(
                f"{title} - load a product on the Product page first"
            )
        else:
            self.statusBar().showMessage(f"Ready - {title} workspace")

    def log_activity(self, kind: str, message: str) -> None:
        """Forward a detailed activity line to the Engineering Activity panel.

        Public hook so long-running operations (Load Family, and future
        Generate/Import/Export) can feed their progress-reporter activity events
        into the shared Activity timeline.
        """
        self._assistant_panel.log_activity(kind, message)


    def _on_product_loaded(self, label: str) -> None:
        self._product_status.setText(label)


    def _on_snapshot_changed(self) -> None:
        self.refresh_workspaces()

    #: Workspaces that read the Snapshot's product data directly, refreshed as
    #: soon as the snapshot is published (before Engineering Initialization).
    _SNAPSHOT_DEPENDENT_STEPS: tuple[WorkflowStep, ...] = ()

    #: Workspaces that consume ``snapshot.engineering`` and therefore only
    #: become populated once background Engineering Initialization completes.
    #: Class Creation groups by the reduction's ``article_sets`` (materialised by
    #: Engineering Initialization), so it belongs here, not at snapshot-publish.
    _ENGINEERING_DEPENDENT_STEPS = (
        # Class Creation is authoritative for Development article reduction,
        # so it must materialize Article Sets before Articles is refreshed.
        WorkflowStep.CLASS_CREATION,
        WorkflowStep.ARTICLES,
        WorkflowStep.TEXT,
        WorkflowStep.RELATION,
        WorkflowStep.PRICING,
        WorkflowStep.PRICING_RELATION,
        WorkflowStep.REVIEW,
        WorkflowStep.ENGINEERING,
    )


    def _on_snapshot_published(self) -> None:
        """Family load Stage A: the snapshot is published but Engineering
        Initialization is still running. Refresh only the snapshot-dependent
        workspaces; the engineering-dependent ones are refreshed once, later, by
        :meth:`_on_engineering_ready`, so no workspace is rebuilt twice.
        """
        for step in self._SNAPSHOT_DEPENDENT_STEPS:
            page = self._pages.get(step)
            if page is not None and hasattr(page, "refresh"):
                page.refresh()
        self._manager.refresh()


    def _on_engineering_ready(self) -> None:
        """Background Engineering Initialization finished: refresh the
        engineering-dependent workspaces exactly once.

        The Product page emits this synchronously during the load-finalization
        stage. Keep this pass single-purpose; _on_load_complete must not rebuild
        the same pages a second time.
        """
        product = self._product_page
        reporter = getattr(product, "_family_reporter", None)
        labels = {
            WorkflowStep.ARTICLES: "Finalizing Articles Workspace",
            WorkflowStep.CLASS_CREATION: "Finalizing Class Creation Workspace",
            WorkflowStep.TEXT: "Finalizing Text Workspace",
            WorkflowStep.RELATION: "Finalizing Relation Workspace",
            WorkflowStep.PRICING: "Finalizing Pricing Workspace",
            WorkflowStep.PRICING_RELATION: "Finalizing Pricing Relation Workspace",
            WorkflowStep.REVIEW: "Finalizing Review Workspace",
            WorkflowStep.ENGINEERING: "Finalizing Engineering Workspace",
        }
        for step in self._ENGINEERING_DEPENDENT_STEPS:
            label = labels.get(step, f"Finalizing {step.name.title()} Workspace")
            if reporter is not None:
                reporter.advance(label)
            page = self._pages.get(step)
            if page is not None and hasattr(page, "refresh"):
                page.refresh()
        self._manager.refresh()
        self.statusBar().showMessage("Snapshot Ready")


    def _on_load_complete(self) -> None:
        """Mark the load complete without rebuilding every workspace again.

        Engineering-dependent workspaces were already refreshed by
        _on_engineering_ready. Re-running refresh_workspaces here caused the
        finalization phase to execute the same expensive Article/Class Creation
        work twice.
        """
        reporter = getattr(self._product_page, "_family_reporter", None)
        if reporter is not None:
            reporter.advance("Workspace finalization complete")
        self._manager.refresh()
        self.statusBar().showMessage("Snapshot Ready")


    def refresh_workspaces(self) -> None:
        """Refresh all workspaces and the workflow state."""
        for page in self._refreshable_pages:
            page.refresh()
        self._manager.refresh()

    # -- UI standardisation ------------------------------------------------

    def _build_assistant_dock(self) -> None:
        # AI Engineering Assistant (dockable, additive layer above the app).
        self._assistant_panel = AssistantPanel(
            self._context, self._manager, self._pages, self.refresh_workspaces, self
        )
        # The panel provides its own bold "Engineering Assistant" header, and
        # the dock's title bar is hidden so no title-bar box appears above it.
        # Show/hide is still available from the View menu toggle.
        dock = QDockWidget("Engineering Assistant", self)
        dock.setObjectName("assistantDock")
        dock.setWidget(self._assistant_panel)
        dock.setTitleBarWidget(QWidget(dock))
        dock.setMinimumWidth(260)
        dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        self._assistant_dock = dock
        # Keep the assistant compact by default so the Product Workspace gets
        # more room; docking/floating/resizing behaviour is unchanged.
        self.resizeDocks([dock], [self._DEFAULT_ASSISTANT_WIDTH], Qt.Orientation.Horizontal)

    def _build_activity_dock(self) -> None:
        # Activity panel (dockable, additive layer). It subscribes to the shared
        # ActivityService resolved from the application context - no new bus or
        # service is created here, and no workflow is touched.
        self._activity_panel = ActivityPanel(self._context.activity_service, self)
        dock = QDockWidget("Activity", self)
        dock.setObjectName("activityDock")
        dock.setWidget(self._activity_panel)
        dock.setMinimumWidth(260)
        dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        self._activity_dock = dock
        # Tab it together with the assistant so it does not consume extra space
        # by default; standard dock show/hide/float behaviour is unchanged.
        self.tabifyDockWidget(self._assistant_dock, dock)
        self._assistant_dock.raise_()
        # Hidden by default; shown via the View menu toggle.
        dock.hide()

    def _build_pages(self) -> None:
        # Every workspace page takes the shared context; the product page also
        # emits load/snapshot signals the window reacts to.
        constructors: dict[WorkflowStep, type[BasePage]] = {
            WorkflowStep.PRODUCT: ProductPage,
            WorkflowStep.ARTICLES: ArticlesPage,
            WorkflowStep.CLASS_CREATION: ClassCreationPage,
            WorkflowStep.TEXT: TextPage,
            WorkflowStep.RELATION: RelationPage,
            WorkflowStep.PRICING: PricingPage,
            WorkflowStep.PRICING_RELATION: PricingRelationPage,
            WorkflowStep.REVIEW: ReviewPage,
            WorkflowStep.ENGINEERING: EngineeringPage,
            WorkflowStep.MAINTENANCE: MaintenancePage,
            # CET SIF Validation - unused when the step is disconnected in core.workflow.
            WorkflowStep.CET_SIF_VALIDATION: CetSifValidationPage,
            WorkflowStep.OBX_VALIDATION: ObxValidationPage,
        }

        self._refreshable_pages: list[BasePage] = []
        for item in WORKFLOW_ITEMS:
            page = constructors[item.step](self._context, self)
            if item.step == WorkflowStep.PRODUCT:
                self._product_page = page
                page.product_loaded.connect(self._on_product_loaded)
                page.snapshot_changed.connect(self._on_snapshot_changed)
                page.snapshot_published.connect(self._on_snapshot_published)
                page.engineering_ready.connect(self._on_engineering_ready)
                page.load_complete.connect(self._on_load_complete)
            elif hasattr(page, "refresh"):
                self._refreshable_pages.append(page)
            self._stack.addWidget(page)
            self._pages[item.step] = page

    def _build_central_layout(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setObjectName("mainSplitter")
        splitter.setChildrenCollapsible(False)

        left = self._build_left_panel()
        center = self._build_center_panel()

        # Minimum widths keep panels usable while remaining freely resizable.
        left.setMinimumWidth(220)
        center.setMinimumWidth(480)

        splitter.addWidget(left)
        splitter.addWidget(center)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes(self._DEFAULT_SPLITTER_SIZES)

        self._left_panel = left
        self._main_splitter = splitter
        self.setCentralWidget(splitter)

    def _build_left_panel(self) -> QWidget:
        from PySide6.QtWidgets import QComboBox, QPushButton, QVBoxLayout
        from core.config import PDM_DATABASE_PRESETS
        from ui.components._styles import secondary_button_qss

        container = QWidget()
        container.setObjectName("leftPanel")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(
            theme.PANEL_INSET, theme.PANEL_INSET,
            theme.PANEL_INSET, theme.PANEL_INSET,
        )

        # PDM database selector, above the workflow navigator. Choosing a
        # database re-points the connection so product loads / snapshots
        # come from that database.
        db_label = QLabel("Database:", container)
        db_label.setObjectName("databaseSelectorLabel")
        layout.addWidget(db_label)

        self._database_selector = QComboBox(container)
        self._database_selector.setObjectName("databaseSelector")
        self._database_selector.addItems(list(PDM_DATABASE_PRESETS.keys()))
        active = self._context.config.active_pdm_preset()
        if active:
            self._database_selector.setCurrentText(active)
        self._database_selector.currentTextChanged.connect(self._on_database_changed)
        layout.addWidget(self._database_selector)

        module_label = QLabel("Module", container)
        module_label.setObjectName("activeModuleLabel")
        layout.addWidget(module_label)
        self._active_module_label = module_label

        monitor_btn = QPushButton("Check PDM Changes", container)
        monitor_btn.setObjectName("pdmMonitorBtn")
        monitor_btn.setStyleSheet(secondary_button_qss("pdmMonitorBtn"))
        monitor_btn.clicked.connect(self._on_check_pdm_changes)
        layout.addWidget(monitor_btn)

        layout.addSpacing(theme.SECTION_SPACING)
        layout.addWidget(self._navigator, 1)
        return container

    def _on_module_selected(self, module: WorkbenchModule) -> None:
        """Enter Level 2 and expose only the workflows for the selected module."""
        self._active_module = module
        self._product_page.set_module(module)
        steps = list(module_workflows(module))
        self._active_module_label.setText(module_title(module))

        self._module_home.hide()
        self._module_placeholder.hide()
        self._assistant_dock.hide()
        self._activity_dock.hide()
        self._toggle_navigator_action.setEnabled(True)

        if not steps:
            self._left_panel.hide()
            self._nav_footer.hide()
            self._module_placeholder.set_module(module)
            self._module_placeholder.show()
            self._stack.setCurrentWidget(self._module_placeholder)
            self.statusBar().showMessage(f"Module: {module_title(module)}", 4000)
            return

        # Preserve the module's declared workflow order. Filtering the
        # global WORKFLOW_ITEMS tuple alone would incorrectly force its legacy
        # Articles-before-Class-Creation order onto Development.
        items_by_step = {item.step: item for item in WORKFLOW_ITEMS}
        self._navigator.set_workflow_items(tuple(
            items_by_step[step] for step in steps if step in items_by_step
        ))
        self._manager.set_steps(steps)
        self._left_panel.show()
        self._nav_footer.show()
        self._stack.setCurrentWidget(self._pages[self._manager.current_step()])
        self.statusBar().showMessage(f"Module: {module_title(module)}", 4000)

    def _show_module_home(self) -> None:
        """Return to Level 1 and hide all workflow-specific UI."""
        self._active_module = None
        self._left_panel.hide()
        self._nav_footer.hide()
        self._assistant_dock.hide()
        self._activity_dock.hide()
        self._toggle_navigator_action.setEnabled(False)
        self._toggle_navigator_action.setChecked(False)
        self._module_placeholder.hide()
        self._module_home.show()
        self._stack.setCurrentWidget(self._module_home)
        self.statusBar().showMessage("Select a module", 4000)

    def _on_database_changed(self, name: str) -> None:
        """Switch the active PDM database and re-sync the product hierarchy."""
        if not self._context.config.set_pdm_database(name):
            return
        cfg = self._context.config
        self.statusBar().showMessage(
            f"PDM database set to {name} ({cfg.pdm_server}/{cfg.pdm_database})", 6000
        )
        # A switch is a clean slate: drop the loaded snapshot and every workspace
        # built from the old database, then reload the hierarchy from the new one
        # - so no lingering query result or view can mix databases.
        self._product_page.reset_for_database_switch()

    def _build_center_panel(self) -> QWidget:
        """Center workspace: the active page plus the shared Back / Continue
        navigation footer that drives the workflow for whichever page is shown."""
        from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout
        from ui.components._styles import secondary_button_qss

        container = QWidget()
        container.setObjectName("centerPanel")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(
            theme.PANEL_INSET, theme.PANEL_INSET,
            theme.PANEL_INSET, theme.PANEL_INSET,
        )
        layout.setSpacing(theme.SECTION_SPACING)
        layout.addWidget(self._stack, 1)

        footer_widget = QWidget(container)
        footer = QHBoxLayout(footer_widget)
        footer.setContentsMargins(0, 0, 0, 0)
        self._modules_btn = QPushButton("\u2190 Modules", footer_widget)
        self._modules_btn.setObjectName("backToModulesButton")
        self._modules_btn.setToolTip("Return to the module selection")
        self._modules_btn.setStyleSheet(secondary_button_qss("backToModulesButton"))
        self._modules_btn.clicked.connect(self._show_module_home)
        footer.addWidget(self._modules_btn)

        self._back_btn = QPushButton("\u2190 Back", footer_widget)
        self._back_btn.setObjectName("navBackButton")
        self._back_btn.setToolTip("Go to the previous workflow step")
        self._back_btn.clicked.connect(self._on_nav_back)
        footer.addWidget(self._back_btn)
        footer.addStretch(1)
        self._continue_btn = QPushButton("Continue \u2192", footer_widget)
        self._continue_btn.setObjectName("navContinueButton")
        self._continue_btn.setDefault(True)
        self._continue_btn.setToolTip("Continue to the next workflow step")
        self._continue_btn.clicked.connect(self._on_nav_continue)
        footer.addWidget(self._continue_btn)
        self._nav_footer = footer_widget
        layout.addWidget(footer_widget)

        self._manager.state_changed.connect(self._update_nav_buttons)
        self._manager.step_changed.connect(lambda *_: self._update_nav_buttons())
        return container

    def _on_nav_back(self) -> None:
        self._manager.back()

    def _on_nav_continue(self) -> None:
        self._manager.next()

    def _update_nav_buttons(self) -> None:
        self._back_btn.setEnabled(self._manager.can_go_back())
        self._continue_btn.setEnabled(self._manager.can_continue())
        steps = self._manager.steps()
        current = self._manager.current_step()
        index = steps.index(current)
        if index + 1 < len(steps):
            next_title = self._manager.title(steps[index + 1])
            self._continue_btn.setText(f"Continue to {next_title} \u2192")
        else:
            self._continue_btn.setText("Continue \u2192")

    def _build_menu_bar(self) -> None:
        menu_bar: QMenuBar = self.menuBar()

        file_menu = menu_bar.addMenu("&File")
        new_action = QAction("New", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._on_file_new)
        file_menu.addAction(new_action)
        open_action = QAction("Open...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_file_open)
        file_menu.addAction(open_action)
        save_action = QAction("Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._on_file_save)
        file_menu.addAction(save_action)
        file_menu.addSeparator()
        exit_action = self._make_action("Exit")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = menu_bar.addMenu("&View")

        # Collapsible side panels. The workspace expands automatically when
        # either panel is hidden (splitter stretch + dock removal).
        nav_action = QAction("Workflow Navigator", self)
        nav_action.setCheckable(True)
        nav_action.setChecked(self._left_panel.isVisible())
        nav_action.toggled.connect(self._left_panel.setVisible)
        self._toggle_navigator_action = nav_action
        view_menu.addAction(nav_action)

        assistant_action = self._assistant_dock.toggleViewAction()
        assistant_action.setText("Engineering Assistant")
        view_menu.addAction(assistant_action)

        activity_action = self._activity_dock.toggleViewAction()
        activity_action.setText("Activity")
        view_menu.addAction(activity_action)

        view_menu.addSeparator()
        reset_action = QAction("Reset Layout", self)
        reset_action.triggered.connect(self._reset_layout)
        view_menu.addAction(reset_action)

        tools_menu = menu_bar.addMenu("&Tools")
        tools_menu.addAction(self._make_action("Options..."))

        settings_menu = menu_bar.addMenu("&Settings")
        settings_menu.addAction(self._make_action("Preferences..."))

        generate_menu = menu_bar.addMenu("&Generate")
        varcond_action = QAction("Generate VARCOND", self)
        varcond_action.triggered.connect(self._on_generate_varcond)
        generate_menu.addAction(varcond_action)
        pricing_action = QAction("Generate Pricing", self)
        pricing_action.triggered.connect(self._on_generate_pricing)
        generate_menu.addAction(pricing_action)
        generate_menu.addSeparator()
        value_tables_action = QAction("Export Value Tables...", self)
        value_tables_action.triggered.connect(self._on_export_value_tables)
        generate_menu.addAction(value_tables_action)
        xocd_action = QAction("Export XOCD Package...", self)
        xocd_action.triggered.connect(self._on_export_xocd)
        generate_menu.addAction(xocd_action)
        mdb_action = QAction("Export MDB (Direct)...", self)
        mdb_action.triggered.connect(self._on_export_mdb)
        generate_menu.addAction(mdb_action)

        help_menu = menu_bar.addMenu("&Help")
        help_menu.addAction(self._make_action("About"))

    # -- File menu (project save/open) ------------------------------------
    def _projects_dir(self):
        """The workspace ``projects/`` folder (created on demand)."""
        from pathlib import Path

        directory = Path("projects").resolve()
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def _last_project_dir(self) -> str:
        """The folder last used for opening/saving a project.

        Falls back to the workspace ``projects/`` folder until the user picks
        a location. (When a repository is configured later, wire it here.)
        """
        from pathlib import Path

        saved = QSettings().value("lastProjectDir", "", type=str)
        if saved and Path(saved).is_dir():
            return saved
        return str(self._projects_dir())

    def _last_project_path(self) -> str | None:
        """The file path of the last opened/saved project.

        Returns ``None`` if no project has been opened yet.
        """
        from pathlib import Path

        saved = QSettings().value("lastProjectPath", "", type=str)
        if saved and Path(saved).is_file():
            return saved
        return None

    def _remember_project_path(self, path: str) -> None:
        """Persist the project file path for auto-open on next launch."""
        if path:
            QSettings().setValue("lastProjectPath", path)

    def _apply_design_standards(self) -> None:
        """Apply shared table and tree UI standards after all pages are built."""
        for table in self.findChildren(QTableWidget):
            standardize_table(table)
        for tree in self.findChildren(QTreeWidget):
            standardize_tree(tree)

    def _try_auto_open_last_project(self) -> None:
        """Attempt to open the last opened project on app startup.

        Silently skips if no last project or if the file no longer exists.
        """
        last_path = self._last_project_path()
        if not last_path:
            return

        try:
            project = self._context.project_service.load_project(last_path)
            if project.selected_product is not None:
                label = (
                    project.selected_product.code
                    or project.selected_product.name
                    or "Product"
                )
                self._product_status.setText(label)
            self.refresh_workspaces()
            if project.current_step is not None:
                self._manager.jump_to(project.current_step)
        except Exception:  # noqa: BLE001 (silently skip if load fails)
            # If auto-open fails, just proceed with a new project
            pass

    def _remember_project_dir(self, path: str) -> None:
        """Persist the folder of ``path`` as the last-used project location."""
        from pathlib import Path

        if path:
            QSettings().setValue("lastProjectDir", str(Path(path).resolve().parent))

    def _confirm_discard_if_modified(self) -> bool:
        """Prompt Save/Discard/Cancel when there are unsaved changes.

        Returns ``True`` to proceed (saved or discarded) or ``False`` to cancel.
        """
        if not self._context.snapshot_manager.is_modified():
            return True
        from PySide6.QtWidgets import QMessageBox

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("Unsaved Changes")
        box.setText("You have unsaved changes. Save before continuing?")
        box.setStandardButtons(
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel
        )
        box.setDefaultButton(QMessageBox.StandardButton.Save)
        choice = box.exec()
        if choice == QMessageBox.StandardButton.Save:
            return self._on_file_save()
        if choice == QMessageBox.StandardButton.Discard:
            return True
        return False

    def _on_file_new(self) -> None:
        """Start a fresh project (prompting to save any unsaved changes first)."""
        if not self._confirm_discard_if_modified():
            return
        self._context.project_service.new_project()
        self._product_status.setText("No Product Selected")
        self._manager.reset()
        self.refresh_workspaces()
        self.statusBar().showMessage("New project")

    def _on_file_open(self) -> None:
        """Open a saved ``.mkproj`` project and restore its session."""
        if not self._confirm_discard_if_modified():
            return
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Project",
            self._last_project_dir(),
            "MK Project (*.mkproj);;All Files (*)",
        )
        if not path:
            return
        try:
            project = self._context.project_service.load_project(path)
        except Exception as error:  # noqa: BLE001 (surface any load failure)
            QMessageBox.critical(
                self, "Open Project", f"Could not open project:\n{error}"
            )
            return
        self._remember_project_dir(path)
        self._remember_project_path(path)
        if project.selected_product is not None:
            label = (
                project.selected_product.code
                or project.selected_product.name
                or "Product"
            )
            self._product_status.setText(label)
        self.refresh_workspaces()
        if project.current_step is not None:
            self._manager.jump_to(project.current_step)
        self.statusBar().showMessage(f"Opened {project.name or path}")

    def _on_file_save(self) -> bool:
        """Save the active project; prompt for a path on first save.

        Returns ``True`` on success, ``False`` if cancelled or failed.
        """
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        if not self._context.snapshot_manager.has_snapshot():
            QMessageBox.information(
                self, "Save Project", "Nothing to save - load or create a project first."
            )
            return False

        service = self._context.project_service
        target = service.path
        if target is None:
            from pathlib import Path

            path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Project",
                str(Path(self._last_project_dir()) / "project.mkproj"),
                "MK Project (*.mkproj)",
            )
            if not path:
                return False
            target = path
        try:
            saved = service.save_project(
                target,
                name=service.name,
                current_step=self._manager.current_step().value,
            )
        except Exception as error:  # noqa: BLE001 (surface any save failure)
            QMessageBox.critical(
                self, "Save Project", f"Could not save project:\n{error}"
            )
            return False
        self._remember_project_dir(str(saved))
        self._remember_project_path(saved)
        self.statusBar().showMessage(f"Saved {saved}")
        return True

    def _on_check_pdm_changes(self) -> None:
        from ui.dialogs.pdm_changes_dialog import PdmChangesDialog
        dlg = PdmChangesDialog(self._context, self)
        dlg.exec()

    def _on_generate_varcond(self) -> None:
        """Generate PA_PRICING variant-condition rules from the active snapshot."""
        from PySide6.QtWidgets import QMessageBox
        from services.varcond_service import VarCondService

        if not self._context.snapshot_manager.has_snapshot():
            QMessageBox.information(
                self, "Generate VARCOND", "Load a product first."
            )
            return
        inputs = self._prompt_varcond_inputs()
        if inputs is None:
            return
        prefix, exclusions, substitutions = inputs
        result = VarCondService(self._context).generate(
            prefix=prefix,
            property_exclusions=exclusions,
            property_substitutions=substitutions,
        )
        self._show_text_result(
            "Generate VARCOND", result.text, result.warnings, "varcond.txt"
        )

    def _prompt_varcond_inputs(self) -> tuple[str, str, str] | None:
        """Prompt for PDM ``SuperProductVarCondRelation`` inputs.

        Returns ``(prefix, exclusions, substitutions)`` or ``None`` if cancelled.
        """
        from PySide6.QtWidgets import (
            QDialog,
            QDialogButtonBox,
            QFormLayout,
            QLineEdit,
            QVBoxLayout,
        )

        dialog = QDialog(self)
        dialog.setWindowTitle("Generate VARCOND for PA_PRICING")
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        prefix_edit = QLineEdit()
        prefix_edit.setPlaceholderText("pCon property-class prefix (usually empty)")
        excl_edit = QLineEdit()
        excl_edit.setPlaceholderText("e.g. LegStyle,Worktop")
        subs_edit = QLineEdit()
        subs_edit.setPlaceholderText("e.g. Width=WorktopWidth,Depth=WorktopDepth")
        form.addRow("Prefix:", prefix_edit)
        form.addRow("Exclusions:", excl_edit)
        form.addRow("Substitutions:", subs_edit)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return (
            prefix_edit.text().strip(),
            excl_edit.text().strip(),
            subs_edit.text().strip(),
        )

    def _on_generate_pricing(self) -> None:
        from PySide6.QtWidgets import QMessageBox
        from services.pricing_service import PricingService

        if not self._context.snapshot_manager.has_snapshot():
            QMessageBox.information(
                self, "Generate Pricing", "Load a product first."
            )
            return
        result = PricingService(self._context).generate()
        warnings = list(result.warnings)
        warnings.append(
            "Base article $PRICE (PriceMatrix / PriceFormula / region BasePrice) "
            "is a separate subsystem and is not included yet - this report covers "
            "option increment prices."
        )
        self._show_text_result(
            "Generate Pricing", result.text, warnings, "pricing.txt"
        )

    def _on_export_value_tables(self) -> None:
        """Export the OCD value combination tables (``<name>_tbl.csv``) + their
        ``TABLE()`` constraints to a chosen folder, for pCon import/maintenance.
        """
        from pathlib import Path

        from PySide6.QtWidgets import QFileDialog, QMessageBox

        if not self._context.snapshot_manager.has_snapshot():
            QMessageBox.information(
                self, "Export Value Tables", "Load a product first."
            )
            return
        snapshot = self._context.active_snapshot
        service = self._context.engineering_value_table_service
        tables = service.ensure_value_tables(snapshot)
        if not tables:
            QMessageBox.information(
                self, "Export Value Tables",
                "No value combination tables to export (load a family with "
                "configurable properties or fabric/finish dependencies).",
            )
            return
        directory = QFileDialog.getExistingDirectory(
            self, "Export Value Tables to folder"
        )
        if not directory:
            return
        out = Path(directory)
        written: list[str] = []
        constraints: list[str] = []
        for table in tables:
            rows = service.to_csv_rows(table)
            filename = f"{table.name}_tbl.csv"
            (out / filename).write_text(
                "\r\n".join(rows) + "\r\n", encoding="utf-8"
            )
            written.append(filename)
            constraints.append(service.constraint_body(table))
        (out / "value_table_constraints.txt").write_text(
            "\r\n\r\n".join(constraints) + "\r\n", encoding="utf-8"
        )
        written.append("value_table_constraints.txt")
        QMessageBox.information(
            self, "Export Value Tables",
            f"Exported {len(written)} file(s) to:\n{directory}\n\n"
            + "\n".join(written),
        )

    def _on_export_xocd(self) -> None:
        """Run the complete unattended XOCD publish workflow.

        The visible workflow is:
        Cleanup -> Update -> Export -> Add -> Commit -> Validate.
        The commit is limited to files generated by this export.
        """
        from pathlib import Path
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        from ui.widgets.xocd_publish_progress import XocdPublishProgress

        if not self._context.snapshot_manager.has_snapshot():
            QMessageBox.information(self, "Export XOCD", "Load a product first.")
            return

        xocd = Path(self._context.config.xocd_svn_path)
        if not xocd.is_dir():
            chosen = QFileDialog.getExistingDirectory(
                self,
                "Select the SVN XOCD folder",
                str(xocd.parent if xocd.parent.is_dir() else Path.home()),
            )
            if not chosen:
                return
            xocd = Path(chosen)
            self._context.config.xocd_svn_path = str(xocd)
            QSettings().setValue("xocd/svnPath", str(xocd))

        service = self._context.xocd_svn_service
        fallback_tortoise = service.svn_exe() is None
        if fallback_tortoise and service.tortoise_proc() is None:
            QMessageBox.warning(
                self, "Export XOCD",
                "Neither svn.exe nor TortoiseProc.exe was found. Install TortoiseSVN.",
            )
            return

        wc_root = service.find_working_copy_root(xocd)
        if wc_root is None:
            QMessageBox.warning(
                self,
                "Export XOCD",
                "The selected XOCD folder is not inside an SVN working copy.",
            )
            return

        # Do not use SubWCRev's WCINSVN result as a blocking directory check.
        # TortoiseSVN already recognizes this folder as part of the working copy,
        # and the actual SVN cleanup/update/commit operation is authoritative.
        try:
            status = service.read_status(xocd)
            if status.raw:
                self.statusBar().showMessage(
                    f"XOCD SVN status: revision {status.revision or 'unknown'}"
                )
        except Exception as exc:
            self.statusBar().showMessage(f"XOCD SVN status check skipped: {exc}")

        self._xocd_publish_path = xocd
        self._xocd_publish_wc_root = wc_root
        self._xocd_publish_service = service
        self._xocd_publish_stage = "cleanup"
        self._xocd_publish_tortoise = fallback_tortoise
        self._xocd_publish_files = []
        self._xocd_publish_progress = XocdPublishProgress(self)
        self._xocd_publish_progress.show()
        self._xocd_publish_progress.raise_()
        self._xocd_publish_progress.activateWindow()

        self._set_xocd_publish_stage(
            0, "1. SVN Cleanup", "Cleaning the working copy before export..."
        )
        if fallback_tortoise:
            self._xocd_publish_progress.append_output(
                "Using TortoiseSVN fallback. Select and confirm generated files "
                "in its commit dialog."
            )
            self._start_xocd_svn_process(service.tortoise_cleanup_args(wc_root))
        else:
            self._start_xocd_svn_process(service.cleanup_args(wc_root))

    def _set_xocd_publish_stage(
        self, number: int, title: str, detail: str = "", busy: bool = True
    ) -> None:
        dialog = getattr(self, "_xocd_publish_progress", None)
        if dialog is None:
            return
        dialog.set_stage(number, title, detail)
        dialog.set_busy(busy)
        self.statusBar().showMessage(title + (f" - {detail}" if detail else ""))

    def _start_xocd_svn_process(self, args: list[str]) -> None:
        """Run one SVN command without blocking the Qt event loop."""
        if not args:
            return
        process = QProcess(self)
        self._xocd_publish_process = process
        process.readyReadStandardOutput.connect(self._on_xocd_svn_output)
        process.readyReadStandardError.connect(self._on_xocd_svn_output)
        process.finished.connect(self._on_xocd_svn_finished)
        process.setProgram(args[0])
        process.setArguments(args[1:])
        process.start()
        if not process.waitForStarted(3000):
            self._xocd_publish_process = None
            self._xocd_publish_failed(
                "Could not start svn.exe. Install the TortoiseSVN command-line tools."
            )

    def _on_xocd_svn_output(self) -> None:
        process = getattr(self, "_xocd_publish_process", None)
        dialog = getattr(self, "_xocd_publish_progress", None)
        if process is None or dialog is None:
            return
        stdout = bytes(process.readAllStandardOutput()).decode(errors="replace")
        stderr = bytes(process.readAllStandardError()).decode(errors="replace")
        if stdout:
            dialog.append_output(stdout)
        if stderr:
            dialog.append_output(stderr)

    def _on_xocd_svn_finished(self, exit_code: int, _exit_status) -> None:
        """Advance the automated XOCD workflow after each SVN command."""
        from pathlib import Path
        from PySide6.QtWidgets import QMessageBox

        process = self._xocd_publish_process
        self._xocd_publish_process = None
        stage = getattr(self, "_xocd_publish_stage", "")
        if process is None:
            return

        output = bytes(process.readAllStandardOutput()).decode(errors="replace")
        error_text = bytes(process.readAllStandardError()).decode(errors="replace")
        dialog = getattr(self, "_xocd_publish_progress", None)
        if dialog is not None:
            if output:
                dialog.append_output(output)
            if error_text:
                dialog.append_output(error_text)

        service = self._xocd_publish_service
        xocd: Path = self._xocd_publish_path

        if getattr(self, "_xocd_publish_tortoise", False):
            self._on_xocd_tortoise_finished(stage, exit_code)
            return

        if exit_code != 0:
            detail = error_text.strip() or output.strip() or f"svn.exe exited with code {exit_code}."
            self._xocd_publish_failed(f"SVN {stage} failed.\n\n{detail}")
            return

        if stage == "cleanup":
            self._xocd_publish_stage = "update"
            self._set_xocd_publish_stage(
                1, "2. SVN Update", "Updating the XOCD working copy..."
            )
            self._start_xocd_svn_process(service.update_args(xocd))
            return

        if stage == "update":
            snapshot = self._context.active_snapshot
            psvc = self._context.price_update_service
            standardised = psvc.apply_registry(snapshot, psvc.registry_path())
            self._xocd_publish_standardised = standardised

            self._set_xocd_publish_stage(
                2, "3. XOCD Export", "Generating the XOCD CSV files...", busy=True
            )
            result = self._context.xocd_export_service.export_series(
                snapshot, xocd, force=True
            )
            if result.error:
                self._xocd_publish_failed(f"XOCD export failed:\n\n{result.error}")
                return

            self._xocd_publish_program = result.program
            self._xocd_publish_files = sorted(result.files.keys())
            total = len(self._xocd_publish_files)
            rows = sum(result.files.values())
            if dialog is not None:
                dialog.set_files(self._xocd_publish_files)
                dialog.append_output(
                    f"Generated {total} XOCD file(s), {rows} row(s)."
                )

            self._xocd_publish_stage = "status"
            self._set_xocd_publish_stage(
                3, "4. Prepare Commit", f"Checking {total} generated file(s)..."
            )
            self._start_xocd_svn_process(service.status_args(xocd))
            return

        if stage == "status":
            try:
                status_xml = output
                unversioned = service.parse_unversioned_paths(status_xml, xocd)
                generated = {
                    (xocd / name).resolve()
                    for name in self._xocd_publish_files
                }
                to_add = sorted(
                    (path for path in generated if path in unversioned),
                    key=lambda path: str(path).lower(),
                )
            except Exception as exc:
                self._xocd_publish_failed(
                    f"Could not determine which XOCD files need to be added.\n\n{exc}"
                )
                return

            self._xocd_publish_add_paths = to_add
            if dialog is not None:
                dialog.append_output(
                    f"Files already versioned: "
                    f"{len(self._xocd_publish_files) - len(to_add)}"
                )
                dialog.append_output(f"New files to add: {len(to_add)}")

            if to_add:
                self._xocd_publish_stage = "add"
                self._set_xocd_publish_stage(
                    4, "5. Add XOCD Files", f"Adding {len(to_add)} new file(s)..."
                )
                self._start_xocd_svn_process(service.add_args(to_add))
            else:
                self._xocd_publish_stage = "remote_check"
                self._set_xocd_publish_stage(
                    4, "5. Prepare Commit", "Checking that the repository is still current..."
                )
                self._start_xocd_svn_process(service.status_args(xocd, show_updates=True))
            return

        if stage == "add":
            self._xocd_publish_stage = "remote_check"
            self._set_xocd_publish_stage(
                4, "5. Prepare Commit", "Checking that the repository is still current..."
            )
            self._start_xocd_svn_process(service.status_args(xocd, show_updates=True))
            return

        if stage == "remote_check":
            try:
                if service.has_remote_updates(output):
                    self._xocd_publish_failed(
                        "The SVN repository changed after the update. "
                        "The XOCD files were not committed. Run Export XOCD again "
                        "to update the working copy before publishing."
                    )
                    return
            except Exception as exc:
                self._xocd_publish_failed(
                    f"Could not verify SVN freshness before commit.\n\n{exc}"
                )
                return

            commit_paths = [
                (xocd / name).resolve()
                for name in self._xocd_publish_files
                if (xocd / name).is_file()
            ]
            if not commit_paths:
                self._xocd_publish_failed("No generated XOCD files are available to commit.")
                return

            comment = f"{self._xocd_publish_program} - Updating OAS"
            self._xocd_publish_stage = "commit"
            self._set_xocd_publish_stage(
                5,
                "6. Commit to SVN",
                f"Committing {len(commit_paths)} XOCD file(s). Comment: {comment}",
            )
            self._start_xocd_svn_process(service.commit_args(commit_paths, comment))
            return

        if stage == "commit":
            revision = ""
            import re
            match = re.search(r"Committed revision (\d+)\.", output + "\n" + error_text)
            if match:
                revision = match.group(1)
            self._xocd_publish_revision = revision

            if dialog is not None:
                dialog.append_output(
                    f"SVN commit completed"
                    + (f" at revision {revision}." if revision else ".")
                )
                dialog.set_files(self._xocd_publish_files)

            self._xocd_publish_stage = "validate"
            self._set_xocd_publish_stage(
                6, "7. Validate", "Verifying the generated XOCD files are clean..."
            )
            self._start_xocd_svn_process(service.status_args(xocd))
            return

        if stage == "validate":
            try:
                statuses = service.parse_status_items(output, xocd)
                dirty = []
                for name in self._xocd_publish_files:
                    path = (xocd / name).resolve()
                    item = statuses.get(path)
                    if item and item not in ("normal", "none"):
                        dirty.append(f"{name} ({item})")
                if dirty:
                    self._xocd_publish_failed(
                        "SVN commit finished, but validation found remaining "
                        "changes in generated files:\n\n" + "\n".join(dirty)
                    )
                    return
            except Exception as exc:
                self._xocd_publish_failed(
                    f"Commit completed, but final SVN validation failed.\n\n{exc}"
                )
                return

            revision = getattr(self, "_xocd_publish_revision", "")
            standardised = getattr(self, "_xocd_publish_standardised", 0)
            extra = (
                f" Standardised {standardised} base article(s)."
                if standardised else ""
            )
            if dialog is not None:
                dialog.complete(
                    f"Committed {len(self._xocd_publish_files)} file(s)"
                    + (f" in revision {revision}." if revision else ".")
                    + extra
                )
            self.statusBar().showMessage("XOCD publish completed and validated")
            QMessageBox.information(
                self,
                "Export XOCD",
                f"XOCD commit completed successfully.\n\n"
                f"Files committed: {len(self._xocd_publish_files)}"
                + (f"\nRevision: {revision}" if revision else "")
                + extra,
            )
            return

    def _on_xocd_tortoise_finished(self, stage: str, exit_code: int) -> None:
        """TortoiseSVN fallback: the commit dialog requires user confirmation."""
        service = self._xocd_publish_service
        xocd = self._xocd_publish_path
        dialog = self._xocd_publish_progress
        if exit_code != 0:
            self._xocd_publish_failed(
                f"TortoiseSVN {stage} failed or was cancelled (exit {exit_code})."
            )
            return

        if stage == "cleanup":
            self._xocd_publish_stage = "update"
            self._set_xocd_publish_stage(
                1, "2. SVN Update", "Updating with TortoiseSVN..."
            )
            self._start_xocd_svn_process(service.tortoise_update_args(xocd))
            return

        if stage == "update":
            try:
                snapshot = self._context.active_snapshot
                psvc = self._context.price_update_service
                standardised = psvc.apply_registry(snapshot, psvc.registry_path())
                result = self._context.xocd_export_service.export_series(
                    snapshot, xocd, force=True
                )
                if result.error:
                    self._xocd_publish_failed(f"XOCD export failed: {result.error}")
                    return
                self._xocd_publish_standardised = standardised
                self._xocd_publish_files = sorted(result.files.keys())
                self._xocd_publish_program = result.program
                if not self._xocd_publish_files:
                    self._xocd_publish_failed("No XOCD files were generated.")
                    return
                dialog.set_files(self._xocd_publish_files)
                dialog.append_output(
                    f"Generated {len(self._xocd_publish_files)} file(s). "
                    "Select only these generated files in the TortoiseSVN commit dialog."
                )
                comment = f"{result.program} - Updating OAS"
                self._xocd_publish_stage = "commit"
                self._set_xocd_publish_stage(
                    5, "6. Commit to SVN",
                    "Select the generated files in TortoiseSVN and click OK. "
                    f"Comment: {comment}"
                )
                self._start_xocd_svn_process(
                    service.tortoise_commit_args(xocd, comment)
                )
            except Exception as exc:
                self._xocd_publish_failed(f"XOCD export failed: {exc}")
            return

        if stage == "commit":
            try:
                status = service.read_status(xocd)
            except Exception as exc:
                self._xocd_publish_failed(
                    f"Commit dialog closed; SVN validation failed: {exc}"
                )
                return
            if status.modified or status.unversioned:
                self._xocd_publish_failed(
                    "TortoiseSVN closed, but the XOCD folder still contains "
                    "modified or unversioned files. Check the generated files "
                    "and commit status in TortoiseSVN."
                )
                return
            dialog.complete(
                "TortoiseSVN closed and the XOCD working copy is clean. "
                "Check the SVN log to verify the committed revision."
            )
            self.statusBar().showMessage(
                "XOCD TortoiseSVN fallback finished; working copy clean"
            )

    def _xocd_publish_failed(self, message: str) -> None:
        dialog = getattr(self, "_xocd_publish_progress", None)
        if dialog is not None:
            dialog.fail(message)
            dialog.append_output(message)
        self.statusBar().showMessage("XOCD publish stopped")
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(self, "Export XOCD", message)

    def _on_export_mdb(self) -> None:
        """Export the active product directly as a ``pcr_data_com_ocd.mdb``.

        Copies the category template, wipes its example product, and writes the
        snapshot's ``tCOMd_*`` rows. This is the alternative to the XOCD CSV
        publish - a finished COM database rather than an import package.
        """
        from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox

        if not self._context.snapshot_manager.has_snapshot():
            QMessageBox.information(self, "Export MDB", "Load a product first.")
            return
        directory = QFileDialog.getExistingDirectory(
            self, "Export MDB to folder (a pcr_data_com_ocd.mdb is written inside)"
        )
        if not directory:
            return

        choice, ok = QInputDialog.getItem(
            self, "Export MDB", "Template:",
            ["Auto", "Seating", "Tables"], 0, False,
        )
        if not ok:
            return
        kind = None if choice == "Auto" else choice.lower()

        snapshot = self._context.active_snapshot
        # Standardise base article lengths to the registry (CAD) before export.
        psvc = self._context.price_update_service
        standardised = psvc.apply_registry(snapshot, psvc.registry_path())
        result = self._context.ocd_export_service.export(snapshot, directory, kind)

        if not result.ok or result.error:
            QMessageBox.warning(
                self, "Export MDB", f"Export failed:\n{result.error or 'unknown error'}"
            )
            return

        total = sum(result.table_counts.values())
        QMessageBox.information(
            self, "Export MDB",
            f"Exported '{result.template}' MDB ({total} rows across "
            f"{len(result.table_counts)} table(s)) into:\n{result.mdb_path}"
            + (f"\n\nStandardised {standardised} base article(s) to CAD Maintenance."
               if standardised else ""),
        )

    def _show_text_result(
        self, title: str, text: str, warnings: list, default_name: str
    ) -> None:
        """Show generated text in a read-only dialog with Copy/Save."""
        from PySide6.QtWidgets import (
            QDialog,
            QDialogButtonBox,
            QFileDialog,
            QPlainTextEdit,
            QVBoxLayout,
        )

        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.resize(760, 500)
        layout = QVBoxLayout(dlg)

        if warnings:
            warn = QLabel("\n".join(warnings), dlg)
            warn.setWordWrap(True)
            warn.setObjectName("pageSubtitle")
            layout.addWidget(warn)

        editor = QPlainTextEdit(dlg)
        editor.setReadOnly(True)
        editor.setPlainText(text or "(nothing generated)")
        layout.addWidget(editor, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, dlg)
        save_btn = buttons.addButton(
            "Save...", QDialogButtonBox.ButtonRole.ActionRole
        )
        copy_btn = buttons.addButton(
            "Copy", QDialogButtonBox.ButtonRole.ActionRole
        )
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        def _copy() -> None:
            from PySide6.QtWidgets import QApplication

            QApplication.clipboard().setText(text or "")

        def _save() -> None:
            path, _ = QFileDialog.getSaveFileName(
                dlg, "Save", default_name, "Text files (*.txt)"
            )
            if path:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(text or "")

        copy_btn.clicked.connect(_copy)
        save_btn.clicked.connect(_save)
        dlg.exec()

    def _make_action(self, text: str) -> QAction:
        # Actions are intentionally inert in Phase 1.
        return QAction(text, self)

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if not self._confirm_discard_if_modified():
            event.ignore()
            return
        self._save_layout()
        super().closeEvent(event)

    def _build_status_bar(self) -> None:
        status: QStatusBar = self.statusBar()
        status.showMessage("Ready")

        # Background task indicator (clickable): shows the current background
        # activity + percentage and reopens the progress monitor. It observes
        # the shared ActivityService, so any future background task appears here
        # without touching this window.
        self._background_status = BackgroundStatusIndicator(
            self._context.activity_service, self
        )
        self._background_status.clicked.connect(self._open_progress_monitor)
        status.addPermanentWidget(self._background_status)

        self._product_status = QLabel("No Product Selected", self)
        self._product_status.setObjectName("productStatus")
        status.addPermanentWidget(self._product_status)

    def _open_progress_monitor(self) -> None:
        """Reopen the existing (reusable) progress monitor from the status bar."""
        dialog = self._product_page.progress_monitor()
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    # -- layout persistence ------------------------------------------------
    def _restore_layout(self) -> None:
        """Restore window geometry, dock layout, splitter sizes and collapse
        state from the previous session, if any were saved."""
        settings = QSettings()
        geometry = settings.value("layout/geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        window_state = settings.value("layout/windowState")
        if window_state is not None:
            self.restoreState(window_state)
        splitter_state = settings.value("layout/splitter")
        if splitter_state is not None:
            self._main_splitter.restoreState(splitter_state)

        nav_visible = settings.value("layout/navigatorVisible", True, type=bool)
        self._left_panel.setVisible(nav_visible)
        self._toggle_navigator_action.setChecked(nav_visible)

    def _save_layout(self) -> None:
        """Persist the current layout so it is restored on the next launch."""
        settings = QSettings()
        settings.setValue("layout/geometry", self.saveGeometry())
        settings.setValue("layout/windowState", self.saveState())
        settings.setValue("layout/splitter", self._main_splitter.saveState())
        settings.setValue("layout/navigatorVisible", self._left_panel.isVisible())

    def _reset_layout(self) -> None:
        """Discard the saved layout and restore the default arrangement."""
        QSettings().remove("layout")

        self._left_panel.setVisible(True)
        self._toggle_navigator_action.setChecked(True)

        self._assistant_dock.setFloating(False)
        self.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea, self._assistant_dock
        )
        self._assistant_dock.setVisible(True)

        self._main_splitter.setSizes(self._DEFAULT_SPLITTER_SIZES)
        self.resizeDocks(
            [self._assistant_dock],
            [self._DEFAULT_ASSISTANT_WIDTH],
            Qt.Orientation.Horizontal,
        )