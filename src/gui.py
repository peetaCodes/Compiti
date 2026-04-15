import tkinter

import ttkbootstrap as ttk
from ttkbootstrap.widgets.scrolled import ScrolledFrame, ScrolledText
from ttkbootstrap.constants import *
#from ttkbootstrap.style import Style
from ttkbootstrap.utility import enable_high_dpi_awareness
from tkinter import StringVar, IntVar, DoubleVar

from datetime import date, timedelta
from math import ceil
import re
from calendar import monthrange as last_day_of

from os.path import exists
#from pathlib import Path

import os

from typing import Dict, Tuple, List, Callable, Final, Optional, Any, Union

from src.storage.datatypes import SessionData, Agenda, Event, Task, TasksStore, RawSequence
from src.storage.datatypes import ENGLISH_SHORT_DAYS, ITALIAN_DAYS, ENGLISH_TO_ITALIAN_DAYS, ENGLISH_TO_ITALIAN_MONTHS, ITALIAN_ORDINAL_NUMBERS
from src.system_utils.screen_profiler import getScreenInfo
from src.system_utils.assets.fonts_scaler import createFontsForStyle, applyFontsToStyles, applyOptionsToStyles
from src.algorithm import InputTransformer
from src.algorithm.scheduler import Scheduler
from src.exceptions.exceptions import ScheduleError
from src.system_utils.assets import *

THEME: Final[str] = "pulse"

class Screen:
    dpi: float
    size: Tuple[int, int]
    scaling: float

