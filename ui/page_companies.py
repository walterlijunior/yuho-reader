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

"""Página Empresas: pesquisa, escolha dos exercícios e botão BAIXAR."""

from __future__ import annotations

import re
from datetime import date

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QScrollArea, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from core.api import day_cache_path, today_jst
from core.companies import Company, search
from core.config import cache_dir
from core.job import JobOptions
from core.periods import build_targets, clamp_date, estimate, last_fiscal_years

from . import icons, theme
from .state import AppState
from .widgets import FlowLayout, button, card, chip, label, primary, separator

DEFAULT_YEARS = 3
_FISCAL_END = re.compile(r"\s*(\d{1,2})\s*/\s*(\d{1,2})\s*")


class CompaniesPage(QWidget):
    def __init__(self, state: AppState, window):
        super().__init__()
        self.setObjectName("page")
        self._state = state
        self._window = window
        self._results: list[Company] = []
        self._company: Company | None = None
        self._fiscal_end = (3, 31)
        self._year_boxes: list[tuple[QCheckBox, date]] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)

        # ------------------------------------------------------------ busca
        top = QHBoxLayout()
        top.setSpacing(16)
        self._search = QLineEdit()
        self._search.setObjectName("searchBox")
        self._search.setPlaceholderText("Nome em inglês ou japonês, código da bolsa (9697) ou código EDINET (E02417)")
        self._search.setClearButtonEnabled(True)
        self._search.addAction(icons.icon("search", theme.MUTED, 18), QLineEdit.LeadingPosition)
        top.addWidget(self._search, 1)
        self._listed_only = QCheckBox("Só listadas em bolsa")
        self._listed_only.setChecked(True)
        top.addWidget(self._listed_only)
        root.addLayout(top)

        self._notice = QFrame()
        self._notice.setObjectName("warningCard")
        notice_row = QHBoxLayout(self._notice)
        notice_row.setContentsMargins(16, 10, 16, 10)
        self._notice_text = label(wrap=True)
        notice_row.addWidget(self._notice_text, 1)
        self._notice_button = primary("Baixar lista de empresas")
        self._notice_button.clicked.connect(state.update_codelist)
        notice_row.addWidget(self._notice_button)
        root.addWidget(self._notice)

        body = QHBoxLayout()
        body.setSpacing(18)
        root.addLayout(body, 1)

        # ---------------------------------------------------------- tabela
        left = QVBoxLayout()
        left.setSpacing(8)
        self._status = label("", "muted")
        left.addWidget(self._status)
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Bolsa", "Empresa", "Setor", "EDINET"])
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(34)
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setFocusPolicy(Qt.StrongFocus)
        header = self._table.horizontalHeader()
        header.setHighlightSections(False)
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        left.addWidget(self._table, 1)
        body.addLayout(left, 1)

        # ---------------------------------------------------------- painel
        panel_area = QScrollArea()
        panel_area.setWidgetResizable(True)
        panel_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        panel_area.setFixedWidth(410)
        panel_area.setStyleSheet("QScrollArea { background: transparent; }")
        panel, layout = card(margins=22, spacing=10)
        panel_area.setWidget(panel)
        body.addWidget(panel_area)

        self._empty = label("Pesquise e escolha uma empresa na tabela ao lado para ver as opções de download.",
                            "muted", wrap=True)
        self._empty.setAlignment(Qt.AlignCenter)
        self._empty.setMinimumHeight(200)
        layout.addWidget(self._empty)

        self._details = QWidget()
        details = QVBoxLayout(self._details)
        details.setContentsMargins(0, 0, 0, 0)
        details.setSpacing(10)
        layout.addWidget(self._details)
        layout.addStretch()

        self._name = label(name="h2", wrap=True)
        self._name_jp = label(name="muted", wrap=True)
        details.addWidget(self._name)
        details.addWidget(self._name_jp)
        chips_host = QWidget()
        self._chips = FlowLayout(chips_host, spacing=6)
        details.addWidget(chips_host)
        details.addWidget(separator())

        row = QHBoxLayout()
        row.addWidget(label("ENCERRAMENTO DO EXERCÍCIO", "section"))
        row.addStretch()
        self._fiscal_edit = QLineEdit()
        self._fiscal_edit.setFixedWidth(80)
        self._fiscal_edit.setAlignment(Qt.AlignCenter)
        self._fiscal_edit.setToolTip("Dia/mês em que o exercício social termina. Ex.: 31/03")
        self._fiscal_edit.editingFinished.connect(self._fiscal_edited)
        row.addWidget(self._fiscal_edit)
        details.addLayout(row)

        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(label("EXERCÍCIOS", "section"))
        row.addStretch()
        for text, count in (("Últimos 5", 5), ("Todos", 12), ("Nenhum", 0)):
            shortcut = button(text)
            shortcut.setObjectName("flat")
            shortcut.setText(text)
            shortcut.clicked.connect(lambda _=False, n=count: self._check_years(n))
            row.addWidget(shortcut)
        details.addLayout(row)
        self._years_grid = QGridLayout()
        self._years_grid.setHorizontalSpacing(10)
        self._years_grid.setVerticalSpacing(8)
        details.addLayout(self._years_grid)
        details.addWidget(separator())

        details.addWidget(label("TIPOS DE RELATÓRIO", "section"))
        self._annual = QCheckBox("Anual (有価証券報告書)")
        self._annual.setChecked(True)
        self._semiannual = QCheckBox("Semestral (半期報告書)")
        self._amendments = QCheckBox("Incluir retificações")
        self._amendments.setToolTip("Procura também as versões corrigidas. A busca demora mais.")
        for box in (self._annual, self._semiannual, self._amendments):
            box.toggled.connect(self._update_estimate)
            details.addWidget(box)
        details.addWidget(separator())

        details.addWidget(label("FORMATOS", "section"))
        formats = QHBoxLayout()
        self._csv = QCheckBox("CSV")
        self._csv.setChecked(True)
        self._csv.setEnabled(False)
        self._csv.setToolTip("Sempre baixado: é dele que sai a planilha.")
        self._xbrl = QCheckBox("XBRL")
        self._pdf = QCheckBox("PDF")
        self._pdf.setChecked(True)
        for box in (self._csv, self._xbrl, self._pdf):
            formats.addWidget(box)
        formats.addStretch()
        details.addLayout(formats)
        details.addWidget(separator())

        self._estimate = label(name="muted", wrap=True)
        details.addWidget(self._estimate)
        self._download = primary("Baixar")
        self._download.setMinimumHeight(42)
        self._download.clicked.connect(self._start)
        details.addWidget(self._download)

        # ----------------------------------------------------------- sinais
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(180)
        self._timer.timeout.connect(self._run_search)
        self._search.textChanged.connect(lambda: self._timer.start())
        self._search.returnPressed.connect(self._run_search)
        self._listed_only.toggled.connect(self._run_search)
        self._table.itemSelectionChanged.connect(self._selection_changed)
        self._table.itemDoubleClicked.connect(lambda: self._download.setFocus())
        state.companies_changed.connect(self._companies_changed)
        state.codelist_busy.connect(lambda busy: self._companies_changed())
        state.codelist_failed.connect(self._codelist_failed)

        self._show_company(None)
        self._companies_changed()

    # ------------------------------------------------------------------ busca

    def showEvent(self, event):
        super().showEvent(event)
        self._search.setFocus()
        self._update_estimate()

    def _companies_changed(self) -> None:
        loaded = bool(self._state.companies)
        busy = self._state.codelist_running
        self._notice.setVisible(not loaded)
        self._notice_button.setEnabled(not busy)
        self._notice_text.setText(
            "Baixando a lista de empresas do EDINET..." if busy else
            "A lista de empresas ainda não foi baixada. Sem ela, a pesquisa só aceita o código EDINET (ex.: E02417)."
        )
        self._run_search()

    def _codelist_failed(self, error: str) -> None:
        self._notice_text.setText(f"{error} Tente de novo ou importe o arquivo em Configurações.")

    def _run_search(self) -> None:
        self._timer.stop()
        term = self._search.text().strip()
        self._results = search(self._state.companies, term, self._listed_only.isChecked())
        self._table.setRowCount(len(self._results))
        for row, company in enumerate(self._results):
            name = company.name_en or company.name_jp or "Empresa fora da lista"
            if company.name_en and company.name_jp:
                name = f"{company.name_en}  ·  {company.name_jp}"
            for column, text in enumerate((company.sec_code, name, company.industry, company.edinet_code)):
                item = QTableWidgetItem(text)
                item.setToolTip(text)
                self._table.setItem(row, column, item)
        if not term:
            total = len(self._state.companies)
            self._status.setText(f"{total:,} empresas na lista. Digite para pesquisar.".replace(",", ".")
                                 if total else "Digite um código EDINET para continuar.")
        elif not self._results:
            self._status.setText("Nenhuma empresa encontrada. Tente desmarcar “Só listadas em bolsa”.")
        else:
            count = len(self._results)
            self._status.setText(f"{count} resultado{'s' if count != 1 else ''}"
                                 + (" (mostrando os 200 primeiros)" if count >= 200 else ""))
        if len(self._results) == 1:
            self._table.selectRow(0)

    def _selection_changed(self) -> None:
        rows = self._table.selectionModel().selectedRows()
        if rows and rows[0].row() < len(self._results):
            self._show_company(self._results[rows[0].row()])

    # ----------------------------------------------------------------- painel

    def _show_company(self, company: Company | None) -> None:
        self._company = company
        self._empty.setVisible(company is None)
        self._details.setVisible(company is not None)
        if company is None:
            return
        self._name.setText(company.name_en or company.name_jp or company.edinet_code)
        self._name_jp.setText(company.name_jp if company.name_en else "")
        self._name_jp.setVisible(bool(company.name_en and company.name_jp))
        self._chips.clear()
        self._chips.addWidget(chip(company.edinet_code, accent=True))
        if company.sec_code:
            self._chips.addWidget(chip(f"Bolsa {company.sec_code}"))
        if company.industry:
            self._chips.addWidget(chip(company.industry))
        if company.manual:
            self._chips.addWidget(chip("Fora da lista"))
        elif not company.listed:
            self._chips.addWidget(chip("Não listada"))
        self._fiscal_end = company.fiscal_end
        self._rebuild_years()

    def _fiscal_text(self) -> str:
        month, day = self._fiscal_end
        shown = clamp_date(2025, month, day)  # "fim do mês" aparece como o último dia
        return f"{shown.day:02d}/{shown.month:02d}"

    def _fiscal_edited(self) -> None:
        match = _FISCAL_END.fullmatch(self._fiscal_edit.text())
        if match:
            day, month = int(match.group(1)), int(match.group(2))
            if 1 <= month <= 12 and 1 <= day <= 31:
                last_day = clamp_date(2025, month, 31).day
                new_end = (month, 31 if day >= last_day else day)
                if new_end != self._fiscal_end:
                    self._fiscal_end = new_end
                    self._rebuild_years()
                    return
        self._fiscal_edit.setText(self._fiscal_text())

    def _rebuild_years(self) -> None:
        self._fiscal_edit.setText(self._fiscal_text())
        while self._years_grid.count():
            widget = self._years_grid.takeAt(0).widget()
            if widget is not None:
                widget.deleteLater()
        self._year_boxes = []
        for index, end in enumerate(last_fiscal_years(*self._fiscal_end, today_jst())):
            box = QCheckBox(f"{end:%m/%Y}")
            box.setToolTip(f"Exercício encerrado em {end:%d/%m/%Y}")
            box.setChecked(index < DEFAULT_YEARS)
            box.toggled.connect(self._update_estimate)
            self._year_boxes.append((box, end))
            self._years_grid.addWidget(box, index // 4, index % 4)
        self._update_estimate()

    def _check_years(self, count: int) -> None:
        for index, (box, _) in enumerate(self._year_boxes):
            box.blockSignals(True)
            box.setChecked(index < count)
            box.blockSignals(False)
        self._update_estimate()

    def _selected_years(self) -> list[date]:
        return [end for box, end in self._year_boxes if box.isChecked()]

    def _update_estimate(self) -> None:
        if self._company is None:
            return
        years = self._selected_years()
        targets = build_targets(years, self._annual.isChecked(), self._semiannual.isChecked())
        self._download.setEnabled(bool(targets))
        if not years:
            self._estimate.setText("Marque pelo menos um exercício.")
            return
        if not targets:
            self._estimate.setText("Marque Anual ou Semestral.")
            return
        folder = cache_dir()
        result = estimate(
            targets, self._state.config.pause, today_jst(),
            is_cached=lambda day: day_cache_path(folder, day).is_file(),
            amendments=self._amendments.isChecked(),
        )
        count = len(targets)
        self._estimate.setText(f"{count} relatório{'s' if count != 1 else ''} a procurar. {result.describe()}.")

    def _start(self) -> None:
        if self._company is None:
            return
        company = self._company
        company.fiscal_end = self._fiscal_end
        self._window.start_job(JobOptions(
            company=company,
            fiscal_year_ends=self._selected_years(),
            output_dir=self._state.config.output_path,
            annual=self._annual.isChecked(),
            semiannual=self._semiannual.isChecked(),
            amendments=self._amendments.isChecked(),
            xbrl=self._xbrl.isChecked(),
            pdf=self._pdf.isChecked(),
        ))
