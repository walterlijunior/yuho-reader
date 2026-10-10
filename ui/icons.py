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

"""Ícones originais, desenhados por código (nenhum arquivo de imagem de terceiros)."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap

from core.config import local_dir

GREEN = "#76b900"


def _path(*segments: str) -> QPainterPath:
    """Mini-linguagem: 'M x y', 'L x y', 'Z' numa grade de 24 x 24."""
    path = QPainterPath()
    for segment in segments:
        tokens = segment.split()
        index = 0
        while index < len(tokens):
            command = tokens[index]
            if command == "Z":
                path.closeSubpath()
                index += 1
                continue
            x, y = float(tokens[index + 1]), float(tokens[index + 2])
            if command == "M":
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
            index += 3
    return path


def paint_icon(painter: QPainter, name: str, rect: QRectF, color: QColor | str) -> None:
    """Desenha o ícone `name` dentro de `rect`, em traço, na cor indicada."""
    color = QColor(color)
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    painter.translate(rect.topLeft())
    painter.scale(rect.width() / 24, rect.height() / 24)
    pen = QPen(color, 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)

    if name == "home":
        painter.drawPath(_path("M 3 11.5 L 12 3.5 L 21 11.5", "M 5.5 10 L 5.5 20 L 18.5 20 L 18.5 10",
                               "M 10 20 L 10 14 L 14 14 L 14 20"))
    elif name == "building":
        painter.drawRect(QRectF(5, 3, 14, 18))
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        for x in (8.2, 13):
            for y in (6.2, 10.2, 14.2):
                painter.drawRect(QRectF(x, y, 2.8, 2))
    elif name == "download":
        painter.drawPath(_path("M 12 3 L 12 15", "M 7 10.5 L 12 15.5 L 17 10.5",
                               "M 4 17 L 4 20.5 L 20 20.5 L 20 17"))
    elif name == "gear":
        painter.drawEllipse(QPointF(12, 12), 6.2, 6.2)
        painter.drawEllipse(QPointF(12, 12), 2.4, 2.4)
        painter.setPen(QPen(color, 2.6, Qt.SolidLine, Qt.RoundCap))
        for step in range(8):
            angle = math.radians(step * 45)
            painter.drawLine(QPointF(12 + 7.6 * math.cos(angle), 12 + 7.6 * math.sin(angle)),
                             QPointF(12 + 9.6 * math.cos(angle), 12 + 9.6 * math.sin(angle)))
    elif name == "code":
        painter.drawPath(_path("M 8 7 L 3 12 L 8 17", "M 16 7 L 21 12 L 16 17", "M 13.8 5 L 10.2 19"))
    elif name == "help":
        painter.drawEllipse(QPointF(12, 12), 9, 9)
        font = QFont("Segoe UI")
        font.setPixelSize(13)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(0, 0, 24, 23.5), Qt.AlignCenter, "?")
    elif name in ("eye", "eye_off"):
        path = QPainterPath(QPointF(2, 12))
        path.quadTo(QPointF(12, 1.5), QPointF(22, 12))
        path.quadTo(QPointF(12, 22.5), QPointF(2, 12))
        painter.drawPath(path)
        painter.drawEllipse(QPointF(12, 12), 3, 3)
        if name == "eye_off":
            painter.drawLine(QPointF(4, 20), QPointF(20, 4))
    elif name == "folder":
        painter.drawPath(_path("M 3 6 L 9.5 6 L 11.5 8.5 L 21 8.5 L 21 19 L 3 19 Z"))
    elif name == "sheet":
        painter.drawRect(QRectF(3, 4, 18, 16))
        painter.drawPath(_path("M 3 9.3 L 21 9.3", "M 3 14.6 L 21 14.6", "M 9 4 L 9 20", "M 15 4 L 15 20"))
    elif name == "external":
        painter.drawPath(_path("M 14 4 L 20 4 L 20 10", "M 20 4 L 11 13", "M 17 14 L 17 20 L 4 20 L 4 7 L 10 7"))
    elif name == "search":
        painter.drawEllipse(QPointF(10.5, 10.5), 6.5, 6.5)
        painter.drawLine(QPointF(15.5, 15.5), QPointF(21, 21))
    elif name == "warning":
        painter.drawPath(_path("M 12 3.5 L 21.5 20 L 2.5 20 Z", "M 12 10 L 12 14.5"))
        painter.setBrush(color)
        painter.drawEllipse(QPointF(12, 17.2), 0.6, 0.6)
    elif name == "doc":
        painter.drawPath(_path("M 6 3 L 14 3 L 19 8 L 19 21 L 6 21 Z", "M 14 3 L 14 8 L 19 8",
                               "M 9 13 L 16 13", "M 9 17 L 16 17"))
    elif name == "list":
        painter.drawPath(_path("M 8 6 L 21 6", "M 8 12 L 21 12", "M 8 18 L 21 18"))
        painter.setBrush(color)
        for y in (6, 12, 18):
            painter.drawEllipse(QPointF(4, y), 0.9, 0.9)
    elif name == "check":
        painter.setPen(QPen(color, 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(_path("M 5 12.5 L 10 17.5 L 19 7"))
    elif name == "up":
        painter.setPen(QPen(color, 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(_path("M 5 16 L 12 8 L 19 16"))
    elif name == "down":
        painter.setPen(QPen(color, 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(_path("M 5 8 L 12 16 L 19 8"))
    painter.restore()


def pixmap(name: str, color: str = "#e8e8e8", size: int = 20) -> QPixmap:
    scale = 2  # desenha em dobro para ficar nítido em telas de alta resolução
    image = QPixmap(size * scale, size * scale)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    paint_icon(painter, name, QRectF(0, 0, size * scale, size * scale), color)
    painter.end()
    image.setDevicePixelRatio(scale)
    return image


def icon(name: str, color: str = "#e8e8e8", size: int = 20) -> QIcon:
    return QIcon(pixmap(name, color, size))


def paint_app_icon(painter: QPainter, size: float) -> None:
    """Ícone do programa: quadrado escuro com barras verdes e uma linha de tendência."""
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    painter.scale(size / 64, size / 64)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#1a1a1a"))
    painter.drawRoundedRect(QRectF(2, 2, 60, 60), 12, 12)
    painter.setPen(QPen(QColor(GREEN), 2.5))
    painter.setBrush(Qt.NoBrush)
    painter.drawRoundedRect(QRectF(3.2, 3.2, 57.6, 57.6), 11, 11)

    painter.setPen(Qt.NoPen)
    for x, height in ((14, 14), (26, 22), (38, 30)):
        gradient = QLinearGradient(0, 50 - height, 0, 50)
        gradient.setColorAt(0, QColor(GREEN))
        gradient.setColorAt(1, QColor("#3f6300"))
        painter.setBrush(gradient)
        painter.drawRoundedRect(QRectF(x, 50 - height, 9, height), 1.5, 1.5)
    painter.setPen(QPen(QColor("#d9ff8a"), 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.drawPath(_path("M 12 30 L 24 24 L 34 18 L 50 12"))
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#ffffff"))
    painter.drawEllipse(QPointF(50, 12), 3.2, 3.2)
    painter.restore()


def app_pixmap(size: int) -> QPixmap:
    image = QPixmap(size, size)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    paint_app_icon(painter, size)
    painter.end()
    return image


def app_icon() -> QIcon:
    result = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        result.addPixmap(app_pixmap(size))
    return result


def ensure_assets() -> dict[str, str]:
    """Pequenas imagens que a folha de estilo precisa (marca da caixa de seleção, setas)."""
    folder = local_dir() / "ui"
    folder.mkdir(parents=True, exist_ok=True)
    assets = {}
    for key, name, color in (("check", "check", "#111111"), ("up", "up", "#bdbdbd"), ("down", "down", "#bdbdbd")):
        path = folder / f"{key}.png"
        image = QPixmap(32, 32)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        paint_icon(painter, name, QRectF(0, 0, 32, 32), color)
        painter.end()
        image.save(str(path), "PNG")
        assets[key] = path.as_posix()
    return assets