class AppRoot:
    """A singleton-like root manager for ttkbootstrap applications."""
    _root: Union[None, ttk.Window]  = None

    @classmethod
    def _initRoot(cls, theme:str = THEME, **kwargs):
        if os.name == "nt":  # Windows
            enable_high_dpi_awareness()
            cls._root = ttk.Window(themename=theme, **kwargs)
        else:
            cls._root = ttk.Window(themename=theme, **kwargs)

        Screen.size = (cls._root.winfo_screenwidth(), cls._root.winfo_screenheight())
        Screen.dpi = cls._root.winfo_fpixels('1i')
        Screen.scaling = Screen.dpi / 72

        print(Screen.size, Screen.dpi, Screen.scaling)

        cls._root.minsize(Screen.size[0] // 2, Screen.size[1] // 2)
        cls._root.resizable(True, True)
        cls._root.tk.call("tk", "scaling", Screen.scaling)

        Screen.dpi, Screen.size, Screen.scaling = getScreenInfo(cls._root)

    @classmethod
    def get_root(cls, theme: Optional[str] = THEME, **kwargs):
        if cls._root is None:
            cls._initRoot(theme, **kwargs)

        return cls._root

    @classmethod
    def hide(cls):
        if cls._root is not None:
            cls._root.withdraw()

    @classmethod
    def show(cls):
        if cls._root is not None:
            cls._root.deiconify()

    @classmethod
    def destroy(cls):
        if cls._root is not None:
            cls._root.destroy()
            cls._root = None

class Popup:
    """Base popup handler that ensures a hidden root window exists."""

    def __init__(self, title: str, size: Tuple[int, int] = (600, 400)): #
        self.root = AppRoot.get_root()  # shared root

        # Create the popup as a Toplevel
        self.window = ttk.Toplevel(master=self.root, title=title)
        self.window.geometry(f"{size[0]}x{size[1]}")
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

        self.closed = False

    def show_modal(self):
        """Block until the popup is closed."""
        self.window.grab_set()
        self.window.wait_window()

    def close(self):
        self.closed = True
        self.window.destroy()

    def on_close(self):
        """Default close behavior: mark as closed."""
        self.closed = True
        self.window.destroy()

class PopupMaster:
    def __init__(self, hideRoot = True):
        if hideRoot: AppRoot.hide()  # keep root hidden during popups

        self.usernameVar = StringVar(value="")
        self.passwordVar = StringVar(value="")
        self.keyVar = StringVar(value="")

    @staticmethod
    def popup(title:str = "Generic Popup", size: Tuple[int, int] = (800, 400)):
        popup = Popup(title=title, size=size)

        return popup # return the popup instance for further use

    def ask_credentials(self, oldCredentialsCorrupted: bool, style: str = "primary"):
        popup = self.popup("Inserimento credenziali (CVV)", size=(1000, 650))

        ttk.Label(popup.window, text="Inserisci le credenziali", font="futura 25 bold").pack(pady=20)
        ttk.Label(popup.window, text="""Le credenziali salvate risultano corrotte o eliminate.
Re-inseriscile in modo che il programma possa salvarle""" if oldCredentialsCorrupted else """Dato che è la prima esecuzione del programma, devi inserire le tue credenziali di Classeviva.
Queste verranno usate per scaricare i compiti autonomamente. Verranno criptate per sicurezza""", font="futura 16", justify="center").pack(pady=10)

        ttk.Label(popup.window, text="Username:", font="futura 18", bootstyle=style).pack(pady=5) # noqa
        ttk.Entry(popup.window, textvariable=self.usernameVar).pack(pady=10)
        ttk.Label(popup.window, text="Password:", font="futura 18", bootstyle=style).pack(pady=5) # noqa
        ttk.Entry(popup.window, textvariable=self.passwordVar, show="*").pack(pady=10)
        ttk.Button(popup.window, text="Submit", command=popup.close, bootstyle=style).pack(pady=10) # noqa

        popup.show_modal()
        return self.usernameVar.get(), self.passwordVar.get()

    def ask_key(self, first_time: bool, style: str = "primary"):
        popup = self.popup("Inserimento chiave d'accesso", size=(1000, 650))

        ttk.Label(
            popup.window,
            text=("Inserisci una parola da usare come chiave per criptare le tue credenziali.\nLa dovrai inserire ogni volta che avvierai il programma.\nDeve essere un insieme di caratteri qualsiasi di qualunque lunghezza."
                  if first_time else
                  "Inserisci la chiave d'accesso per decriptare le credenziali"),
            font="futura 16",
            justify="center",
        ).pack(pady=20)
        ttk.Entry(popup.window, textvariable=self.keyVar).pack(pady=10)
        ttk.Button(popup.window, text="Submit", bootstyle=style, command=popup.close).pack(pady=10) # noqa

        popup.show_modal()
        return self.keyVar.get()

    def showAuthenticationPopup(self, path: Path, force: bool = False):
        running = not exists(path) or force
        status = 200

        username = password = None

        if running:
            username, password = self.ask_credentials(force)
            if username and password:
                status = 401
            else:
                status = 400
                return status, ("", "", "")

        key = self.ask_key(first_time=(status == 401))
        if not key:
            status = 400
            return status, ("", "", "")

        if status == 401:
            return status, (username, password, key)
        return status, ("", "", key)

    def showErrorPopup(self, message: str, tb: Optional[str] = None, size: Tuple[int, int] = (800, 400), title: str = "Errore"):
        popup = self.popup(size=size, title=title)

        ttk.Label(popup.window, text="Si è verificato un errore imprevisto:", font="Futura 20 bold").pack(pady=10)
        messageLabel = ttk.Label(popup.window, text=message, font="Inter 20 bold", bootstyle='danger') # noqa
        messageLabel.pack(fill='x', padx=10, pady=10)

        if tb:
            ttk.Label(popup.window, text="Dettagli tecnici:", font="Futura 20 bold").pack(pady=10)
            tracebackBox = ScrolledText(popup.window, font="Futura 16", autohide=True, hbar=True)
            tracebackBox.insert(END, tb) # noqa
            tracebackBox.pack(expand=True, fill='both', padx=10, pady=10)

        infoLabel = ttk.Label(popup.window, text="""Cliccando su 'chiudi' ignorerai l'errore ed andrai avanti con il programma.
Il programma potrebbe chiudersi inavvertitamente oppure malfunzionare dopo questo errore.
Se dopo aver chiuso questa finestra riscontrerai dei problemi, riavvia il programma.

Se vuoi, puoi segnalare questo errore su GitHub sul repository ufficiale: https://github.com/peetaCodes/School-Week_Planner""", font="Futura 16 italic")
        infoLabel.pack(pady=10, padx=20)

        ttk.Button(popup.window, text="Chiudi", command=popup.close, bootstyle="danger").pack(pady=10) # noqa

        popup.show_modal()
        return popup

class UI(Screen):
    def __init__(self, session: SessionData, updater_callback: Any) -> None:
        self.bottomPadding = 20

        self.window = AppRoot.get_root()  # use shared root
        self.origStyle = self.window.style # "snapshot" of the root's <default> style before applying any changes (unless it auto-syncs with self.windw.style, IDK)
        style = self.window.style # local style variable

        specs = {
            "task"   : ("Futura", 1),
            "day"    : ("Futura", 20, "bold"),
            "utility": ("Futura", 3, "normal", "italic")
        }

        fonts = createFontsForStyle(AppRoot.get_root(), Screen.dpi, specs)

        fonts["task_debug"] = tkinter.font.Font(
            root=self.window,
            family="Futura",
            size=-40,  # 40 pixels; positive would mean points
        )

        applyFontsToStyles(style, {
            "task.danger.TButton"  : fonts["task"],
            "task.warning.TButton" : fonts["task"],
            "task.success.TButton" : fonts["task"],
            "day.secondary.TButton": fonts["day"],
            "day.primary.TButton"  : fonts["day"],
            "day.info.TButton"     : fonts["day"],
            "day.dark.TButton"     : fonts["day"],
            "utility.info.TButton" : fonts["utility"]
        })

        applyOptionsToStyles(self.origStyle, {
            "task.danger.TButton"  : {"anchor": "w"},
            "task.warning.TButton" : {"anchor": "w"},
            "task.success.TButton" : {"anchor": "w"},
            "day.secondary.TButton": {"anchor": "w"},
            "day.primary.TButton"  : {"anchor": "w"},
            "day.info.TButton"     : {"anchor": "w"},
            "day.dark.TButton"     : {"anchor": "w"},
            "utility.info.TButton" : {"anchor": "w"}
        })

        print("Futura in Tk?", "Futura" in tkinter.font.families(self.window))
        print("available sample:", [f for f in tkinter.font.families(self.window) if "Fut" in f])
        print("available fonts:", tkinter.font.families(self.window))

        print("style task.danger.TButton:")
        task_font_name = style.lookup("task.danger.TButton", "font")
        print(task_font_name)
        print(tkinter.font.nametofont(task_font_name).actual())

        print("style day.dark.TButton:")
        day_font_name = style.lookup("day.dark.TButton", "font")
        print(day_font_name)
        print(tkinter.font.nametofont(day_font_name).actual())

        print("style utility.info.TButton:")
        utility_font_name = style.lookup("utility.info.TButton", "font")
        print(utility_font_name)
        print(tkinter.font.nametofont(utility_font_name).actual())

        AppRoot.show()  # now reveal it

        self.window.title("School-Week planner")

        self.mainFrame = ttk.Frame(
            self.window,
            bootstyle='light'  # noqa
        )

        self.modes:  Tuple[str, str] = (
            "Visualizzazione compiti",
            "Visualizzazione programma"
        )
        self.mode  : StringVar  = StringVar(value=self.modes[0])

        self._session: SessionData = session
        self._saver: Any = updater_callback

        self.today = date.today()
        self.year  = self.today.year
        self.month = self.today.month
        self.day   = self.today.day

        self.selectedSchedule: StringVar = StringVar(value=tuple(self._session.schedules.keys())[0] if self._session.schedules else "")

        self.STATEMENT = r'(?<=[.!?])\s+(?=[A-ZÀ-ÖØ-Þ])' # A statement is any sequence of at least 20 characters (letters, numbers, spaces and common punctuation marks)
        self.ABBREVIATIONS = [
            "Mr.", "Mrs.", "Ms.", "Dr.", "Prof.", "Prof.sa" "Sr.", "Jr.", "St.",
            "vs.", "etc.", "i.e.", "e.g.", "p.m.", "a.m.",
            "Es.", "Fig.", "Inc.", "Ltd.", "Co.",
            "Dott.", "Sig.", "Sig.ra", "S.p.A.",
            "Pag.", "Cap.", "Art."
        ]

        self._initStage()

    # Button-related functions

    def showAssignment(self, uid: str) -> None:
        amountVar: IntVar = self._session.tasks.get(uid).effortVar
        for e in self._session.agenda:
            if e.id == int(uid):
                event: Event = e
                break
        eventTime: str = self.normalizeMonth(event.startingTime.partition("T")[2].partition("+")[0]) if type(event.startingTime).__name__ != 'NoneType' else 'Tutta la giornata' # noqa
        eventDate: str = self.normalizeMonth(event.date.strftime("%d %b %Y"))
        assignmentPopup = ttk.Toplevel(title=f"Compito del {eventDate}", size=(len(event.author)*15+1250, 750))

        assignmentFrame = ttk.Frame(assignmentPopup)
        ttk.Label       (assignmentFrame, text=f"{event.author} ha assegnato",  font="Futura 30 bold").pack(fill='x')
        ttk.Label       (assignmentFrame, text=f"{eventDate}; {eventTime}\n",  font="Futura 22")     .pack(fill='x')

        body = ScrolledText(assignmentFrame, font="Futura 20", autohide=True, hbar=True)
        body.insert(END, self.processText(event.notes))  # noqa
        body.pack(expand=False, anchor="w")

        effortFrame = ttk.Frame(assignmentPopup)
        effortEntry = ttk.Meter(
            effortFrame,
            bootstyle="primary",
            metersize=450,
            meterthickness=22,
            padding=5,

            amountused=amountVar.get(),
            metertype="full",
            interactive=True,
            subtext="impegno",
            subtextfont="-size 20 -family Futura -weight bold" # noqa
        )

        self._session.tasks.get(uid).effortVar = effortEntry.amountusedvar
        self._saver(self._session)

        resetButton = ttk.Button(
            effortFrame,
            text="Reimposta impegno",
            command=lambda: effortEntry.configure(amountused=0),
            bootstyle="primary" # noqa
        )
        resetButton.pack(side='bottom', pady=10)
        effortEntry.pack(side='left',   padx=10)

        assignmentFrame.pack(side="left", fill='both', expand=True, anchor='w')
        effortFrame.pack(side="right", fill='y', expand=True, anchor='ne')
        assignmentPopup.wait_window()

        if self.mode.get() == self.modes[0]: self.agenda()
        else: self.schedule()

    def createSchedule(self, guides: dict, coefficients: dict[str, float], names:dict[str, str]) -> None:
        self._session.daysCoefficients=coefficients;self._saver(self._session)

        rawSchedule = InputTransformer.generate_schedule_inputs_from_tasks(
            tasksStore=self.getTasksForDays(self._session.tasks, self._session.selectedDays),
            selectedDays=self._session.selectedDays,
            coefficients=coefficients,
            sequences=self._session.sequences,
            sequencesNames=names
        )
        scheduler = Scheduler(**guides)
        for seq in rawSchedule:
            self._session.schedules[seq.name]=scheduler.schedule(seq.days, start_in_days=seq.start_in_days, verbose=True)
        self._saver(self._session)

        self.selectedSchedule = StringVar(value=list(self._session.schedules.keys())[0])

    def previousMonth(self):
        self.month -= 1
        self.month %= 12
        if self.month == 0:
            self.year -= 1
            self.month = 12
        self.agenda()

    def nextMonth(self):
        self.month += 1
        self.month %= 12
        if self.month == 0:
            self.month = 12
        if self.month == 1:
            self.year += 1
        self.agenda()

    # utility functions

    @staticmethod
    def getTime(event: Event) -> Tuple[str, str]:
        return event.startingTime.partition('T')[2].partition('+')[0], event.startingTime.partition('T')[2].partition('+')[0]

    @staticmethod
    def normalizeDay(text):
        for en, it in ENGLISH_TO_ITALIAN_DAYS.items():
            text = text.replace(en, it)
        return text\

    @staticmethod
    def normalizeMonth(text) -> str:
        for en, it in ENGLISH_TO_ITALIAN_MONTHS.items():
            text = text.replace(en, it)
        return text

    @staticmethod
    def getDaysFromTo(staringDay: date, endingDay: date) -> Tuple[date, ...]:
        dayRange: List[date] = []

        for d in (staringDay + timedelta(n) for n in range( (endingDay - staringDay).days+1)):
            dayRange.append(d)

        return tuple(dayRange)

    @staticmethod
    def getDays(agenda: Agenda) -> Tuple[date]:
        days: Dict[str, date] = {}

        event: Event
        for event in agenda:
            if event.date.strftime("%Y-%m-%d") not in days.keys():
                days[event.date.strftime("%Y-%m-%d")] = event.date
        return tuple(days.values()) # noqa

    @staticmethod
    def getEventsForDay(agenda: Agenda, day: date) -> Tuple[Event, ...]:
        events: List[Event] = [] # noqa

        event: Event
        for event in agenda:
            if event.date == day: events.append(event)

        return tuple(events)

    @staticmethod
    def getTasksForDay(tasksStore: TasksStore, day: date) -> TasksStore:
        tasks: TasksStore = TasksStore()

        task: Task
        for tid, task in tasksStore.items():
            if task.due_date == day: tasks.add(uid=tid, due_date=task.due_date, effortVar=task.effortVar)

        return tasks

    @staticmethod
    def getTasksForDays(tasksStore: TasksStore, days: List[date]) -> TasksStore:
        tasksForGivenDays: TasksStore = TasksStore()

        for day in days:
            tasksForGivenDays += UI.getTasksForDay(tasksStore, day)

        return tasksForGivenDays

    def processText(self, text: str) -> str:
        placeholder_map = {}
        for i, abbr in enumerate(self.ABBREVIATIONS):
            placeholder = f"__ABBR{i}__"
            text = text.replace(abbr, placeholder)
            placeholder_map[placeholder] = abbr

        # Now safe to split sentences
        sentences = re.split(self.STATEMENT, text)

        # Restore abbreviations
        sentences = [s.strip() for s in sentences if s.strip()]
        restored = []
        for s in sentences:
            for placeholder, abbr in placeholder_map.items():
                s = s.replace(placeholder, abbr)
            restored.append(s)
        return "\n".join(restored)

    def preProcessSession(self):
        self._session.selectedDays = sorted(self._session.selectedDays)
        today = date.today()
        startingDelta = (self._session.selectedDays[0] - today).days
        sequences: List[RawSequence] = []
        for i, d in enumerate(self._session.selectedDays):
            if (d - self._session.selectedDays[i - 1]).days == 1:
                sequences[-1].days.append(d); continue
            else:
                sequences.append(RawSequence(
                                name=f"sequence_from_{d}",
                                days=[d],
                                start_in_days=startingDelta
                ))
        self._session.sequences = sequences

        GuideConfigurator(self.window, self._session.daysCoefficients, self._session.sequences,
                          self.createSchedule),


    # class functions

    def _emptyScreen(self):
        for child in self.mainFrame.winfo_children():
            child.destroy()

    def _initFrames(self) -> None:
        self.gridFrame = ScrolledFrame(
            self.mainFrame,
            autohide=True,
            width=self.size[0],
            height=self.size[1] - 35 + (self.bottomPadding * 2), # Leave space for the buttons (35 pixels) plus 20 pixels for their vertical padding (both above and under)
            bootstyle='light'
        )
        self.buttonsFrame = ttk.Frame(
            self.mainFrame,
            bootstyle='light' # noqa
        )
        self.modeFrame = ttk.Frame(
            self.mainFrame,
            bootstyle='light' # noqa
        )

    def _initButtons(self) -> None:
        modeButton = ttk.Combobox(self.modeFrame, textvariable=self.mode, values=self.modes, bootstyle="danger") # noqa
        modeButton.config(state='readonly')
        modeButton.bind("<<ComboboxSelected>>", self._updateStage)
        modeButton.pack(pady=10, padx=25, side='left')

        if self.mode.get() == self.modes[0]:
            ttk.Button(self.buttonsFrame, text="Indietro", command=self.previousMonth,
                       style="utility.info.TButton").pack(side='left', padx=20)
            ttk.Button(self.buttonsFrame, text="Avanti", command=self.nextMonth, style="utility.info.TButton").pack(
                side='left')

            self.summit_button = ttk.Button(
                self.buttonsFrame,
                text="Crea programma",
                command=self.preProcessSession,
                style="utility.info.TButton",
                state="disabled"
            )

            self.summit_button.pack(padx=15, side='right')

            self.buttonsFrame.pack(side='bottom', fill='x', pady=self.bottomPadding)

        if self.mode.get() == self.modes[1]:
            scheduleNames: List[str] = list(self._session.schedules.keys())
            if scheduleNames:
                scheduleSelector = ttk.Combobox(
                    self.modeFrame,
                    textvariable=self.selectedSchedule,
                    values=scheduleNames,
                    bootstyle="danger" # noqa
                )
                scheduleSelector.config(state='readonly')
                scheduleSelector.bind("<<ComboboxSelected>>", self._updateStage)
                scheduleSelector.pack(pady=10, padx=25, side='right')

        self.modeFrame.pack(side='top', fill='x')

    def _initStage(self, *args: Optional[Any]) -> None: # noqa
        self._emptyScreen()
        self._initFrames()
        self._initButtons()

        self.mainFrame.pack(fill='both')

    def _updateStage(self, *args: Optional[Any]) -> None: # noqa
        self._emptyScreen()
        self._initFrames()
        self._initButtons()

        if self.mode.get() == self.modes[0]:
            self.agenda()
        else:
            self.schedule()

        self.mainFrame.pack(fill='both')

    def agenda(self) -> None:
        monthDaysRange = last_day_of(self.year, self.month)
        endingDate    : date = date(self.year, self.month, monthDaysRange[1])
        startingDate  : date = date(self.year, self.month, 1)
        startingDelta: int  = monthDaysRange[0]
        endingDelta  : int  = 7 - (ITALIAN_DAYS.index(ENGLISH_TO_ITALIAN_DAYS[endingDate.strftime("%a")])+1) # convert last  weekday from english short ("Mon") to italian full ("Lunedì"), then do a bunch of $hit to get the ending delta.
        days: Tuple[date, ...] = self.getDaysFromTo(staringDay=startingDate, endingDay=endingDate)

        self.summit_button["state"] = "disabled" if not self._session.selectedDays else "normal"

        for child in self.gridFrame.winfo_children(): # remove any remains of previous cells
            child.destroy()

        cols: Final[int] = 7
        rows: Final[int] = ceil( (len(days)+startingDelta+endingDelta) / 7 )

        for i in range(cols):
            self.gridFrame.columnconfigure(i, weight=1, uniform="horizontal")
        for i in range(1, rows + 1):
            self.gridFrame.rowconfigure(i, weight=2)

        for col in range(cols):
            ttk.Label(master=self.gridFrame, text=ITALIAN_DAYS[col], anchor=CENTER, style="day.dark.TButton").grid(
                row=0, column=col, sticky="we", padx=8, pady=4)

        for r in range(1, rows + 1):
            for col in range(cols):
                day: date = startingDate+timedelta(days=col-startingDelta)
                events: Tuple[Event, ...] = self.getEventsForDay(self._session.agenda, day)


                bStyle = "secondary"
                if (col < startingDelta and r == 1) or (day > endingDate): bStyle = "dark"
                elif day == self.today: bStyle = "info"

                if day in self._session.selectedDays: bStyle = "primary"
                style = f"day.{bStyle}.TButton"

                tasksFrame = ttk.Frame(
                    self.gridFrame,
                    bootstyle=bStyle # noqa
                )
                tasksFrame.columnconfigure(0, weight=1)

                dayFrame = ttk.Frame(
                    tasksFrame,
                    bootstyle=bStyle, # noqa
                    height=20
                )  # The label representing the day containing the following tasks needs to have a fixed height, so a separate frame

                dayLabel = ToggleButton(
                    dayFrame,
                    text=self.normalizeMonth(day.strftime("%d %b")),
                    starting_style=style,

                    variable=day,
                    callback=self.agenda,
                    selected_list=self._session.selectedDays,
                    max_length=14
                )
                dayLabel.pack(side='top')

                dayFrame.grid(row=0, column=0)
                tasksFrame.grid(row=r, column=col, padx=2, pady=4, sticky="nswe")

                if not ((col < startingDelta and r == 1) or (day > endingDate)):

                    for i in range(len(events)):
                        tasksFrame.rowconfigure(i+1, weight=12 // len(events))

                    for i, event in enumerate(events):
                        t: str = f'{event.author}\n{event.notes[:36]} {"..." if len(event.notes) >= 35 else ""}'
                        uid: str = str(event.id)
                        var: IntVar = IntVar(value=0)

                        # if it didn't exist, add it manually
                        if not uid in self._session.tasks:
                            self._session.tasks.add(
                                due_date=day,
                                effortVar=var,
                                uid=uid
                            )

                        #print(day in self._session.selectedDays, self._session.tasks.get(uid).effortVar.get())

                        if day not in self._session.selectedDays:
                            s = "task.danger.TButton" if col % 2 == 0 else "task.warning.TButton"
                        else:
                            effort =  self._session.tasks.get(uid).effortVar.get()
                            if effort >= 64:
                                s = "task.danger.TButton"
                            elif 33 <= effort < 64:
                                s = "task.warning.TButton"
                            else :
                                s = "task.success.TButton"

                        button = ttk.Button(
                            tasksFrame,
                            text=t,
                            command=lambda UID=uid: self.showAssignment(UID),
                            style=s
                        )
                        button.grid(row=i+1, column=0, padx=0, pady=2, sticky="nswe")

                        #if uid == "507067": print(*[f"{p}: {repr(getattr(button, p))}" for p in dir(button)], sep="\n") # print all properties of the button for debugging

            startingDate+=timedelta(days=col+1) # noqa

        self.gridFrame.pack(fill='both', padx=15)

        self._saver(self._session)

    def schedule(self) -> None:
        cols = 7
        schedule_name: str = self.selectedSchedule.get()

        for child in self.gridFrame.winfo_children():
            child.destroy()

        scheduler_result: Dict[str, Any] = self._session.schedules.get(schedule_name)

        slot_plan: List[List[Dict[str, Any]]] = scheduler_result.get("slot_plan", [])
        task_completion: List[Dict[str, Any]] = scheduler_result.get("task_completion", [])
        stats: Dict[str, Any] = scheduler_result.get("stats", {"unschedulable": False})

        n_slots = len(slot_plan)
        if "per_due_by_slot" in scheduler_result:
            n_due_days = len(scheduler_result["per_due_by_slot"])
        elif "per_due_totals_required" in stats:
            n_due_days = len(stats["per_due_totals_required"])
        else: raise ScheduleError("Cannot determine number of due days from scheduler result: the provided schedule was malformed.")

        start_in_days = int(stats["start_in_days"]) if "start_in_days" in stats else max(0, n_slots - n_due_days)

        # Build mapping of task totals for pct computation.
        # Task completions include 'task_uid' in your scheduler; we index by (due_day, str(uid))
        task_totals: Dict[Tuple[int, str], float] = {}
        for t in task_completion:
            due = int(t["due_day"])
            uid = t.get("task_uid")
            key = (due, str(uid)) if uid is not None else (due, str(t.get("task_idx")))
            task_totals[key] = float(t["units_required"])

        rows = ceil(n_slots / cols)
        for c in range(cols):
            self.gridFrame.columnconfigure(c, weight=1)
        for r in range(rows + 1):
            self.gridFrame.rowconfigure(r, weight=1)

        # create slot cells
        slot_idx = 0
        for r in range(1, rows + 1):
            for c in range(cols):
                if slot_idx >= n_slots:
                    # empty placeholder
                    placeholder = ttk.Frame(self.gridFrame, height=80, bootstyle="dark") # noqa
                    placeholder.grid(row=r, column=c, padx=6, pady=6, sticky="nswe")
                    slot_idx += 1
                    continue

                cell = ttk.Frame(self.gridFrame, padding=6, bootstyle="secondary") # noqa
                cell.grid(row=r, column=c, padx=6, pady=6, sticky="nswe")
                cell.columnconfigure(0, weight=1)

                # label for the slot
                if slot_idx < start_in_days:
                    slot_label = f"Slot {slot_idx + 1}\n(pre-start)"
                else:
                    schedule_day_for_slot = slot_idx - start_in_days + 1
                    slot_label = f"Slot {slot_idx + 1}\n(night before day {schedule_day_for_slot})"
                ttk.Label(cell, text=slot_label, anchor=CENTER, font="Futura 12 bold", bootstyle='inverse-secondary').grid( # noqa
                    row=0, column=0, sticky="we", pady=(0, 6)
                )

                inner = ttk.Frame(cell)
                inner.grid(row=1, column=0, sticky="nswe")
                inner.columnconfigure(0, weight=1)

                entries = slot_plan[slot_idx] if slot_idx < len(slot_plan) else []
                if not entries:
                    ttk.Label(inner, text="(no tasks)", font="Futura 10 italic", bootstyle='inverse-secondary').pack(anchor="w", pady=4) # noqa
                else:
                    per_slot_total = sum(float(x.get("units", 0.0)) for x in entries)
                    for e in entries:
                        due_day = int(e["due_day"])
                        units = float(e.get("units", 0.0))
                        task_uid_raw = e.get("task_uid")
                        repaired = bool(e.get("repaired", False))

                        uid_display = str(task_uid_raw) if task_uid_raw is not None else f"frag-{due_day}"
                        total_key = (due_day, uid_display)
                        total_units = task_totals.get(total_key, None)
                        pct = (100.0 * units / total_units) if (total_units is not None and total_units > 0.0) else None

                        if pct is not None: txt = f"{uid_display}\n{pct:.1f}% • {units:.2f}u"
                        else: txt = f"{uid_display}\n{units:.2f}u"

                        # choose bootstyle based on pct
                        if pct is not None:
                            if pct >= 50.0: bs = "danger"
                            elif pct >= 25.0: bs = "warning"
                            else: bs = "success"
                        else:
                            ratio = (units / per_slot_total) if per_slot_total > 0 else 0.0
                            if ratio >= 0.5: bs = "danger"
                            elif ratio >= 0.25: bs = "warning"
                            else: bs = "success"

                        def _callback(uid_local=task_uid_raw, uid_raw=task_uid_raw, d=due_day, u=units, p=pct):
                            # if integer uid and present in tasks store, use your popup
                            if uid_local is not None and uid_local in self._session.tasks:
                                self.showAssignment(uid_local)
                                return
                            # else try to find matching event id in agenda (Event.id are ints)
                            if uid_local is not None:
                                for ev in self._session.agenda:
                                    if ev.id == uid_local:
                                        self.showAssignment(uid_local)
                                        return
                            # fallback: small info popup for fragments / unknown UID
                            popup = ttk.Toplevel(size=(600,300))
                            popup.title(f"Task {uid_raw}" if uid_raw is not None else "Fragment")
                            frame = ttk.Frame(popup, padding=12)
                            ttk.Label(frame, text=f"Task {uid_raw}" if uid_raw is not None else "Fragment", font="Futura 20 bold").pack(anchor="w")
                            ttk.Label(frame, text=f"Due schedule day: {d}", font="Futura 14").pack(anchor="w", pady=(6, 0))
                            ttk.Label(frame, text=f"Units in this slot: {u:.2f}u", font="Futura 14").pack(anchor="w", pady=(2, 0))
                            if p is not None:
                                ttk.Label(frame, text=f"Percent of task: {p:.1f}%", font="Futura 14").pack(anchor="w",  pady=(2, 6))
                            ttk.Button(frame, text="Chiudi", command=popup.destroy, bootstyle="primary").pack(anchor="e", pady=(10, 0)) # noqa
                            frame.pack(fill="both", expand=True)
                            popup.grab_set()
                            popup.wait_window()

                        btn = ttk.Button(inner, text=txt, bootstyle=bs, command=_callback) # noqa
                        if repaired:
                            btn.configure(text=btn.cget("text") + "\n(repaired)")
                        btn.pack(fill="x", pady=3)

                slot_idx += 1

        self.gridFrame.pack(fill='both', padx=15)

# specialized button that toggles its style and updates an external list
class ToggleButton(ttk.Button):
    def __init__(self, master, starting_style, variable, selected_list, max_length, callback:Callable, **kwargs):
        super().__init__(master, **kwargs)
        self.variable:      Any        = variable       # The variable to add/remove from the list
        self.callback:      Callable   = callback
        self.selected_list: List[Any]  = selected_list
        self.max_length:    Final[int] = max_length
        self.current_style: str        = starting_style

        # If the style is dark, disable the button
        if "dark" in self.current_style: action = None
        else: action = self.on_click

        self.configure(style=self.current_style, command=action)

    def on_click(self):
        if len(self.selected_list) >= self.max_length and not (self.current_style == "day.primary.TButton" or self.current_style == "day.info.TButton"):
            return # do nothing if the max length is reached and we are trying to select another day
        if self.current_style == "day.secondary.TButton" or self.current_style == "day.info.TButton":
            self.selected_list.append(self.variable)
        else:
            self.selected_list.remove(self.variable)

        self.callback() # Update the parent GUI

class GuideConfigurator(Screen):
    def __init__(self, parent, coefficients, sequences, launch_callback):
        """
        parent: master window or frame
        dpi: your scaling factor
        launch_callback: function(dict) called with guide values when "Launch Training" pressed
        """
        super().__init__()

        self.parent = parent
        self.launch_callback = launch_callback

        # Define the 4 characteristics and default values
        self.guides: Dict[str,str] = {
            "avoid_burnout": "medium",
            "distribute_evenly": "medium",
            "lightness": "medium",
            "finish_early": "medium",
        }

        self.coefficients: List[DoubleVar] = [DoubleVar(value=val) for val in coefficients.values()]
        self.sequences = sequences

        # Create the popup window
        self.popup = ttk.Toplevel(title="Pre-configurazione")
        self.popup.resizable(False, False)

        # Frame for options
        self._days_coeff_container: ttk.Frame = ttk.Frame(self.popup)
        self._days_coeff_container.pack(fill="x", expand=True, padx=5, pady=10)

        self._sched_coeff_container: ttk.Frame = ttk.Frame(self.popup)
        self._sched_coeff_container.pack(fill="both", expand=True, padx=40, pady=30)

        for day in ENGLISH_SHORT_DAYS[:5]:
            self._days_coeff_container.columnconfigure(ENGLISH_SHORT_DAYS.index(day), weight=1)
        for i in range(3):
            self._days_coeff_container.rowconfigure(i, weight=1)

        ttk.Label(
            self._days_coeff_container,
            text="Coefficiente di difficoltà per giorno della settimana (1-2)",
            font=("Segoe UI", 17, "bold")
        ).grid(row=0, column=0, columnspan=len(ENGLISH_SHORT_DAYS), padx=5, pady=10)

        for coeff, day in zip(self.coefficients, ITALIAN_DAYS[:5]):
            ttk.Label(
                self._days_coeff_container,
                text=day,
                font=("Segoe UI", 14)
            ).grid(row=1, column=ITALIAN_DAYS.index(day), padx=5, pady=5)

            ttk.Entry(
                self._days_coeff_container,
                textvariable=coeff,
                font=("Segoe UI", 14)
            ).grid(row=2, column=ITALIAN_DAYS.index(day), padx=5, pady=5)


        # Define row layout
        self.options = [
            ("Preferisci carichi di lavoro omogenei", "distribute_evenly"),
            ("Penalizza la creazione di giorni pesanti", "avoid_burnout"),
            ("Fai in modo di finire i compiti in anticipo", "finish_early"),
            ("Crea giorni più leggeri", "lightness"),
        ]

        self._populate_choices()

        # Launch button
        ttk.Button(
            self.popup,
            text="Invia",
            style="info.TButton",
            command=self._on_launch,
            bootstyle=SUCCESS # noqa
        ).pack(pady=20)

    def _populate_choices(self):
        for child in self._sched_coeff_container.winfo_children(): child.destroy()
        for i, item in enumerate(self.options):
            self._create_option_row(self._sched_coeff_container, i, *item)

    def _create_option_row(self, parent, row, text, key):
        """Create a single labeled row with 3 toggle buttons."""
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=10)

        frame.columnconfigure(0, weight=2)
        for i in range(1, 4 + 1):
            frame.columnconfigure(i, uniform="level")

        ttk.Label(frame, text=text, font="Futura 18").grid(row=row, column=0, padx=(0, 30), sticky="w")

        def make_button(info, style, value, column):
            btn = ttk.Checkbutton(
                frame,
                text=info.capitalize(),
                bootstyle=f"{style}-toolbutton" # noqa
            )
            if self.guides[key]==value: btn.invoke()
            btn.configure(command=lambda: self._set_value(key, value))
            btn.grid(column=column, row=row, padx=5, sticky="e")
            return btn

        self._buttons_for_key = []
        self._buttons_for_key.append(make_button("poco" , "success", "low"   , 1))
        self._buttons_for_key.append(make_button("medio", "warning", "medium", 2))
        self._buttons_for_key.append(make_button("tanto", "danger" , "high"  , 3))

    def _set_value(self, key, value):
        """Update the internal guide dict."""
        self.guides[key] = value
        self._populate_choices()

    def _on_launch(self):
        """Called when the Launch button is pressed."""
        self.popup.destroy()

        names: Dict[str, str] = {}
        seq: RawSequence
        for i, seq in enumerate(self.sequences):
            name_popup = PopupMaster(False).popup(size=(1050, 330), title="Nome programma")
            name_popup.window.resizable(False, False)

            nameVar = StringVar(value="")

            ttk.Label(name_popup.window, text=f"""Inserisci del {ITALIAN_ORDINAL_NUMBERS[i]} programma (da {seq.days[0].strftime("%d %B, %Y")} a {seq.days[-1].strftime("%d %B, %Y")}): """, font=("Futura", 22, "bold"), anchor='center').pack(pady=8, fill='x')
            ttk.Separator(name_popup.window).pack(fill="x", pady=0)
            ttk.Entry(name_popup.window, textvariable=nameVar, font=("Futura", 16)).pack(side='top')
            ttk.Button(name_popup.window, text="Invia", style="utility.info.TButton", command=name_popup.close).pack(side='top', ipady=15)

            name_popup.show_modal()

            names[seq.name]=nameVar.get()

        self.launch_callback(self.guides, {day:val for val, day in zip([var.get() for var in self.coefficients], ENGLISH_SHORT_DAYS)}, names)