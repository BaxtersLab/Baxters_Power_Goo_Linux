#!/usr/bin/env python3
"""
Error Handler — Baxters Power Goo
Centralised exception logging and user-visible error display.
"""

import logging
import traceback
from typing import Optional

logger = logging.getLogger(__name__)


class BPGError(Exception):
    """Base exception for Baxters Power Goo."""


class InputError(BPGError):
    """Raised when an image cannot be loaded."""


class ProcessingError(BPGError):
    """Raised during goo-brain or asset-generation failures."""


class RenderError(BPGError):
    """Raised during deformation or render-pipeline failures."""


def handle_exception(exc: Exception, context: str = "", show_dialog: bool = False) -> str:
    """
    Log *exc* and optionally display a Qt error dialog.

    Returns the formatted error string.
    """
    tb = traceback.format_exc()
    message = f"[{context}] {type(exc).__name__}: {exc}" if context else f"{type(exc).__name__}: {exc}"
    logger.error(message)
    logger.debug(tb)

    if show_dialog:
        _show_qt_dialog(message)

    return message


def _show_qt_dialog(message: str) -> None:
    """Display a Qt critical message box if QApplication exists."""
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
        app = QApplication.instance()
        if app is not None:
            box = QMessageBox()
            box.setWindowTitle("Baxters Power Goo — Error")
            box.setIcon(QMessageBox.Icon.Critical)
            box.setText(message)
            box.exec()
    except Exception:
        pass  # Qt not available; error already logged


def setup_logging(level: int = logging.INFO, log_file: Optional[str] = None) -> None:
    """Configure root logger with console (and optional file) handler."""
    fmt = "%(asctime)s  %(levelname)-8s  %(name)s — %(message)s"
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(level=level, format=fmt, handlers=handlers, force=True)
