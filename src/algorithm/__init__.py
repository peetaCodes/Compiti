from typing import List, Dict, Tuple, Any
from datetime import date

from src.storage.datatypes import ENGLISH_SHORT_DAYS, UID, InputDay, RawSequence, ProcessedSequence

class InputTransformer:
    def __init__(self):
        pass

    @classmethod
    def generate_schedule_inputs_from_tasks(
            cls,
            tasksStore,
            selectedDays: List[date],
            coefficients: Dict[str, float],
            sequences: List[RawSequence],
            sequencesNames: Dict[str, str],
            *,
            require_presence: bool = True,
    ) -> List[ProcessedSequence]:
        """
        Convert TasksStore + chosen calendar days -> scheduler input structure grouped into sequences.

        Args:
          tasksStore: TasksStore instance (as in your code). Uses tasks_store.items() or tasks_store.list().
          selectedDays: list of datetime.date objects (order may be arbitrary). The function groups them
                         into consecutive-date sequences.
          coefficients: mapping like {'Mon': 1.0, 'Tue': 1.6, ...}. Missing keys default to 1.0.
          sequences: mapping from start_in_days -> list of datetime.date objects (consecutive days).
          sequencesNames: mapping from original (generated) sequence names to new (customized) names.
          require_presence: if True and some selected_days contain no tasks, they will still appear as empty day dicts.
                            If False, days with zero tasks are dropped from sequences (not usually desired).
        Returns:
          dict: keys are integers `start_in_days` (days between `today` and that sequence's first date),
                values are sequences (lists of per-day dicts). Each per-day dict maps uid -> (effort, coeff).
                Example:
                {
                  1: [  # sequence starting 1 day from today
                        { uid1: (40, 1.0), uid2: (20, 1.6) },  # day 1
                        { uid3: (10, 1.0) },                   # day 2
                      ],
                  5: [ ... ]  # another sequence starting 5 days from today
                }

        Notes:
          - `effort` is read from `task.effortVar.get()` (works for Tk IntVar-like objects). If the attribute
            doesn't have `.get()`, the value is used directly.
          - UIDs keep their original Python type (int or str).
        """
        if not selectedDays:
            return []

        def weekday_coeff_for(d: date) -> float:
            name = ENGLISH_SHORT_DAYS[d.weekday()]
            return float(coefficients.get(name, 1.0))

        # build lookup: due_date -> list of (uid, task)
        out: List[ProcessedSequence] = []
        due_lookup: Dict[date, List[Tuple[UID, Any]]] = {}
        for uid, task in tasksStore.items():
            due_lookup.setdefault(task.due_date, []).append((uid, task))

        for seq in sequences:

            if seq.name and seq.name in sequencesNames:
                seq.name = sequencesNames[seq.name]

            seq_days_list: List[InputDay] = []
            for d in seq:
                day: InputDay = []
                tasks_for_day = due_lookup.get(d, [])
                if tasks_for_day:
                    for uid, task in tasks_for_day:
                        coeff = weekday_coeff_for(d)
                        day.append({uid: (task.effortVar.get(), coeff)})

                elif require_presence:
                    day = []

                seq_days_list.append(day)

            out.append(
                ProcessedSequence(
                    name=seq.name,
                    start_in_days=seq.start_in_days,
                    days=seq_days_list
                )
            )

        return out