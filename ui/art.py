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

"""Artes animadas do banner da tela inicial, todas originais e desenhadas por código."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient

GREEN = QColor("#76b900")
BRIGHT = QColor("#c8ff5a")

BARS, DOCUMENTS, GRID = range(3)


def _alpha(color: QColor, alpha: int) -> QColor:
    result = QColor(color)
    result.setAlpha(max(0, min(255, alpha)))
    return result


def paint_art(painter: QPainter, rect: QRectF, variant: int, t: float) -> None:
    """Desenha a arte `variant` em `rect`; `t` é o tempo em segundos (anima o desenho)."""
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setClipRect(rect)
    (_bars, _documents, _grid)[variant % 3](painter, rect, t)
    painter.restore()


def _bars(painter: QPainter, rect: QRectF, t: float) -> None:
    base = rect.bottom() - 34
    left = rect.left() + 20
    width = rect.width() - 50
    painter.setPen(QPen(QColor(255, 255, 255, 18), 1))
    for step in range(5):
        y = base - step * (rect.height() - 70) / 4
        painter.drawLine(QPointF(left, y), QPointF(left + width, y))

    heights = (0.30, 0.42, 0.36, 0.55, 0.50, 0.70, 0.64, 0.86)
    slot = width / len(heights)
    tops = []
    for index, factor in enumerate(heights):
        height = (rect.height() - 110) * factor * (0.9 + 0.1 * math.sin(t * 1.4 + index * 0.8))
        x = left + index * slot + slot * 0.2
        bar = QRectF(x, base - height, slot * 0.6, height)
        gradient = QLinearGradient(0, bar.top(), 0, bar.bottom())
        gradient.setColorAt(0, _alpha(GREEN, 235))
        gradient.setColorAt(1, _alpha(GREEN, 40))
        painter.setPen(Qt.NoPen)
        painter.setBrush(gradient)
        painter.drawRoundedRect(bar, 3, 3)
        tops.append(QPointF(bar.center().x(), bar.top() - 26 - 6 * math.sin(t * 1.1 + index)))

    line = QPainterPath(tops[0])
    for point in tops[1:]:
        line.lineTo(point)
    painter.setBrush(Qt.NoBrush)
    for pen_width, alpha in ((12, 22), (7, 45), (2.6, 255)):  # brilho em camadas
        painter.setPen(QPen(_alpha(BRIGHT, alpha), pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(line)

    position = (t * 0.22) % 1 * (len(tops) - 1)
    index = min(int(position), len(tops) - 2)
    fraction = position - index
    dot = tops[index] + (tops[index + 1] - tops[index]) * fraction
    glow = QRadialGradient(dot, 20)
    glow.setColorAt(0, _alpha(BRIGHT, 200))
    glow.setColorAt(1, _alpha(BRIGHT, 0))
    painter.setPen(Qt.NoPen)
    painter.setBrush(glow)
    painter.drawEllipse(dot, 20, 20)
    painter.setBrush(QColor("#ffffff"))
    painter.drawEllipse(dot, 4, 4)


def _documents(painter: QPainter, rect: QRectF, t: float) -> None:
    center = rect.center()
    page_w, page_h = rect.height() * 0.50, rect.height() * 0.66
    pages = ((-page_w * 0.62, -11, 0.0), (page_w * 0.62, 10, 1.6), (0, 0, 3.1))
    for index, (dx, angle, phase) in enumerate(pages):
        front = index == len(pages) - 1
        painter.save()
        painter.translate(center.x() + dx, center.y() + 7 * math.sin(t * 1.2 + phase))
        painter.rotate(angle + 1.5 * math.sin(t * 0.8 + phase))
        page = QRectF(-page_w / 2, -page_h / 2, page_w, page_h)
        painter.setPen(QPen(QColor("#5c5c5c" if front else "#484848"), 1.2))
        painter.setBrush(QColor("#343434" if front else "#2b2b2b"))
        painter.drawRoundedRect(page, 6, 6)
        painter.setPen(Qt.NoPen)
        painter.setBrush(_alpha(GREEN, 230 if front else 110))
        painter.drawRoundedRect(QRectF(page.left() + 12, page.top() + 14, page_w * 0.45, 7), 3, 3)
        painter.setBrush(QColor(255, 255, 255, 60 if front else 30))
        for row in range(6):
            line_w = page_w * (0.78 if row % 3 else 0.6) - 24
            painter.drawRoundedRect(QRectF(page.left() + 12, page.top() + 36 + row * 15, line_w, 5), 2, 2)
        if front:
            badge = QPointF(page.right() - 6, page.bottom() - 6)
            pulse = 1 + 0.06 * math.sin(t * 3)
            painter.setBrush(GREEN)
            painter.drawEllipse(badge, 21 * pulse, 21 * pulse)
            painter.setPen(QPen(QColor("#111111"), 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            offset = 2.5 * math.sin(t * 3)
            painter.drawLine(badge + QPointF(0, -9 + offset), badge + QPointF(0, 7 + offset))
            painter.drawLine(badge + QPointF(-6, 1 + offset), badge + QPointF(0, 7 + offset))
            painter.drawLine(badge + QPointF(6, 1 + offset), badge + QPointF(0, 7 + offset))
        painter.restore()


def _grid(painter: QPainter, rect: QRectF, t: float) -> None:
    columns, rows = 5, 7
    table = QRectF(rect.left() + 24, rect.top() + 34, rect.width() - 64, rect.height() - 68)
    cell_w, cell_h = table.width() / columns, table.height() / rows
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#262626"))
    painter.drawRoundedRect(table.adjusted(-6, -6, 6, 6), 8, 8)
    for row in range(rows):
        for column in range(columns):
            cell = QRectF(table.left() + column * cell_w + 2, table.top() + row * cell_h + 2, cell_w - 4, cell_h - 4)
            if row == 0:
                painter.setBrush(QColor("#1a1a1a"))
                painter.drawRoundedRect(cell, 3, 3)
                painter.setBrush(GREEN)
                painter.drawRoundedRect(QRectF(cell.left() + 8, cell.center().y() - 3, cell.width() * 0.55, 6), 3, 3)
                continue
            painter.setBrush(QColor("#313131"))
            painter.drawRoundedRect(cell, 3, 3)
            wave = math.sin(t * 2.0 - (column + row) * 0.75)
            if wave > 0:
                painter.setBrush(_alpha(GREEN, int(wave * 95)))
                painter.drawRoundedRect(cell, 3, 3)
            length = cell.width() * (0.35 + 0.4 * ((row * 7 + column * 3) % 5) / 4)
            start = cell.left() + 8 if column == 0 else cell.right() - 8 - length
            painter.setBrush(QColor(255, 255, 255, 70))
            painter.drawRoundedRect(QRectF(start, cell.center().y() - 2.5, length, 5), 2, 2)
