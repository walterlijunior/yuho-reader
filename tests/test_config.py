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

import json

from core import config as cfg


def test_configuracao_padrao():
    padrao = cfg.load_config()
    assert padrao.api_key == "" and not padrao.has_key
    assert padrao.pause == 0.5
    assert padrao.output_path.name == "Yuho Reader"


def test_salvar_e_carregar(tmp_path):
    cfg.save_config(cfg.Config(api_key=" abc123 ", output_dir=str(tmp_path / "x"), pause=1.5))
    arquivo = tmp_path / "appdata" / "YuhoReader" / "config.json"
    assert json.loads(arquivo.read_text(encoding="utf-8"))["pause"] == 1.5
    lida = cfg.load_config()
    assert lida.api_key == "abc123" and lida.has_key
    assert lida.output_path == tmp_path / "x"


def test_arquivo_estragado_volta_ao_padrao():
    cfg.config_path().parent.mkdir(parents=True)
    cfg.config_path().write_text("{isto nao e json", encoding="utf-8")
    assert cfg.load_config() == cfg.Config()


def test_limpar_cache(client):
    from datetime import date
    client.cache_dir = cfg.cache_dir()
    client.list_documents(date(2025, 6, 20))
    assert cfg.cache_size()[0] == 1
    assert cfg.clear_cache() == 1
    assert cfg.cache_size() == (0, 0)
