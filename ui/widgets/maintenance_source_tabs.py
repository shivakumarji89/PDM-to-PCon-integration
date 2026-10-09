"""PDM / MDB source selector for Maintenance workflow pages.

Maintenance pages can show either the PDM snapshot or the imported released
MDB snapshot. The selection is *page-local*: it never touches
``ApplicationContext.active_snapshot`` or the snapshot source. Each page wraps
its context in :class:`SourceContext`, which resolves the snapshot the page
should read:

    no tabs (Development, other modules) -> context.active_snapshot (unchanged)
    PDM tab                               -> context.pdm_snapshot
    MDB tab                               -> context.mdb_import_snapshot

The MDB tab is strictly read-only: ``snapshot_manager.mark_modified`` is a
no-op for it, mutating page actions are disabled, and mutating handlers are
skipped (see :func:`read_only_in_mdb`).
"""
from __future__ import annotations

import functools

import shiboken6

from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QTabBar,
    QWidget,
)

from core.modules import WorkbenchModule
from services.article_service import ArticleService
from services.option_service import OptionService
from services.option_value_service import OptionValueService
from services.property_service import PropertyService
from services.property_value_service import PropertyValueService

SOURCE_PDM = "pdm"
SOURCE_MDB = "mdb"

MDB_NOT_LOADED_TEXT = "MDB repository not loaded."


class _ReadOnlySnapshotManager:
    """Snapshot manager facade for the MDB view: modification is never recorded."""

    def __init__(self, manager) -> None:
        self._manager = manager

    def mark_modified(self) -> None:  # noqa: D401 - intentionally a no-op
        return None

    def __getattr__(self, name):
        return getattr(self._manager, name)


class SourceContext:
    """Page-local view of the ApplicationContext for one Maintenance source."""

    def __init__(self, context) -> None:
        object.__setattr__(self, "_real", context)
        object.__setattr__(self, "source", None)
        object.__setattr__(self, "_bound_services", {})

    @property
    def real(self):
        return self._real

    @property
    def active_snapshot(self):
        source = self.source
        if source == SOURCE_PDM:
            return self._real.pdm_snapshot
        if source == SOURCE_MDB:
            return self._real.mdb_import_snapshot
        return self._real.active_snapshot

    @property
    def snapshot_manager(self):
        manager = self._real.snapshot_manager
        if self.source == SOURCE_MDB:
            return _ReadOnlySnapshotManager(manager)
        return manager

    def _bound(self, service_type):
        """A snapshot-implicit service reading *this* source's snapshot.

        These services resolve ``context.active_snapshot`` internally, so the
        shared instance on the real context would read the global snapshot
        whichever tab is selected. Without a source (Development / other
        modules) the shared service is returned unchanged.
        """
        if self.source is None:
            return self._real.get_service(service_type)
        service = self._bound_services.get(service_type)
        if service is None:
            service = service_type(self)
            self._bound_services[service_type] = service
        return service

    @property
    def article_service(self) -> ArticleService:
        return self._bound(ArticleService)

    @property
    def property_service(self) -> PropertyService:
        return self._bound(PropertyService)

    @property
    def property_value_service(self) -> PropertyValueService:
        return self._bound(PropertyValueService)

    @property
    def option_service(self) -> OptionService:
        return self._bound(OptionService)

    @property
    def option_value_service(self) -> OptionValueService:
        return self._bound(OptionValueService)

    def __getattr__(self, name):
        return getattr(self._real, name)

    def __setattr__(self, name, value) -> None:
        if name == "source":
            object.__setattr__(self, name, value)
        else:
            setattr(self._real, name, value)


class _KeepDisabled(QObject):
    """Event filter that re-disables a widget when page code re-enables it."""

    def __init__(self, owner: "MaintenanceSourceMixin") -> None:
        super().__init__(owner)
        self._owner = owner

    def eventFilter(self, obj, event) -> bool:  # noqa: N802 (Qt override)
        if (
            event.type() == QEvent.Type.EnabledChange
            and self._owner.is_mdb_view()
            and obj.isEnabled()
        ):
            obj.setEnabled(False)
        return False


