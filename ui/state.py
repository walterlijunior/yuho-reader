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

"""Dados compartilhados entre as páginas e as tarefas que rodam em segundo plano."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, QThread, Signal

from core import companies as companies_mod
from core.api import Cancelled, EdinetClient, EdinetError
from core.config import Config, cache_dir, load_config, save_config
from core.job import JobOptions, run_job


class TaskWorker(QThread):
    """Roda uma função qualquer fora da janela principal."""

    done = Signal(object)
    failed = Signal(str)

    def __init__(self, function: Callable[[], object], parent=None):
        super().__init__(parent)
        self._function = function

    def run(self):
        try:
            self.done.emit(self._function())
        except EdinetError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # nunca derruba o programa
            self.failed.emit(f"Erro inesperado: {exc}")


class JobWorker(QThread):
    """Busca, download e planilha de uma empresa, com progresso e cancelamento."""

    progress = Signal(int, str)
    log = Signal(str)
    succeeded = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, config: Config, options: JobOptions, parent=None):
        super().__init__(parent)
        self._api_key = config.api_key
        self._pause = config.pause
        self._options = options
        self._cancel = threading.Event()

    def cancel(self):
        self._cancel.set()

    def run(self):
        client = EdinetClient(self._api_key, pause=self._pause, cache_dir=cache_dir(), cancel_event=self._cancel)
        try:
            result = run_job(client, self._options, on_progress=self.progress.emit, on_log=self.log.emit)
        except Cancelled:
            self.cancelled.emit()
        except EdinetError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:
            self.failed.emit(f"Erro inesperado: {exc}")
        else:
            self.succeeded.emit(result)


class AppState(QObject):
    config_changed = Signal()
    companies_changed = Signal()
    library_changed = Signal()
    codelist_busy = Signal(bool)
    codelist_failed = Signal(str)

    def __init__(self):
        super().__init__()
        self.config: Config = load_config()
        self.companies: list[companies_mod.Company] = companies_mod.load_companies()
        self._codelist_worker: TaskWorker | None = None

    def save(self) -> None:
        save_config(self.config)
        self.config_changed.emit()

    # ------------------------------------------------- lista de empresas

    @property
    def codelist_running(self) -> bool:
        return self._codelist_worker is not None

    def update_codelist(self) -> None:
        self._run_codelist(companies_mod.download_codelist)

    def import_codelist(self, path: Path) -> None:
        self._run_codelist(lambda: companies_mod.import_codelist(path))

    def _run_codelist(self, function: Callable[[], list]) -> None:
        if self._codelist_worker is not None:
            return
        worker = TaskWorker(function, self)
        self._codelist_worker = worker
        worker.done.connect(self._codelist_done)
        worker.failed.connect(self.codelist_failed)
        worker.finished.connect(self._codelist_finished)
        self.codelist_busy.emit(True)
        worker.start()

    def _codelist_done(self, companies: list) -> None:
        self.companies = companies
        self.companies_changed.emit()

    def _codelist_finished(self) -> None:
        worker, self._codelist_worker = self._codelist_worker, None
        if worker is not None:
            worker.deleteLater()
        self.codelist_busy.emit(False)
