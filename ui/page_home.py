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

"""Página Início: banner em carrossel, Biblioteca e Saiba mais."""

from __future__ import annotations

import time

from PySide6.QtCore import QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from core import EDINET_API_URL, EDINET_PORTAL_URL, GITHUB_URL
from core.companies import CODELIST_PAGE
from core.job import LibraryEntry, list_library

from . import art, icons, theme
from .state import AppState
from .widgets import ClickableCard, FlowLayout, label, open_path, open_url, primary, scroll_page

SLIDES = (
    ("Demonstrações contábeis japonesas, direto da fonte",
     "Baixe os relatórios auditados que as empresas arquivam no EDINET, o sistema oficial "
     "da FSA do Japão, e receba tudo organizado para a sua análise.",
     "Escolher empresa", "companies", art.BARS),
    ("Relatórios anuais e semestrais em poucos cliques",
     "Você escolhe a empresa e os exercícios. O programa encontra os documentos oficiais "
     "e baixa os dados em CSV, o XBRL original e o PDF.",
     "Começar", "companies", art.DOCUMENTS),
    ("Uma planilha Excel pronta para analisar",
     "As contas do balanço, do resultado e do fluxo de caixa ficam lado a lado, um relatório "
     "por coluna, prontas para calcular indicadores.",
     "Abrir pasta das planilhas", "folder", art.GRID),
)
SLIDE_SECONDS = 8


class Banner(QFrame):
    action = Signal(str)

    def __init__(self):
        super().__init__()
        self.setFixedHeight(300)
        self._index = 0
        self._started = time.monotonic()

        self._title = label(name="h1", wrap=True)
        self._text = label(name="bannerText", wrap=True)
        self._button = primary("")
        self._button.clicked.connect(lambda: self.action.emit(SLIDES[self._index][3]))

        self._dots = []
        dots = QHBoxLayout()
        dots.setSpacing(8)
        for index in range(len(SLIDES)):
            dot = primary("")
            dot.setObjectName("dot")
            dot.setCheckable(True)
            dot.setToolTip(f"Slide {index + 1}")
            dot.clicked.connect(lambda _=False, i=index: self.show_slide(i))
            self._dots.append(dot)
            dots.addWidget(dot)
        dots.addStretch()

        column = QVBoxLayout()
        column.setContentsMargins(36, 34, 0, 22)
        column.setSpacing(14)
        column.addWidget(self._title)
        column.addWidget(self._text)
        column.addSpacing(6)
        column.addWidget(self._button, 0, Qt.AlignLeft)
        column.addStretch()
        column.addLayout(dots)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(column, 55)
        layout.addStretch(45)  # espaço da arte, desenhada em paintEvent

        self._frames = QTimer(self)
        self._frames.timeout.connect(self.update)
        self._rotation = QTimer(self)
        self._rotation.timeout.connect(lambda: self.show_slide(self._index + 1))
        self.show_slide(0)

    def show_slide(self, index: int) -> None:
        self._index = index % len(SLIDES)
        title, text, button_text, _, _ = SLIDES[self._index]
        self._title.setText(title)
        self._text.setText(text)
        self._button.setText(button_text.upper())
        for position, dot in enumerate(self._dots):
            dot.setChecked(position == self._index)
        self._rotation.start(SLIDE_SECONDS * 1000)
        self.update()

    def showEvent(self, event):
        self._frames.start(33)
        self._rotation.start(SLIDE_SECONDS * 1000)
        super().showEvent(event)

    def hideEvent(self, event):  # não gasta processador com a página escondida
        self._frames.stop()
        self._rotation.stop()
        super().hideEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect())
        clip = QPainterPath()
        clip.addRoundedRect(rect, 8, 8)
        painter.setClipPath(clip)
        gradient = QLinearGradient(rect.topLeft(), rect.topRight())
        gradient.setColorAt(0.0, QColor("#2c2c2c"))
        gradient.setColorAt(0.55, QColor("#242622"))
        gradient.setColorAt(1.0, QColor("#1d2a0c"))
        painter.fillRect(rect, gradient)
        art_rect = QRectF(rect.width() * 0.56, 0, rect.width() * 0.44, rect.height())
        art.paint_art(painter, art_rect, SLIDES[self._index][4], time.monotonic() - self._started)
        painter.end()


