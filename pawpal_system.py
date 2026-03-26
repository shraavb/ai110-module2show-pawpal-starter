from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List


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

    def generate_daily_plan(self) -> List[PlanEntry]:
        """Greedily schedule tasks by priority, respecting time budget and slot conflicts."""
        entries: List[PlanEntry] = []
        committed: List[tuple] = []   # (start: datetime, duration_mins: int)
        total_mins = 0

        for pet_name, task in self.get_upcoming_tasks():
            time_label = task.due_time.strftime("%I:%M %p")

            # Hard cutoff: owner doesn't have enough time left
            if total_mins + task.duration_mins > self.owner.available_minutes:
                entries.append(PlanEntry(
                    pet_name=pet_name,
                    task=task,
                    scheduled=False,
                    reason=f"Skipped: time budget exceeded "
                           f"({total_mins}/{self.owner.available_minutes} min used)",
                ))
                continue

            # Conflict check against already-committed slots
            task_start = task.due_time
            task_end = task_start + timedelta(minutes=task.duration_mins)
            conflict_with = next(
                (s for s, d in committed
                 if task_start < s + timedelta(minutes=d) and task_end > s),
                None,
            )
            if conflict_with is not None:
                entries.append(PlanEntry(
                    pet_name=pet_name,
                    task=task,
                    scheduled=False,
                    reason=f"Skipped: time conflict at {conflict_with.strftime('%I:%M %p')}",
                ))
                continue

            # Task fits — add to plan
            entries.append(PlanEntry(
                pet_name=pet_name,
                task=task,
                scheduled=True,
                reason=f"{task.priority} priority · due {time_label} · {task.duration_mins} min",
            ))
            committed.append((task_start, task.duration_mins))
            total_mins += task.duration_mins

        return entries

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
