from src.index import API
from storage.coder import Coder
from src.storage.datatypes import SessionData, Credentials, TasksStore, Agenda, ENGLISH_SHORT_DAYS
from src.storage.saver import MemoryStorage
from src.gui import UI, PopupMaster, AppRoot
from src.system_utils.assets import *

from pathlib import Path
from userpaths import get_local_appdata
from platformdirs import user_cache_dir

from cryptography.fernet import InvalidToken

class App(UI):
    def __init__(self):
        self.appPath = Path(get_local_appdata(), "School Scheduler")
        self.appPath.mkdir(exist_ok=True)

        self.cachePath = Path(user_cache_dir("School Scheduler", "peetaCodes", "0.1.0", ensure_exists=True))

        self.coder = Coder()
        AppRoot.get_root(
            theme="pulse",
            iconphoto=IMAGES_DIR / "icon.png",
        )

        #key = self.auth()
        key = "peeta"
        try:
            credentials = self.loadCredentials(self.appPath / "credentials.txt", key)
        except InvalidToken:
            self.auth(True) # force re-authentication
            credentials = self.loadCredentials(self.appPath / "credentials.txt", key)

        homework: Agenda = API.getMyHomework(credentials.username, credentials.password)

        del key         # delete the key for security reasons
        del credentials # delete the credentials for security reasons

        self.session = SessionData(
            agenda=homework,
            selectedDays=[],
            tasks=TasksStore(),
            daysCoefficients={},
            schedules={}
        )
        cached_data = MemoryStorage.load(self.cachePath / "session.json", SessionData(daysCoefficients={day:1.0 for day in ENGLISH_SHORT_DAYS[:5]}))
        self.session.selectedDays = cached_data.selectedDays
        self.session.daysCoefficients = cached_data.daysCoefficients
        app_data = MemoryStorage.load(self.appPath / "data.json", SessionData())
        self.session.tasks = app_data.tasks
        self.session.schedules = app_data.schedules

        super().__init__(self.session, self.updateSessison)

        self.agenda()
        self.window.mainloop()

    def updateSessison(self, session: SessionData):
        self.session = session
        MemoryStorage.save(self.cachePath / "session.json", self.session, agenda=False, tasks=False)
        MemoryStorage.save(self.appPath   / "data.json"  , self.session, agenda=False, selected=False, coeff=False, schedules=True)


    def auth(self, force: bool = False) -> str:
        status, response = PopupMaster().showAuthenticationPopup(self.appPath / "credentials.txt", force)
        key = response[-1]  # key in plain text
        if status == 401:
            self.writeCredentials(self.appPath / "credentials.txt", response[0], response[1], key)
        if status == 400:
            exit(0)
        return key

    def writeCredentials(self, path: Path, username: str, password: str, key) -> None:
        with open(path, "wt") as f:
            f.write(username+"\n"+password)
        self.coder.encryptFile(path, key)

    def loadCredentials(self, path: Path, password: str) -> Credentials:
        self.coder.decryptFile(path, password)
        with open(path) as f:
            result = f.read().split("\n")
        self.coder.encryptFile(path, password)

        return Credentials(result[0], result[1])

if __name__ == '__main__':
    App()