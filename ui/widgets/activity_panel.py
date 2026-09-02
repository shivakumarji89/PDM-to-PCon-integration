"""Reusable activity panel (container).

The :class:`ActivityPanel` is a thin container around the Activity framework. It
is responsible only for:

  * managing sections (Running / Completed / Failed),
  * receiving activity events from the shared event bus,
  * adding / updating / moving / removing :class:`~ui.widgets.operation_card.
    OperationCard` instances by activity id,
  * filtering which activities are shown.

It never manipulates an individual label or progress bar - it simply passes the
latest immutable :class:`~core.activity.models.ActivitySnapshot` to the matching
card's :meth:`OperationCard.update`. This keeps the per-activity rendering fully
owned by :class:`OperationCard`, so other views can reuse cards without this
panel.

This first version prioritises architecture (hierarchy, update flow, event
handling, performance, reusability) over appearance; visual polish can be added
later without changing this structure.
"""
from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.activity.events import ActivityEvent
from core.activity.log_export import format_activity_log
from core.activity.models import ActivitySnapshot, ActivityStatus
from ui.widgets.operation_card import OperationCard

# Section order and labels. Sections are keyed by an internal "bucket" name.
_SECTIONS: tuple[tuple[str, str], ...] = (
    ("running", "Running"),
    ("completed", "Completed"),
    ("failed", "Failed"),
)


def _bucket_for(status: ActivityStatus) -> str:
    """Map an activity status to its display section (bucket).

    Cancelled activities share the "failed" section (both are non-success
    terminal states); a dedicated section can be added later without changing
    callers.
    """
    if status in (ActivityStatus.PENDING, ActivityStatus.RUNNING):
        return "running"
    if status is ActivityStatus.COMPLETED:
        return "completed"
    return "failed"


