# Yuho Reader - baixa demonstrações contábeis do EDINET e monta planilhas Excel.
# Copyright (C) 2026 walterlijunior
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Tema escuro com destaque verde: cores, folha de estilo e barra de título escura."""

from __future__ import annotations

import sys

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QWidget

BG = "#1a1a1a"
SIDEBAR = "#202020"
HEADER = "#242424"
CARD = "#2a2a2a"
CARD_HOVER = "#343434"
FIELD = "#1f1f1f"
BORDER = "#3a3a3a"
ACCENT = "#76b900"
ACCENT_HOVER = "#8fd400"
TEXT = "#e8e8e8"
MUTED = "#9b9b9b"
DANGER = "#ff6b6b"
WARNING = "#f5a524"
FONT = "Segoe UI"
MONO = "Consolas"

_QSS = """
* { font-family: "Segoe UI"; }
QWidget { color: @TEXT; font-size: 13px; }
QMainWindow, QDialog, QMessageBox, #page, #scrollBody { background: @BG; }
QScrollArea { border: none; background: @BG; }
QLabel { background: transparent; }
QToolTip { background: #333333; color: @TEXT; border: 1px solid #555555; padding: 4px; }

#sidebar { background: @SIDEBAR; }
#header { background: @HEADER; border-bottom: 1px solid #2e2e2e; }
#headerTitle { font-size: 18px; font-weight: 600; }

QFrame#card, QFrame#cardClick { background: @CARD; border-radius: 6px; }
QFrame#cardClick:hover { background: @CARD_HOVER; }
QFrame#warningCard { background: #332a14; border: 1px solid #6b5416; border-radius: 6px; }
QFrame#separator { background: @BORDER; max-height: 1px; min-height: 1px; }

QLabel#h1 { font-size: 28px; font-weight: 700; color: #ffffff; }
QLabel#h2 { font-size: 17px; font-weight: 600; color: #ffffff; }
QLabel#h3 { font-size: 14px; font-weight: 600; color: #ffffff; }
QLabel#section { font-size: 11px; font-weight: 700; color: @MUTED; }
QLabel#muted { color: @MUTED; }
QLabel#bannerText { font-size: 14px; color: #cfcfcf; }
QLabel#bigCode { font-size: 30px; font-weight: 700; color: @ACCENT; }
QLabel#ok { color: @ACCENT; }
QLabel#error { color: @DANGER; }
QLabel#chip { background: #3a3a3a; border-radius: 10px; padding: 3px 10px; font-size: 12px; }
QLabel#chipAccent { border: 1px solid @ACCENT; color: @ACCENT; border-radius: 10px;
                    padding: 2px 10px; font-size: 12px; font-weight: 600; }

QPushButton { background: transparent; border: 1px solid #5a5a5a; border-radius: 3px;
              padding: 7px 16px; font-weight: 600; color: @TEXT; }
