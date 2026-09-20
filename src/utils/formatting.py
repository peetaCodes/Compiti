from typing import Final, Tuple, Dict

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