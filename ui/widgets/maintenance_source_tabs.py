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

from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QTabBar,
    QWidget,
)

from core.modules import WorkbenchModule

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

    def _begin_refresh(self) -> bool:
        """Sync source/lock state. Return True when the refresh can be skipped.

        PDM and non-Maintenance refreshes always run (behaviour unchanged). The
        MDB view is immutable, so it is rendered once per MDB snapshot.
        """
        self._sync_source()
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

    def _set_widgets_locked(self, locked: bool) -> None:
        """Lock/unlock the page's mutating widgets, restoring prior state."""
        if locked:
            for widget in self._lockable_widgets():
                if widget is None or widget in self._locked_widgets:
                    continue
                if isinstance(widget, QAbstractItemView):
                    self._locked_widgets[widget] = widget.editTriggers()
                    widget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
                else:
                    self._locked_widgets[widget] = widget.isEnabled()
                    widget.installEventFilter(self._keep_disabled)
                    widget.setEnabled(False)
            return
        for widget, previous in self._locked_widgets.items():
            if isinstance(widget, QAbstractItemView):
                widget.setEditTriggers(previous)
            else:
                widget.removeEventFilter(self._keep_disabled)
                widget.setEnabled(previous)
        self._locked_widgets = {}
