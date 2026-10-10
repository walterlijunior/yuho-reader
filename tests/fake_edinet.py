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

"""Um EDINET de mentira: responde como a API real, sem usar a internet."""

from __future__ import annotations

import io
import re
import zipfile
from datetime import date

from core.api import BASE_URL
from core.companies import CODELIST_URL

KEY = "chave-de-teste"
CAPCOM = "E02417"
TODAY = date(2025, 10, 10)

CSV_HEADER = ["要素ID", "項目名", "コンテキストID", "相対年度", "連結・個別", "期間・時点", "ユニットID", "単位", "値"]


def make_csv_zip(rows: list[list[str]], with_auditor: bool = True) -> bytes:
    """ZIP tipo 5: CSV em UTF-16 separado por tabulação, dentro de XBRL_TO_CSV/."""
    def encode(lines: list[list[str]]) -> bytes:
        text = "\r\n".join("\t".join(f'"{cell}"' for cell in line) for line in [CSV_HEADER, *lines])
        return text.encode("utf-16")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("XBRL_TO_CSV/jpcrp030000-asr-001_E02417-000.csv", encode(rows))
        if with_auditor:
            auditor = [["jpaud_cor:AuditOpinion", "監査意見", "FilingDateInstant", "提出日時点", "その他", "時点", "", "", "適正"]]
            archive.writestr("XBRL_TO_CSV/jpaud-aar-cc-001_E02417-000.csv", encode(auditor))
        archive.writestr("leiame.txt", "arquivo que deve ser ignorado")
    return buffer.getvalue()


def statement_rows(sales: int, assets: int, operating: int = -5) -> list[list[str]]:
    """Linhas típicas de um relatório consolidado J-GAAP."""
    return [
        ["jpdei_cor:FilerNameInJapaneseDEI", "提出者名", "FilingDateInstant", "提出日時点", "その他", "時点", "", "", "株式会社カプコン"],
        ["jpcrp_cor:NumberOfEmployees", "従業員数", "CurrentYearInstant", "当期末", "連結", "時点", "pure", "", "3,766"],
        ["jppfs_cor:Assets", "資産", "CurrentYearInstant", "当期末", "連結", "時点", "JPY", "円", str(assets)],
        ["jppfs_cor:Assets", "資産", "Prior1YearInstant", "前期末", "連結", "時点", "JPY", "円", "1"],
        ["jppfs_cor:NetSales", "売上高", "CurrentYearDuration", "当期", "連結", "期間", "JPY", "円", str(sales)],
        ["jppfs_cor:NetSales", "売上高", "Prior1YearDuration", "前期", "連結", "期間", "JPY", "円", "2"],
        ["jppfs_cor:NetSales", "売上高", "CurrentYearDuration_NonConsolidatedMember", "当期", "個別", "期間", "JPY", "円", "3"],
        ["jppfs_cor:NetSales", "売上高", "CurrentYearDuration_DigitalContentsReportableSegmentsMember", "当期", "連結", "期間", "JPY", "円", "4"],
        ["jppfs_cor:OperatingIncome", "営業利益", "CurrentYearDuration", "当期", "連結", "期間", "JPY", "円", str(operating)],
        ["jpcrp_cor:BusinessRisksTextBlock", "事業等のリスク", "FilingDateInstant", "提出日時点", "その他", "時点", "", "", "=texto que parece fórmula\x0b"],
    ]


def make_codelist_zip() -> bytes:
    lines = [
        "ダウンロード実行日,2025年10月1日現在,件数,6件",
        "ＥＤＩＮＥＴコード,提出者種別,上場区分,連結の有無,資本金,決算日,提出者名,提出者名（英字）,提出者名（ヨミ）,所在地,提出者業種,証券コード,提出者法人番号",
        '"E02417","内国法人・組合","上場","有","33239","3月31日","株式会社カプコン","CAPCOM CO., LTD.","カブシキガイシャカプコン","大阪市中央区","情報・通信業","96970","3120001077461"',
        '"E01777","内国法人・組合","上場","有","880214","3月31日","ソニーグループ株式会社","SONY GROUP CORPORATION","ソニーグループカブシキガイシャ","東京都港区","電気機器","67580","5010401067252"',
        '"E02367","内国法人・組合","上場","有","10065","3月31日","任天堂株式会社","Nintendo Co., Ltd.","ニンテンドウカブシキガイシャ","京都市南区","その他製品","79740",""',
        '"E99001","内国法人・組合","非上場","無","100","12月31日","カプセル商事株式会社","Micro Capcom Trading","カプセルショウジカブシキガイシャ","東京都","卸売業","",""',
        '"E99002","個人（組合発起人を除く）","非上場","","","","山田 太郎","","ヤマダ タロウ","","個人（組合発起人を除く）","",""',
        '"E99003","内国法人・組合","上場","有","500","2月末日","株式会社エービーシー","ABC Test Holdings","エービーシー","東京都","小売業","130A0",""',
    ]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("EdinetcodeDlInfo.csv", "\r\n".join(lines).encode("cp932"))
    return buffer.getvalue()


class FakeResponse:
    def __init__(self, status=200, json_data=None, content=b"", content_type="application/json; charset=utf-8"):
        self.status_code = status
        self._json = json_data
        self._content = content
        self.headers = {"Content-Type": content_type}

    def json(self):
        if self._json is None:
            raise ValueError("sem JSON")
        return self._json

    @property
    def content(self) -> bytes:
        if self._json is not None:
            import json
            return json.dumps(self._json).encode("utf-8")
        return self._content

    def iter_content(self, chunk_size=65536):
        for start in range(0, len(self._content), chunk_size):
            yield self._content[start:start + chunk_size]

    def close(self):
        pass


