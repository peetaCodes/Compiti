from typing import List, Tuple, Optional, Dict, Any
from src.storage.datatypes import InputSequence


class SchedulingError(Exception):
    pass


class Scheduler:
    """
    Deterministic scheduler with human-guidance coefficients.

    New constructor args (each accepts "low"|"medium"|"high"):
      - avoid_burnout: prefer to avoid large single-slot peaks
      - distribute_evenly: prefer even distribution across available slots
      - lightness: try to keep already-light days light (don't overload their preceding slot)
      - finish_early: bias toward earlier slots (finish sooner)

    Behavior: these are combined into per-slot biases during allocation and used
    in a weighted waterfill allocator that still respects slot capacities.
    """

    LEVEL_MAP = {"low": 0.0, "medium": 0.5, "high": 1.0}

    def __init__(
            self,
            max_daily_work: Optional[float] = None,
            eps: float = 1e-12,
            default_start_in_days: int = 0,
            avoid_burnout: str = "medium",
            distribute_evenly: str = "medium",
            lightness: str = "medium",
            finish_early: str = "medium",
            light_avg_threshold: float = 0.25,
    ):
        if max_daily_work is not None and max_daily_work <= 0:
            raise ValueError("max_daily_work must be > 0 or None")
        if default_start_in_days < 0:
            raise ValueError("default_start_in_days must be >= 0")

        self.max_daily_work = float(max_daily_work) if max_daily_work is not None else None
        self.eps = float(eps)
        self.default_start_in_days = int(default_start_in_days)

        def _norm_level(s):
            if s not in self.LEVEL_MAP:
                raise ValueError(f"Level must be one of {list(self.LEVEL_MAP.keys())}")
            return float(self.LEVEL_MAP[s])

        self.avoid_burnout_lvl = _norm_level(avoid_burnout)
        self.distribute_evenly_lvl = _norm_level(distribute_evenly)
        self.lightness_lvl = _norm_level(lightness)
        self.finish_early_lvl = _norm_level(finish_early)
        self.light_avg_threshold = float(light_avg_threshold)

    @staticmethod
    def _flatten_tasks(schedule: List[List[Any]]) -> List[Dict[str, Any]]:
        """
        Accepts two task representations for compatibility:
          - legacy: each day is a list of (effort,) or (effort, difficulty) tuples/lists
          - new:    each day is a list of dicts with a single key UID (str) -> (effort, difficulty)
                    e.g. [{"586458": (40.0, 1.0)}, {"586467": (60.0,1.0)}, ...]
        Returns flat list with entries:
          { due_day, task_idx, task_uid (or None), effort, difficulty, units }
        """
        flat = []
        for day_idx, day in enumerate(schedule):
            due_day = day_idx + 1
            for task_idx, entry in enumerate(day):
                task_uid = None
                difficulty = 1.0

                # new form: dict with single key = uid
                if isinstance(entry, dict):
                    if len(entry) != 1:
                        raise ValueError("Task dict must contain exactly one UID->(effort,difficulty) mapping")
                    # extract uid and tuple
                    uid, tup = next(iter(entry.items()))
                    task_uid = str(uid)
                    if tup is None:
                        raise ValueError("Task mapping value must be a tuple/list (effort[, difficulty])")
                    if isinstance(tup, (tuple, list)) and len(tup) >= 1:
                        effort = float(tup[0])
                        if len(tup) >= 2:
                            difficulty = float(tup[1])
                    else:
                        raise ValueError("Task tuple must be (effort,) or (effort, difficulty)")
                elif isinstance(entry, (tuple, list)):
                    # legacy tuple form
                    effort = float(entry[0])
                    if len(entry) >= 2:
                        difficulty = float(entry[1])
                else:
                    raise ValueError(
                        "Each task must be a dict {uid: (effort,difficulty)} or a (effort[,difficulty]) tuple/list")

                units = effort * difficulty
                flat.append({
                    "due_day": due_day,
                    "task_idx": task_idx,  # ordinal index within the due-day
                    "task_uid": task_uid,  # may be None for legacy inputs
                    "effort": effort,
                    "difficulty": difficulty,
                    "units": units
                })
        return flat

    # --- existing waterfill helpers (unchanged) ---
    @staticmethod
    def _waterfill_distribute(amount: float, slot_indices: List[int], slot_remaining: List[float]) -> Dict[int, float]:
        if amount <= 0:
            return {i: 0.0 for i in slot_indices}
        total_capacity = sum(slot_remaining[i] for i in slot_indices)
        if total_capacity + 1e-12 < amount:
            raise SchedulingError(f"Insufficient capacity to fit amount={amount:.6f} into slots {slot_indices} "
                                  f"(total_capacity={total_capacity:.6f})")

        remaining_amount = amount
        slots = list(slot_indices)
        allocations = {i: 0.0 for i in slot_indices}
        rem = {i: float(slot_remaining[i]) for i in slots}

        while remaining_amount > 1e-12 and slots:
            n = len(slots)
            target = remaining_amount / n
            tight = [i for i in slots if rem[i] <= target + 1e-12]
            if tight:
                for i in tight:
                    allocations[i] += rem[i]
                    remaining_amount -= rem[i]
                    rem[i] = 0.0
                slots = [i for i in slots if i not in tight]
            else:
                for i in slots:
                    allocations[i] += target
                    remaining_amount -= target
                    rem[i] -= target
                break

        for i in allocations:
            if allocations[i] < 1e-14:
                allocations[i] = 0.0
        if remaining_amount > 1e-6:
            raise SchedulingError(f"Could not fully distribute amount; remaining={remaining_amount}")
        return allocations

    @staticmethod
    def _waterfill_distribute_from_caps(amount: float, slots: List[int], rem_cap: Dict[int, float]) -> Dict[int, float]:
        if amount <= 0:
            return {i: 0.0 for i in slots}
        total_capacity = sum(rem_cap.get(i, 0.0) for i in slots)
        if total_capacity + 1e-12 < amount:
            raise SchedulingError(
                f"Insufficient capacity to fit amount={amount:.6f} into slots {slots} (total_capacity={total_capacity:.6f})")

        remaining = float(amount)
        slots_list = list(slots)
        allocations = {i: 0.0 for i in slots_list}
        rem = {i: float(rem_cap.get(i, 0.0)) for i in slots_list}

        while remaining > 1e-12 and slots_list:
            n = len(slots_list)
            target = remaining / n
            tight = [i for i in slots_list if rem[i] <= target + 1e-12]
            if tight:
                for i in tight:
                    allocations[i] += rem[i]
                    remaining -= rem[i]
                    rem[i] = 0.0
                slots_list = [i for i in slots_list if i not in tight]
            else:
                for i in slots_list:
                    allocations[i] += target
                    rem[i] -= target
                    remaining -= target
                break

        for i in list(allocations.keys()):
            if abs(allocations[i]) < 1e-14:
                allocations[i] = 0.0

        if remaining > 1e-6:
            raise SchedulingError(f"Could not fully distribute amount; remaining={remaining}")
        return allocations

    @staticmethod
    def _weighted_waterfill_distribute(amount: float, slot_indices: List[int], slot_remaining: List[float],
                                       slot_bias: Dict[int, float], eps: float = 1e-12) -> Dict[int, float]:
        if amount <= 0:
            return {i: 0.0 for i in slot_indices}

        total_cap = sum(slot_remaining[i] for i in slot_indices)
        if total_cap + eps < amount:
            raise SchedulingError("Insufficient capacity for weighted allocation")

        remaining_amount = float(amount)
        slots = list(slot_indices)
        allocations = {i: 0.0 for i in slot_indices}
        rem_cap = {i: float(slot_remaining[i]) for i in slots}
        bias = {i: max(eps, float(slot_bias.get(i, 1.0))) for i in slots}

        while remaining_amount > eps and slots:
            sum_bias = sum(bias[i] for i in slots)
            if sum_bias <= eps:
                extra = Scheduler._waterfill_distribute_from_caps(remaining_amount, slots, rem_cap)
                for k, v in extra.items():
                    allocations[k] += v
                    rem_cap[k] -= v
                    remaining_amount -= v
                break

            targets = {i: remaining_amount * (bias[i] / sum_bias) for i in slots}
            tight = [i for i in slots if targets[i] >= rem_cap[i] - 1e-12]
            if tight:
                for i in tight:
                    give = rem_cap[i]
                    allocations[i] += give
                    remaining_amount -= give
                    rem_cap[i] = 0.0
                slots = [i for i in slots if i not in tight]
            else:
                for i in slots:
                    allocations[i] += targets[i]
                    rem_cap[i] -= targets[i]
                    remaining_amount -= targets[i]
                break

        for i in allocations:
            if abs(allocations[i]) < 1e-14:
                allocations[i] = 0.0

        if remaining_amount > 1e-6:
            raise SchedulingError(f"Weighted allocation incomplete: remaining={remaining_amount:.8f}")
        return allocations

    # --- bias computation unchanged ---
    def _compute_slot_bias(self, n_slots: int, per_slot_totals: List[float], day_totals: List[float],
                           start_in_days: int) -> Dict[int, float]:
        bias = {}
        max_slot_total = max(max(per_slot_totals) if per_slot_totals else 0.0, 1e-8)
        total_units = sum(day_totals) if day_totals else 1.0
        n = max(1, n_slots - 1)

        for s in range(n_slots):
            finish_component = 1.0 + self.finish_early_lvl * ((n - s) / n)
            even_gap = (max_slot_total - per_slot_totals[s]) / (max_slot_total + self.eps)
            combined_even_level = 0.5 * (self.distribute_evenly_lvl + self.avoid_burnout_lvl)
            even_component = 1.0 + combined_even_level * even_gap

            light_component = 1.0
            if s >= start_in_days:
                due_idx = s - start_in_days
                if 0 <= due_idx < len(day_totals):
                    day_total = day_totals[due_idx]
                    day_norm = float(day_total) / (1.0 + total_units)
                    if day_norm <= self.light_avg_threshold and self.lightness_lvl > 0.0:
                        light_component = max(0.1, 1.0 - 0.5 * self.lightness_lvl)

            b = finish_component * even_component * light_component
            bias[s] = float(max(self.eps, b))

        return bias

    # ---------------- main scheduling function (adapted to UIDs) ----------------
    def schedule(self, schedule: InputSequence, *, start_in_days: Optional[int] = None,
                 verbose: bool = False) -> Dict[str, Any]:
        start_in_days = self.default_start_in_days if start_in_days is None else int(start_in_days)
        if start_in_days < 0:
            raise ValueError("start_in_days must be >= 0")

        n_due_days = len(schedule)
        if n_due_days == 0:
            return {
                "units_schedule": [],
                "slot_plan": [],
                "readable_schedule": [],
                "task_completion": [],
                "stats": {"unschedulable": False},
            }

        flat_tasks = self._flatten_tasks(schedule)
        n_slots = start_in_days + n_due_days

        if self.max_daily_work is None:
            big = sum(t["units"] for t in flat_tasks) + 1.0
            slot_remaining = [big for _ in range(n_slots)]
        else:
            slot_remaining = [float(self.max_daily_work) for _ in range(n_slots)]

        per_slot_totals = [0.0 for _ in range(n_slots)]
        units_schedule = [[0.0 for _ in range(n_due_days)] for _ in range(n_slots)]
        slot_plan: List[List[Dict[str, Any]]] = [[] for _ in range(n_slots)]

        flat_tasks_sorted = sorted(flat_tasks, key=lambda x: x["due_day"])

        unschedulable = False
        insufficient_details = []
        task_completion = []

        day_totals = [sum(((t[0] if isinstance(t, (list, tuple)) else next(iter(list(t.values())))[0])
                           * ((t[1] if isinstance(t, (list, tuple)) and len(t) > 1 else
                               (next(iter(list(t.values())))[1] if isinstance(t, dict) else 1.0)))
                           ) for t in schedule[d]) for d in range(n_due_days)]

        # schedule tasks EDF as before, but store task_uid when present
        for task in flat_tasks_sorted:
            orig_due_idx = task["due_day"] - 1
            units = float(task["units"])
            if units <= 1e-12:
                task_completion.append({
                    "due_day": task["due_day"],
                    "task_idx": task["task_idx"],
                    "task_uid": task.get("task_uid"),
                    "units_required": 0.0,
                    "units_assigned": 0.0,
                    "completed_before_due": True,
                })
                continue

            due_slot_index = start_in_days + orig_due_idx
            available_slots = list(range(0, due_slot_index + 1))

            slot_bias_map = self._compute_slot_bias(n_slots, per_slot_totals, day_totals, start_in_days)
            slot_bias_local = {i: slot_bias_map[i] for i in available_slots}

            try:
                alloc_map = self._weighted_waterfill_distribute(amount=units,
                                                                slot_indices=available_slots,
                                                                slot_remaining=slot_remaining,
                                                                slot_bias=slot_bias_local,
                                                                eps=self.eps)
            except SchedulingError:
                try:
                    alloc_map = self._waterfill_distribute(amount=units, slot_indices=available_slots,
                                                           slot_remaining=slot_remaining)
                except SchedulingError:
                    unschedulable = True
                    total_avail = sum(slot_remaining[i] for i in available_slots)
                    deficit = units - total_avail
                    insufficient_details.append({
                        "orig_due_day_index": orig_due_idx,
                        "due_day": task["due_day"],
                        "task_idx": task["task_idx"],
                        "task_uid": task.get("task_uid"),
                        "units_required": units,
                        "total_available_on_window": total_avail,
                        "deficit": deficit,
                        "available_slots": available_slots,
                    })
                    break

            for slot_idx, amt in alloc_map.items():
                if amt <= 1e-14:
                    continue
                units_schedule[slot_idx][orig_due_idx] += amt
                slot_plan[slot_idx].append({
                    "due_day": task["due_day"],
                    "task_idx": task["task_idx"],
                    "task_uid": task.get("task_uid"),  # new: propagate uid
                    "units": amt
                })
                slot_remaining[slot_idx] -= amt
                per_slot_totals[slot_idx] += amt

            total_assigned = sum(alloc_map.values())
            completed_before_due = abs(total_assigned - units) <= 1e-6
            task_completion.append({
                "due_day": task["due_day"],
                "task_idx": task["task_idx"],
                "task_uid": task.get("task_uid"),
                "units_required": units,
                "units_assigned": total_assigned,
                "completed_before_due": completed_before_due,
            })

        # ---------- REPAIR PASS (task-aware) ----------
        def repair_deadline_violations():
            nonlocal units_schedule, slot_plan, slot_remaining, per_slot_totals, unschedulable, insufficient_details
            for d in range(n_due_days):
                due_day = d + 1
                last_allowed_slot = start_in_days + d
                late_slots = [s for s in range(last_allowed_slot + 1, n_slots)]
                if not late_slots:
                    continue

                # gather late entries (slot,index,entry)
                late_entries = []
                for s in late_slots:
                    for e in list(slot_plan[s]):
                        if int(e.get("due_day", -999)) == due_day:
                            late_entries.append((s, e))

                if not late_entries:
                    continue

                for (orig_slot, entry) in late_entries:
                    late_amt = float(entry.get("units", 0.0))
                    if late_amt <= 1e-12:
                        continue

                    # remove first matching entry from orig_slot
                    removed = False
                    new_entries = []
                    for ent in slot_plan[orig_slot]:
                        if (not removed
                                and int(ent.get("due_day", -999)) == due_day
                                and int(ent.get("task_idx", -999)) == int(entry.get("task_idx", -999))
                                and abs(float(ent.get("units", 0.0)) - late_amt) <= 1e-9):
                            removed = True
                            per_slot_totals[orig_slot] -= float(ent.get("units", 0.0))
                            slot_remaining[orig_slot] += float(ent.get("units", 0.0))
                            units_schedule[orig_slot][d] -= float(ent.get("units", 0.0))
                            continue
                        new_entries.append(ent)
                    slot_plan[orig_slot] = new_entries

                    legal_slots = list(range(0, last_allowed_slot + 1))
                    rem_cap = {i: float(slot_remaining[i]) for i in legal_slots}
                    try:
                        moved = Scheduler._waterfill_distribute_from_caps(late_amt, legal_slots, rem_cap)
                    except SchedulingError:
                        unschedulable = True
                        total_avail = sum(slot_remaining[i] for i in legal_slots)
                        deficit = late_amt - total_avail
                        insufficient_details.append({
                            "orig_due_day_index": d,
                            "due_day": due_day,
                            "task_idx": entry.get("task_idx"),
                            "task_uid": entry.get("task_uid"),
                            "units_required_to_repair": late_amt,
                            "total_available_on_window": total_avail,
                            "deficit": deficit,
                            "available_slots": legal_slots,
                        })
                        return

                    for t_slot, amt in moved.items():
                        if amt <= 1e-12:
                            continue
                        units_schedule[t_slot][d] += amt
                        slot_plan[t_slot].append({
                            "due_day": due_day,
                            "task_idx": entry.get("task_idx", -1),
                            "task_uid": entry.get("task_uid"),
                            "units": amt,
                            "repaired": True,
                        })
                        slot_remaining[t_slot] -= amt
                        per_slot_totals[t_slot] += amt

        repair_deadline_violations()
        # ---------- end repair pass ----------

        # Build readable_schedule & compact_readable (use task_uid when present)
        readable_schedule = []
        compact_readable = []
        for slot_idx in range(n_slots):
            # grouped by due_day for readable_schedule
            grouped_by_due = {}
            for e in slot_plan[slot_idx]:
                grouped_by_due[e["due_day"]] = grouped_by_due.get(e["due_day"], 0.0) + float(e["units"])
            parts = []
            for due, amt in sorted(grouped_by_due.items()):
                day_total = day_totals[due - 1] if 0 <= (due - 1) < len(day_totals) else 0.0
                pct = (100.0 * amt / day_total) if day_total > 0 else 0.0
                parts.append(f"{pct:.2f}% of due-day {due} -> {amt:.3f}u")
            readable_schedule.append(
                f"Slot {slot_idx + 1}: " + "; ".join(parts) if parts else f"Slot {slot_idx + 1}: do nothing")

            # compact_readable: merge by (due_day, task_uid or task_idx)
            merged = {}
            for e in slot_plan[slot_idx]:
                key = (e["due_day"], e.get("task_uid") if e.get("task_uid") is not None else e.get("task_idx"))
                merged[key] = merged.get(key, 0.0) + float(e["units"])
            parts_c = []
            for (due, tkey), amt in sorted(merged.items()):
                day_total = day_totals[due - 1] if 0 <= (due - 1) < len(day_totals) else 0.0
                pct = 100.0 * amt / day_total if day_total > 0 else 0.0
                label = f"Task({tkey})" if isinstance(tkey, (str,)) else f"Task(due{due}, idx{tkey})"
                parts_c.append(f"{pct:.1f}% of {label} -> {amt:.2f}u")
            compact_readable.append(
                f"Slot {slot_idx + 1}: " + "; ".join(parts_c) if parts_c else f"Slot {slot_idx + 1}: do nothing")

        per_slot_totals = [sum(units_schedule[s]) for s in range(n_slots)]
        per_due_totals_assigned = [sum(units_schedule[s][d] for s in range(n_slots)) for d in range(n_due_days)]
        per_due_totals_required = day_totals

        stats = {
            "per_slot_totals": per_slot_totals,
            "per_due_totals_assigned": per_due_totals_assigned,
            "per_due_totals_required": per_due_totals_required,
            "unschedulable": unschedulable,
            "insufficient_details": insufficient_details,
            "n_slots": n_slots,
            "start_in_days": start_in_days,
        }
        if self.max_daily_work is not None and unschedulable:
            total_units_req = sum(per_due_totals_required)
            stats["minimal_uniform_capacity_suggested"] = total_units_req / max(1, n_slots)

        result = {
            "units_schedule": units_schedule,
            "slot_plan": slot_plan,
            "readable_schedule": readable_schedule,
            "compact_readable": compact_readable,
            "task_completion": task_completion,
            "per_due_by_slot": [[units_schedule[s][d] for s in range(n_slots)] for d in range(n_due_days)],
            "stats": stats,
            "preferences": {
                "avoid_burnout": self.avoid_burnout_lvl,
                "distribute_evenly": self.distribute_evenly_lvl,
                "lightness": self.lightness_lvl,
                "finish_early": self.finish_early_lvl,
            }
        }
        if verbose:
            result["slot_remaining_after_schedule"] = slot_remaining
            result["per_slot_totals"] = per_slot_totals
            result["slot_bias_example"] = self._compute_slot_bias(n_slots, per_slot_totals, day_totals, start_in_days)
        return result


