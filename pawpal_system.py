import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional


@dataclass
class Task:
    """Represents a single pet care activity."""
    id: int
    description: str
    due_time: datetime
    duration_mins: int = 15
    priority: str = "Medium"   # "Low" | "Medium" | "High"
    frequency: str = "Once"    # "Once" | "Daily" | "Weekly"
    is_completed: bool = False

    def mark_complete(self):
        """Mark this task as done."""
        self.is_completed = True

    def priority_score(self) -> int:
        """Return a numeric score for sorting (higher = more urgent)."""
        return {"High": 3, "Medium": 2, "Low": 1}.get(self.priority, 0)

    def to_dict(self) -> dict:
        """Serialize to a JSON-safe dictionary."""
        return {
            "id": self.id,
            "description": self.description,
            "due_time": self.due_time.isoformat(),
            "duration_mins": self.duration_mins,
            "priority": self.priority,
            "frequency": self.frequency,
            "is_completed": self.is_completed,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Task":
        """Deserialize from a dictionary produced by to_dict()."""
        return cls(
            id=d["id"],
            description=d["description"],
            due_time=datetime.fromisoformat(d["due_time"]),
            duration_mins=d["duration_mins"],
            priority=d["priority"],
            frequency=d["frequency"],
            is_completed=d["is_completed"],
        )


@dataclass
class Pet:
    """Represents a pet profile."""
    id: int
    name: str
    species: str
    age: int
    tasks: List[Task] = field(default_factory=list)

    def add_task(self, task: Task):
        """Add a care task to this pet."""
        self.tasks.append(task)

    def get_pending_tasks(self) -> List[Task]:
        """Return all tasks that are not yet completed."""
        return [t for t in self.tasks if not t.is_completed]

    def to_dict(self) -> dict:
        """Serialize to a JSON-safe dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "species": self.species,
            "age": self.age,
            "tasks": [t.to_dict() for t in self.tasks],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Pet":
        """Deserialize from a dictionary produced by to_dict()."""
        pet = cls(id=d["id"], name=d["name"], species=d["species"], age=d["age"])
        pet.tasks = [Task.from_dict(t) for t in d.get("tasks", [])]
        return pet


@dataclass
class Owner:
    """Represents the pet owner and their daily care capacity."""
    name: str
    available_minutes: int = 120   # default: 2 hours of care time per day
    pets: List[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet):
        """Add a pet to this owner's roster."""
        self.pets.append(pet)

    def get_all_tasks(self) -> List[tuple]:
        """Return (pet_name, task) tuples for every pending task across all pets."""
        return [
            (pet.name, task)
            for pet in self.pets
            for task in pet.get_pending_tasks()
        ]

    def total_task_minutes(self) -> int:
        """Sum of duration across all pending tasks for all pets."""
        return sum(task.duration_mins for _, task in self.get_all_tasks())

    def owner_summary(self) -> str:
        """Return a one-line summary string for display purposes."""
        return f"{self.name} ({self.available_minutes} min, {len(self.pets)} pet(s))"

    def to_dict(self) -> dict:
        """Serialize the entire owner (pets + tasks) to a JSON-safe dictionary."""
        return {
            "name": self.name,
            "available_minutes": self.available_minutes,
            "pets": [p.to_dict() for p in self.pets],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Owner":
        """Deserialize from a dictionary produced by to_dict()."""
        owner = cls(name=d["name"], available_minutes=d["available_minutes"])
        owner.pets = [Pet.from_dict(p) for p in d.get("pets", [])]
        return owner

    def save_to_json(self, path: str = "data.json") -> None:
        """Persist the owner, pets, and all tasks to a JSON file."""
        Path(path).write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load_from_json(cls, path: str = "data.json") -> Optional["Owner"]:
        """Load owner data from a JSON file; returns None if the file doesn't exist."""
        p = Path(path)
        if not p.exists():
            return None
        return cls.from_dict(json.loads(p.read_text()))


@dataclass
class PlanEntry:
    """One scheduled or skipped task in the daily plan, with a human-readable reason."""
    pet_name: str
    task: Task
    scheduled: bool          # True = included in plan, False = skipped
    reason: str              # e.g. "High priority · 8:00 AM" or "Skipped: time budget exceeded"


class Scheduler:
    """Brain of PawPal+: sorts, conflict-checks, and generates the daily care plan."""

    def __init__(self, owner: Owner):
        self.owner = owner

    def get_upcoming_tasks(self) -> List[tuple]:
        """Return all pending (pet_name, task) tuples sorted by priority then due_time."""
        return sorted(
            self.owner.get_all_tasks(),
            key=lambda x: (-x[1].priority_score(), x[1].due_time),
        )

    def sort_by_time(self) -> List[tuple]:
        """Return all pending (pet_name, task) tuples sorted by due_time only, earliest first."""
        return sorted(self.owner.get_all_tasks(), key=lambda x: x[1].due_time)

    def filter_tasks(self, pet_name: str = None, completed: bool = None) -> List[tuple]:
        """Return (pet_name, task) tuples filtered by pet name and/or completion status."""
        results = []
        for pet in self.owner.pets:
            if pet_name and pet.name.lower() != pet_name.lower():
                continue
            for task in pet.tasks:
                if completed is not None and task.is_completed != completed:
                    continue
                results.append((pet.name, task))
        return results

    def find_next_slot(self, duration_mins: int, after: datetime = None) -> Optional[datetime]:
        """
        Scan forward in 15-minute steps from `after` (default: now) and return the
        earliest datetime at which a free window of `duration_mins` exists.
        Returns None if no free slot is found before midnight.
        """
        start = (after or datetime.now()).replace(second=0, microsecond=0)
        # Round up to the next 15-minute boundary
        remainder = start.minute % 15
        if remainder:
            start += timedelta(minutes=15 - remainder)
        end_of_day = start.replace(hour=23, minute=45)

        busy = [
            (t.due_time, t.due_time + timedelta(minutes=t.duration_mins))
            for _, t in self.owner.get_all_tasks()
        ]

        candidate = start
        while candidate + timedelta(minutes=duration_mins) <= end_of_day + timedelta(minutes=15):
            window_end = candidate + timedelta(minutes=duration_mins)
            overlap = any(
                candidate < b_end and window_end > b_start
                for b_start, b_end in busy
            )
            if not overlap:
                return candidate
            candidate += timedelta(minutes=15)

        return None  # no free slot found today

    def check_conflicts(self, new_task: Task) -> bool:
        """Return True if new_task's time window overlaps any pending task across all pets."""
        new_start = new_task.due_time
        new_end = new_start + timedelta(minutes=new_task.duration_mins)

        for _, task in self.owner.get_all_tasks():
            if task is new_task:
                continue
            existing_start = task.due_time
            existing_end = existing_start + timedelta(minutes=task.duration_mins)
            if new_start < existing_end and new_end > existing_start:
                return True
        return False

    def get_conflict_warnings(self) -> List[str]:
        """Scan all pending tasks and return a warning string for every overlapping pair."""
        warnings = []
        tasks = self.owner.get_all_tasks()
        for i, (pet_a, task_a) in enumerate(tasks):
            a_start = task_a.due_time
            a_end   = a_start + timedelta(minutes=task_a.duration_mins)
            for pet_b, task_b in tasks[i + 1:]:
                b_start = task_b.due_time
                b_end   = b_start + timedelta(minutes=task_b.duration_mins)
                if a_start < b_end and a_end > b_start:
                    warnings.append(
                        f"⚠ Conflict: [{pet_a}] '{task_a.description}' "
                        f"({a_start.strftime('%I:%M %p')}–{a_end.strftime('%I:%M %p')}) "
                        f"overlaps [{pet_b}] '{task_b.description}' "
                        f"({b_start.strftime('%I:%M %p')}–{b_end.strftime('%I:%M %p')})"
                    )
        return warnings

    def generate_daily_plan(self) -> List[PlanEntry]:
        """Greedily schedule tasks by priority, respecting time budget and slot conflicts."""
        entries: List[PlanEntry] = []
        committed: List[tuple] = []
        total_mins = 0

        for pet_name, task in self.get_upcoming_tasks():
            time_label = task.due_time.strftime("%I:%M %p")

            if total_mins + task.duration_mins > self.owner.available_minutes:
                entries.append(PlanEntry(
                    pet_name=pet_name, task=task, scheduled=False,
                    reason=f"Skipped: time budget exceeded "
                           f"({total_mins}/{self.owner.available_minutes} min used)",
                ))
                continue

            task_start = task.due_time
            task_end = task_start + timedelta(minutes=task.duration_mins)
            conflict_with = next(
                (s for s, d in committed
                 if task_start < s + timedelta(minutes=d) and task_end > s),
                None,
            )
            if conflict_with is not None:
                entries.append(PlanEntry(
                    pet_name=pet_name, task=task, scheduled=False,
                    reason=f"Skipped: time conflict at {conflict_with.strftime('%I:%M %p')}",
                ))
                continue

            entries.append(PlanEntry(
                pet_name=pet_name, task=task, scheduled=True,
                reason=f"{task.priority} priority · due {time_label} · {task.duration_mins} min",
            ))
            committed.append((task_start, task.duration_mins))
            total_mins += task.duration_mins

        return entries

    def mark_task_complete(self, task: Task) -> None:
        """Mark a task done and immediately queue its next occurrence if it recurs."""
        task.mark_complete()
        pet = next((p for p in self.owner.pets if task in p.tasks), None)
        if pet is None or task.frequency == "Once":
            return
        delta = timedelta(days=1) if task.frequency == "Daily" else timedelta(weeks=1)
        all_ids = [t.id for p in self.owner.pets for t in p.tasks]
        pet.add_task(Task(
            id=max(all_ids, default=0) + 1,
            description=task.description,
            due_time=task.due_time + delta,
            duration_mins=task.duration_mins,
            priority=task.priority,
            frequency=task.frequency,
            is_completed=False,
        ))

    def generate_recurring_tasks(self):
        """Append the next occurrence of each completed Daily/Weekly task to its pet."""
        all_ids = [task.id for pet in self.owner.pets for task in pet.tasks]
        next_task_id = max(all_ids, default=0) + 1

        for pet in self.owner.pets:
            new_tasks = []
            for task in pet.tasks:
                if not task.is_completed:
                    continue
                if task.frequency == "Daily":
                    delta = timedelta(days=1)
                elif task.frequency == "Weekly":
                    delta = timedelta(weeks=1)
                else:
                    continue

                new_tasks.append(Task(
                    id=next_task_id,
                    description=task.description,
                    due_time=task.due_time + delta,
                    duration_mins=task.duration_mins,
                    priority=task.priority,
                    frequency=task.frequency,
                    is_completed=False,
                ))
                next_task_id += 1

            for t in new_tasks:
                pet.add_task(t)
