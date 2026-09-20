from dataclasses import dataclass, field
from typing import TypedDict, NamedTuple, List, Dict, Any, Optional, Callable, Tuple, get_origin, get_args, Union, Literal, NotRequired
from tkinter import IntVar
from tkinter.font import Font
from datetime import date

from src.utils.formatting import ITALIAN_DAYS

# ---- type aliases ----

type StringDate = str  # date in "YYYY-MM-DD" format
type UID = str

type EventPredicate = Callable[[dict], bool]
type EventConverter = Callable[[dict], Event]
type AgendaPredicate = Callable[[list[dict]], bool]
type AgendaConverter = Callable[[list[dict]], Agenda]

EventHandler = Tuple[EventPredicate, EventConverter, str]
AgendaHandler = Tuple[AgendaPredicate, AgendaConverter, str]

_EVENT_REGISTRY: List[EventHandler] = []
_AGENDA_REGISTRY: List[AgendaHandler] = []

# typing pickled datatypes

class DateList(NamedTuple):
    year: int
    month: int
    day: int

class EventDict(TypedDict, total=True):
    id: int
    code: str
    date: DateList
    startingTime: str
    endingTime: str
    isFullDay: bool
    notes: str
    author: str
    className: str
    subjectId: int
    subjectName: str
    homeworkId: int

class TaskDict(TypedDict, total=True):
    due_date: DateList
    effort: int

class PreferencesStoreDict(TypedDict, total=True):
    theme: str
    font_family: str
    font_size: int
    scroll_sensitivity: float | int
    fonts: dict[str, str]

class RawSequenceDict(TypedDict, total=True):
    name: str
    start_in_days: int
    days: List[DateList]

class ProcessedSequenceDict(TypedDict, total=True):
    name: str
    start_in_days: int
    days: List[ScheduleDay]

class SessionDataDict(TypedDict, total=True):
    agenda: NotRequired[AgendaDict]
    selected_days: NotRequired[list[DateList]]
    tasks: NotRequired[TaskStoreDict]
    days_coefficients: NotRequired[dict[str, float]]
    sequences: NotRequired[list[RawSequenceDict]]
    schedules: NotRequired[dict[str, dict[str, Any]]]
    preferences: NotRequired[PreferencesStoreDict]

type SelectedDaysList = List[DateList]
type AgendaDict = List[EventDict]
type TaskStoreDict = Dict[UID, TaskDict]

# (algorithm/)scheduler type aliases
type ScheduleTask = Dict[UID, Tuple[float, float]]  # uid -> (effort, weekday_coeff)
type ScheduleDay = List[ScheduleTask]
type InputSequence = List[ScheduleDay]

def dateToList(d: date) -> DateList:
    return DateList(*[int(v) for v in d.strftime("%Y-%m-%d").split("-")])

def dateFromList(d: DateList) -> date:
    return date(d[0], d[1], d[2])


# --- Generic datatypes used by application ---

@dataclass
class Task:
    dueDate: date
    effortVar: IntVar

    def __str__(self):
        return f"Compiti.Task(dueDate={self.dueDate}, effortVar={self.effortVar})"

    def to_dict(self) -> TaskDict:
        return {
            "due_date": dateToList(self.dueDate),
            "effort": self.effortVar.get()
        }

@dataclass
class TasksStore:
    _tasks: dict[UID, Task] = field(default_factory=dict[UID, Task])

    def __str__(self) -> str:
        return str(self._tasks)

    def __contains__(self, item) -> bool:
        return item in self._tasks

    def __bool__(self) -> bool:
        return bool(self._tasks)

    def __eq__(self, other) -> bool:
        return self._tasks == other

    def __len__(self) -> int:
        return len(self._tasks)

    def __add__(self, other: "TasksStore"):
        return TasksStore({**self._tasks, **other._tasks})

    def __getitem__(self, item):
        return self._tasks[item]

    def keys(self):
        return self._tasks.keys()

    def values(self):
        return self._tasks.values()

    def items(self):
        return self._tasks.items()

    def add(
        self,
        uid: str,
        due_date: date,
        effortVar: IntVar,
    ):

        self._tasks[uid] = Task(due_date, effortVar)

    def get(self, uid: UID) -> Optional[Task]:
        return self._tasks.get(uid)

    def remove(self, uid: UID) -> None:
        self._tasks.pop(uid, None)

    def list(self) -> List[Task]:
        return list(self._tasks.values())

    def to_dict(self) -> TaskStoreDict:
        return {tid: t.to_dict() for tid, t in self._tasks.items()}

    @classmethod
    def from_dict(cls, data: Dict[UID, TaskDict]) -> "TasksStore":
        store = cls()
        for tid, d in data.items():
            store._tasks[str(tid)] = Task(
                dueDate=dateFromList(d.get("due_date")),
                effortVar=IntVar(value=int(d.get("effort", 0)))
            )
        return store

