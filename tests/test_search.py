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

from datetime import date

from core.periods import build_targets
from core.search import find_documents
from tests.fake_edinet import CAPCOM, TODAY


def buscar(client, anos, annual=True, semiannual=False, amendments=False, **kwargs):
    alvos = build_targets([date(a, 3, 31) for a in anos], annual, semiannual)
    return find_documents(client, CAPCOM, alvos, amendments=amendments, today=TODAY, **kwargs)


def test_acha_o_anual_e_para_de_procurar(client, fake):
    achados, faltando = buscar(client, [2025])
    assert [(d.label, d.doc_id) for d in achados] == [("Anual_2025-03", "S100AN25")]
    assert faltando == []
    # A janela começa em 26/05 (dia útil) e o relatório saiu em 20/06: 20 dias consultados, não 32.
    assert fake.count("documents.json") == 20
    assert fake.calls[0][1]["date"] == "2025-05-26"
    assert fake.calls[-1][1]["date"] == "2025-06-20"


def test_ignora_retirado_e_outras_empresas(client):
    achados, _ = buscar(client, [2025])
    assert {d.doc_id for d in achados} == {"S100AN25"}


def test_repetir_a_busca_usa_o_cache(make_client, fake):
    buscar(make_client(), [2025])
    chamadas = fake.count("documents.json")
    achados, _ = buscar(make_client(), [2025])
    assert fake.count("documents.json") == chamadas
    assert achados[0].doc_id == "S100AN25"


def test_sem_retificacoes_marcadas_elas_ficam_de_fora(client):
    achados, _ = buscar(client, [2024])
    assert [d.label for d in achados] == ["Anual_2024-03"]


def test_com_retificacoes(client):
    achados, _ = buscar(client, [2024], amendments=True)
    assert [(d.label, d.doc_id, d.amendment) for d in achados] == [
        ("Anual_2024-03", "S100AN24", False),
        ("Anual_2024-03_retif_2024-07-03", "S100RT24", True),
    ]


def test_semestral_novo_e_trimestral_antigo(client):
    achados, faltando = buscar(client, [2025, 2024], annual=False, semiannual=True)
    assert [(d.label, d.doc_id) for d in achados] == [
        ("Semestral_2024-09", "S100SE24"),
        ("Semestral_2023-09", "S100Q223"),   # o trimestral de 3 meses (S100Q3M3) não serve
    ]
    assert faltando == []


def test_atrasado_aparece_na_prorrogacao(client):
    mensagens = []
    achados, faltando = buscar(client, [2023], on_log=mensagens.append)
    assert [d.doc_id for d in achados] == ["S100AN23"]
    assert faltando == []
    assert any("estendendo" in m for m in mensagens)


def test_nao_encontrado(client):
    achados, faltando = buscar(client, [2020])
    assert achados == []
    assert [t.label for t in faltando] == ["Anual_2020-03"]


def test_periodo_precisa_bater(client, fake):
    # Um relatório anual de outro exercício arquivado dentro da janela não é aceito.
    fake.add_doc("2022-06-20", "S100ERRA", start="2020-04-01", end="2021-03-31")
    achados, faltando = buscar(client, [2022])
    assert achados == [] and len(faltando) == 1
    # Diferença de poucos dias (exercício de 52 semanas) é aceita.
    fake.add_doc("2021-06-21", "S100PERT", start="2020-04-01", end="2021-03-27")
    achados, _ = buscar(client, [2021])
    assert [d.doc_id for d in achados] == ["S100PERT"]


def test_ordem_e_progresso(client):
    passos = []
    achados, _ = buscar(client, [2024, 2025], semiannual=True, amendments=True,
                        on_progress=lambda feito, total: passos.append((feito, total)))
    assert [d.label for d in achados] == [
        "Anual_2025-03",
        "Semestral_2024-09",
        "Anual_2024-03",
        "Anual_2024-03_retif_2024-07-03",
        "Semestral_2023-09",
    ]
    assert passos[-1][0] == passos[-1][1]
    assert all(feito <= total for feito, total in passos)
