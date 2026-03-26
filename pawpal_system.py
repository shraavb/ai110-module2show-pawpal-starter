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

    def total_task_minutes(self) -> int:
        """Sum of duration across all pending tasks for all pets."""
        return sum(
            task.duration_mins
            for pet in self.pets
            for task in pet.get_pending_tasks()
        )


class Scheduler:
    """
    Manages scheduling logic, conflict detection, and plan generation.
    This is the 'brain' of the system.
    """

    def __init__(self, owner: Owner):
        self.owner = owner

    def get_upcoming_tasks(self) -> List[tuple]:
        """
        Return all pending tasks sorted by priority (High first),
        then by due_time. Each item is a (pet_name, task) tuple.
        """
        all_tasks = [
            (pet.name, task)
            for pet in self.owner.pets
            for task in pet.get_pending_tasks()
        ]
        return sorted(all_tasks, key=lambda x: (-x[1].priority_score(), x[1].due_time))

    def check_conflicts(self, new_task: Task) -> bool:
        """
        Return True if new_task's time window overlaps with any
        already-scheduled task across all pets.
        """
        new_start = new_task.due_time
        new_end = new_start + timedelta(minutes=new_task.duration_mins)

        for pet in self.owner.pets:
            for task in pet.get_pending_tasks():
                if task is new_task:
                    continue
                existing_start = task.due_time
                existing_end = existing_start + timedelta(minutes=task.duration_mins)
                if new_start < existing_end and new_end > existing_start:
                    return True
        return False

    def generate_daily_plan(self) -> List[tuple]:
        """
        Greedy scheduler: place tasks in priority+time order,
        skipping any that conflict with already-placed ones or would
        exceed the owner's available_minutes for the day.
        Returns a list of (pet_name, task) tuples in scheduled order.
        """
        plan = []
        scheduled_tasks = []
        total_scheduled_mins = 0

        for pet_name, task in self.get_upcoming_tasks():
            if total_scheduled_mins + task.duration_mins > self.owner.available_minutes:
                continue

            task_start = task.due_time
            task_end = task_start + timedelta(minutes=task.duration_mins)
            conflict = any(
                task_start < (s + timedelta(minutes=d)) and task_end > s
                for s, d in scheduled_tasks
            )
            if not conflict:
                plan.append((pet_name, task))
                scheduled_tasks.append((task_start, task.duration_mins))
                total_scheduled_mins += task.duration_mins

        return plan

    def generate_recurring_tasks(self):
        """
        For each completed Daily or Weekly task, create the next
        occurrence and add it back to the pet's task list.
        """
        next_task_id = sum(len(pet.tasks) for pet in self.owner.pets) + 1

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
