from dataclasses import dataclass, field
from typing import TypedDict, List, Dict, Any, Optional, Callable, Tuple, get_origin, get_args, Union, Final
from tkinter import IntVar
from datetime import date

# -------------------------

# ---- application-specific type aliases ---

STRING_DATE = str  # date in "YYYY-MM-DD" format
STRING_ARG  = str  # a class argument stored as a literal string

UID = str


DATE_DICT = List[int]

EVENT_DICT  = dict[
    STRING_ARG, Union[Optional[int], Optional[str], Optional[bool]],
]

AGENDA_DICT = List[EVENT_DICT]
SELECTED_DAYS_DICT = List[DATE_DICT]

TASK_DICT = dict[
    STRING_ARG, Union[DATE_DICT, int]
]

TASK_STORE_DICT = Dict[UID, TASK_DICT]
SESSION_DATA_DICT = dict[STRING_ARG, Union[AGENDA_DICT, SELECTED_DAYS_DICT, TASK_STORE_DICT]]

# --- Formatting utils ---
ENGLISH_SHORT_DAYS: Final[Tuple[str, str, str, str, str, str, str]] = (
    "Mon",
    "Tue",
    "Wed",
    "Thu",
    "Fri",
    "Sat",
    "Sun"
)

ITALIAN_DAYS: Final[Tuple[str, str, str, str, str, str, str]] = (
    "Lunedì",
    "Martedì",
    "Mercoledì",
    "Giovedì",
    "Venerdì",
    "Sabato",
    "Domenica"
)

ENGLISH_TO_ITALIAN_DAYS: Final[Dict[str, str]] = {
    "Mon": "Lunedì",
    "Tue": "Martedì",
    "Wed": "Mercoledì",
    "Thu": "Giovedì",
    "Fri": "Venerdì",
    "Sat": "Sabato",
    "Sun": "Domenica"
}

ITALIAN_TO_ENGLISH_DAYS: Final[Dict[str, str]] = {
    "Lunedì": "Mon",
    "Martedì": "Tue",
    "Mercoledì": "Wed",
    "Giovedì": "Thu",
    "Venerdì": "Fri",
    "Sabato": "Sat",
    "Domenica": "Sun"
}

ENGLISH_TO_ITALIAN_MONTHS: Final[Dict[str, str]] = {
    "Jan": "Gennaio",
    "Feb": "Febbraio",
    "Mar": "Marzo",
    "Apr": "Aprile",
    "May": "Maggio",
    "Jun": "Giugno",
    "Jul": "Luglio",
    "Aug": "Agosto",
    "Sep": "Settembre",
    "Oct": "Ottobre",
    "Nov": "Novembre",
    "Dec": "Dicembre"
}

ITALIAN_ORDINAL_NUMBERS: Final[Tuple[str, str, str, str, str, str, str, str, str, str]] = (
    "primo",
    "secondo",
    "terzo",
    "quarto",
    "quinto",
    "sesto",
    "settimo",
    "ottavo",
    "nono",
    "decimo",
)

# --- Scheduler-related type aliases ---
TaskDict = Dict[UID, Tuple[float, float]]  # uid -> (effort, weekday_coeff)
InputDay = List[TaskDict]
InputSequence = List[InputDay]

# --- API-related type aliases for the application's internal use ---

class CvvEventDict(TypedDict, total=True):
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
class CvvAgentaList(List):
    pass

class ArgoEventDict(TypedDict, total=True):
    evtDatetimeBegin: str
    evtDatetimeEnd: str
    notes: str
    authorName: str
    classDesc: str
    subjectDesc: str
class ArgoAgendaList(List):
    pass

# --- application-specific datatypes ---
@dataclass
class Task:
    due_date: date
    effortVar: IntVar

    def to_dict(self) -> TASK_DICT:
        return {
            "due_date": dateToDict(self.due_date),
            "effort": self.effortVar.get()
        }

@dataclass
class TasksStore:
    _tasks: dict[UID, Task] = field(default_factory=dict[UID, Task])

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
        effortVar: Optional[IntVar] = None,
    ):

        self._tasks[uid] = Task(due_date, effortVar)

    def get(self, uid: UID) -> Optional[Task]:
        return self._tasks.get(uid)

    def remove(self, uid: UID) -> None:
        self._tasks.pop(uid, None)

    def list(self) -> List[Task]:
        return list(self._tasks.values())

    def to_dict(self) -> TASK_STORE_DICT:
        return {tid: t.to_dict() for tid, t in self._tasks.items()}

    @classmethod
    def from_dict(cls, data: Dict[UID, TASK_DICT]) -> "TasksStore":
        store = cls()
        for tid, d in data.items():
            store._tasks[str(tid)] = Task(
                due_date=date(*d.get("due_date")),
                effortVar=IntVar(value=d.get("effort"))
            )
        return store

# TODO: Add support for other APIs if needed

# --- ClasseViva Data Types ---
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

