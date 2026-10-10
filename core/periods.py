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

"""Exercícios sociais e janelas de datas em que cada relatório costuma ser arquivado."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable, Iterable

ANNUAL = "Anual"
SEMIANNUAL = "Semestral"

# (primeiro dia, último dia) contados a partir do fim do período.
ANNUAL_WINDOW = (55, 100)       # prazo legal de 3 meses
SEMIANNUAL_WINDOW = (25, 50)    # prazo legal de 45 dias
EXTENSION_DAYS = 35             # prorrogações
PERIOD_TOLERANCE = 7            # diferença aceita no periodEnd, em dias
SECONDS_PER_CALL = 0.7          # tempo médio de resposta do EDINET (estimativa)


def clamp_date(year: int, month: int, day: int) -> date:
    """Data válida mais próxima: (2025, 2, 31) -> 28/02/2025."""
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def _is_month_end(day: date) -> bool:
    return day.day == calendar.monthrange(day.year, day.month)[1]


def semester_end(fiscal_year_end: date) -> date:
    """Fim do 1º semestre: seis meses antes do fim do exercício."""
    index = fiscal_year_end.year * 12 + fiscal_year_end.month - 1 - 6
    year, month = divmod(index, 12)
    day = 31 if _is_month_end(fiscal_year_end) else fiscal_year_end.day
    return clamp_date(year, month + 1, day)


def last_fiscal_years(month: int, day: int, today: date, count: int = 12) -> list[date]:
    """Datas de encerramento dos últimos exercícios já terminados, do mais novo ao mais antigo."""
    year = today.year
    if clamp_date(year, month, day) >= today:
        year -= 1
    return [clamp_date(year - offset, month, day) for offset in range(count)]


@dataclass(frozen=True)
class Target:
    """Um relatório procurado: anual ou semestral de um exercício."""

    kind: str
    period_end: date
    fiscal_year_end: date

    @property
    def label(self) -> str:
        return f"{self.kind}_{self.period_end:%Y-%m}"

    @property
    def _offsets(self) -> tuple[int, int]:
        return ANNUAL_WINDOW if self.kind == ANNUAL else SEMIANNUAL_WINDOW

    def window(self) -> tuple[date, date]:
        first, last = self._offsets
        return self.period_end + timedelta(days=first), self.period_end + timedelta(days=last)

    def extension(self) -> tuple[date, date]:
        last = self._offsets[1]
        return (
            self.period_end + timedelta(days=last + 1),
            self.period_end + timedelta(days=last + EXTENSION_DAYS),
        )


def build_targets(fiscal_year_ends: Iterable[date], annual: bool, semiannual: bool) -> list[Target]:
    """Relatórios a procurar, do exercício mais recente para o mais antigo."""
    targets: list[Target] = []
    for end in sorted(set(fiscal_year_ends), reverse=True):
        if annual:
            targets.append(Target(ANNUAL, end, end))
        if semiannual:
            targets.append(Target(SEMIANNUAL, semester_end(end), end))
    return targets


def business_days(start: date, end: date, today: date) -> list[date]:
    """Dias de segunda a sexta entre as duas datas, sem passar de hoje."""
    end = min(end, today)
    days = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


@dataclass(frozen=True)
class Estimate:
    days: int       # dias a consultar
    cached: int     # quantos já estão no cache
    seconds: float  # tempo aproximado

    @property
    def to_fetch(self) -> int:
        return self.days - self.cached

    def describe(self) -> str:
        if self.days == 0:
            return "Nada a consultar."
        text = f"{self.days} dias a consultar"
        if self.cached:
            text += f" ({self.cached} já no cache)"
        if self.seconds < 1:
            return text + " — instantâneo"
        if self.seconds < 90:
            return text + f" — cerca de {round(self.seconds)} s"
        return text + f" — cerca de {round(self.seconds / 60)} min"


def estimate(
    targets: Iterable[Target],
    pause: float,
    today: date,
    is_cached: Callable[[date], bool] = lambda day: False,
    amendments: bool = False,
) -> Estimate:
    """Quantos dias serão consultados e quanto tempo isso deve levar.

    Considera a janela normal de cada relatório; com retificações marcadas,
    também a prorrogação (onde elas costumam aparecer).
    """
    days: set[date] = set()
    for target in targets:
        days.update(business_days(*target.window(), today))
        if amendments:
            days.update(business_days(*target.extension(), today))
    cached = sum(1 for day in days if is_cached(day))
    seconds = (len(days) - cached) * (pause + SECONDS_PER_CALL)
    return Estimate(len(days), cached, seconds)