class LibraryCard(ClickableCard):
    def __init__(self, entry: LibraryEntry):
        super().__init__()
        self.setFixedSize(QSize(230, 150))
        self.setToolTip(f"Abrir a pasta\n{entry.folder}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(2)
        layout.addWidget(label(entry.sec_code or entry.edinet_code, "bigCode"))
        years = entry.years
        period = "" if not years else str(years[0]) if len(years) == 1 else f"{years[0]}–{years[-1]}"
        layout.addWidget(label(" · ".join(part for part in (entry.edinet_code, period) if part), "muted"))
        layout.addStretch()
        name = label(entry.name, "h3", wrap=True)
        name.setMaximumHeight(40)
        layout.addWidget(name)
        self.clicked.connect(lambda: open_path(entry.folder))


class LinkCard(ClickableCard):
    def __init__(self, icon_name: str, title: str, text: str, url: str):
        super().__init__()
        self.setFixedSize(QSize(230, 120))
        self.setToolTip(url)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(6)
        top = QHBoxLayout()
        picture = QLabel()
        picture.setPixmap(icons.pixmap(icon_name, theme.ACCENT, 22))
        top.addWidget(picture)
        top.addStretch()
        arrow = QLabel()
        arrow.setPixmap(icons.pixmap("external", theme.MUTED, 14))
        top.addWidget(arrow)
        layout.addLayout(top)
        layout.addWidget(label(title, "h3"))
        layout.addWidget(label(text, "muted", wrap=True))
        layout.addStretch()
        self.clicked.connect(lambda: open_url(url))


class HomePage(QWidget):
    def __init__(self, state: AppState, window):
        super().__init__()
        self.setObjectName("page")
        self._state = state
        self._window = window

        area, layout = scroll_page()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(area)

        # Aviso de chave ausente
        self._warning = QFrame()
        self._warning.setObjectName("warningCard")
        row = QHBoxLayout(self._warning)
        row.setContentsMargins(16, 12, 16, 12)
        row.setSpacing(12)
        picture = QLabel()
        picture.setPixmap(icons.pixmap("warning", theme.WARNING, 22))
        row.addWidget(picture)
        row.addWidget(label("<b>Falta a chave da API do EDINET.</b> Sem ela não é possível baixar "
                            "relatórios. A chave é gratuita e fica guardada só no seu computador.", wrap=True), 1)
        configure = primary("Informar a chave")
        configure.clicked.connect(lambda: window.navigate("settings"))
        row.addWidget(configure)
        layout.addWidget(self._warning)

        banner = Banner()
        banner.action.connect(self._banner_action)
        layout.addWidget(banner)

        layout.addSpacing(8)
        layout.addWidget(label("Biblioteca", "h2"))
        self._library_empty = label(
            "As empresas que você baixar aparecem aqui. Clique em um cartão para abrir a pasta.", "muted")
        layout.addWidget(self._library_empty)
        library_host = QWidget()
        self._library = FlowLayout(library_host)
        layout.addWidget(library_host)

        layout.addSpacing(8)
        layout.addWidget(label("Saiba mais", "h2"))
        links_host = QWidget()
        links = FlowLayout(links_host)
        for item in (
            ("doc", "Portal EDINET", "Consulta pública dos documentos arquivados.", EDINET_PORTAL_URL),
            ("code", "API do EDINET", "Documentação oficial e cadastro da chave.", EDINET_API_URL),
            ("list", "Lista de empresas", "Códigos EDINET de todas as empresas.", CODELIST_PAGE),
            ("external", "Código-fonte", "Software livre no GitHub, licença GPL-3.0.", GITHUB_URL),
        ):
            links.addWidget(LinkCard(*item))
        layout.addWidget(links_host)
        layout.addStretch()

        state.config_changed.connect(self.refresh)
        state.library_changed.connect(self.refresh)
        self.refresh()

    def _banner_action(self, action: str) -> None:
        if action == "folder":
            folder = self._state.config.output_path
            folder.mkdir(parents=True, exist_ok=True)
            open_path(folder)
        else:
            self._window.navigate(action)

    def refresh(self) -> None:
        self._warning.setVisible(not self._state.config.has_key)
        entries = list_library(self._state.config.output_path)
        self._library.clear()
        for entry in entries:
            self._library.addWidget(LibraryCard(entry))
        self._library_empty.setVisible(not entries)