QPushButton:hover { border-color: @ACCENT; color: #ffffff; }
QPushButton:pressed { background: #2f2f2f; }
QPushButton:disabled { color: #666666; border-color: #383838; }
QPushButton#primary { background: @ACCENT; border: none; color: #111111; font-weight: 700; padding: 9px 22px; }
QPushButton#primary:hover { background: @ACCENT_HOVER; color: #111111; }
QPushButton#primary:disabled { background: #3d4a22; color: #7d7d7d; }
QPushButton#flat { border: none; padding: 6px 10px; color: @MUTED; font-weight: 600; }
QPushButton#flat:hover { color: #ffffff; background: #2e2e2e; }
QPushButton#link { border: none; padding: 0; color: @ACCENT; font-weight: 600; text-align: left; }
QPushButton#link:hover { color: @ACCENT_HOVER; }
QPushButton#iconButton { border: 1px solid @BORDER; padding: 6px; }
QPushButton#dot { background: #5a5a5a; border: none; border-radius: 5px; padding: 0;
                  min-width: 10px; max-width: 10px; min-height: 10px; max-height: 10px; }
QPushButton#dot:checked { background: @ACCENT; }

QLineEdit, QDoubleSpinBox { background: @FIELD; border: 1px solid @BORDER; border-radius: 3px; padding: 7px 10px;
            selection-background-color: @ACCENT; selection-color: #111111; }
QLineEdit:focus, QDoubleSpinBox:focus { border-color: @ACCENT; }
QLineEdit:disabled { color: #777777; }
QLineEdit#searchBox { font-size: 15px; padding: 10px 12px; }
QDoubleSpinBox { padding: 7px 24px 7px 12px; }
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { subcontrol-origin: border; width: 22px;
            border: none; background: transparent; }
QDoubleSpinBox::up-button { subcontrol-position: top right; }
QDoubleSpinBox::down-button { subcontrol-position: bottom right; }
QDoubleSpinBox::up-arrow { image: url(@UP); width: 9px; height: 9px; }
QDoubleSpinBox::down-arrow { image: url(@DOWN); width: 9px; height: 9px; }

QCheckBox { spacing: 8px; background: transparent; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #6a6a6a; border-radius: 2px; background: @FIELD; }
QCheckBox::indicator:hover { border-color: @ACCENT; }
QCheckBox::indicator:checked { background: @ACCENT; border-color: @ACCENT; image: url(@CHECK); }
QCheckBox::indicator:checked:disabled { background: #556b22; border-color: #556b22; }
QCheckBox:disabled { color: #8a8a8a; }

QProgressBar { background: @FIELD; border: none; border-radius: 4px; max-height: 8px; min-height: 8px; }
QProgressBar::chunk { background: @ACCENT; border-radius: 4px; }

QPlainTextEdit { background: #141414; border: 1px solid @BORDER; border-radius: 4px; padding: 6px;
                 font-family: "Consolas"; font-size: 12px; color: #cfcfcf;
                 selection-background-color: @ACCENT; selection-color: #111111; }

QTableWidget { background: @CARD; border: none; border-radius: 6px; gridline-color: transparent;
               alternate-background-color: #2e2e2e; selection-background-color: #3d4d1c;
               selection-color: #ffffff; outline: none; }
QTableWidget::item { padding: 6px 8px; border: none; }
QHeaderView { background: transparent; }
QHeaderView::section { background: #242424; color: @MUTED; border: none; border-bottom: 1px solid @BORDER;
                       padding: 8px; font-weight: 600; }
QTableCornerButton::section { background: #242424; border: none; }

QScrollBar:vertical { background: transparent; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: #4a4a4a; border-radius: 5px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #666666; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 0; }
QScrollBar::handle:horizontal { background: #4a4a4a; border-radius: 5px; min-width: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
"""


def stylesheet(assets: dict[str, str]) -> str:
    qss = _QSS
    for token, value in (
        ("@ACCENT_HOVER", ACCENT_HOVER), ("@ACCENT", ACCENT), ("@CARD_HOVER", CARD_HOVER), ("@CARD", CARD),
        ("@SIDEBAR", SIDEBAR), ("@HEADER", HEADER), ("@BORDER", BORDER), ("@FIELD", FIELD), ("@MUTED", MUTED),
        ("@DANGER", DANGER), ("@TEXT", TEXT), ("@BG", BG),
        ("@CHECK", assets["check"]), ("@UP", assets["up"]), ("@DOWN", assets["down"]),
    ):
        qss = qss.replace(token, value)
    return qss


def apply_theme(app: QApplication, assets: dict[str, str]) -> None:
    app.setStyle("Fusion")
    palette = QPalette()
    for role, color in (
        (QPalette.Window, BG), (QPalette.Base, FIELD), (QPalette.AlternateBase, CARD),
        (QPalette.Button, CARD), (QPalette.WindowText, TEXT), (QPalette.Text, TEXT),
        (QPalette.ButtonText, TEXT), (QPalette.ToolTipBase, "#333333"), (QPalette.ToolTipText, TEXT),
        (QPalette.Highlight, ACCENT), (QPalette.HighlightedText, "#111111"),
        (QPalette.PlaceholderText, "#777777"), (QPalette.Link, ACCENT),
    ):
        palette.setColor(role, QColor(color))
    app.setPalette(palette)
    app.setStyleSheet(stylesheet(assets))


def dark_titlebar(widget: QWidget) -> None:
    """Pede ao Windows a barra de título escura para a janela."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        hwnd = int(widget.winId())
        value = ctypes.c_int(1)
        for attribute in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE (19 em versões antigas do Windows 10)
            result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                ctypes.c_void_p(hwnd), attribute, ctypes.byref(value), ctypes.sizeof(value)
            )
            if result == 0:
                break
    except Exception:
        pass
