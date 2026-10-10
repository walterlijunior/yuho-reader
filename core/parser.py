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

"""Leitura dos CSV que vêm dentro do ZIP tipo 5 do EDINET (XBRL convertido)."""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path, PurePosixPath

import pandas as pd

from .api import EdinetError

CSV_FOLDER = "XBRL_TO_CSV/"
COLUMNS = ["要素ID", "項目名", "コンテキストID", "相対年度", "連結・個別", "期間・時点", "ユニットID", "単位", "値"]
NUMERIC = "valor_numerico"
TAXONOMIES = {"jppfs_cor:": "J-GAAP", "jpigp_cor:": "IFRS"}

_NUMBER = re.compile(r"-?\d+(\.\d+)?")


def to_number(text: object) -> int | float | None:
    value = str(text).strip().replace(",", "")
    if not _NUMBER.fullmatch(value):
        return None
    return float(value) if "." in value else int(value)


def read_csv_zip(path: Path) -> pd.DataFrame:
    """Todas as linhas dos CSV do relatório (menos o parecer do auditor) + valor_numerico."""
    frames = []
    try:
        with zipfile.ZipFile(path) as archive:
            for name in sorted(archive.namelist()):
                file_name = PurePosixPath(name).name
                if not name.startswith(CSV_FOLDER) or not file_name.lower().endswith(".csv"):
                    continue
                if file_name.startswith("jpaud"):
                    continue
                frame = pd.read_csv(
                    io.BytesIO(archive.read(name)),
                    sep="\t",
                    encoding="utf-16",
                    dtype=str,
                    keep_default_na=False,
                )
                frames.append(frame.reindex(columns=COLUMNS, fill_value=""))
    except (zipfile.BadZipFile, OSError, UnicodeError, pd.errors.ParserError) as exc:
        raise EdinetError(f"Não consegui ler o arquivo {Path(path).name}: {exc}") from exc
    if not frames:
        raise EdinetError(f"O arquivo {Path(path).name} não tem dados em CSV.")
    table = pd.concat(frames, ignore_index=True).fillna("").astype(object)
    table[NUMERIC] = pd.Series([to_number(v) for v in table["値"]], dtype=object, index=table.index)
    return table


def _taxonomy(element_id: str) -> str:
    for prefix, name in TAXONOMIES.items():
        if element_id.startswith(prefix):
            return name
    return ""


def extract_statements(table: pd.DataFrame) -> pd.DataFrame:
    """Contas das demonstrações do período atual.

    Fica com J-GAAP/IFRS, consolidado (ou individual, se a empresa não consolida),
    período atual e sem segmentos. Acrescenta as colunas `taxonomia` e `natureza`.
    """
    data = table.copy()
    data["taxonomia"] = [_taxonomy(str(v)) for v in data["要素ID"]]
    data = data[data["taxonomia"] != ""]

    scope = "連結" if (data["連結・個別"] == "連結").any() else "個別"
    data = data[data["連結・個別"] == scope]
    data = data[[str(v).startswith("当") for v in data["相対年度"]]]
    # Contextos com "Member" são segmentos, exceto o que só indica "não consolidado".
    data = data[["Member" not in str(v).replace("_NonConsolidatedMember", "") for v in data["コンテキストID"]]]

    data = data.copy()
    data["natureza"] = ["saldo" if "時点" in str(v) else "fluxo" for v in data["期間・時点"]]
    return data.reset_index(drop=True)


def current_values(statements: pd.DataFrame) -> dict[tuple[str, str], dict]:
    """Um valor por conta, na ordem em que aparecem: {(elemento, natureza): linha}.

    Quando a conta aparece no trimestre isolado e no acumulado, vale o acumulado.
    """
    values: dict[tuple[str, str], dict] = {}
    for row in statements.to_dict("records"):
        if row[NUMERIC] is None or pd.isna(row[NUMERIC]):
            continue
        key = (row["要素ID"], row["natureza"])
        current = values.get(key)
        if current is None or ("累計" in str(row["相対年度"]) and "累計" not in str(current["相対年度"])):
            values[key] = row
    return values