"""
Just for testing type overloading logic; not actually correct
# --- ARGO Data Types ---

class _ArgoEvent:
    startingTime: str
    endingTime: str
    notes: str
    author: str
    className: str
    subjectName: str

@dataclass
class _ArgoAgenda:
    schedules: List[_ArgoEvent]
"""

# -------------------------
# Generic datatypes used by application
# -------------------------
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

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "date": [self.date.year, self.date.month, self.date.day],
            "startingTime": self.startingTime,
            "endingTime": self.endingTime,
            "isFullDay": self.isFullDay,
            "notes": self.notes,
            "author": self.author,
            "className": self.className,
            "subjectId": self.subjectId,
            "subjectName": self.subjectName,
            "homeworkId": self.homeworkId,
        }

@dataclass
class Agenda:
    _schedules: list[Event] = field(default_factory=list[Event])

    def __eq__(self, other) -> bool:
        return self._schedules == other

    def __iter__(self):
        return self._schedules.__iter__()

    def to_dict(self):
        return [event.to_dict() for event in self._schedules]

    @classmethod
    def from_dict(cls, data: AGENDA_DICT) -> "Agenda":
        store = cls()
        for ev in data:
            store._schedules.append(
                Event(
                    id=ev.get("id"),
                    code=ev.get("code"),
                    date=date(*ev.get("startingTime").partition("T")[0].split("-")),
                    startingTime=ev.get("startingTime").partition("T")[2],
                    endingTime=ev.get("endingTime").partition("T")[2],
                    isFullDay=ev.get("isFullDay"),
                    notes=ev.get("notes"),
                    author=ev.get("author"),
                    className=ev.get("className"),
                    subjectId=ev.get("subjectId"),
                    subjectName=ev.get("subjectName"),
                    homeworkId=ev.get("homeworkId")
                )
            )
        return store

# --- Conversion system utils ---
def _isInstanceOfAnnotation(value: Any, annotation) -> bool:
    if annotation is Any:
        return True
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is None:
        if isinstance(annotation, type):
            return isinstance(value, annotation)
        return True
    if origin is Union:
        for sub in args:
            if sub is type(None) and value is None:
                return True
            if sub is not type(None) and _isInstanceOfAnnotation(value, sub):
                return True
        return False
    if origin is list:
        if not isinstance(value, list):
            return False
        if not args:
            return True
        subtype = args[0]
        return all(_isInstanceOfAnnotation(v, subtype) for v in value)
    if origin is dict:
        if not isinstance(value, dict):
            return False
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

# --- Registry and decorators for Conversion Functions ---
EventHandler = Tuple[Callable[[dict], bool], Callable[[dict], Event], str]
AgendaHandler = Tuple[Callable[[List[dict]], bool], Callable[[List[dict]], Agenda], str]

_EVENT_REGISTRY: List[EventHandler] = []
_AGENDA_REGISTRY: List[AgendaHandler] = []

def registerEvent(*, typedict=None, predicate: Callable[[dict], bool]=None, name: Optional[str]=None):
    if typedict is not None and predicate is None:
        predicate = _makeTypedictPredicate(typedict)
    if predicate is None:
        raise ValueError("typedict or predicate is required")
    def deco(func: Callable[[dict], Event]):
        n = name or func.__name__
        _EVENT_REGISTRY.insert(0, (predicate, func, n))
        return func
    return deco

def registerAgenda(*, element_typedict=None, predicate: Callable[[List[dict]], bool]=None, name: Optional[str]=None):
    if element_typedict is not None and predicate is None:
        elem_pred = _makeTypedictPredicate(element_typedict)
        def list_pred(l: List[dict]) -> bool:
            if not isinstance(l, list):
                return False
            return all(elem_pred(item) for item in l)
        predicate = list_pred
    if predicate is None:
        raise ValueError("element_typedict or predicate is required")
    def deco(func: Callable[[List[dict]], Agenda]):
        n = name or func.__name__
        _AGENDA_REGISTRY.insert(0, (predicate, func, n))
        return func
    return deco

# --- Conversion functions ---

def toEvent(payload: dict) -> Event:
    if not isinstance(payload, dict):
        raise TypeError("toEvent expects a dict-like payload")

    for pred, handler, name in _EVENT_REGISTRY:
        if pred(payload):
            return handler(payload)
    raise TypeError("No registered event converter matched payload")

def toAgenda(payload: Union[List[Any], Any]) -> Agenda:
    if isinstance(payload, Agenda):
        return payload

    if not isinstance(payload, list):
        raise TypeError("toAgenda expects a list of dicts")

    for pred, handler, name in _AGENDA_REGISTRY:
        if pred(payload):
            return handler(payload)

    # Fallback: convert element-wise using toEvent
    events: List[Event] = []
    for item in payload:
        if not isinstance(item, dict):
            raise TypeError("Agenda items must be dict-like")
        events.append(toEvent(item))
    return Agenda(_schedules=events)

