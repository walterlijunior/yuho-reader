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

"""Página Configurações: chave da API, pasta de saída, lista de empresas, pausa, cache e Sobre."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDoubleSpinBox, QFileDialog, QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout, QWidget

from core import APP_NAME, COPYRIGHT, EDINET_KEY_URL, LICENSE, __version__
from core.api import EdinetClient
from core.companies import codelist_updated_at
from core.config import cache_size, clear_cache, default_output_dir

from . import icons, theme
from .state import AppState, TaskWorker
from .widgets import button, card, confirm, label, link, open_path, open_url, primary, scroll_page


class SettingsPage(QWidget):
    def __init__(self, state: AppState, window):
        super().__init__()
        self.setObjectName("page")
        self._state = state
        self._test_worker: TaskWorker | None = None

        area, layout = scroll_page(max_width=900)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(area)

        # ------------------------------------------------------ chave da API
        frame, box = card()
        layout.addWidget(frame)
        box.addWidget(label("Chave da API do EDINET", "h2"))
        box.addWidget(label(
            "A chave é gratuita e identifica você no EDINET. Ela fica guardada somente neste computador "
            "e nunca é enviada a outro lugar além do próprio EDINET.", "muted", wrap=True))
        row = QHBoxLayout()
        row.setSpacing(8)
        self._key = QLineEdit(state.config.api_key)
        self._key.setEchoMode(QLineEdit.Password)
        self._key.setPlaceholderText("Cole aqui a sua chave (Subscription-Key)")
        self._key.returnPressed.connect(self._save_key)
        row.addWidget(self._key, 1)
        self._eye = QPushButton()
        self._eye.setObjectName("iconButton")
        self._eye.setCheckable(True)
        self._eye.setToolTip("Mostrar ou ocultar a chave")
        self._eye.setIcon(icons.icon("eye", theme.TEXT, 18))
        self._eye.toggled.connect(self._toggle_key)
        row.addWidget(self._eye)
        save = primary("Salvar")
        save.clicked.connect(self._save_key)
        row.addWidget(save)
        self._test = button("Testar")
        self._test.clicked.connect(self._test_key)
        row.addWidget(self._test)
        box.addLayout(row)
        row = QHBoxLayout()
        self._key_status = label("", "muted", wrap=True)
        row.addWidget(self._key_status, 1)
        how = link("Como obter a chave")
        how.clicked.connect(lambda: open_url(EDINET_KEY_URL))
        row.addWidget(how)
        box.addLayout(row)

        # ----------------------------------------------------- pasta de saída
        frame, box = card()
        layout.addWidget(frame)
        box.addWidget(label("Pasta de saída", "h2"))
        box.addWidget(label("Onde ficam as planilhas e os arquivos baixados, uma pasta por empresa.", "muted"))
        row = QHBoxLayout()
        row.setSpacing(8)
        self._folder = QLineEdit()
        self._folder.setReadOnly(True)
        row.addWidget(self._folder, 1)
        choose = button("Escolher")
        choose.clicked.connect(self._choose_folder)
        row.addWidget(choose)
        open_button = button("Abrir", "folder")
        open_button.clicked.connect(self._open_folder)
        row.addWidget(open_button)
        default = button("Padrão")
        default.setToolTip(str(default_output_dir()))
        default.clicked.connect(lambda: self._set_folder(""))
        row.addWidget(default)
        box.addLayout(row)

        # -------------------------------------------------- lista de empresas
        frame, box = card()
        layout.addWidget(frame)
        box.addWidget(label("Lista de empresas", "h2"))
        self._codelist_status = label("", "muted", wrap=True)
        box.addWidget(self._codelist_status)
        row = QHBoxLayout()
        row.setSpacing(8)
        self._update = button("Atualizar agora", "download")
        self._update.clicked.connect(state.update_codelist)
        row.addWidget(self._update)
        self._import = button("Importar arquivo")
        self._import.setToolTip("Use se o download automático falhar: escolha o Edinetcode.zip ou o CSV.")
        self._import.clicked.connect(self._import_codelist)
        row.addWidget(self._import)
        row.addStretch()
        box.addLayout(row)

        # --------------------------------------------------- pausa e cache
        frame, box = card()
        layout.addWidget(frame)
        box.addWidget(label("Consultas ao EDINET", "h2"))
        row = QHBoxLayout()
        row.addWidget(label("Pausa entre chamadas (segundos). Valores maiores são mais gentis com o "
                            "EDINET; menores, mais rápidos.", "muted", wrap=True), 1)
        self._pause = QDoubleSpinBox()
        self._pause.setRange(0.0, 10.0)
        self._pause.setSingleStep(0.1)
        self._pause.setDecimals(1)
        self._pause.setFixedWidth(90)
        self._pause.setAlignment(Qt.AlignCenter)
        self._pause.setValue(state.config.pause)
        self._pause.valueChanged.connect(self._pause_changed)
        row.addWidget(self._pause)
        box.addLayout(row)
        row = QHBoxLayout()
        self._cache_status = label("", "muted", wrap=True)
        row.addWidget(self._cache_status, 1)
        clear = button("Limpar cache")
        clear.clicked.connect(self._clear_cache)
        row.addWidget(clear)
        box.addLayout(row)

        # ------------------------------------------------------------ sobre
        frame, box = card()
        layout.addWidget(frame)
        box.addWidget(label("Sobre", "h2"))
        box.addWidget(label(f"<b>{APP_NAME}</b> — versão {__version__}"))
        box.addWidget(label(
            f"{COPYRIGHT}. Software livre sob a licença {LICENSE}: você pode usar, estudar, modificar e "
            "redistribuir, sem nenhuma garantia.<br>"
            "Os dados vêm do EDINET, mantido pela Financial Services Agency (FSA) do Japão. O Yuho Reader "
            "não é um programa oficial e não tem ligação com a FSA nem com o EDINET: ele só lê e baixa "
            "documentos públicos.", "muted", wrap=True))
        layout.addStretch()

        state.companies_changed.connect(self._refresh_codelist)
        state.codelist_busy.connect(self._codelist_busy)
        state.codelist_failed.connect(lambda error: self._codelist_status.setText(error))
        self._refresh_folder()
        self._refresh_codelist()

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_cache()

    # -------------------------------------------------------------- chave

    def _toggle_key(self, visible: bool) -> None:
        self._key.setEchoMode(QLineEdit.Normal if visible else QLineEdit.Password)
        self._eye.setIcon(icons.icon("eye_off" if visible else "eye", theme.TEXT, 18))

    def _set_key_status(self, text: str, name: str = "muted") -> None:
        self._key_status.setObjectName(name)
        self._key_status.style().unpolish(self._key_status)
        self._key_status.style().polish(self._key_status)
        self._key_status.setText(text)

    def _save_key(self) -> None:
        self._state.config.api_key = self._key.text().strip()
        self._state.save()
        self._set_key_status("Chave salva." if self._state.config.has_key else "Chave removida.", "ok")

    def _test_key(self) -> None:
        key = self._key.text().strip()
        if not key:
            self._set_key_status("Cole a chave antes de testar.", "error")
            return
        if self._test_worker is not None:
            return
        self._test.setEnabled(False)
        self._set_key_status("Testando a chave no EDINET...")
        worker = TaskWorker(lambda: EdinetClient(key, pause=0, max_tries=2).test_key(), self)
        self._test_worker = worker
        worker.done.connect(lambda _: self._set_key_status("Chave válida: o EDINET aceitou.", "ok"))
        worker.failed.connect(lambda error: self._set_key_status(error, "error"))
        worker.finished.connect(self._test_finished)
        worker.start()

    def _test_finished(self) -> None:
        worker, self._test_worker = self._test_worker, None
        if worker is not None:
            worker.deleteLater()
        self._test.setEnabled(True)

    # -------------------------------------------------------------- pasta

    def _refresh_folder(self) -> None:
        self._folder.setText(str(self._state.config.output_path))

    def _set_folder(self, folder: str) -> None:
        self._state.config.output_dir = folder
        self._state.save()
        self._refresh_folder()
        self._state.library_changed.emit()

    def _choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Escolha a pasta de saída", str(self._state.config.output_path))
        if folder:
            self._set_folder(str(Path(folder)))

    def _open_folder(self) -> None:
        folder = self._state.config.output_path
        folder.mkdir(parents=True, exist_ok=True)
        open_path(folder)

    # ---------------------------------------------------- lista de empresas

    def _refresh_codelist(self) -> None:
        total = len(self._state.companies)
        updated = codelist_updated_at()
        if total and updated:
            count = f"{total:,}".replace(",", ".")
            self._codelist_status.setText(f"{count} empresas. Atualizada em {updated:%d/%m/%Y às %H:%M}.")
        else:
            self._codelist_status.setText("A lista ainda não foi baixada. Ela é pública e não usa a chave.")

    def _codelist_busy(self, busy: bool) -> None:
        self._update.setEnabled(not busy)
        self._import.setEnabled(not busy)
        if busy:
            self._codelist_status.setText("Atualizando a lista de empresas...")

    def _import_codelist(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Importar lista de empresas", str(Path.home() / "Downloads"), "Lista do EDINET (*.zip *.csv)")
        if path:
            self._state.import_codelist(Path(path))

    # ------------------------------------------------------ pausa e cache

    def _pause_changed(self, value: float) -> None:
        self._state.config.pause = round(value, 1)
        self._state.save()

    def _refresh_cache(self) -> None:
        files, size = cache_size()
        if files:
            self._cache_status.setText(
                f"Cache: {files} dia(s) guardado(s), {size / 1_048_576:.1f} MB. "
                "Graças a ele, repetir uma busca é instantâneo.")
        else:
            self._cache_status.setText("Cache vazio. Ele guarda a lista de documentos de cada dia já consultado.")

    def _clear_cache(self) -> None:
        if confirm(self, "Limpar cache", "Apagar o cache? As próximas buscas voltarão a consultar o EDINET."):
            clear_cache()
            self._refresh_cache()