class ActivityPanel(QWidget):
    """Lightweight coordinator that renders activities as :class:`OperationCard`s.

    It keeps a dictionary of cards keyed by activity id, creates a card once when
    an activity first appears, and thereafter only *updates* and *moves* that
    same card - cards are never recreated because of a status change. The panel
    never manipulates a card's labels, progress bar, or child widgets; it passes
    the immutable snapshot straight to :meth:`OperationCard.update`. Section
    layouts are built once and reused (never rebuilt).

    Extension seams (add future capabilities without redesigning the hierarchy):
      * **Grouping / sections** - :func:`_bucket_for` maps a status to a section.
      * **Ordering / sorting** - :meth:`_insert_card` is the single placement
        point; future sorting reorders here.
      * **Search / filtering** - :meth:`_is_visible` is the single visibility
        predicate.
      * **Retention** - removal happens only via :meth:`remove_card` /
        :meth:`clear_finished`; nothing is removed implicitly.
    """

    def __init__(self, activity_service, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("activityPanel")

        self._service = activity_service
        self._cards: dict[str, OperationCard] = {}
        self._card_bucket: dict[str, str] = {}
        self._filter_text: str = ""
        self._filter_type: str | None = None

        self._sections: dict[str, tuple[QGroupBox, QVBoxLayout]] = {}
        self._build_ui()

        # Subscribe once to every activity event; the same handler add-or-updates
        # the matching card and moves it between sections on status change.
        self._service.event_bus.subscribe(self._on_activity_event, ActivityEvent)

        # Render any activities that already exist (panel created after start).
        for snapshot in self._service.snapshots():
            self._upsert(snapshot)

    # -- construction ------------------------------------------------------
    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        toolbar = QHBoxLayout()
        self._save_log_btn = QPushButton("Save Log\u2026", self)
        self._save_log_btn.setToolTip("Export the full activity timeline to a log file.")
        self._save_log_btn.clicked.connect(self.export_log)
        toolbar.addWidget(self._save_log_btn)
        self._clear_btn = QPushButton("Clear Finished", self)
        self._clear_btn.setToolTip("Remove completed/failed activities from the list.")
        self._clear_btn.clicked.connect(self.clear_finished)
        toolbar.addWidget(self._clear_btn)
        toolbar.addStretch(1)
        outer.addLayout(toolbar)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        for bucket, label in _SECTIONS:
            box = QGroupBox(label, content)
            box.setObjectName(f"activitySection_{bucket}")
            section_layout = QVBoxLayout(box)
            section_layout.setContentsMargins(0, 0, 0, 0)
            section_layout.addStretch(1)  # cards are inserted before this
            self._sections[bucket] = (box, section_layout)
            content_layout.addWidget(box)
        content_layout.addStretch(1)

        scroll.setWidget(content)

    # -- event handling ----------------------------------------------------
    def _on_activity_event(self, event: ActivityEvent) -> None:
        # Single entry point for every activity event; the snapshot carries all
        # state, so the panel never inspects the mutable Activity.
        self._upsert(event.snapshot)

    # -- card management ---------------------------------------------------
    def _upsert(self, snapshot: ActivitySnapshot) -> None:
        card = self._cards.get(snapshot.id)
        if card is None:
            # Create once. Cards are never recreated for later status changes.
            card = OperationCard(snapshot)
            self._cards[snapshot.id] = card
        else:
            # Reuse the existing card: status changes update it, never recreate.
            card.update(snapshot)
        self._place_in_bucket(snapshot.id, card, _bucket_for(snapshot.status))
        card.setVisible(self._is_visible(snapshot))
        self._update_section_titles()

    def _place_in_bucket(self, activity_id: str, card: OperationCard, bucket: str) -> None:
        current = self._card_bucket.get(activity_id)
        if current == bucket:
            return
        if current is not None:
            self._sections[current][1].removeWidget(card)
        self._insert_card(bucket, card)
        self._card_bucket[activity_id] = bucket

    def _insert_card(self, bucket: str, card: OperationCard) -> None:
        # Single placement seam: cards are appended in arrival order today, so
        # future sorting / grouping can reorder here without touching callers.
        section_layout = self._sections[bucket][1]
        section_layout.insertWidget(section_layout.count() - 1, card)
        card.setParent(self._sections[bucket][0])
        card.show()

    def remove_card(self, activity_id: str) -> None:
        """Remove the card for ``activity_id`` (explicit removal only)."""
        card = self._cards.pop(activity_id, None)
        if card is None:
            return
        bucket = self._card_bucket.pop(activity_id, None)
        if bucket is not None:
            self._sections[bucket][1].removeWidget(card)
        card.setParent(None)
        card.deleteLater()
        self._update_section_titles()

    def clear_finished(self) -> None:
        """Remove finished cards and clear finished activities in the service.

        Explicit retention operation; nothing is removed automatically.
        """
        for activity_id in list(self._cards.keys()):
            snapshot = self._service.get_snapshot(activity_id)
            if snapshot is not None and snapshot.is_finished:
                self.remove_card(activity_id)
        self._service.clear_finished()

    def export_log(self) -> None:
        """Save the full activity timeline (all activities + logs) to a file."""
        snapshots = self._service.snapshots()
        if not snapshots:
            QMessageBox.information(
                self, "Save Log", "There is no activity to export yet."
            )
            return
        default = f"activity_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Activity Log", default, "Log files (*.log *.txt);;All files (*)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(format_activity_log(snapshots))
        except OSError as error:
            QMessageBox.critical(self, "Save Log", f"Could not write the log:\n\n{error}")
            return
        QMessageBox.information(self, "Save Log", f"Activity log saved to:\n{path}")

    # -- filtering ---------------------------------------------------------
    def set_filter(self, text: str = "", activity_type: str | None = None) -> None:
        """Filter shown activities by title substring and/or activity type."""
        self._filter_text = (text or "").strip().lower()
        self._filter_type = activity_type
        self._refresh_visibility()

    def _refresh_visibility(self) -> None:
        for activity_id, card in self._cards.items():
            snapshot = self._service.get_snapshot(activity_id)
            if snapshot is not None:
                card.setVisible(self._is_visible(snapshot))
        self._update_section_titles()

    def _is_visible(self, snapshot: ActivitySnapshot) -> bool:
        # Single visibility predicate: the extension point for search and
        # filtering. Returns whether the card for ``snapshot`` should be shown.
        if self._filter_text and self._filter_text not in snapshot.title.lower():
            return False
        if self._filter_type is not None and snapshot.type != self._filter_type:
            return False
        return True

    # -- section headers ---------------------------------------------------
    def _update_section_titles(self) -> None:
        counts = {bucket: 0 for bucket, _ in _SECTIONS}
        for activity_id, bucket in self._card_bucket.items():
            card = self._cards.get(activity_id)
            if card is not None and card.isVisibleTo(self):
                counts[bucket] += 1
        for bucket, label in _SECTIONS:
            box, _ = self._sections[bucket]
            box.setTitle(f"{label} ({counts[bucket]})")
