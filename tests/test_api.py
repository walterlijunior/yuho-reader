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

import threading
from datetime import date

import pytest
import requests

from core.api import Cancelled, EdinetError, InvalidKeyError, day_cache_path
from tests.fake_edinet import KEY, TODAY


def test_lista_do_dia_envia_a_chave_e_filtra_os_tipos(client, fake):
    docs = client.list_documents(date(2025, 6, 20))
    url, params = fake.calls[0]
    assert url.endswith("/api/v2/documents.json")
    assert params == {"date": "2025-06-20", "type": "2", "Subscription-Key": KEY}
    # O documento tipo 030 (fundo) não interessa e é descartado.
    assert [d["docID"] for d in docs] == ["S100OUT1", "S100AN25"]
    assert "campoQueNaoInteressa" not in docs[0]


def test_dia_passado_fica_em_cache_no_disco(make_client, fake, tmp_path):
    day = date(2025, 6, 20)
    first = make_client().list_documents(day)
    assert day_cache_path(tmp_path / "cache", day).is_file()
    # Um cliente novo (programa reaberto) não chama o EDINET de novo.
    second = make_client().list_documents(day)
    assert second == first
    assert fake.count("documents.json") == 1


def test_dia_de_hoje_nao_vai_para_o_disco(make_client, fake, tmp_path):
    make_client().list_documents(TODAY)
    assert not day_cache_path(tmp_path / "cache", TODAY).exists()
    make_client().list_documents(TODAY)
    assert fake.count("documents.json") == 2


def test_chave_invalida_http_401(make_client):
    with pytest.raises(InvalidKeyError):
        make_client(key="errada").list_documents(date(2025, 6, 20))


def test_chave_invalida_em_json(make_client, fake, tmp_path):
    fake.invalid_as_json = True
    with pytest.raises(InvalidKeyError):
        make_client(key="errada").list_documents(date(2025, 6, 20))
    assert not day_cache_path(tmp_path / "cache", date(2025, 6, 20)).exists()


def test_sem_chave_nem_chama_o_edinet(make_client, fake):
    with pytest.raises(InvalidKeyError):
        make_client(key="  ").list_documents(date(2025, 6, 20))
    assert fake.calls == []


def test_testar_chave(make_client):
    make_client().test_key()
    with pytest.raises(InvalidKeyError):
        make_client(key="errada").test_key()


def test_tenta_de_novo_em_429_e_5xx(make_client, fake, sleeps):
    fake.failures = [429, 503]
    docs = make_client(backoff=2.0).list_documents(date(2025, 6, 20))
    assert len(docs) == 2
    assert fake.count("documents.json") == 3
    assert sleeps == [2.0, 4.0]  # espera crescente entre as tentativas


def test_desiste_depois_de_varias_falhas(make_client, fake):
    fake.failures = [500] * 10
    with pytest.raises(EdinetError):
        make_client().list_documents(date(2025, 6, 20))
    assert fake.count("documents.json") == 4


def test_pausa_entre_chamadas(make_client, sleeps):
    client = make_client(pause=0.5)
    for day in (16, 17, 18):
        client.list_documents(date(2025, 6, day))
    assert sleeps == [0.5, 0.5]  # nenhuma pausa antes da primeira chamada


def test_falha_de_conexao_nao_revela_a_chave(make_client, fake):
    def broken(url, params=None, **kwargs):
        raise requests.ConnectionError(f"falhou em {url}?Subscription-Key={params['Subscription-Key']}")
    fake.get = broken
    with pytest.raises(EdinetError) as error:
        make_client().list_documents(date(2025, 6, 20))
    assert KEY not in str(error.value)


def test_baixa_documento(client, fake, tmp_path):
    dest = client.download_document("S100AN25", 2, tmp_path / "saida" / "doc.pdf")
    assert dest.read_bytes() == b"%PDF-S100AN25"
    assert fake.calls[-1][1]["type"] == "2"
    assert not (tmp_path / "saida" / "doc.pdf.part").exists()


def test_erro_em_json_no_lugar_do_arquivo(client, tmp_path):
    dest = tmp_path / "doc.zip"
    with pytest.raises(EdinetError) as error:
        client.download_document("S100NAOEXISTE", 5, dest)
    assert "404" in str(error.value)
    assert not dest.exists()


def test_cancelar_interrompe(make_client):
    cancel = threading.Event()
    client = make_client(cancel_event=cancel)
    client.list_documents(date(2025, 6, 20))
    cancel.set()
    with pytest.raises(Cancelled):
        client.list_documents(date(2025, 6, 19))
