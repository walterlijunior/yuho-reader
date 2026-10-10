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

from core import periods as pe
from tests.fake_edinet import TODAY


def test_ultimos_exercicios():
    anos = pe.last_fiscal_years(3, 31, TODAY)
    assert len(anos) == 12
    assert anos[0] == date(2025, 3, 31) and anos[-1] == date(2014, 3, 31)
    # Exercício que termina em dezembro: o de 2025 ainda não acabou.
    assert pe.last_fiscal_years(12, 31, TODAY)[0] == date(2024, 12, 31)
    # "Fim de fevereiro" acompanha o ano bissexto.
    assert pe.last_fiscal_years(2, 31, TODAY)[:2] == [date(2025, 2, 28), date(2024, 2, 29)]


def test_fim_do_semestre():
    assert pe.semester_end(date(2025, 3, 31)) == date(2024, 9, 30)
    assert pe.semester_end(date(2024, 12, 31)) == date(2024, 6, 30)
    assert pe.semester_end(date(2025, 2, 28)) == date(2024, 8, 31)
    assert pe.semester_end(date(2025, 5, 20)) == date(2024, 11, 20)


def test_rotulos_e_janelas():
    anual, semestral = pe.build_targets([date(2025, 3, 31)], annual=True, semiannual=True)
    assert anual.label == "Anual_2025-03"
    assert semestral.label == "Semestral_2024-09"
    assert anual.window() == (date(2025, 5, 25), date(2025, 7, 9))          # 55 a 100 dias
    assert semestral.window() == (date(2024, 10, 25), date(2024, 11, 19))   # 25 a 50 dias
    assert anual.extension() == (date(2025, 7, 10), date(2025, 8, 13))      # mais 35 dias


def test_so_dias_uteis_e_nunca_no_futuro():
    dias = pe.business_days(date(2025, 10, 3), date(2025, 10, 20), TODAY)
    assert dias == [date(2025, 10, d) for d in (3, 6, 7, 8, 9, 10)]


def test_estimativa():
    alvos = pe.build_targets([date(2025, 3, 31)], annual=True, semiannual=False)
    est = pe.estimate(alvos, pause=0.5, today=TODAY)
    assert est.days == 33 and est.cached == 0
    assert est.seconds == 33 * 1.2
    assert est.describe() == "33 dias a consultar — cerca de 40 s"

    tudo_em_cache = pe.estimate(alvos, pause=0.5, today=TODAY, is_cached=lambda day: True)
    assert tudo_em_cache.describe() == "33 dias a consultar (33 já no cache) — instantâneo"

    com_retificacoes = pe.estimate(alvos, pause=0.5, today=TODAY, amendments=True)
    assert com_retificacoes.days == 33 + 25