class MaintenanceSourceTabs(QWidget):
    """``[ PDM ] [ MDB ]`` selector with a one-line source indicator."""

    source_changed = Signal(str)

    _STYLE = (
        "QTabBar::tab { padding: 5px 22px; border: 1px solid #b8bec8;"
        " border-bottom: none; background: #eef1f5; color: #44505e; }"
        "QTabBar::tab:selected { background: #2f6fed; color: white;"
        " font-weight: bold; }"
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("maintenanceSourceTabs")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._bar = QTabBar(self)
        self._bar.setExpanding(False)
        self._bar.setDrawBase(False)
        self._bar.setStyleSheet(self._STYLE)
        self._bar.addTab("PDM")
        self._bar.addTab("MDB")
        self._bar.currentChanged.connect(self._on_current_changed)
        layout.addWidget(self._bar)
        self._indicator = QLabel("", self)
        layout.addWidget(self._indicator, 1)
        self.setVisible(False)

    @property
    def source(self) -> str:
        return SOURCE_MDB if self._bar.currentIndex() == 1 else SOURCE_PDM

    def set_source(self, source: str) -> None:
        self._bar.setCurrentIndex(1 if source == SOURCE_MDB else 0)

    def set_indicator(self, text: str) -> None:
        self._indicator.setText(text)

    def _on_current_changed(self, _index: int) -> None:
        self.source_changed.emit(self.source)


def read_only_in_mdb(*names: str):
    """Class decorator: make the named mutating methods no-ops in the MDB view.

    Applied at class level so signal connections made with bound methods are
    covered too. PDM / non-Maintenance behaviour is untouched.
    """

    def decorate(cls):
        for name in names:
            original = getattr(cls, name)

            def make(fn):
                @functools.wraps(fn)
                def guarded(self, *args, **kwargs):
                    if self.is_mdb_view():
                        return None
                    return fn(self, *args, **kwargs)

                return guarded

            setattr(cls, name, make(original))
        return cls

    return decorate


class MaintenanceSourceMixin:
    """Shared page logic for the PDM/MDB source tabs (Maintenance only)."""

    def _init_source_tabs(self, context) -> None:
        """Wrap ``context`` and create the (initially hidden) tab bar."""
        self._context = SourceContext(context)
        self._source_tabs = MaintenanceSourceTabs(self)
        self._source_tabs.source_changed.connect(self._on_source_changed)
        self._keep_disabled = _KeepDisabled(self)
        self._locked_widgets: dict = {}
        self._mdb_render_key = None
        self.add_content(self._source_tabs)

    # -- source resolution -------------------------------------------------
    def is_maintenance_module(self) -> bool:
        return (
            getattr(self.window(), "_active_module", None) == WorkbenchModule.MAINTENANCE
        )

    def current_source(self) -> str | None:
        return self._context.source

    def is_mdb_view(self) -> bool:
        return self._context.source == SOURCE_MDB

    def source_snapshot(self):
        return self._context.active_snapshot

    def _on_source_changed(self, _source: str) -> None:
        self.refresh()

    def _sync_source(self) -> None:
        """Align the page-local source with the active module."""
        tabs = self._source_tabs
        if self.is_maintenance_module():
            tabs.setVisible(True)
            self._context.source = tabs.source
        else:
            tabs.setVisible(False)
            if tabs.source != SOURCE_PDM:
                tabs.blockSignals(True)
                tabs.set_source(SOURCE_PDM)
                tabs.blockSignals(False)
            self._context.source = None
        self._update_indicator()

    def _resync_on_show(self) -> bool:
        """Re-sync the source when the page is shown; True if the source changed."""
        previous = self._context.source
        self._sync_source()
        return self._context.source != previous

    def _update_indicator(self) -> None:
        source = self._context.source
        if source == SOURCE_MDB:
            if self._context.active_snapshot is None:
                text = MDB_NOT_LOADED_TEXT
            else:
                text = "Source: MDB repository snapshot (read-only)"
        elif source == SOURCE_PDM:
            text = "Source: PDM snapshot"
        else:
            text = ""
        self._source_tabs.set_indicator(text)

    def _ensure_pdm_scope(self) -> None:
        """Maintenance PDM view with a released MDB: make sure the derived MDB
        base lengths (Article Sets overlay + member reductions) are in place.

        Done here, for every Maintenance page, so no page depends on another
        having been opened first (Open Project, repository change, ...).
        Idempotent and cached; a no-op for the MDB view and other modules.
        """
        if self._context.source != SOURCE_PDM:
            return
        real = self._context.real
        pdm, mdb = real.pdm_snapshot, real.mdb_import_snapshot
        if pdm is None or mdb is None:
            return
        from services.maintenance_alignment_service import MaintenanceAlignmentService

        MaintenanceAlignmentService(real).ensure_pdm_scope(pdm, mdb)

    def _begin_refresh(self) -> bool:
        """Sync source/lock state. Return True when the refresh can be skipped.

        PDM and non-Maintenance refreshes always run (behaviour unchanged). The
        MDB view is immutable, so it is rendered once per MDB snapshot.
        """
        self._sync_source()
        self._ensure_pdm_scope()
        mdb = self.is_mdb_view()
        self._set_widgets_locked(mdb)
        if not mdb:
            self._mdb_render_key = None
            return False
        snapshot = self._context.active_snapshot
        key = (id(snapshot), getattr(snapshot, "id", None)) if snapshot is not None else None
        if key is not None and key == self._mdb_render_key:
            return True
        self._mdb_render_key = key
        return False

    # -- read-only widgets -------------------------------------------------
    def _lockable_widgets(self) -> list[QWidget]:
        """Widgets that edit/compute/generate. Override per page."""
        return []

    def _page_item_views(self) -> list[QAbstractItemView]:
        """The page's own item views, never a view that belongs to an editor.

        ``findChildren(QAbstractItemView)`` also returns the popup ``QListView``
        of every ``QComboBox`` embedded in a table/tree cell. Those belong to
        the cell editors, which are destroyed whenever the page rebuilds its
        views, so they must never be registered as lockable.
        """
        views = []
        for view in self.findChildren(QAbstractItemView):
            ancestor = view.parentWidget()
            inside_editor = False
            while ancestor is not None and ancestor is not self:
                if isinstance(ancestor, QComboBox):
                    inside_editor = True
                    break
                ancestor = ancestor.parentWidget()
            if not inside_editor:
                views.append(view)
        return views

    def _apply_lock_state(self) -> None:
        """Re-assert the lock for the current source (call after a rebuild)."""
        self._set_widgets_locked(self.is_mdb_view())

    def _set_widgets_locked(self, locked: bool) -> None:
        """Lock/unlock the page's mutating widgets, restoring prior state.

        ``self._lockable_widgets()`` is the single authority on which widgets
        currently belong to the page. Every call first reconciles the saved
        state against it, so a widget the page has since replaced or deleted
        never survives in the lock table (and is never restored).
        """
        current = [w for w in self._lockable_widgets() if w is not None]
        self._reconcile_locked(current)
        if locked:
            for widget in current:
                if widget in self._locked_widgets:
                    continue
                if isinstance(widget, QAbstractItemView):
                    self._locked_widgets[widget] = widget.editTriggers()
                    widget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
                else:
                    self._locked_widgets[widget] = widget.isEnabled()
                    widget.installEventFilter(self._keep_disabled)
                    widget.setEnabled(False)
                # A widget that is destroyed later leaves the table at once
                # (hooked once per widget, not once per lock cycle).
                if not widget.property("_sourceLockHooked"):
                    widget.setProperty("_sourceLockHooked", True)
                    widget.destroyed.connect(
                        lambda _obj=None, key=widget: self._locked_widgets.pop(key, None)
                    )
            return
        states, self._locked_widgets = self._locked_widgets, {}
        for widget, previous in states.items():
            self._restore_widget(widget, previous)

    def _reconcile_locked(self, current: list) -> None:
        """Drop lock state for widgets that are no longer the page's own."""
        keep = set(current)
        for widget in [w for w in self._locked_widgets if w not in keep]:
            previous = self._locked_widgets.pop(widget)
            # Replaced but still alive (e.g. re-parented): give its state back.
            # Destroyed: nothing to restore - the entry is simply discarded.
            self._restore_widget(widget, previous)

    def _restore_widget(self, widget, previous) -> None:
        if not shiboken6.isValid(widget):  # defensive only; entries are pruned
            return
        if isinstance(widget, QAbstractItemView):
            widget.setEditTriggers(previous)
        else:
            widget.removeEventFilter(self._keep_disabled)
            widget.setEnabled(previous)
