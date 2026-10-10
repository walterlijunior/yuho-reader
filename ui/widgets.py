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

"""Peças reaproveitadas pelas páginas: cartões, botões, chips, layout em fluxo."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QSize, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame, QLabel, QLayout, QMessageBox, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from . import icons, theme


def label(text: str = "", name: str = "", wrap: bool = False) -> QLabel:
    widget = QLabel(text)
    if name:
        widget.setObjectName(name)
    widget.setWordWrap(wrap)
    return widget


def chip(text: str, accent: bool = False) -> QLabel:
    widget = QLabel(text)
    widget.setObjectName("chipAccent" if accent else "chip")
    widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
    return widget


def primary(text: str) -> QPushButton:
    """Botão principal: verde, texto escuro em MAIÚSCULAS."""
    button = QPushButton(text.upper())
    button.setObjectName("primary")
    button.setCursor(Qt.PointingHandCursor)
    return button


def button(text: str, icon_name: str = "") -> QPushButton:
    widget = QPushButton(text.upper())
    widget.setCursor(Qt.PointingHandCursor)
    if icon_name:
        widget.setIcon(icons.icon(icon_name, theme.TEXT, 16))
        widget.setText(f"  {text.upper()}")
    return widget


def link(text: str) -> QPushButton:
    widget = QPushButton(text)
    widget.setObjectName("link")
    widget.setCursor(Qt.PointingHandCursor)
    return widget


def card(margins: int = 20, spacing: int = 12) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(margins, margins, margins, margins)
    layout.setSpacing(spacing)
    return frame, layout


def separator() -> QFrame:
    line = QFrame()
    line.setObjectName("separator")
    return line


def scroll_page(max_width: int = 0) -> tuple[QScrollArea, QVBoxLayout]:
    """Página rolável; devolve a área e o layout onde colocar o conteúdo."""
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    body = QWidget()
    body.setObjectName("scrollBody")
    layout = QVBoxLayout(body)
    layout.setContentsMargins(28, 24, 28, 28)
    layout.setSpacing(16)
    if max_width:
        body.setMaximumWidth(max_width)
    area.setWidget(body)
    return area, layout


class ClickableCard(QFrame):
    clicked = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("cardClick")
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class FlowLayout(QLayout):
    """Coloca os itens lado a lado e quebra a linha quando falta espaço."""

    def __init__(self, parent=None, spacing: int = 14):
        super().__init__(parent)
        self._items = []
        self._spacing = spacing
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def clear(self):
        while self._items:
            widget = self._items.pop().widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self.invalidate()

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._arrange(QRect(0, 0, width, 0), apply=False)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._arrange(rect, apply=True)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        return size

    def _arrange(self, rect: QRect, apply: bool) -> int:
        x, y, row_height = rect.x(), rect.y(), 0
        for item in self._items:
            hint = item.sizeHint()
            if x + hint.width() > rect.right() + 1 and row_height > 0:
                x = rect.x()
                y += row_height + self._spacing
                row_height = 0
            if apply:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x += hint.width() + self._spacing
            row_height = max(row_height, hint.height())
        return y + row_height - rect.y()


def open_path(path: Path | str) -> bool:
    return QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


def open_url(url: str) -> bool:
    return QDesktopServices.openUrl(QUrl(url))


def message(parent: QWidget, title: str, text: str, kind: str = "info") -> None:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setTextFormat(Qt.RichText)
    box.setText(text)
    box.setIcon({"info": QMessageBox.Information, "warning": QMessageBox.Warning,
                 "error": QMessageBox.Critical, "none": QMessageBox.NoIcon}[kind])
    box.setStandardButtons(QMessageBox.Ok)
    theme.dark_titlebar(box)
    box.exec()


def confirm(parent: QWidget, title: str, text: str) -> bool:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setIcon(QMessageBox.Question)
    yes = box.addButton("Sim", QMessageBox.YesRole)
    box.addButton("Não", QMessageBox.NoRole)
    theme.dark_titlebar(box)
    box.exec()
    return box.clickedButton() is yes
