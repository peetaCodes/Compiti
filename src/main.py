from src.index import Client
from src.storage.coder import Coder
from src.storage import Storage
from src.storage.datatypes import Credentials, TasksStore, PreferencesStore, Agenda
from src.storage.saver import MemoryStorage
from src.gui import UI, PopupMaster, AppRoot, Defaults
from src.utils.assets import *
from src.utils.formatting import ENGLISH_SHORT_DAYS

from pathlib import Path
from userpaths import get_local_appdata
from platformdirs import user_cache_dir

from cryptography.fernet import InvalidToken

class App(UI):
    def __init__(self):
        self.appPath = Path(get_local_appdata(), "School Scheduler")
        self.cachePath = Path(user_cache_dir("School Scheduler", "peetaCodes", "0.1.0"))
        Storage.load(  # Init empty session data
            cachePath=self.cachePath,
            appPath=self.appPath,

            agenda=Agenda(),
            selectedDays=[],
            tasks=TasksStore(),
            daysCoefficients={day: 1.0 for day in ENGLISH_SHORT_DAYS[:5]},
            schedules={},
            preferences=Defaults.defaultPreferences(),
        )

        # load only the system preferences
        preferencesDict = MemoryStorage.loadKey("preferences", self.appPath / "data.json", {})
        Storage.session().preferences = PreferencesStore.from_dict(preferencesDict, Defaults.defaultPreferences())

        AppRoot.get_root(
            themename=Storage.session().preferences.theme,
            iconphoto=IMAGES_DIR / "icon.png"
        )
        super().__init__()  # initialise the UI daemon

        self.coder = Coder()

        #key = self.auth()
        key = "peeta"
        try:
            credentials = self.loadCredentials(self.appPath / "credentials.txt", key)
        except InvalidToken:
            self.auth(True) # force re-authentication
            credentials = self.loadCredentials(self.appPath / "credentials.txt", key)

        Storage.session().agenda = Client.getMyHomework(credentials.username, credentials.password)

        del key         # delete the key object from memory for security reasons
        del credentials # delete the credentials object from memory for security reasons

        cached_data = MemoryStorage.load(self.cachePath / "session.json", Defaults.defaultPreferences(), Storage.session())
        Storage.session().selectedDays = cached_data.selectedDays
        Storage.session().daysCoefficients = cached_data.daysCoefficients

        app_data = MemoryStorage.load(self.appPath / "data.json", Defaults.defaultPreferences(), Storage.session())
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

    def loadCredentials(self, path: Path, key: str) -> Credentials:
        self.coder.decryptFile(path, key)
        with open(path) as f:
            result = f.read().split("\n")
        self.coder.encryptFile(path, key)

        return Credentials(result[0], result[1])

if __name__ == '__main__':
    App()