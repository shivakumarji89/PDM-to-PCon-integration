"""Base class for all center workspace pages.

Provides a consistent placeholder layout (title + description + content area)
so each concrete page only needs to declare its own metadata. No business
logic lives here.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ui import theme


class BasePage(QWidget):
    """Common scaffold for workspace pages."""

    def __init__(
        self,
        title: str,
        description: str = "",
        parent: QWidget | None = None,
        show_placeholder: bool = True,
        content_stretch: bool = False,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("workspacePage")

        self._title = title
        self._description = description

        root = QVBoxLayout(self)
        # The center panel owns the outer padding; the page adds none, so page
        # content aligns with the left panel's content (a single PANEL_INSET).
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(theme.SECTION_SPACING)

        header = QLabel(title, self)
        header.setObjectName("pageTitle")
        root.addWidget(header)

        if description:
            subtitle = QLabel(description, self)
            subtitle.setObjectName("pageSubtitle")
            subtitle.setWordWrap(True)
            root.addWidget(subtitle)

        divider = QFrame(self)
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setObjectName("pageDivider")
        root.addWidget(divider)

        # Content area that concrete pages can fill in later phases. When
        # ``content_stretch`` is set the content expands to fill the workspace
        # (largest working area, no trailing whitespace); otherwise content is
        # top-aligned with a trailing stretch. This keeps a single reusable
        # scaffold for every workspace.
        self._content = QVBoxLayout()
        self._content.setSpacing(theme.SECTION_SPACING)

        placeholder = QLabel(f"{title} Workspace", self)
        placeholder.setObjectName("pagePlaceholder")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if content_stretch:
            root.addLayout(self._content, 1)
        else:
            root.addLayout(self._content)

        if show_placeholder:
            self._content.addWidget(placeholder)
        else:
            placeholder.deleteLater()

        if not content_stretch:
            root.addStretch(1)

    @property
    def title(self) -> str:
        """Human-readable page title."""
        return self._title

    def add_content(self, widget: QWidget) -> None:
        """Append a widget to the page content area."""
        self._normalize_group_boxes(widget)
        self._content.addWidget(widget)

    @staticmethod
    def _normalize_group_boxes(widget: QWidget) -> None:
        """Make every group box rely on the shared QSS card padding for its
        border-to-content gap. Ad-hoc layout margins are cleared so the inset
        is a consistent 8px everywhere and never doubled on top of the padding.
        """
        boxes = list(widget.findChildren(QGroupBox))
        if isinstance(widget, QGroupBox):
            boxes.append(widget)
        for box in boxes:
            layout = box.layout()
            if layout is not None:
                layout.setContentsMargins(0, 0, 0, 0)

    # -- workspace lifecycle (hooks for the workflow framework) -----------
    # Default implementations are intentionally no-ops so hosting a page in the
    # workflow never duplicates its existing refresh logic. Concrete pages
    # override refresh()/is_ready() where meaningful.
    def refresh(self) -> None:
        """Reload the page from the active snapshot. Overridden by pages."""

    def is_ready(self) -> bool:
        """Whether this workspace is satisfied enough to continue."""
        return True

    def on_enter(self) -> None:
        """Called when the workspace becomes active."""

    def on_leave(self) -> None:
        """Called when the workspace is left."""

    def activate(self) -> None:
        """Called when the workspace is activated by the host."""

    def deactivate(self) -> None:
        """Called when the workspace is deactivated by the host."""