class FakeEdinet:
    """Faz o papel de `requests.Session`."""

    def __init__(self):
        self.key = KEY
        self.invalid_as_json = False      # chave errada: HTTP 401 ou JSON com StatusCode 401
        self.failures: list[int] = []     # códigos HTTP a devolver nas próximas chamadas
        self.docs: dict[str, list[dict]] = {}
        self.files: dict[tuple[str, str], tuple[bytes, str]] = {}
        self.calls: list[tuple[str, dict]] = []

    # ------------------------------------------------------------ montagem

    def add_doc(self, day: str, doc_id: str, doc_type: str = "120", code: str = CAPCOM,
                start: str | None = None, end: str | None = None, description: str = "有価証券報告書",
                withdrawn: bool = False, parent: str | None = None, csv_rows=None) -> None:
        self.docs.setdefault(day, []).append({
            "seqNumber": len(self.docs.get(day, [])) + 1,
            "docID": doc_id,
            "edinetCode": code,
            "secCode": "96970",
            "filerName": "株式会社カプコン",
            "docTypeCode": doc_type,
            "docDescription": description,
            "periodStart": start,
            "periodEnd": end,
            "submitDateTime": f"{day} 15:00",
            "withdrawalStatus": "1" if withdrawn else "0",
            "parentDocID": parent,
            "xbrlFlag": "1", "pdfFlag": "1", "csvFlag": "1",
            "campoQueNaoInteressa": "x",
        })
        rows = csv_rows if csv_rows is not None else statement_rows(1000, 5000)
        self.files[(doc_id, "5")] = (make_csv_zip(rows), "application/octet-stream")
        self.files[(doc_id, "1")] = (b"PK-xbrl-" + doc_id.encode(), "application/octet-stream")
        self.files[(doc_id, "2")] = (b"%PDF-" + doc_id.encode(), "application/pdf")

    # ------------------------------------------------------------- pedidos

    def count(self, fragment: str) -> int:
        return sum(1 for url, _ in self.calls if fragment in url)

    def get(self, url, params=None, timeout=None, stream=False):
        params = {key: str(value) for key, value in (params or {}).items()}
        self.calls.append((url, params))
        if url == CODELIST_URL:
            return FakeResponse(content=make_codelist_zip(), content_type="application/zip")
        if self.failures:
            return FakeResponse(status=self.failures.pop(0), json_data={"erro": "temporário"})
        if params.get("Subscription-Key") != self.key:
            if self.invalid_as_json:
                return FakeResponse(json_data={
                    "StatusCode": 401,
                    "message": "Access denied due to invalid subscription key.",
                })
            return FakeResponse(status=401, json_data={"statusCode": 401, "message": "Access denied"})

        if url == f"{BASE_URL}/documents.json":
            results = self.docs.get(params["date"], [])
            data = {"metadata": {"status": "200", "message": "OK", "resultset": {"count": len(results)}}}
            if params.get("type") == "2":
                data["results"] = results
            return FakeResponse(json_data=data)

        match = re.fullmatch(re.escape(BASE_URL) + r"/documents/(\w+)", url)
        if match:
            item = self.files.get((match.group(1), params.get("type", "")))
            if item is None:
                return FakeResponse(json_data={"metadata": {"status": "404", "message": "Not Found"}})
            return FakeResponse(content=item[0], content_type=item[1])
        return FakeResponse(status=404, json_data={})


def capcom_edinet() -> FakeEdinet:
    """Cenário usado na maioria dos testes (hoje = 10/10/2025)."""
    fake = FakeEdinet()
    # Anual 2025-03, no prazo. No mesmo período há um documento retirado e ruído de outra empresa.
    fake.add_doc("2025-06-19", "S100RET1", start="2024-04-01", end="2025-03-31", withdrawn=True)
    fake.add_doc("2025-06-20", "S100OUT1", code="E99999", start="2024-04-01", end="2025-03-31")
    fake.add_doc("2025-06-20", "S100FUND", doc_type="030", description="有価証券届出書")
    fake.add_doc("2025-06-20", "S100AN25", start="2024-04-01", end="2025-03-31",
                 csv_rows=statement_rows(169604, 243000, operating=65777))
    # Anual 2024-03 e uma retificação sem período, ligada ao original.
    fake.add_doc("2024-06-21", "S100AN24", start="2023-04-01", end="2024-03-31",
                 csv_rows=statement_rows(152410, 243476, operating=-5))
    fake.add_doc("2024-07-03", "S100RT24", doc_type="130", description="訂正有価証券報告書",
                 parent="S100AN24", csv_rows=statement_rows(152411, 243476, operating=-5))
    # Semestral 2024-09 (formato novo, 半期報告書).
    fake.add_doc("2024-11-08", "S100SE24", doc_type="160", description="半期報告書",
                 start="2024-04-01", end="2024-09-30", csv_rows=statement_rows(56400, 230000))
    # Trimestrais antigos: só o do 2º trimestre (6 meses acumulados) serve como semestral.
    fake.add_doc("2023-11-09", "S100Q3M3", doc_type="140", description="四半期報告書",
                 start="2023-07-01", end="2023-09-30")
    fake.add_doc("2023-11-10", "S100Q223", doc_type="140", description="四半期報告書",
                 start="2023-04-01", end="2023-09-30", csv_rows=statement_rows(74900, 220000))
    # Anual 2023-03 arquivado com atraso (111 dias depois: só aparece na prorrogação).
    fake.add_doc("2023-07-20", "S100AN23", start="2022-04-01", end="2023-03-31")
    return fake