@dataclass
class Event:
    id: Optional[int]
    code: Optional[str]
    date: date
    startingTime: Optional[str]
    endingTime: Optional[str]
    isFullDay: Optional[bool]
    notes: Optional[str]
    author: Optional[str]
    className: Optional[str]
    subjectId: Optional[int]
    subjectName: Optional[str]
    homeworkId: Optional[int]

    def __str__(self) -> str:
        return f"Compiti.Event(id={self.id}, date={self.date}, subjectId={self.subjectId}, subjectName={self.subjectName})"

@dataclass
class Agenda:
    _schedules: list[Event] = field(default_factory=list[Event])

    def __str__(self) -> str:
        return str(self._schedules)

    def __eq__(self, other) -> bool:
        return self._schedules == other

    def __iter__(self):
        return self._schedules.__iter__()

    @classmethod
    def from_dict(cls, data: AgendaDict) -> "Agenda":
        store = cls()
        for ev in data:
            store._schedules.append(
                Event(
                    id=int(ev.get("id", 0)),
                    code=str(ev.get("code")),
                    date=date(*str(ev.get("startingTime")).partition("T")[0].split("-")),
                    startingTime=str(ev.get("startingTime")).partition("T")[2],
                    endingTime=str(ev.get("endingTime")).partition("T")[2],
                    isFullDay=bool(ev.get("isFullDay")),
                    notes=str(ev.get("notes")),
                    author=str(ev.get("author")),
                    className=str(ev.get("className")),
                    subjectId=int(ev.get("subjectId", 0)),
                    subjectName=str(ev.get("subjectName")),
                    homeworkId=int(ev.get("homeworkId", 0))
                )
            )
        return store

@dataclass
class PreferencesStore:
    theme: str
    fontFamily: str
    fontSize: int
    scrollSensitivity: float | int
    fonts: dict[str, str | Font]

    def __str__(self) -> str:
        return f"Compiti.PreferencesStore(theme={self.theme}, fontFamily={self.fontFamily}, fontSize={self.fontSize}, scrollSensitivity={self.scrollSensitivity})"

    def to_dict(self) -> PreferencesStoreDict:
        fonts_json: dict[str, str] = {}
        for fname, fobj in self.fonts.items():
            if type(fobj) is Font:
                fonts_json[fname] = fobj.name

        return {
            "theme": self.theme,
            "font_family": self.fontFamily,
            "font_size": self.fontSize,
            "scroll_sensitivity": self.scrollSensitivity,
            "fonts": fonts_json
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any], default: PreferencesStore) -> "PreferencesStore":
        return cls(
            theme=d.get("theme", default.theme),
            fontFamily=d.get("font_family", default.fontFamily),
            fontSize=d.get("font_size", default.fontSize),
            scrollSensitivity=d.get("scroll_sensitivity", default.scrollSensitivity),
            fonts=d.get("fonts", default.fonts)
        )

