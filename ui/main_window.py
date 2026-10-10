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

"""Janela principal: barra lateral, cabeçalho e as páginas."""

from __future__ import annotations

from PySide6.QtCore import QRect, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QAbstractButton, QButtonGroup, QFrame, QHBoxLayout, QMainWindow, QPushButton, QStackedWidget,
    QVBoxLayout, QWidget,
)

from core import APP_NAME, GITHUB_URL
from core.job import JobOptions

from . import icons, theme
from .page_companies import CompaniesPage
from .page_downloads import DownloadsPage
from .page_home import HomePage
from .page_settings import SettingsPage
from .state import AppState
from .widgets import confirm, label, message, open_url

PAGES = (
    ("home", "Início", "home"),
    ("companies", "Empresas", "building"),
    ("downloads", "Downloads", "download"),
    ("settings", "Configurações", "gear"),
)

HELP_TEXT = """
<h3>Como usar</h3>
<ol style="margin-left:-18px">
<li style="margin-bottom:6px">Em <b>Configurações</b>, cole a sua chave da API do EDINET e clique em SALVAR.</li>
<li style="margin-bottom:6px">Em <b>Empresas</b>, pesquise pelo nome, pelo código da bolsa (ex.: 9697)
ou pelo código EDINET (ex.: E02417).</li>
<li style="margin-bottom:6px">Marque os exercícios, os tipos de relatório e os formatos; depois clique em BAIXAR.</li>
<li style="margin-bottom:6px">Acompanhe em <b>Downloads</b>. Ao terminar, clique em ABRIR PLANILHA.</li>
</ol>
<p><b>Por que demora?</b> O EDINET não tem busca por empresa: o programa consulta a lista de documentos
de cada dia do prazo legal. Os dias já consultados ficam guardados, então repetir é instantâneo.</p>
<p><b>A planilha</b> tem as abas INDICE (os relatórios), PAINEL (contas lado a lado),
DEMONSTRACOES (formato longo) e uma aba com todos os dados de cada relatório.</p>
"""


class NavButton(QAbstractButton):
    """Item da barra lateral: ícone em cima, texto embaixo, faixa verde quando ativo."""

    def __init__(self, text: str, icon_name: str):
        super().__init__()
        self._icon = icon_name
        self.setText(text)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover)
        self.setFixedSize(QSize(100, 78))
        self.setToolTip(text)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        active, hover = self.isChecked(), self.underMouse()
        if active or hover:
            painter.fillRect(self.rect(), QColor("#2b2b2b" if active else "#262626"))
        if active:
            painter.fillRect(QRect(0, 0, 4, self.height()), QColor(theme.ACCENT))
        icon_color = theme.ACCENT if active else (theme.TEXT if hover else theme.MUTED)
        icons.paint_icon(painter, self._icon, QRectF((self.width() - 26) / 2, 15, 26, 26), icon_color)
        font = QFont(theme.FONT)
        font.setPixelSize(11)
        font.setWeight(QFont.DemiBold if active else QFont.Normal)
        painter.setFont(font)
        painter.setPen(QColor("#ffffff" if active else (theme.TEXT if hover else theme.MUTED)))
        painter.drawText(QRect(0, 47, self.width(), 20), Qt.AlignCenter, self.text())
        painter.end()


class MainWindow(QMainWindow):
    def __init__(self, state: AppState | None = None):
        super().__init__()
        self.state = state or AppState()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(icons.app_icon())
        self.resize(1200, 780)
        self.setMinimumSize(1000, 660)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ------------------------------------------------------ barra lateral
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(100)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(0, 10, 0, 10)
        side.setSpacing(2)
        self._nav: dict[str, NavButton] = {}
        group = QButtonGroup(self)
        for name, title, icon_name in PAGES:
            nav = NavButton(title, icon_name)
            nav.clicked.connect(lambda _=False, n=name: self.navigate(n))
            group.addButton(nav)
            self._nav[name] = nav
            if name == "settings":
                side.addStretch()
            side.addWidget(nav)
        root.addWidget(sidebar)

        # ---------------------------------------------------------- cabeçalho
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)
        root.addLayout(right, 1)
        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(58)
        bar = QHBoxLayout(header)
        bar.setContentsMargins(28, 0, 18, 0)
        self._title = label("", "headerTitle")
        bar.addWidget(self._title)
        bar.addStretch()
        for text, icon_name, action in (
            ("GitHub", "code", lambda: open_url(GITHUB_URL)),
            ("Ajuda", "help", self.show_help),
        ):
            flat = QPushButton(f" {text}")
            flat.setObjectName("flat")
            flat.setCursor(Qt.PointingHandCursor)
            flat.setIcon(icons.icon(icon_name, theme.MUTED, 18))
            flat.clicked.connect(action)
            bar.addWidget(flat)
        right.addWidget(header)

        # ------------------------------------------------------------ páginas
        self._stack = QStackedWidget()
        right.addWidget(self._stack, 1)
        self.downloads = DownloadsPage(self.state, self)
        self._pages = {
            "home": HomePage(self.state, self),
            "companies": CompaniesPage(self.state, self),
            "downloads": self.downloads,
            "settings": SettingsPage(self.state, self),
        }
        for name, _, _ in PAGES:
            self._stack.addWidget(self._pages[name])
        self.navigate("home")

        # A lista de empresas é pública: na primeira vez, já baixa sozinha.
        if not self.state.companies:
            self.state.update_codelist()

    def showEvent(self, event):
        super().showEvent(event)
        theme.dark_titlebar(self)

    def navigate(self, name: str) -> None:
        if name not in self._pages:
            return
        self._stack.setCurrentWidget(self._pages[name])
        self._nav[name].setChecked(True)
        self._title.setText(next(title for key, title, _ in PAGES if key == name))

    def show_help(self) -> None:
        message(self, "Ajuda", HELP_TEXT, "none")

    def start_job(self, options: JobOptions) -> None:
        if self.downloads.running:
            message(self, "Download em andamento",
                    "Já existe um download em andamento. Espere terminar ou cancele-o na página Downloads.", "warning")
            self.navigate("downloads")
            return
        if not self.state.config.has_key:
            message(self, "Falta a chave da API",
                    "Para baixar relatórios é preciso informar a chave da API do EDINET.<br>"
                    "Cole a chave em <b>Configurações</b> e clique em SALVAR.", "warning")
            self.navigate("settings")
            return
        self.navigate("downloads")
        self.downloads.start(self.state.config, options)

    def closeEvent(self, event):
        if self.downloads.running:
            if not confirm(self, "Sair", "Há um download em andamento. Cancelar e sair?"):
                event.ignore()
                return
            self.downloads.cancel()
            self.downloads.wait()
        super().closeEvent(event)
