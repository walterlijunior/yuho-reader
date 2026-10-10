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

"""Cliente da API do EDINET (versão 2).

Cuida da pausa entre chamadas, das novas tentativas em erros 429/5xx e do
cache em disco da lista de documentos de cada dia já passado.
"""

from __future__ import annotations

import json
import threading
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

import requests

BASE_URL = "https://api.edinet-fsa.go.jp/api/v2"
PDF_URL = "https://disclosure2dl.edinet-fsa.go.jp/searchdocument/pdf/{doc_id}.pdf"
RETRY_STATUS = {429, 500, 502, 503, 504}
TIMEOUT = 60

TYPE_XBRL = 1
TYPE_PDF = 2
TYPE_CSV = 5

# Só estes tipos de documento interessam; o resto nem vai para o cache.
DOC_TYPES = {"120", "130", "140", "150", "160", "170"}
DOC_FIELDS = (
    "docID", "edinetCode", "secCode", "filerName", "docTypeCode", "docDescription",
    "periodStart", "periodEnd", "submitDateTime", "withdrawalStatus", "parentDocID",
    "xbrlFlag", "pdfFlag", "csvFlag",
)


class EdinetError(Exception):
    """Erro devolvido pelo EDINET ou falha de comunicação."""


class InvalidKeyError(EdinetError):
    """Chave da API ausente ou recusada."""


class Cancelled(Exception):
    """O usuário cancelou a tarefa."""


def today_jst() -> date:
    """Data de hoje no Japão (o EDINET funciona no horário japonês)."""
    return datetime.now(timezone(timedelta(hours=9))).date()


def pdf_link(doc_id: str) -> str:
    return PDF_URL.format(doc_id=doc_id)


def day_cache_path(cache_dir: Path, day: date) -> Path:
    return Path(cache_dir) / "documents" / f"{day.isoformat()}.json"