# --- ClasseViva converters ---
@registerEvent(typedict=CvvEventDict, name="CVV")
def _cvvToEvent(d: CvvEventDict) -> Event:
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
        subjectId=int(d.get("subjectId")) if d.get("subjectId") is not None else None,
        subjectName=d.get("subjectDesc"),
        homeworkId=int(d.get("homeworkId")) if d.get("homeworkId") is not None else None
    )

@registerAgenda(element_typedict=CvvEventDict, name="CVVAgenda")
def _cvvToAgenda(lst: List[CvvEventDict]) -> Agenda:
    return Agenda(_schedules=[_cvvToEvent(item) for item in lst])

"""
Just for testing type overloading logic; not actually correct
# --- ARGO converters ---
@registerEvent(typedict=ArgoEventDict, name="ARGO")
def _argoToEvent(d: ArgoEventDict) -> Event:
    return Event(
        id=None,
        code=None,
        date=date(*d.get("evtDatetimeBegin").partition("T")[0].split("-")),
        startingTime=d.get("evtDatetimeBegin"),
        endingTime=d.get("evtDatetimeEnd"),
        isFullDay=None,
        notes=d.get("notes"),
        author=d.get("authorName"),
        className=d.get("classDesc"),
        subjectId=None,
        subjectName=d.get("subjectDesc"),
        homeworkId=None
    )

@registerAgenda(element_typedict=ArgoEventDict, name="ARGOAgenda")
def _argoToAgenda(lst: List[ArgoEventDict]) -> Agenda:
    return Agenda(_schedules=[_argoToEvent(item) for item in lst])
"""

# Other conversion functions

def dateToDict(d: date):
    return [int(v) for v in d.strftime("%Y %m %d").split(" ")]

def dateFromDict(d: DATE_DICT):
    return date(d[0], d[1], d[2])

# --- Other application Data Types ---

@dataclass
class RawSequence:
    name: Optional[str]
    start_in_days: int
    days: List[date]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "start_in_days": self.start_in_days,
            "days": [dateToDict(d) for d in self.days]
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RawSequence":
        return cls(
            name=d.get("name", ""),
            start_in_days=d.get("start_in_days", 0),
            days=[dateFromDict(dd) for dd in d.get("days", [])]
        )

    def __iter__(self):
        return self.days.__iter__()

@dataclass
class ProcessedSequence:
    name: Optional[str]
    start_in_days: int
    days: List[InputDay]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "start_in_days": self.start_in_days,
            "days": self.days
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ProcessedSequence":
        return cls(
            name=d.get("name", ""),
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
    daysCoefficients: dict[str, float] = field(default_factory=dict[str, float])
    sequences: list[RawSequence] = field(default_factory=list[RawSequence])
    schedules: dict[str, dict[str, Any]] = field(default_factory=dict[str, dict[str, Any]])

    def __bool__(self) -> bool:
        if type(self) == type(None): return False
        if self.agenda == [] and self.selectedDays == [] and self.tasks == {} and self.daysCoefficients == []: return False
        return True

    def properties(self) -> Tuple[Union[str, None], Union[str, None], Union[str, None], Union[str, None]]:
        return "Agenda" if self.agenda else None, "SelectedDays" if self.selectedDays else None, "Tasks" if self.selectedDays else None, "Coefficients" if self.daysCoefficients else None

    def keys(self) -> Tuple[Agenda, List[date], TasksStore, Dict[str, float]]:
        return self.agenda, self.selectedDays, self.tasks, self.daysCoefficients

    def types(self):
        return tuple([type(self.agenda), type(self.selectedDays), type(self.tasks), type(self.daysCoefficients)])

    def to_dict(self, agenda: bool = True, selected: bool = True, tasks:bool = True, coeff:bool = True, seq:bool = False, schedules:bool = False) -> SESSION_DATA_DICT:
        out = {}
        if agenda:out["agenda"] = self.agenda.to_dict()
        if selected:out["selected_days"] = [dateToDict(d) for d in self.selectedDays]
        if tasks:out["tasks"] = self.tasks.to_dict()
        if coeff:out["days_coefficients"] = self.daysCoefficients
        if seq:out["sequences"] = [seq.to_dict() for seq in self.sequences]
        if schedules:out["schedules"] = self.schedules
        return out

    @classmethod
    def from_dict(cls, d:SESSION_DATA_DICT) -> "SessionData":
        return cls(
            agenda=Agenda.from_dict(d.get("agenda", [])),
            selectedDays=[dateFromDict(dVar) for dVar in d.get( "selected_days", [])], # noqa
            tasks=TasksStore.from_dict(d.get("tasks", {})),
            daysCoefficients=d.get("days_coefficients", {day: 1 for day in ITALIAN_DAYS}), # noqa
            sequences=d.get("sequences", []), # noqa
            schedules=d.get("schedules", {})
        )


@dataclass
class Credentials:
    username: str
    password: str