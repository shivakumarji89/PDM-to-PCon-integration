"""Modern progress dialog (design-system).

A concise, card-based progress popup built from design-system components
(:class:`~ui.components.dialog_template.DialogTemplate`,
:class:`~ui.components.progress_card.ProgressCard`,
:class:`~ui.components.metric.MetricTile` / ``StatisticsGrid``). It is a pure
presentation surface: it consumes the same :class:`~core.progress.
ProgressReporter` data as before through the identical public API
(:meth:`bind`, the ``set_*`` setters, :meth:`finish`, :attr:`cancel_requested`),
so the loading workflow, ``ProgressReporter`` and ``ActivityService`` are
unchanged.
"""
from __future__ import annotations

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QWidget

from ui import theme
from ui.components import DialogTemplate, ProgressCard
from ui.components._styles import label_color_qss, secondary_button_qss


class ProgressDialog(DialogTemplate):
    """Concise, reusable progress popup driven by a ProgressReporter."""

    #: Emitted when the user clicks Cancel (wired for future cancellation).
    cancel_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # A reusable live monitor: never input-blocks the window and stays
        # alive across loads (closing is a hide, not a destroy).
        self.setModal(False)
        self.set_title("Working...")
        self.setFixedWidth(430)
        self._finished = False
        self._reporter = None
        self._elapsed_str = "00:00"
        self._eta_str = "00:00"

        self._build_header_trailing()
        self._build_content()
        self._build_footer()

    # -- construction ------------------------------------------------------
    def _build_header_trailing(self) -> None:
        self._percent = QLabel("0%", self)
        self._percent.setFont(theme.font("percent"))
        self._percent.setStyleSheet(label_color_qss(theme.ACCENT))
        self.set_header_trailing(self._percent)

    def _build_content(self) -> None:
        self._subtitle = QLabel("-", self)
        self._subtitle.setFont(theme.font("subtitle"))
        self._subtitle.setStyleSheet(label_color_qss(theme.MUTED))
        self._subtitle.setWordWrap(False)
        self.add_content(self._subtitle)

        self._progress_card = ProgressCard(self)
        self.add_content(self._progress_card)

        # Elapsed/ETA shown compactly right under the progress bar - no tiles.
        self._timing_label = QLabel("Elapsed 00:00   \u00b7   ETA 00:00", self)
        self._timing_label.setFont(theme.font("subtitle"))
        self._timing_label.setStyleSheet(label_color_qss(theme.MUTED))
        self.add_content(self._timing_label)

    def _build_footer(self) -> None:
        self._cancel_btn = QPushButton("Cancel", self)
        self._cancel_btn.setObjectName("secondaryButton")
        self._cancel_btn.setStyleSheet(secondary_button_qss("secondaryButton"))
        self._cancel_btn.setFont(theme.font("button"))
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)
        self.add_footer_button(self._cancel_btn)

    # -- reporter binding --------------------------------------------------
    def bind(self, reporter) -> None:
        """Connect a :class:`~core.progress.ProgressReporter` to this dialog.

        The dialog is a reusable monitor: binding a new reporter first detaches
        the previous one and resets the visuals, so the same instance can drive
        one load after another without accumulating connections.
        """
        if reporter is self._reporter:
            return
        self._unbind()
        self.reset()
        self._reporter = reporter
        reporter.title_changed.connect(self.set_title)
        reporter.family_changed.connect(self.set_family)
        reporter.product_changed.connect(self.set_product)
        reporter.step_changed.connect(self.set_step)
        reporter.progress_changed.connect(self.set_progress)
        reporter.elapsed_changed.connect(self.set_elapsed)
        reporter.remaining_changed.connect(self.set_remaining)
        reporter.finished.connect(self._on_reporter_finished)
        # Cancel is wired to the reporter's (currently advisory) flag.
        self.cancel_requested.connect(reporter.request_cancel)

    def _unbind(self) -> None:
        """Detach the currently-bound reporter, if any."""
        reporter = self._reporter
        if reporter is None:
            return
        try:
            reporter.title_changed.disconnect(self.set_title)
            reporter.family_changed.disconnect(self.set_family)
            reporter.product_changed.disconnect(self.set_product)
            reporter.step_changed.disconnect(self.set_step)
            reporter.progress_changed.disconnect(self.set_progress)
            reporter.elapsed_changed.disconnect(self.set_elapsed)
            reporter.remaining_changed.disconnect(self.set_remaining)
            reporter.finished.disconnect(self._on_reporter_finished)
            self.cancel_requested.disconnect(reporter.request_cancel)
        except (RuntimeError, TypeError):
            # Already disconnected or the reporter was deleted - nothing to do.
            pass
        self._reporter = None

    def unbind_reporter(self, reporter) -> None:
        """Detach ``reporter`` if (and only if) it is the one currently bound.

        Lets a finished operation release its reporter from the monitor without
        disturbing a newer run that may already have rebound the dialog. The
        displayed final state is left intact; the reporter is simply released.
        """
        if reporter is self._reporter:
            self._unbind()

    def reset(self) -> None:
        """Clear the visuals so the monitor is ready for a fresh run."""
        self._finished = False
        self.set_title("Working...")
        self.set_family("-")
        self.set_product("-")
        self.set_step("-")
        self.set_progress(0)
        self.set_elapsed(0)
        self.set_remaining(0)
        self._cancel_btn.setText("Cancel")

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        """Closing hides the monitor; it never cancels loading or destroys it.

        The reporter stays bound while hidden, so the dialog keeps receiving
        updates and shows the current progress when reopened.
        """
        self.hide()
        event.ignore()

    # -- simple update API -------------------------------------------------
    def set_family(self, name: str) -> None:
        self._subtitle.setText(name or "-")

    def set_product(self, name: str) -> None:
        # Current Product tile removed: loading is bulk, not per-article.
        return

    def set_step(self, text: str) -> None:
        self._progress_card.set_operation(text or "-")

    def set_progress(self, percent: int) -> None:
        value = max(0, min(100, int(percent)))
        self._percent.setText(f"{value}%")
        self._progress_card.set_progress(value)

    def set_stage(self, text: str) -> None:
        """Optional prominent stage line (e.g. 'Stage 4 of 6')."""
        self._progress_card.set_stage(text)

    def set_elapsed(self, seconds: int) -> None:
        self._elapsed_str = self._format_time(seconds)
        self._render_timing()

    def set_remaining(self, seconds: int) -> None:
        self._eta_str = self._format_time(seconds)
        self._render_timing()

    def _render_timing(self) -> None:
        self._timing_label.setText(
            f"Elapsed {self._elapsed_str}   \u00b7   ETA {self._eta_str}"
        )

    def finish(self, success: bool = True, message: str = "") -> None:
        """Put the dialog into its terminal state, then auto-close it shortly
        after so the popup dismisses itself once the load completes."""
        self._finished = True
        self.set_progress(100)
        if message:
            self._progress_card.set_operation(message)
        self._cancel_btn.setText("Close")
        # Brief pause so the user glimpses 100% / the final message, then close.
        QTimer.singleShot(700, self._auto_dismiss)

    def _auto_dismiss(self) -> None:
        """Close the popup if it is still in its finished state (a newer run may
        have rebound it in the meantime, in which case leave it open)."""
        if self._finished:
            self.accept()

    # -- interaction -------------------------------------------------------
    def _on_cancel_clicked(self) -> None:
        if self._finished:
            self.accept()
            return
        self.cancel_requested.emit()

    def _on_reporter_finished(self, success: bool, message: str) -> None:
        self.finish(success, message)

    @staticmethod
    def _format_time(seconds: int) -> str:
        seconds = max(0, int(seconds))
        return f"{seconds // 60:02d}:{seconds % 60:02d}"
