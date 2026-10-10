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

"""Página Downloads: progresso da tarefa, botões de ação e registro."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import QHBoxLayout, QPlainTextEdit, QProgressBar, QVBoxLayout, QWidget

from core.config import Config
from core.job import JobOptions, JobResult, company_folder

from .state import AppState, JobWorker
from .widgets import FlowLayout, button, card, chip, label, open_path, primary


class DownloadsPage(QWidget):
    def __init__(self, state: AppState, window):
        super().__init__()
        self.setObjectName("page")
        self._state = state
        self._worker: JobWorker | None = None
        self._result: JobResult | None = None
        self._folder = None

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        frame, layout = card(margins=24, spacing=12)
        root.addWidget(frame)
        self._name = label("Nenhum download em andamento", "h2", wrap=True)
        layout.addWidget(self._name)
        chips_host = QWidget()
        self._chips = FlowLayout(chips_host, spacing=6)
        layout.addWidget(chips_host)
        self._bar = QProgressBar()
        self._bar.setTextVisible(False)
        self._bar.setRange(0, 100)
        layout.addSpacing(4)
        layout.addWidget(self._bar)
        status_row = QHBoxLayout()
        self._status = label("Escolha uma empresa na página Empresas e clique em BAIXAR.", "muted", wrap=True)
        self._percent = label("", "muted")
        status_row.addWidget(self._status, 1)
        status_row.addWidget(self._percent)
        layout.addLayout(status_row)
        layout.addSpacing(4)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        self._cancel = button("Cancelar")
        self._open_workbook = primary("Abrir planilha")
        self._open_folder = button("Abrir pasta", "folder")
        self._new_search = button("Nova busca", "search")
        self._cancel.clicked.connect(self.cancel)
        self._open_workbook.clicked.connect(self._open_result)
        self._open_folder.clicked.connect(lambda: self._folder and open_path(self._folder))
        self._new_search.clicked.connect(lambda: window.navigate("companies"))
        for widget in (self._cancel, self._open_workbook, self._open_folder):
            buttons.addWidget(widget)
        buttons.addStretch()
        buttons.addWidget(self._new_search)
        layout.addLayout(buttons)

        root.addWidget(label("REGISTRO", "section"))
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(5000)
        self._log.setPlaceholderText("O passo a passo da busca e dos downloads aparece aqui.")
        root.addWidget(self._log, 1)
        self._set_running(False)

    # ---------------------------------------------------------------- estado

    @property
    def running(self) -> bool:
        return self._worker is not None

    def _set_running(self, running: bool) -> None:
        self._cancel.setEnabled(running)
        self._new_search.setEnabled(not running)
        self._open_workbook.setEnabled(bool(not running and self._result and self._result.workbook))
        self._open_folder.setEnabled(bool(not running and self._folder and self._folder.is_dir()))

    def _write(self, text: str) -> None:
        self._log.appendPlainText(f"{datetime.now():%H:%M:%S}  {text}")

    # ---------------------------------------------------------------- tarefa

    def start(self, config: Config, options: JobOptions) -> None:
        company = options.company
        self._result = None
        self._folder = company_folder(options.output_dir, company)
        self._name.setText(company.display_name)
        self._chips.clear()
        self._chips.addWidget(chip(company.edinet_code, accent=True))
        if company.sec_code:
            self._chips.addWidget(chip(f"Bolsa {company.sec_code}"))
        if company.industry:
            self._chips.addWidget(chip(company.industry))
        self._chips.addWidget(chip(f"{len(options.fiscal_year_ends)} exercício(s)"))
        self._log.clear()
        self._on_progress(0, "Iniciando...")

        worker = JobWorker(config, options, self)
        self._worker = worker
        worker.progress.connect(self._on_progress)
        worker.log.connect(self._write)
        worker.succeeded.connect(self._on_success)
        worker.failed.connect(self._on_failure)
        worker.cancelled.connect(self._on_cancelled)
        worker.finished.connect(self._on_finished)
        self._set_running(True)
        worker.start()

    def cancel(self) -> None:
        if self._worker is not None:
            self._cancel.setEnabled(False)
            self._status.setText("Cancelando...")
            self._worker.cancel()

    def wait(self, milliseconds: int = 5000) -> None:
        if self._worker is not None:
            self._worker.wait(milliseconds)

    def _on_progress(self, percent: int, status: str) -> None:
        self._bar.setValue(percent)
        self._percent.setText(f"{percent}%")
        self._status.setObjectName("muted")
        self._restyle(self._status)
        self._status.setText(status)

    def _restyle(self, widget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _finish_status(self, text: str, name: str) -> None:
        self._status.setObjectName(name)
        self._restyle(self._status)
        self._status.setText(text)

    def _on_success(self, result: JobResult) -> None:
        self._result = result
        self._folder = result.folder
        if result.workbook is None:
            self._finish_status("Nenhum relatório encontrado para os exercícios escolhidos.", "error")
            return
        text = f"Concluído: {len(result.reports)} relatório(s) na planilha."
        if result.missing:
            text += f" Não encontrados: {', '.join(result.missing)}."
        self._finish_status(text, "ok")

    def _on_failure(self, error: str) -> None:
        self._write(f"ERRO: {error}")
        self._finish_status(error, "error")

    def _on_cancelled(self) -> None:
        self._write("Cancelado pelo usuário.")
        self._finish_status("Cancelado. O que já foi baixado continua guardado.", "muted")

    def _on_finished(self) -> None:
        worker, self._worker = self._worker, None
        if worker is not None:
            worker.deleteLater()
        self._set_running(False)
        self._state.library_changed.emit()

    def _open_result(self) -> None:
        if self._result and self._result.workbook:
            open_path(self._result.workbook)
