from src.index import API
from storage.coder import Coder
from src.storage import Storage
from src.storage.datatypes import Credentials, TasksStore, PreferencesStore, Agenda, ENGLISH_SHORT_DAYS
from src.storage.saver import MemoryStorage
from src.gui import UI, PopupMaster, AppRoot
from src.system_utils.assets import *

from pathlib import Path
from userpaths import get_local_appdata
from platformdirs import user_cache_dir

from cryptography.fernet import InvalidToken

class App(UI):
    def __init__(self):
        AppRoot.get_root(
            themename="pulse",
            iconphoto=IMAGES_DIR / "icon.png",
        )
        super().__init__()  # initialise the UI daemon

        self.appPath = Path(get_local_appdata(), "School Scheduler")
        self.cachePath = Path(user_cache_dir("School Scheduler", "peetaCodes", "0.1.0"))

        preferencesDict = MemoryStorage.loadKey("preferences", self.appPath / "data.json", {})
        Storage.load( # start loading user preferences. Set the rest to default
            cachePath=self.cachePath,
            appPath=self.appPath,

            agenda=Agenda(),
            selectedDays=[],
            tasks=TasksStore(),
            daysCoefficients={day: 1.0 for day in ENGLISH_SHORT_DAYS[:5]},
            schedules={},
            preferences=PreferencesStore.from_dict(preferencesDict),
        )

        self.coder = Coder()

        key = self.auth()
        try:
            credentials = self.loadCredentials(self.appPath / "credentials.txt", key)
        except InvalidToken:
            self.auth(True) # force re-authentication
            credentials = self.loadCredentials(self.appPath / "credentials.txt", key)

        Storage.session().agenda = API.getMyHomework(credentials.username, credentials.password)

        del key         # delete the local key object for security reasons
        del credentials # delete the local credentials object for security reasons

        cached_data = MemoryStorage.load(self.cachePath / "session.json", Storage.session())
        Storage.session().selectedDays = cached_data.selectedDays
        Storage.session().daysCoefficients = cached_data.daysCoefficients

        app_data = MemoryStorage.load(self.appPath / "data.json", Storage.session())
        Storage.session().tasks = app_data.tasks
        Storage.session().schedules = app_data.schedules

        AppRoot.show() # now reveal the app root
        self.agenda()
        self.window.mainloop()

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