import json
from json.decoder import JSONDecodeError
from pathlib import Path
from os.path import exists

from src.storage.datatypes import SessionData

from typing import Union, Optional, Any

class FileSystem:
    def __init__(self) -> None:
        pass

    @classmethod
    def saveFile(cls, path: Path, data: str) -> None:
        with open(path.absolute(), "w", encoding="utf-8") as f:
            f.write(data)

    @classmethod
    def loadFile(cls, path: Path) -> str:
        if not exists(path.absolute()):
            return ""
        with open(path.absolute(), "r", encoding="utf-8") as f:
            return f.read()

class MemoryStorage:
    def __init__(self) -> None:
        pass

    @classmethod
    def load(cls, path: Path, default: Optional[Any] = None) -> SessionData | Any:
        try:
            return SessionData.from_dict(json.loads(path.absolute().read_text()))
        except (JSONDecodeError,FileNotFoundError):
            return default

    @classmethod
    def loadKey(cls, key: str, path: Path, default: Optional[Any] = None) -> dict | Any:
        try:
            return json.loads(path.absolute().read_text())[key]
        except (JSONDecodeError,FileNotFoundError,KeyError):
            return default

    @classmethod
    def save(cls, path: Path, data:SessionData, **kwargs) -> None:
        path.touch()
        with open(path.absolute(), "w") as f:
            json.dump(data.to_dict(**kwargs), f) # noqa