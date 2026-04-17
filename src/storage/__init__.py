from pathlib import Path
from src.storage.datatypes import SessionData
from src.storage.saver import MemoryStorage

class Storage: # shared object storing current session data
    _session: SessionData
    _appPath: Path
    _cachePath: Path

    @classmethod
    def load(cls, cachePath: Path, appPath: Path, **kwargs):
        cachePath.mkdir(parents=True, exist_ok=True)
        appPath.mkdir(parents=True, exist_ok=True)

        cls._session = SessionData(**kwargs)
        cls._cachePath = cachePath
        cls._appPath = appPath

    @classmethod
    def session(cls, **kwargs):
        return cls._session

    @classmethod
    def save(cls):
        MemoryStorage.save(cls._cachePath / "session.json", cls._session, coeff=True, seq=True, sched=True)
        MemoryStorage.save(cls._appPath   / "data.json"   , cls._session, pref=True, tasks=True)