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

"""Pastas do programa e configurações do usuário.

A chave da API fica somente em %APPDATA%\\YuhoReader\\config.json.
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

APP_DIR_NAME = "YuhoReader"
OUTPUT_DIR_NAME = "Yuho Reader"
DEFAULT_PAUSE = 0.5


def config_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(base) / APP_DIR_NAME


def local_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / APP_DIR_NAME


def cache_dir() -> Path:
    return local_dir() / "cache"


def config_path() -> Path:
    return config_dir() / "config.json"


def documents_dir() -> Path:
    """Pasta Documentos do Windows (respeita redirecionamento para o OneDrive)."""
    try:
        import ctypes
        from ctypes import wintypes

        class GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", wintypes.DWORD),
                ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD),
                ("Data4", ctypes.c_ubyte * 8),
            ]

        # FOLDERID_Documents = {FDD39AD0-238F-46AF-ADB4-6C85480369C7}
        folder_id = GUID(
            0xFDD39AD0, 0x238F, 0x46AF,
            (ctypes.c_ubyte * 8)(0xAD, 0xB4, 0x6C, 0x85, 0x48, 0x03, 0x69, 0xC7),
        )
        buffer = ctypes.c_wchar_p()
        result = ctypes.windll.shell32.SHGetKnownFolderPath(
            ctypes.byref(folder_id), 0, None, ctypes.byref(buffer)
        )
        if result == 0 and buffer.value:
            path = Path(buffer.value)
            ctypes.windll.ole32.CoTaskMemFree(buffer)
            return path
    except Exception:
        pass
    return Path.home() / "Documents"


def default_output_dir() -> Path:
    return documents_dir() / OUTPUT_DIR_NAME


@dataclass
class Config:
    api_key: str = ""
    output_dir: str = ""
    pause: float = DEFAULT_PAUSE

    @property
    def output_path(self) -> Path:
        return Path(self.output_dir) if self.output_dir else default_output_dir()

    @property
    def has_key(self) -> bool:
        return bool(self.api_key.strip())


def load_config() -> Config:
    try:
        data = json.loads(config_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return Config()
    config = Config()
    if isinstance(data, dict):
        config.api_key = str(data.get("api_key") or "").strip()
        config.output_dir = str(data.get("output_dir") or "")
        try:
            config.pause = max(0.0, float(data.get("pause", DEFAULT_PAUSE)))
        except (TypeError, ValueError):
            config.pause = DEFAULT_PAUSE
    return config


def save_config(config: Config) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")


def cache_size() -> tuple[int, int]:
    """Devolve (quantidade de arquivos, bytes) guardados no cache."""
    files = [p for p in cache_dir().rglob("*") if p.is_file()]
    return len(files), sum(p.stat().st_size for p in files)


def clear_cache() -> int:
    count, _ = cache_size()
    shutil.rmtree(cache_dir(), ignore_errors=True)
    return count
