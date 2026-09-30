#!/usr/bin/env python3
"""
GUI — Main Window
PyQt6 main application window for Baxters Power Goo (Linux).
Provides image loading, goo-effect processing, and result saving.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QImage, QPixmap, QColor, QPalette, QIcon, QAction
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)
from PIL import Image

from baxters_power_goo.block1.input_handler import InputHandler, InputError
from baxters_power_goo.error_handler import handle_exception
from baxters_power_goo.clipboard_linux import is_clipboard_tool_available
from baxters_power_goo.goo_tools import GooTool, TOOL_LABELS, run_goo_tool

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Worker thread — keeps the UI responsive during processing
# ---------------------------------------------------------------------------

class GooWorker(QThread):
    finished = pyqtSignal(object)   # emits PIL Image
    error = pyqtSignal(str)

    def __init__(self, image: Image.Image, tool: GooTool) -> None:
        super().__init__()
        self._image = image
        self._tool = tool

    def run(self) -> None:
        try:
            result_image = run_goo_tool(self._image, self._tool)
            self.finished.emit(result_image)
        except Exception as exc:
            self.error.emit(str(exc))


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self, icon_path: Optional[Path] = None) -> None:
        super().__init__()
        self.setWindowTitle("Baxters Power Goo")
        self.setMinimumSize(900, 650)

        if icon_path and icon_path.is_file():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._source_image: Optional[Image.Image] = None
        self._result_image: Optional[Image.Image] = None
        self._worker: Optional[GooWorker] = None

        self._build_ui()
        self._apply_dark_theme()
        self.statusBar().showMessage("Ready — load an image to begin.")

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setSpacing(6)
        root_layout.setContentsMargins(8, 8, 8, 8)

        # Toolbar
        toolbar = QToolBar("Main", self)
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)

        open_action = QAction("Open Image…", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open_file)
        toolbar.addAction(open_action)

        paste_action = QAction("Paste from Clipboard", self)
        paste_action.setShortcut("Ctrl+V")
        paste_action.triggered.connect(self._on_paste_clipboard)
        if not is_clipboard_tool_available():
            paste_action.setEnabled(False)
            paste_action.setText("Paste (install xclip/wl-paste)")
        toolbar.addAction(paste_action)

        toolbar.addSeparator()

        save_action = QAction("Save Result…", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._on_save)
        toolbar.addAction(save_action)

        # Image panels
        panels = QHBoxLayout()
        panels.setSpacing(8)

        self._source_label = self._make_image_label("Source Image")
        self._result_label = self._make_image_label("Result")

        panels.addWidget(self._source_label["container"])
        panels.addWidget(self._result_label["container"])

        root_layout.addLayout(panels)

        # Controls bar — one button per tool
        controls = QHBoxLayout()
        controls.setSpacing(12)

        self._tool_buttons: dict[GooTool, QPushButton] = {}
        for tool in GooTool:
            btn = QPushButton(TOOL_LABELS[tool])
            btn.setEnabled(False)
            btn.setMinimumHeight(38)
            btn.clicked.connect(lambda checked=False, t=tool: self._on_apply(t))
            controls.addWidget(btn)
            self._tool_buttons[tool] = btn

        controls.addStretch()
        root_layout.addLayout(controls)

    def _make_image_label(self, title: str) -> dict:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)

        heading = QLabel(title)
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(heading)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumSize(350, 400)

        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        label.setStyleSheet("background: #1a1a1a;")
        scroll.setWidget(label)
        layout.addWidget(scroll)

        return {"container": container, "label": label}

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.webp);;All files (*)"
        )
        if not path:
            return
        try:
            handler = InputHandler()
            img = handler.load_from_file(path)
            self._set_source(img)
        except InputError as exc:
            QMessageBox.critical(self, "Load Error", str(exc))

    def _on_paste_clipboard(self) -> None:
        try:
            handler = InputHandler()
            img = handler.load_from_clipboard()
            if img is None:
                QMessageBox.information(self, "Clipboard", "No image found on clipboard.")
                return
            self._set_source(img)
        except Exception as exc:
            QMessageBox.critical(self, "Clipboard Error", str(exc))

    def _on_apply(self, tool: GooTool) -> None:
        if self._source_image is None:
            return
        self._set_tool_buttons_enabled(False)
        self.statusBar().showMessage(f"Applying {TOOL_LABELS[tool]}…")

        self._worker = GooWorker(self._source_image, tool)
        self._worker.finished.connect(self._on_goo_done)
        self._worker.error.connect(self._on_goo_error)
        self._worker.start()

    def _on_goo_done(self, result: Image.Image) -> None:
        self._result_image = result
        self._display_image(result, self._result_label["label"])
        self._set_tool_buttons_enabled(True)
        self.statusBar().showMessage("Goo effect applied successfully.")

    def _on_goo_error(self, message: str) -> None:
        self._set_tool_buttons_enabled(True)
        self.statusBar().showMessage("Error during processing.")
        QMessageBox.critical(self, "Processing Error", message)

    def _set_tool_buttons_enabled(self, enabled: bool) -> None:
        for btn in self._tool_buttons.values():
            btn.setEnabled(enabled)

    def _on_save(self) -> None:
        if self._result_image is None:
            QMessageBox.information(self, "Nothing to save", "Apply the goo effect first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Result", str(Path.home() / "goo_result.png"),
            "PNG (*.png);;JPEG (*.jpg);;BMP (*.bmp)"
        )
        if not path:
            return
        try:
            ext = Path(path).suffix.lower()
            if ext in (".jpg", ".jpeg"):
                self._result_image.convert("RGB").save(path, quality=92)
            else:
                self._result_image.save(path)
            self.statusBar().showMessage(f"Saved: {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Save Error", str(exc))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _set_source(self, img: Image.Image) -> None:
        self._source_image = img
        self._display_image(img, self._source_label["label"])
        self._set_tool_buttons_enabled(True)
        self._result_image = None
        self._result_label["label"].clear()
        self.statusBar().showMessage(
            f"Loaded {img.size[0]}×{img.size[1]} px — pick a tool below."
        )

    @staticmethod
    def _display_image(img: Image.Image, label: QLabel) -> None:
        rgb = img.convert("RGBA")
        w, h = rgb.size
        data = rgb.tobytes("raw", "RGBA")
        qimage = QImage(data, w, h, w * 4, QImage.Format.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qimage).scaled(
            label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        label.setPixmap(pixmap)

    def _apply_dark_theme(self) -> None:
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(45, 45, 45))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(220, 220, 220))
        palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 220))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Text, QColor(220, 220, 220))
        palette.setColor(QPalette.ColorRole.Button, QColor(60, 60, 60))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(220, 220, 220))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))
        self.setPalette(palette)
        self.setStyleSheet(
            "QPushButton { border-radius: 4px; padding: 4px 12px; }"
            "QPushButton:hover { background: #3a3a3a; }"
            "QPushButton:disabled { color: #666; }"
        )
