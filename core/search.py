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

"""Localiza os relatórios de uma empresa consultando o EDINET dia a dia."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable

from .api import EdinetClient, today_jst
from .periods import ANNUAL, PERIOD_TOLERANCE, Target, business_days

ORIGINAL_TYPES = {ANNUAL: {"120"}, "Semestral": {"160", "140"}}
AMENDMENT_TYPES = {ANNUAL: {"130"}, "Semestral": {"170", "150"}}
QUARTERLY_TYPES = {"140", "150"}
MIN_SEMESTER_DAYS = 150  # relatório trimestral só serve se cobrir mais de ~5 meses


@dataclass
class FoundDoc:
    """Um relatório localizado. As datas ficam em texto (AAAA-MM-DD) como o EDINET envia."""

    label: str
    kind: str
    amendment: bool
    doc_id: str
    description: str
    period_start: str
    period_end: str
    submitted: str
    target_end: str
    has_csv: bool = True
    has_xbrl: bool = True
    has_pdf: bool = True

    @property
    def sort_key(self) -> tuple:
        """Mais recente primeiro; o original antes das suas retificações."""
        return (-date.fromisoformat(self.target_end).toordinal(), self.kind, self.amendment, self.submitted)


def _parse_date(text: object) -> date | None:
    try:
        return date.fromisoformat(str(text)[:10])
    except ValueError:
        return None


def _period_matches(doc: dict, target: Target) -> bool:
    end = _parse_date(doc.get("periodEnd"))
    if end is None or abs((end - target.period_end).days) > PERIOD_TOLERANCE:
        return False
    if str(doc.get("docTypeCode")) in QUARTERLY_TYPES:
        # Dos trimestrais antigos só interessa o do 2º trimestre (acumulado de 6 meses).
        start = _parse_date(doc.get("periodStart"))
        if start is not None:
            return (end - start).days > MIN_SEMESTER_DAYS
        description = str(doc.get("docDescription") or "")
        return "第2四半期" in description or "第２四半期" in description
    return True


def _flag(doc: dict, name: str) -> bool:
    value = doc.get(name)
    return True if value is None else str(value) == "1"


def find_documents(
    client: EdinetClient,
    edinet_code: str,
    targets: list[Target],
    amendments: bool = False,
    on_progress: Callable[[int, int], None] | None = None,
    on_log: Callable[[str], None] | None = None,
    today: date | None = None,
) -> tuple[list[FoundDoc], list[Target]]:
    """Devolve (relatórios encontrados, relatórios não encontrados)."""
    today = today or today_jst()
    log = on_log or (lambda message: None)
    windows = {target: business_days(*target.window(), today) for target in targets}
    extensions = {target: business_days(*target.extension(), today) for target in targets}
    # Com retificações a prorrogação é sempre percorrida; sem elas, só se faltar o original.
    total = sum(len(days) for days in windows.values())
    if amendments:
        total += sum(len(days) for days in extensions.values())
    done = 0

    def progress() -> None:
        if on_progress:
            on_progress(done, max(total, 1))

    found: list[FoundDoc] = []
    missing: list[Target] = []
    labels: set[str] = set()

    for target in targets:
        originals: list[str] = []
        hits: list[FoundDoc] = []

        def scan(days: list[date]) -> bool:
            """Percorre os dias; devolve True quando já pode parar."""
            nonlocal done
            for index, day in enumerate(days):
                docs = client.list_documents(day)
                done += 1
                progress()
                for doc in sorted(docs, key=lambda d: str(d.get("submitDateTime") or "")):
                    if doc.get("edinetCode") != edinet_code:
                        continue
                    if str(doc.get("withdrawalStatus") or "0") != "0":
                        continue
                    doc_type = str(doc.get("docTypeCode"))
                    doc_id = str(doc.get("docID") or "")
                    if doc_type in ORIGINAL_TYPES[target.kind]:
                        if originals or not _period_matches(doc, target):
                            continue
                        originals.append(doc_id)
                        is_amendment = False
                    elif doc_type in AMENDMENT_TYPES[target.kind]:
                        # Retificações às vezes vêm sem período: valem se apontam para o original.
                        if not amendments:
                            continue
                        if not (_period_matches(doc, target) or doc.get("parentDocID") in originals):
                            continue
                        is_amendment = True
                    else:
                        continue

                    submitted = str(doc.get("submitDateTime") or day.isoformat())
                    label = target.label
                    if is_amendment:
                        label += f"_retif_{submitted[:10]}"
                    if label in labels:
                        label += f"_{doc_id}"
                    labels.add(label)
                    hits.append(
                        FoundDoc(
                            label=label,
                            kind=target.kind,
                            amendment=is_amendment,
                            doc_id=doc_id,
                            description=str(doc.get("docDescription") or ""),
                            period_start=str(doc.get("periodStart") or ""),
                            period_end=str(doc.get("periodEnd") or ""),
                            submitted=submitted,
                            target_end=target.period_end.isoformat(),
                            has_csv=_flag(doc, "csvFlag"),
                            has_xbrl=_flag(doc, "xbrlFlag"),
                            has_pdf=_flag(doc, "pdfFlag"),
                        )
                    )
                    log(f"  {day:%d/%m/%Y}: {label} ({doc_id})")
                if originals and not amendments:
                    done += len(days) - index - 1
                    progress()
                    return True
            return False

        log(f"Procurando {target.label}...")
        if not scan(windows[target]):
            extension = extensions[target]
            if extension and (amendments or not originals):
                if not originals:
                    log("  Não apareceu no prazo normal; estendendo a busca por 35 dias.")
                if not amendments:
                    total += len(extension)
                scan(extension)
        if not originals:
            log(f"  {target.label}: não encontrado.")
            missing.append(target)
        found.extend(hits)

    found.sort(key=lambda doc: doc.sort_key)
    return found, missing
