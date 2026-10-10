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

"""Lista pública de empresas do EDINET (EdinetcodeDlInfo.csv) e a pesquisa nela."""

from __future__ import annotations

import csv
import io
import re
import unicodedata
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import requests

from .api import EdinetError
from .config import local_dir

CODELIST_URL = "https://disclosure2dl.edinet-fsa.go.jp/searchdocument/codelist/Edinetcode.zip"
CODELIST_PAGE = "https://disclosure2.edinet-fsa.go.jp/weee0020.aspx"
CODELIST_FILE = "EdinetcodeDlInfo.csv"
ENCODING = "cp932"
DEFAULT_FISCAL_END = (3, 31)

_EDINET_CODE = re.compile(r"E\d{5}")
_FISCAL_END = re.compile(r"(\d{1,2})月(?:(\d{1,2})日|末)")


def _normalize(text: str) -> str:
    """Minúsculas, largura normal e hiragana convertido em katakana."""
    text = unicodedata.normalize("NFKC", text or "").casefold().strip()
    return "".join(chr(ord(ch) + 0x60) if "ぁ" <= ch <= "ゖ" else ch for ch in text)


def parse_fiscal_end(text: str) -> tuple[int, int]:
    """'3月31日' -> (3, 31). '2月末日' -> (2, 31), ajustado ao mês na hora de usar."""
    match = _FISCAL_END.search(unicodedata.normalize("NFKC", text or ""))
    if not match:
        return DEFAULT_FISCAL_END
    month = int(match.group(1))
    day = int(match.group(2)) if match.group(2) else 31
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return DEFAULT_FISCAL_END
    return month, day


def is_edinet_code(text: str) -> bool:
    return bool(_EDINET_CODE.fullmatch((text or "").strip().upper()))


@dataclass
class Company:
    edinet_code: str
    name_jp: str = ""
    name_en: str = ""
    name_kana: str = ""
    kind: str = ""
    listed: bool = False
    consolidated: bool | None = None
    capital: str = ""
    fiscal_end: tuple[int, int] = DEFAULT_FISCAL_END
    address: str = ""
    industry: str = ""
    sec_code: str = ""
    corporate_number: str = ""
    manual: bool = False
    _keys: tuple[str, ...] = field(default=(), repr=False, compare=False)

    def __post_init__(self):
        self._keys = tuple(
            _normalize(value)
            for value in (self.sec_code, self.edinet_code, self.name_en, self.name_jp, self.name_kana)
        )

    @property
    def display_name(self) -> str:
        return self.name_en or self.name_jp or self.edinet_code


def manual_company(edinet_code: str) -> Company:
    """Empresa fora da lista: só o código, com encerramento padrão em 31/03."""
    return Company(edinet_code=edinet_code.strip().upper(), manual=True)


# ------------------------------------------------------------------ leitura

def _extract_csv(data: bytes) -> bytes:
    """Aceita tanto o ZIP do EDINET quanto o CSV já extraído."""
    if data[:2] == b"PK":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                names = [n for n in archive.namelist() if n.lower().endswith(".csv")]
                if not names:
                    raise EdinetError("O ZIP não contém a lista de empresas (CSV).")
                preferred = [n for n in names if Path(n).name == CODELIST_FILE]
                return archive.read((preferred or names)[0])
        except zipfile.BadZipFile as exc:
            raise EdinetError("O arquivo ZIP está corrompido.") from exc
    return data


def parse_codelist(data: bytes) -> list[Company]:
    """Lê a lista de empresas a partir do ZIP ou do CSV (cp932)."""
    text = _extract_csv(data).decode(ENCODING, errors="replace")
    companies: list[Company] = []
    for row in csv.reader(io.StringIO(text, newline="")):
        # As duas primeiras linhas (data do download e cabeçalho) não começam com código.
        if not row or not _EDINET_CODE.fullmatch(row[0].strip()):
            continue
        cells = [cell.strip() for cell in row] + [""] * 13
        sec_code = cells[11]
        if len(sec_code) == 5:
            sec_code = sec_code[:4]
        companies.append(
            Company(
                edinet_code=cells[0],
                kind=cells[1],
                listed=cells[2] == "上場",
                consolidated={"有": True, "無": False}.get(cells[3]),
                capital=cells[4],
                fiscal_end=parse_fiscal_end(cells[5]),
                name_jp=cells[6],
                name_en=cells[7],
                name_kana=cells[8],
                address=cells[9],
                industry=cells[10],
                sec_code=sec_code,
                corporate_number=cells[12],
            )
        )
    if not companies:
        raise EdinetError("Não encontrei empresas nesse arquivo. É mesmo a lista do EDINET?")
    return companies


# ------------------------------------------------- armazenamento da lista

def codelist_path() -> Path:
    return local_dir() / CODELIST_FILE


def _store(data: bytes) -> list[Company]:
    raw = _extract_csv(data)
    companies = parse_codelist(raw)  # valida antes de substituir a lista atual
    path = codelist_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return companies


def download_codelist(session: requests.Session | None = None) -> list[Company]:
    """Baixa a lista do site do EDINET (não precisa da chave) e guarda no computador."""
    session = session or requests.Session()
    try:
        response = session.get(CODELIST_URL, timeout=60)
    except requests.RequestException as exc:
        raise EdinetError(f"Não consegui baixar a lista de empresas ({type(exc).__name__}).") from exc
    if response.status_code != 200:
        raise EdinetError(f"Não consegui baixar a lista de empresas (erro {response.status_code}).")
    return _store(response.content)


def import_codelist(path: Path) -> list[Company]:
    """Importa à mão o ZIP ou CSV baixado pelo navegador."""
    try:
        data = Path(path).read_bytes()
    except OSError as exc:
        raise EdinetError(f"Não consegui abrir o arquivo: {exc}") from exc
    return _store(data)


def load_companies() -> list[Company]:
    """Lista já guardada no computador (vazia se ainda não foi baixada)."""
    try:
        return parse_codelist(codelist_path().read_bytes())
    except (OSError, EdinetError):
        return []


def codelist_updated_at() -> datetime | None:
    try:
        return datetime.fromtimestamp(codelist_path().stat().st_mtime)
    except OSError:
        return None


# ----------------------------------------------------------------- pesquisa

def search(
    companies: list[Company], term: str, listed_only: bool = False, limit: int = 200
) -> list[Company]:
    """Procura por nome (inglês, japonês, kana), código da bolsa ou código EDINET.

    Quem começa com o termo aparece antes de quem apenas o contém. Um código
    EDINET válido que não está na lista é devolvido assim mesmo.
    """
    key = _normalize(term)
    if not key:
        return []
    ranked: list[tuple[int, bool, str, Company]] = []
    for company in companies:
        if listed_only and not company.listed:
            continue
        if key in company._keys[:2]:
            score = 0
        elif any(value.startswith(key) for value in company._keys):
            score = 1
        elif any(key in value for value in company._keys):
            score = 2
        else:
            continue
        ranked.append((score, not company.listed, _normalize(company.display_name), company))
    ranked.sort(key=lambda item: item[:3])
    results = [item[3] for item in ranked[:limit]]

    code = term.strip().upper()
    if is_edinet_code(code) and not any(c.edinet_code == code for c in companies):
        results.insert(0, manual_company(code))
    return results
