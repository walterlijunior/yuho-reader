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

import zipfile
import io

import pytest

from core import companies as co
from core.api import EdinetError
from tests.fake_edinet import make_codelist_zip


@pytest.fixture
def lista():
    return co.parse_codelist(make_codelist_zip())


def test_le_o_zip_em_cp932(lista):
    assert len(lista) == 6
    capcom = lista[0]
    assert capcom.edinet_code == "E02417"
    assert capcom.name_jp == "株式会社カプコン"
    assert capcom.name_en == "CAPCOM CO., LTD."
    assert capcom.sec_code == "9697"          # 96970 -> 9697
    assert capcom.listed and capcom.consolidated is True
    assert capcom.fiscal_end == (3, 31)
    assert capcom.industry == "情報・通信業"


def test_le_tambem_o_csv_solto(lista):
    with zipfile.ZipFile(io.BytesIO(make_codelist_zip())) as archive:
        raw = archive.read("EdinetcodeDlInfo.csv")
    assert co.parse_codelist(raw) == lista


def test_encerramento_do_exercicio():
    assert co.parse_fiscal_end("12月31日") == (12, 31)
    assert co.parse_fiscal_end("2月末日") == (2, 31)
    assert co.parse_fiscal_end("") == (3, 31)


def test_codigo_da_bolsa_com_letra(lista):
    assert [c.sec_code for c in lista if c.edinet_code == "E99003"] == ["130A"]


def test_arquivo_errado_e_recusado():
    with pytest.raises(EdinetError):
        co.parse_codelist("nome,idade\nfulano,20".encode("cp932"))


def test_quem_comeca_com_o_termo_vem_primeiro(lista):
    nomes = [c.name_en for c in co.search(lista, "cap")]
    assert nomes == ["CAPCOM CO., LTD.", "Micro Capcom Trading"]


def test_filtro_so_listadas(lista):
    assert [c.edinet_code for c in co.search(lista, "cap", listed_only=True)] == ["E02417"]


@pytest.mark.parametrize("termo", [
    "9697", "E02417", "e02417", "カプコン", "かぶしきがいしゃかぷこん", "ｃａｐｃｏｍ", "CAPCOM CO",
])
def test_formas_de_achar_a_capcom(lista, termo):
    assert co.search(lista, termo)[0].edinet_code == "E02417"


def test_codigo_edinet_fora_da_lista_pode_ser_usado(lista):
    resultado = co.search(lista, "e12345")
    assert len(resultado) == 1
    assert resultado[0].edinet_code == "E12345"
    assert resultado[0].manual and resultado[0].fiscal_end == (3, 31)


def test_baixar_guarda_a_lista(fake):
    assert co.load_companies() == []
    baixadas = co.download_codelist(fake)
    assert len(baixadas) == 6
    assert co.load_companies() == baixadas
    assert co.codelist_updated_at() is not None


def test_importar_a_mao(tmp_path):
    arquivo = tmp_path / "Edinetcode.zip"
    arquivo.write_bytes(make_codelist_zip())
    assert len(co.import_codelist(arquivo)) == 6
    assert len(co.load_companies()) == 6