# ---------------- human-friendly formatter that understands UIDs ----------------
def format_human_readable_schedule(
        schedule: List[List[Any]],
        scheduler_result: Dict[str, Any],
        *,
        start_in_days: int = 1,
        pct_of: str = "task",  # "task" or "day"
        round_pct: int = 1,
        show_units: bool = True,
) -> List[str]:
    """
    Formats scheduler_result.slot_plan using UIDs when present.

    schedule: same structure passed to Scheduler.schedule()
    scheduler_result: dict returned by Scheduler.schedule(...), expects 'slot_plan'
    """
    slot_plan = scheduler_result.get("slot_plan", [])
    n_slots = len(slot_plan)

    # Build task unit lookup: key is (due_day, task_uid) if uid present, else (due_day, task_idx)
    task_units: Dict[Tuple[int, Any], float] = {}
    day_totals = []
    for d_idx, day in enumerate(schedule):
        total = 0.0
        for t_idx, task in enumerate(day):
            if isinstance(task, dict):
                if len(task) != 1:
                    raise ValueError("Each task dict must have single uid->(effort,diff)")
                uid, tup = next(iter(task.items()))
                effort = float(tup[0])
                difficulty = float(tup[1]) if len(tup) >= 2 else 1.0
                units = effort * difficulty
                task_units[(d_idx + 1, str(uid))] = units
                total += units
            elif isinstance(task, (tuple, list)):
                effort = float(task[0])
                difficulty = float(task[1]) if len(task) >= 2 else 1.0
                units = effort * difficulty
                task_units[(d_idx + 1, t_idx)] = units
                total += units
            else:
                raise ValueError("Task must be dict(uid->tuple) or tuple/list")
        day_totals.append(total)

    lines: List[str] = []
    warnings: List[str] = []

    for slot_idx in range(n_slots):
        entries = slot_plan[slot_idx]
        if slot_idx < start_in_days:
            slot_desc = f"Slot {slot_idx + 1} (pre-start / padding)"
        else:
            schedule_day_for_slot = slot_idx - start_in_days + 1
            slot_desc = f"Slot {slot_idx + 1} (night before schedule day {schedule_day_for_slot})"

        if not entries:
            lines.append(f"{slot_desc}:\n  do nothing")
            continue

        # merge by (due_day, task_key) where task_key is uid when present else idx
        merged: Dict[Any, Dict[str, Any]] = {}
        for e in entries:
            due = int(e.get("due_day", -1))
            task_uid = e.get("task_uid")
            task_key = task_uid if task_uid is not None else int(e.get("task_idx", -1))
            key = (due, task_key)
            rec = merged.get(key, {"units": 0.0, "repaired": False})
            rec["units"] += float(e.get("units", 0.0))
            if e.get("repaired"):
                rec["repaired"] = True
            merged[key] = rec

        parts = []
        for (due_day, tkey), info in sorted(merged.items(), key=lambda x: (x[0][0], str(x[0][1]))):
            amt = info["units"]
            units_total = task_units.get((due_day, tkey), None)
            if pct_of == "task" and units_total and units_total > 0.0:
                pct = 100.0 * (amt / units_total)
            elif pct_of == "day":
                day_total = day_totals[due_day - 1] if 1 <= due_day <= len(day_totals) else 0.0
                pct = 100.0 * (amt / day_total) if day_total > 0.0 else 0.0
            else:
                pct = 100.0 * (amt / (units_total or 1.0))

            pct_fmt = f"{round(pct, round_pct):.{round_pct}f}%"
            units_str = f" -> {amt:.2f}u" if show_units else ""
            label = f"task {tkey}" if isinstance(tkey, str) else f"task {tkey + 1}"

            # sanity check: warn only if not repaired
            last_allowed_slot = start_in_days + (due_day - 1)
            if slot_idx > last_allowed_slot + 1e-9 and not info.get("repaired", False):
                warnings.append(
                    f"WARNING: allocation for due-day {due_day} appears in slot {slot_idx + 1} which is after allowed last slot {last_allowed_slot}."
                )

            parts.append(f"Do {pct_fmt} of {label} (due schedule day {due_day}){units_str}")

        body = "\n  ".join(parts)
        lines.append(f"{slot_desc}:\n  {body}")

    if warnings:
        lines.append("\nWarnings:")
        for w in sorted(set(warnings)):
            lines.append("  " + w)

    return lines