class EdinetClient:
    def __init__(
        self,
        api_key: str,
        pause: float = 0.5,
        cache_dir: Path | None = None,
        session: requests.Session | None = None,
        cancel_event: threading.Event | None = None,
        sleep: Callable[[float], None] = time.sleep,
        today: Callable[[], date] = today_jst,
        max_tries: int = 4,
        backoff: float = 2.0,
    ):
        self.api_key = (api_key or "").strip()
        self.pause = max(0.0, pause)
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.session = session or requests.Session()
        self.cancel_event = cancel_event
        self.max_tries = max_tries
        self.backoff = backoff
        self._sleep = sleep
        self._today = today
        self._called = False
        self._memory: dict[date, list[dict]] = {}

    # ----------------------------------------------------------- utilidades

    def check_cancel(self) -> None:
        if self.cancel_event is not None and self.cancel_event.is_set():
            raise Cancelled()

    def _wait(self, seconds: float) -> None:
        if seconds <= 0:
            return
        if self.cancel_event is not None:
            if self.cancel_event.wait(seconds):
                raise Cancelled()
        else:
            self._sleep(seconds)

    def is_cached(self, day: date) -> bool:
        if day in self._memory:
            return True
        return bool(self.cache_dir) and day_cache_path(self.cache_dir, day).is_file()

    def _request(self, path: str, params: dict, stream: bool = False) -> requests.Response:
        if not self.api_key:
            raise InvalidKeyError("Falta a chave da API. Informe-a em Configurações.")
        error = ""
        for attempt in range(1, self.max_tries + 1):
            self.check_cancel()
            if self._called:
                self._wait(self.pause)
            self._called = True
            try:
                response = self.session.get(
                    f"{BASE_URL}{path}",
                    params={**params, "Subscription-Key": self.api_key},
                    timeout=TIMEOUT,
                    stream=stream,
                )
            except requests.RequestException as exc:
                # A mensagem original pode conter o endereço com a chave: não a repasse.
                error = f"falha de conexão ({type(exc).__name__})"
            else:
                if response.status_code == 401:
                    raise InvalidKeyError("O EDINET recusou a chave da API (erro 401).")
                if response.status_code in RETRY_STATUS:
                    error = f"o EDINET respondeu com erro {response.status_code}"
                    response.close()
                elif response.status_code >= 400:
                    raise EdinetError(f"O EDINET respondeu com erro {response.status_code}.")
                else:
                    return response
            if attempt < self.max_tries:
                self._wait(self.backoff * 2 ** (attempt - 1))
        raise EdinetError(f"Não foi possível falar com o EDINET: {error}.")

    @staticmethod
    def _raise_if_error(data: object) -> None:
        """Erros do EDINET podem vir como JSON mesmo com HTTP 200."""
        if not isinstance(data, dict):
            raise EdinetError("Resposta inesperada do EDINET.")
        status = data.get("StatusCode", data.get("statusCode"))
        if status is not None:
            message = data.get("message") or ""
            if str(status) == "401":
                raise InvalidKeyError(f"O EDINET recusou a chave da API (erro 401). {message}".strip())
            raise EdinetError(f"O EDINET respondeu com erro {status}. {message}".strip())
        metadata = data.get("metadata")
        if isinstance(metadata, dict) and str(metadata.get("status")) != "200":
            status = metadata.get("status")
            message = metadata.get("message") or ""
            if str(status) == "401":
                raise InvalidKeyError(f"O EDINET recusou a chave da API (erro 401). {message}".strip())
            raise EdinetError(f"O EDINET respondeu com erro {status}. {message}".strip())

    # ------------------------------------------------------------ chamadas

    def list_documents(self, day: date) -> list[dict]:
        """Relatórios (anuais, trimestrais e semestrais) arquivados no dia."""
        self.check_cancel()
        if day in self._memory:
            return self._memory[day]

        cache_file = day_cache_path(self.cache_dir, day) if self.cache_dir else None
        if cache_file and cache_file.is_file():
            try:
                docs = json.loads(cache_file.read_text(encoding="utf-8"))
                if isinstance(docs, list):
                    self._memory[day] = docs
                    return docs
            except (OSError, ValueError):
                pass

        response = self._request("/documents.json", {"date": day.isoformat(), "type": 2})
        try:
            data = response.json()
        except ValueError as exc:
            raise EdinetError("Resposta inesperada do EDINET.") from exc
        self._raise_if_error(data)
        if not isinstance(data.get("metadata"), dict):
            raise EdinetError("Resposta inesperada do EDINET.")

        docs = [
            {field: item.get(field) for field in DOC_FIELDS}
            for item in data.get("results") or []
            if str(item.get("docTypeCode")) in DOC_TYPES
        ]
        self._memory[day] = docs
        # Só dias já encerrados vão para o disco: o de hoje ainda pode receber documentos.
        if cache_file and day < self._today():
            try:
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                cache_file.write_text(json.dumps(docs, ensure_ascii=False), encoding="utf-8")
            except OSError:
                pass
        return docs

    def test_key(self) -> None:
        """Faz uma consulta mínima; levanta InvalidKeyError se a chave não servir."""
        day = self._today() - timedelta(days=1)
        response = self._request("/documents.json", {"date": day.isoformat(), "type": 1})
        try:
            data = response.json()
        except ValueError as exc:
            raise EdinetError("Resposta inesperada do EDINET.") from exc
        self._raise_if_error(data)

    def download_document(self, doc_id: str, doc_type: int, dest: Path) -> Path:
        """Baixa o documento (1 = XBRL, 2 = PDF, 5 = CSV) para o arquivo `dest`."""
        dest = Path(dest)
        response = self._request(f"/documents/{doc_id}", {"type": doc_type}, stream=True)
        try:
            content_type = (response.headers.get("Content-Type") or "").lower()
            if "json" in content_type:
                # Em caso de erro o EDINET manda JSON no lugar do arquivo.
                try:
                    data = json.loads(response.content.decode("utf-8", errors="replace"))
                except ValueError:
                    data = None
                self._raise_if_error(data)
                raise EdinetError(f"O EDINET não entregou o documento {doc_id}.")

            dest.parent.mkdir(parents=True, exist_ok=True)
            partial = dest.with_name(dest.name + ".part")
            try:
                with open(partial, "wb") as handle:
                    for chunk in response.iter_content(chunk_size=65536):
                        self.check_cancel()
                        if chunk:
                            handle.write(chunk)
                if partial.stat().st_size == 0:
                    raise EdinetError(f"O EDINET entregou o documento {doc_id} vazio.")
                partial.replace(dest)
            finally:
                partial.unlink(missing_ok=True)
        finally:
            response.close()
        return dest
