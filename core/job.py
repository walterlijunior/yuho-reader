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

"""A tarefa completa: procurar os relatórios, baixar os arquivos e montar a planilha."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Callable

from .api import TYPE_CSV, TYPE_PDF, TYPE_XBRL, EdinetClient, EdinetError, InvalidKeyError, today_jst
from .companies import Company
from .excel import Report, build_workbook
from .parser import read_csv_zip
from .periods import build_targets
from .search import FoundDoc, find_documents

INFO_FILE = "empresa.json"
_NOT_WORD = re.compile(r"\W+")


@dataclass
class JobOptions:
    company: Company
    fiscal_year_ends: list[date]
    output_dir: Path
    annual: bool = True
    semiannual: bool = False
    amendments: bool = False
    xbrl: bool = False
    pdf: bool = False


@dataclass
class JobResult:
    folder: Path
    workbook: Path | None
    reports: list[Report] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    downloaded: int = 0
    skipped: int = 0


def company_folder(output_dir: Path, company: Company) -> Path:
    # Só letras, números e "_": sem espaços, vírgulas ou ponto no final.
    name = _NOT_WORD.sub("_", company.display_name).strip("_")[:60].strip("_")
    folder = company.edinet_code if not name or name == company.edinet_code else f"{company.edinet_code}_{name}"
    return Path(output_dir) / folder


def _read_info(folder: Path) -> dict:
    try:
        data = json.loads((folder / INFO_FILE).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def run_job(
    client: EdinetClient,
    options: JobOptions,
    on_progress: Callable[[int, str], None] | None = None,
    on_log: Callable[[str], None] | None = None,
    today: date | None = None,
) -> JobResult:
    """Executa tudo. Levanta `Cancelled` se o usuário cancelar e `EdinetError` em falhas."""
    log = on_log or (lambda message: None)
    highest = 0

    def progress(percent: int, status: str) -> None:
        # A barra nunca anda para trás, mesmo quando a busca precisa ser estendida.
        nonlocal highest
        highest = max(highest, percent)
        if on_progress:
            on_progress(highest, status)

    today = today or today_jst()
    company = options.company
    folder = company_folder(options.output_dir, company)
    result = JobResult(folder=folder, workbook=None)

    # 1) Busca dia a dia (0-60%)
    targets = build_targets(options.fiscal_year_ends, options.annual, options.semiannual)
    if not targets:
        raise EdinetError("Escolha pelo menos um exercício e um tipo de relatório.")
    log(f"Empresa: {company.display_name} ({company.edinet_code})")
    progress(0, "Procurando relatórios...")
    found, missing = find_documents(
        client,
        company.edinet_code,
        targets,
        amendments=options.amendments,
        on_progress=lambda done, total: progress(
            int(60 * done / total), f"Procurando relatórios... dia {done} de {total}"
        ),
        on_log=log,
        today=today,
    )
    result.missing = [target.label for target in missing]
    if not found:
        log("Nenhum relatório encontrado.")
        progress(100, "Nenhum relatório encontrado")
        return result

    # 2) Downloads (60-90%)
    folder.mkdir(parents=True, exist_ok=True)
    wanted = [(TYPE_CSV, "_csv.zip", "has_csv")]
    if options.xbrl:
        wanted.append((TYPE_XBRL, "_xbrl.zip", "has_xbrl"))
    if options.pdf:
        wanted.append((TYPE_PDF, ".pdf", "has_pdf"))
    steps = len(found) * len(wanted)
    step = 0
    for doc in found:
        for doc_type, suffix, flag in wanted:
            step += 1
            name = f"{doc.label}_{doc.doc_id}{suffix}"
            progress(60 + int(30 * step / steps), f"Baixando {name}")
            dest = folder / name
            if dest.is_file() and dest.stat().st_size > 0:
                result.skipped += 1
                log(f"Já existe: {name}")
            elif not getattr(doc, flag):
                log(f"O EDINET não oferece este formato: {name}")
            else:
                try:
                    client.download_document(doc.doc_id, doc_type, dest)
                    result.downloaded += 1
                    log(f"Baixado: {name}")
                except EdinetError as exc:
                    if doc_type == TYPE_CSV or isinstance(exc, InvalidKeyError):
                        raise
                    log(f"Falhou: {name} — {exc}")

    # 3) Registro da pasta: junta o que já havia sido baixado antes
    info = _read_info(folder)
    stored = info.get("relatorios") if isinstance(info.get("relatorios"), dict) else {}
    for doc in found:
        stored[doc.doc_id] = asdict(doc)
    info = {
        "edinet_code": company.edinet_code,
        "sec_code": company.sec_code,
        "nome": company.display_name,
        "nome_jp": company.name_jp,
        "setor": company.industry,
        "relatorios": stored,
    }

    # 4) Planilha (90-100%)
    progress(90, "Lendo os dados...")
    docs: list[FoundDoc] = []
    for item in stored.values():
        try:
            docs.append(FoundDoc(**item))
        except TypeError:
            continue
    for doc in docs:
        client.check_cancel()
        prefix = f"{doc.label}_{doc.doc_id}"
        files = sorted(p.name for p in folder.glob(f"{prefix}*") if p.suffix in (".zip", ".pdf"))
        csv_zip = folder / f"{prefix}_csv.zip"
        data = None
        if csv_zip.is_file():
            try:
                data = read_csv_zip(csv_zip)
            except EdinetError as exc:
                log(f"Aviso: {exc}")
        result.reports.append(Report(doc=doc, files=files, data=data))

    progress(95, "Montando a planilha...")
    workbook_path = folder / f"{folder.name}.xlsx"
    result.workbook = build_workbook(workbook_path, result.reports)
    info["planilha"] = result.workbook.name
    (folder / INFO_FILE).write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")

    if result.missing:
        log("Não encontrados: " + ", ".join(result.missing))
    log(f"Planilha pronta: {result.workbook}")
    progress(100, "Concluído")
    return result


@dataclass
class LibraryEntry:
    folder: Path
    workbook: Path | None
    edinet_code: str
    sec_code: str
    name: str
    years: list[int]


def list_library(output_dir: Path) -> list[LibraryEntry]:
    """Empresas já baixadas (para os cartões da tela inicial), a mais recente primeiro."""
    entries: list[tuple[float, LibraryEntry]] = []
    try:
        folders = [p for p in Path(output_dir).iterdir() if p.is_dir()]
    except OSError:
        return []
    for folder in folders:
        info_file = folder / INFO_FILE
        info = _read_info(folder)
        if not info.get("edinet_code"):
            continue
        reports = info.get("relatorios") if isinstance(info.get("relatorios"), dict) else {}
        years = sorted({
            int(str(item.get("target_end"))[:4])
            for item in reports.values()
            if isinstance(item, dict) and str(item.get("target_end"))[:4].isdigit()
        })
        workbook = folder / str(info.get("planilha") or f"{folder.name}.xlsx")
        entries.append((
            info_file.stat().st_mtime,
            LibraryEntry(
                folder=folder,
                workbook=workbook if workbook.is_file() else None,
                edinet_code=str(info["edinet_code"]),
                sec_code=str(info.get("sec_code") or ""),
                name=str(info.get("nome") or folder.name),
                years=years,
            ),
        ))
    return [entry for _, entry in sorted(entries, key=lambda item: item[0], reverse=True)]
