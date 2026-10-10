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

from core.api import EdinetClient
from tests.fake_edinet import KEY, TODAY, capcom_edinet


@pytest.fixture(autouse=True)
def isolated_folders(tmp_path, monkeypatch):
    """Nenhum teste toca nas pastas reais do usuário."""
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "localappdata"))


@pytest.fixture
def fake():
    return capcom_edinet()


@pytest.fixture
def sleeps():
    return []


@pytest.fixture
def make_client(fake, tmp_path, sleeps):
    def factory(key=KEY, pause=0.0, **kwargs):
        kwargs.setdefault("cache_dir", tmp_path / "cache")
        kwargs.setdefault("backoff", 0.0)
        return EdinetClient(key, pause=pause, session=fake, sleep=sleeps.append,
                            today=lambda: TODAY, **kwargs)
    return factory


@pytest.fixture
def client(make_client):
    return make_client()
