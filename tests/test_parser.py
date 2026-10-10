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

import pytest

from core.api import EdinetError
from core.parser import COLUMNS, NUMERIC, current_values, extract_statements, read_csv_zip, to_number
from tests.fake_edinet import make_csv_zip, statement_rows


def gravar(tmp_path, linhas):
    arquivo = tmp_path / "relatorio_csv.zip"
    arquivo.write_bytes(make_csv_zip(linhas))
    return arquivo


def test_numeros():
    assert to_number("169604000000") == 169604000000
    assert to_number("-5") == -5
    assert to_number("3,766") == 3766
    assert to_number("12.5") == 12.5
    assert to_number("－") is None
    assert to_number("2025-03-31") is None
    assert to_number("") is None


def test_le_utf16_e_ignora_o_parecer_do_auditor(tmp_path):
    tabela = read_csv_zip(gravar(tmp_path, statement_rows(1000, 5000)))
    assert list(tabela.columns) == [*COLUMNS, NUMERIC]
    assert len(tabela) == 10
    assert not any(str(v).startswith("jpaud") for v in tabela["要素ID"])
    assert tabela.loc[tabela["要素ID"] == "jpcrp_cor:NumberOfEmployees", NUMERIC].item() == 3766
    assert tabela.loc[tabela["要素ID"] == "jpdei_cor:FilerNameInJapaneseDEI", NUMERIC].item() is None


def test_demonstracoes_consolidado_periodo_atual_sem_segmentos(tmp_path):
    contas = extract_statements(read_csv_zip(gravar(tmp_path, statement_rows(1000, 5000, -5))))
    assert [(r["要素ID"], r["コンテキストID"], r[NUMERIC], r["natureza"]) for r in contas.to_dict("records")] == [
        ("jppfs_cor:Assets", "CurrentYearInstant", 5000, "saldo"),
        ("jppfs_cor:NetSales", "CurrentYearDuration", 1000, "fluxo"),
        ("jppfs_cor:OperatingIncome", "CurrentYearDuration", -5, "fluxo"),
    ]
    assert set(contas["taxonomia"]) == {"J-GAAP"}


def test_empresa_que_nao_consolida_usa_o_individual(tmp_path):
    linhas = [
        ["jppfs_cor:NetSales", "売上高", "CurrentYearDuration_NonConsolidatedMember", "当期", "個別", "期間", "JPY", "円", "700"],
        ["jppfs_cor:NetSales", "売上高", "Prior1YearDuration_NonConsolidatedMember", "前期", "個別", "期間", "JPY", "円", "600"],
        ["jppfs_cor:CapitalStock", "資本金", "CurrentYearInstant_NonConsolidatedMember_CapitalStockMember", "当期末", "個別", "時点", "JPY", "円", "9"],
    ]
    contas = extract_statements(read_csv_zip(gravar(tmp_path, linhas)))
    assert contas[NUMERIC].tolist() == [700]


def test_ifrs(tmp_path):
    linhas = [
        ["jpigp_cor:RevenueIFRS", "売上収益", "CurrentYearDuration", "当期", "連結", "期間", "JPY", "円", "900"],
        ["jppfs_cor:NetSales", "売上高", "CurrentYearDuration_NonConsolidatedMember", "当期", "個別", "期間", "JPY", "円", "100"],
    ]
    contas = extract_statements(read_csv_zip(gravar(tmp_path, linhas)))
    assert contas["taxonomia"].tolist() == ["IFRS"]
    assert contas[NUMERIC].tolist() == [900]


def test_trimestral_prefere_o_acumulado(tmp_path):
    linhas = [
        ["jppfs_cor:NetSales", "売上高", "CurrentQuarterDuration", "当四半期会計期間", "連結", "期間", "JPY", "円", "30"],
        ["jppfs_cor:NetSales", "売上高", "CurrentYTDDuration", "当四半期累計期間", "連結", "期間", "JPY", "円", "70"],
        ["jppfs_cor:Assets", "資産", "CurrentQuarterInstant", "当四半期会計期間末", "連結", "時点", "JPY", "円", "500"],
    ]
    valores = current_values(extract_statements(read_csv_zip(gravar(tmp_path, linhas))))
    assert [(chave, linha[NUMERIC]) for chave, linha in valores.items()] == [
        (("jppfs_cor:NetSales", "fluxo"), 70),
        (("jppfs_cor:Assets", "saldo"), 500),
    ]


def test_arquivo_estragado(tmp_path):
    arquivo = tmp_path / "ruim.zip"
    arquivo.write_bytes(b"isto nao e um zip")
    with pytest.raises(EdinetError):
        read_csv_zip(arquivo)