@dataclass
class RawSequence:
    name: str
    start_in_days: int
    days: List[date]

    def __str__(self) -> str:
        return f"Compiti.RawSquence(name={self.name}, start_in_days={self.start_in_days})"

    def to_dict(self) -> RawSequenceDict:
        return {
            "name": self.name,
            "start_in_days": self.start_in_days,
            "days": [dateToList(d) for d in self.days]
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RawSequence":
        return cls(
            name=d.get("name", "none"),
            start_in_days=d.get("start_in_days", 0),
            days=[dateFromList(dd) for dd in d.get("days", [])]
        )

    def __iter__(self):
        return self.days.__iter__()

@dataclass
class ProcessedSequence:
    name: str
    start_in_days: int
    days: List[ScheduleDay]

    def __str__(self) -> str:
        return f"Compiti.ProcessedSequence(name={self.name}, start_in_days={self.start_in_days})"

    def to_dict(self) -> ProcessedSequenceDict:
        return {
            "name": self.name,
            "start_in_days": self.start_in_days,
            "days": self.days
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ProcessedSequence":
        return cls(
            name=d.get("name", "none"),
            start_in_days=d.get("start_in_days", 0),
            days=d.get("days", [])
        )

    def __iter__(self):
        return self.days.__iter__()

@dataclass
class SessionData:
    agenda: Agenda = field(default_factory=Agenda)
    selectedDays: list[date] = field(default_factory=list[date])
    tasks: TasksStore = field(default_factory=TasksStore)
    daysCoefficients: dict[str, float | int] = field(default_factory=dict[str, float | int])
    sequences: list[RawSequence] = field(default_factory=list[RawSequence])
    schedules: dict[str, dict[str, Any]] = field(default_factory=dict[str, dict[str, Any]])
    preferences: PreferencesStore = field(default_factory=PreferencesStore)

    def __str__(self) -> str:
        return f"Compiti.SessionData(daysCoefficients={self.daysCoefficients}, sequences={self.sequences}, preferences={self.preferences})"

    def __bool__(self) -> bool:
        if (self.agenda == [] and
            self.selectedDays == [] and
            self.tasks == {} and
            self.daysCoefficients == [] and
            self.sequences == [] and
            self.schedules == {} and
            self.preferences == {}
        ): return False
        return True

    def __getitem__(self, item: Literal["agenda", "selectedDays", "tasks", "daysCoefficients", "schedules", "preferences", "sequences"]):
        match item:
            case "agenda": return self.agenda
            case "selectedDays": return self.selectedDays
            case "tasks": return self.tasks
            case "daysCoefficients": return self.daysCoefficients
            case "sequences": return self.sequences
            case "schedules": return self.schedules
            case "preferences": return self.preferences

    def properties(self) -> Tuple[Union[str, None], Union[str, None], Union[str, None], Union[str, None]]:
        return "Agenda" if self.agenda else None, "SelectedDays" if self.selectedDays else None, "Tasks" if self.selectedDays else None, "Coefficients" if self.daysCoefficients else None

    def keys(self) -> Tuple[Agenda, List[date], TasksStore, Dict[str, float]]:
        return self.agenda, self.selectedDays, self.tasks, self.daysCoefficients

    def types(self):
        return tuple([type(self.agenda), type(self.selectedDays), type(self.tasks), type(self.daysCoefficients)])

    def to_dict(
            self,
            selected: bool = False,
            tasks:bool = False,
            coeff:bool = False,
            seq:bool = False,
            sched:bool = False,
            pref: bool = False,
    ) -> SessionDataDict:

        out: SessionDataDict = {}
        if selected:out["selected_days"] = [dateToList(d) for d in self.selectedDays]
        if tasks:out["tasks"] = self.tasks.to_dict()
        if coeff:out["days_coefficients"] = self.daysCoefficients
        if seq:out["sequences"] = [seq.to_dict() for seq in self.sequences]
        if sched:out["schedules"] = self.schedules
        if pref:out["preferences"] = self.preferences.to_dict()
        return out

    @classmethod
    def from_dict(cls, d:SessionDataDict, default_preferences: PreferencesStore) -> "SessionData":
        return cls(
            preferences=PreferencesStore.from_dict(d.get("preferences", {}), default_preferences),
            agenda=Agenda.from_dict(d.get("agenda", [])),
            selectedDays=[dateFromList(dVar) for dVar in d.get("selected_days", [])], # noqa
            tasks=TasksStore.from_dict(d.get("tasks", {})),
            daysCoefficients=d.get("days_coefficients", {day: 1 for day in ITALIAN_DAYS}), # noqa
            sequences=d.get("sequences", []), # noqa
            schedules=d.get("schedules", {})
        )

@dataclass
class Credentials:
    username: str
    password: str


# --- Conversion system utils ---

def toEvent(payload: dict) -> Event:
    if not isinstance(payload, dict):
        raise TypeError("toEvent expects a dict-like payload")

    for pred, handler, name in _EVENT_REGISTRY:
        if pred(payload):
            return handler(payload)
    raise TypeError("No registered event converter matched payload")

def toAgenda(payload: Union[List[Any], Any]) -> Agenda:
    if not isinstance(payload, list):
        raise TypeError("toAgenda expects a list of dicts")

    for pred, handler, _ in _AGENDA_REGISTRY:
        if pred(payload): # does the given raw agenda match with this API?
            return handler(payload)

    # Fallback: convert element-wise using toEvent
    events: List[Event] = []
    for item in payload:
        if not isinstance(item, dict):
            raise TypeError("Agenda items must be dict-like")
        events.append(toEvent(item))
    return Agenda(_schedules=events)


# --- (internal) API-specific to generic conversion helpers ---

def _isInstanceOfAnnotation(value: Any, annotation) -> bool:
    if annotation is Any: return True

    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is None:
        if isinstance(annotation, type): return isinstance(value, annotation)
        return True

    if origin is Union:
        for sub in args:
            if sub is type(None) and value is None: return True
            if sub is not type(None) and _isInstanceOfAnnotation(value, sub): return True
        return False

    if origin is list:
        if not isinstance(value, list): return False
        if not args: return True
        subtype = args[0]
        return all(_isInstanceOfAnnotation(v, subtype) for v in value)

    if origin is dict:
        if not isinstance(value, dict): return False
        if len(args) >= 2:
            valueType = args[1]
            return all(_isInstanceOfAnnotation(v, valueType) for v in value.values())
        return True
    return True

def _makeTypedictPredicate(typedict_cls) -> Callable[[dict], bool]:
    ann = getattr(typedict_cls, '__annotations__', {})
    total = getattr(typedict_cls, '__total__', True)
    def pred(d: dict) -> bool:
        if not isinstance(d, dict): return False
        if len(d.keys()) != len(ann.keys()): return False

        for key, typ in ann.items():
            if key not in d:
                if total:return False
                else:continue

            if not _isInstanceOfAnnotation(d[key], typ):
                return False
        return True

    return pred

def _makeListPredicate(element_pred) -> Callable[[list], bool]:
    def pred(l: List[dict]) -> bool:
        if not isinstance(l, list):
            return False
        return all(element_pred(item) for item in l)
    return pred

# --- (internal) API-specific to generic conversion ---

def registerEvent(*, predicate: Callable[[dict], bool], name: Optional[str]=None):
    def deco(func: Callable[[dict], Event]):
        n = name or func.__name__
        _EVENT_REGISTRY.insert(0, (predicate, func, n))
        return func
    return deco

def registerAgenda(*, predicate: Callable[[List[dict]], bool], name: Optional[str]=None):
    def deco(func: Callable[[List[dict]], Agenda]):
        n = name or func.__name__
        _AGENDA_REGISTRY.insert(0, (predicate, func, n))
        return func
    return deco


# TODO: Add support for other APIs if needed

# --- ClasseViva-specific datatypes and converters---

@dataclass
class _CvvEvent:
    uid: str
    code: str
    startingTime: str
    endingTime: str
    isFullDay: bool
    notes: str
    author: str
    className: str
    subjectId: Union[int, None]
    subjectName: Union[str, None]
    homeworkId: Union[int, None]

@dataclass
class _CvvAgenda:
    schedules: List[_CvvEvent]

class _CvvEventDict(TypedDict, total=True):
    evtId: int
    evtCode: str
    evtDatetimeBegin: str
    evtDatetimeEnd: str
    isFullDay: bool
    notes: str
    authorName: str
    classDesc: str
    subjectId: Union[int, None]
    subjectDesc: Union[str, None]
    homeworkId: Union[int, None]

type _CvvAgendaList = List[_CvvEventDict]


_cvvEventPredicate = _makeTypedictPredicate(_CvvEventDict)
_cvvAgendaPredicate = _makeListPredicate(_cvvEventPredicate)

@registerEvent(name="CVVEvent", predicate=_cvvEventPredicate)
def _cvvToEvent(d: _CvvEventDict) -> Event:
    return Event(
        id=d.get("evtId"),
        code=d.get("evtCode"),
        date=date(*tuple(map(int, d.get("evtDatetimeBegin").partition("T")[0].split("-")))),
        startingTime=d.get("evtDatetimeBegin"),
        endingTime=d.get("evtDatetimeEnd"),
        isFullDay=bool(d.get("isFullDay")),
        notes=d.get("notes"),
        author=d.get("authorName"),
        className=d.get("classDesc"),
        subjectId=d.get("subjectId"),
        subjectName=d.get("subjectDesc"),
        homeworkId=d.get("homeworkId")
    )

@registerAgenda(name="CVVAgenda", predicate=_cvvAgendaPredicate)
def _cvvToAgenda(lst: List[_CvvEventDict]) -> Agenda:
    return Agenda(_schedules=[_cvvToEvent(item) for item in lst])