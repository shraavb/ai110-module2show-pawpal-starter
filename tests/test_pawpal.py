"""
tests/test_pawpal.py — Unit tests for PawPal+ logic layer.
Run with: python -m pytest
"""

from datetime import datetime
import pytest
from pawpal_system import Task, Pet, Owner, Scheduler


# ── Fixtures ─────────────────────────────────────────────────────────────────

def make_task(id=1, hour=9, minute=0, duration=30, priority="Medium", frequency="Once"):
    return Task(
        id=id,
        description=f"Task {id}",
        due_time=datetime(2026, 1, 1, hour, minute),
        duration_mins=duration,
        priority=priority,
        frequency=frequency,
    )

def make_owner(available_minutes=120):
    owner = Owner(name="Jordan", available_minutes=available_minutes)
    return owner


# ── Task tests ────────────────────────────────────────────────────────────────

def test_mark_complete_changes_status():
    """Calling mark_complete() must flip is_completed to True."""
    task = make_task()
    assert task.is_completed is False
    task.mark_complete()
    assert task.is_completed is True


def test_mark_complete_is_idempotent():
    """Calling mark_complete() twice should not raise or flip back."""
    task = make_task()
    task.mark_complete()
    task.mark_complete()
    assert task.is_completed is True


def test_priority_score_values():
    """priority_score() must return 3/2/1 for High/Medium/Low."""
    assert make_task(priority="High").priority_score()   == 3
    assert make_task(priority="Medium").priority_score() == 2
    assert make_task(priority="Low").priority_score()    == 1


# ── Pet tests ─────────────────────────────────────────────────────────────────

def test_add_task_increases_count():
    """Adding a task to a Pet must increase its task count by 1."""
    pet = Pet(id=1, name="Mochi", species="Dog", age=3)
    assert len(pet.tasks) == 0
    pet.add_task(make_task())
    assert len(pet.tasks) == 1
    pet.add_task(make_task(id=2))
    assert len(pet.tasks) == 2


def test_get_pending_tasks_excludes_completed():
    """get_pending_tasks() must not return completed tasks."""
    pet = Pet(id=1, name="Mochi", species="Dog", age=3)
    t1 = make_task(id=1)
    t2 = make_task(id=2)
    t2.mark_complete()
    pet.add_task(t1)
    pet.add_task(t2)
    pending = pet.get_pending_tasks()
    assert len(pending) == 1
    assert pending[0].id == 1


# ── Owner tests ───────────────────────────────────────────────────────────────

def test_owner_get_all_tasks_spans_pets():
    """get_all_tasks() must return tasks from every pet."""
    owner = make_owner()
    p1 = Pet(id=1, name="Mochi", species="Dog", age=3)
    p2 = Pet(id=2, name="Luna",  species="Cat", age=5)
    p1.add_task(make_task(id=1))
    p2.add_task(make_task(id=2))
    p2.add_task(make_task(id=3))
    owner.add_pet(p1)
    owner.add_pet(p2)
    assert len(owner.get_all_tasks()) == 3


# ── Scheduler tests ───────────────────────────────────────────────────────────

def make_scheduler(available_minutes=120):
    owner = make_owner(available_minutes)
    pet = Pet(id=1, name="Mochi", species="Dog", age=3)
    owner.add_pet(pet)
    return owner, pet, Scheduler(owner)


def test_get_upcoming_tasks_sorted_by_priority():
    """High-priority tasks must come before Low-priority tasks."""
    owner, pet, scheduler = make_scheduler()
    pet.add_task(make_task(id=1, priority="Low",    hour=8))
    pet.add_task(make_task(id=2, priority="High",   hour=9))
    pet.add_task(make_task(id=3, priority="Medium", hour=10))

    result = scheduler.get_upcoming_tasks()
    priorities = [t.priority for _, t in result]
    assert priorities == ["High", "Medium", "Low"]


def test_check_conflicts_detects_overlap():
    """check_conflicts() must return True when windows overlap."""
    owner, pet, scheduler = make_scheduler()
    existing = make_task(id=1, hour=9, minute=0,  duration=60)  # 9:00–10:00
    new_task  = make_task(id=2, hour=9, minute=30, duration=30)  # 9:30–10:00
    pet.add_task(existing)
    assert scheduler.check_conflicts(new_task) is True


def test_check_conflicts_allows_adjacent():
    """check_conflicts() must return False for back-to-back (non-overlapping) tasks."""
    owner, pet, scheduler = make_scheduler()
    existing = make_task(id=1, hour=9, minute=0,  duration=30)  # 9:00–9:30
    new_task  = make_task(id=2, hour=9, minute=30, duration=30)  # 9:30–10:00
    pet.add_task(existing)
    assert scheduler.check_conflicts(new_task) is False


def test_generate_daily_plan_respects_budget():
    """Tasks that push total over available_minutes must be skipped."""
    owner, pet, scheduler = make_scheduler(available_minutes=40)
    pet.add_task(make_task(id=1, hour=8, duration=30, priority="High"))    # fits  (30 min)
    pet.add_task(make_task(id=2, hour=9, duration=20, priority="Medium"))  # skipped (30+20 > 40)

    plan = scheduler.generate_daily_plan()
    scheduled = [e for e in plan if e.scheduled]
    skipped   = [e for e in plan if not e.scheduled]

    assert len(scheduled) == 1
    assert scheduled[0].task.id == 1
    assert len(skipped) == 1
    assert "budget" in skipped[0].reason


def test_generate_recurring_tasks_creates_next_occurrence():
    """A completed Daily task must produce a new task one day later with is_completed=False."""
    owner, pet, scheduler = make_scheduler()
    task = make_task(id=1, hour=8, frequency="Daily")
    task.mark_complete()
    pet.add_task(task)

    scheduler.generate_recurring_tasks()

    new_tasks = [t for t in pet.tasks if t.id != 1]
    assert len(new_tasks) == 1
    assert new_tasks[0].is_completed is False
    assert new_tasks[0].due_time == task.due_time.replace(day=task.due_time.day + 1)


# ── sort_by_time tests ────────────────────────────────────────────────────────

def test_sort_by_time_chronological_order():
    """Tasks added out of order must be returned earliest-first."""
    owner, pet, scheduler = make_scheduler()
    pet.add_task(make_task(id=1, hour=10))
    pet.add_task(make_task(id=2, hour=7))
    pet.add_task(make_task(id=3, hour=9))

    result = scheduler.sort_by_time()
    hours = [t.due_time.hour for _, t in result]
    assert hours == [7, 9, 10]


def test_sort_by_time_empty_pet():
    """sort_by_time() must return an empty list when there are no pending tasks."""
    owner, pet, scheduler = make_scheduler()
    assert scheduler.sort_by_time() == []


def test_sort_by_time_ignores_priority():
    """sort_by_time() must order by time only — a Low task at 7 AM comes before a High task at 9 AM."""
    owner, pet, scheduler = make_scheduler()
    pet.add_task(make_task(id=1, hour=9, priority="High"))
    pet.add_task(make_task(id=2, hour=7, priority="Low"))

    result = scheduler.sort_by_time()
    assert result[0][1].priority == "Low"
    assert result[1][1].priority == "High"


# ── filter_tasks tests ────────────────────────────────────────────────────────

def test_filter_by_pet_name():
    """filter_tasks(pet_name=...) must return only that pet's tasks."""
    owner = make_owner()
    p1 = Pet(id=1, name="Mochi", species="Dog", age=3)
    p2 = Pet(id=2, name="Luna",  species="Cat", age=5)
    p1.add_task(make_task(id=1))
    p2.add_task(make_task(id=2))
    owner.add_pet(p1)
    owner.add_pet(p2)
    scheduler = Scheduler(owner)

    result = scheduler.filter_tasks(pet_name="Mochi")
    assert len(result) == 1
    assert result[0][0] == "Mochi"


def test_filter_by_completion_status():
    """filter_tasks(completed=False) must exclude completed tasks."""
    owner, pet, scheduler = make_scheduler()
    t1 = make_task(id=1)
    t2 = make_task(id=2)
    t2.mark_complete()
    pet.add_task(t1)
    pet.add_task(t2)

    result = scheduler.filter_tasks(completed=False)
    assert len(result) == 1
    assert result[0][1].id == 1


def test_filter_no_match_returns_empty():
    """filter_tasks() with a non-existent pet name must return an empty list."""
    owner, pet, scheduler = make_scheduler()
    pet.add_task(make_task())
    assert scheduler.filter_tasks(pet_name="Ghost") == []


# ── get_conflict_warnings tests ───────────────────────────────────────────────

def test_conflict_warnings_detects_overlap():
    """get_conflict_warnings() must report overlapping tasks."""
    owner, pet, scheduler = make_scheduler()
    pet.add_task(make_task(id=1, hour=9, minute=0,  duration=60))   # 9:00–10:00
    pet.add_task(make_task(id=2, hour=9, minute=30, duration=30))   # 9:30–10:00  ← overlaps

    warnings = scheduler.get_conflict_warnings()
    assert len(warnings) == 1
    assert "overlap" in warnings[0].lower() or "conflict" in warnings[0].lower()


def test_conflict_warnings_exact_same_time():
    """Two tasks starting at the exact same time must be flagged."""
    owner, pet, scheduler = make_scheduler()
    pet.add_task(make_task(id=1, hour=8, minute=0, duration=30))
    pet.add_task(make_task(id=2, hour=8, minute=0, duration=15))

    warnings = scheduler.get_conflict_warnings()
    assert len(warnings) >= 1


def test_conflict_warnings_adjacent_no_conflict():
    """Back-to-back tasks (no gap, no overlap) must produce no warnings."""
    owner, pet, scheduler = make_scheduler()
    pet.add_task(make_task(id=1, hour=9, minute=0,  duration=30))   # 9:00–9:30
    pet.add_task(make_task(id=2, hour=9, minute=30, duration=30))   # 9:30–10:00

    assert scheduler.get_conflict_warnings() == []


def test_conflict_warnings_cross_pet():
    """Overlapping tasks on *different* pets must still be flagged."""
    owner = make_owner()
    p1 = Pet(id=1, name="Mochi", species="Dog", age=3)
    p2 = Pet(id=2, name="Luna",  species="Cat", age=5)
    p1.add_task(make_task(id=1, hour=8, minute=0,  duration=60))    # 8:00–9:00
    p2.add_task(make_task(id=2, hour=8, minute=30, duration=30))    # 8:30–9:00  ← overlaps
    owner.add_pet(p1)
    owner.add_pet(p2)
    scheduler = Scheduler(owner)

    warnings = scheduler.get_conflict_warnings()
    assert len(warnings) == 1


def test_no_warnings_when_no_tasks():
    """get_conflict_warnings() must return an empty list when there are no tasks."""
    owner, pet, scheduler = make_scheduler()
    assert scheduler.get_conflict_warnings() == []


# ── mark_task_complete tests ──────────────────────────────────────────────────

def test_mark_task_complete_sets_flag():
    """mark_task_complete() must mark the task as done."""
    owner, pet, scheduler = make_scheduler()
    task = make_task(id=1, frequency="Once")
    pet.add_task(task)
    scheduler.mark_task_complete(task)
    assert task.is_completed is True


def test_mark_task_complete_daily_creates_next():
    """Completing a Daily task must append a new task due one day later."""
    from datetime import timedelta
    owner, pet, scheduler = make_scheduler()
    task = make_task(id=1, hour=8, frequency="Daily")
    pet.add_task(task)
    scheduler.mark_task_complete(task)

    new_tasks = [t for t in pet.tasks if t.id != 1]
    assert len(new_tasks) == 1
    assert new_tasks[0].due_time == task.due_time + timedelta(days=1)
    assert new_tasks[0].is_completed is False


def test_mark_task_complete_weekly_creates_next():
    """Completing a Weekly task must append a new task due seven days later."""
    from datetime import timedelta
    owner, pet, scheduler = make_scheduler()
    task = make_task(id=1, hour=8, frequency="Weekly")
    pet.add_task(task)
    scheduler.mark_task_complete(task)

    new_tasks = [t for t in pet.tasks if t.id != 1]
    assert len(new_tasks) == 1
    assert new_tasks[0].due_time == task.due_time + timedelta(weeks=1)


def test_mark_task_complete_once_no_recurrence():
    """Completing a Once task must NOT create a new task."""
    owner, pet, scheduler = make_scheduler()
    task = make_task(id=1, frequency="Once")
    pet.add_task(task)
    scheduler.mark_task_complete(task)

    assert len(pet.tasks) == 1   # only the original, no new task


# ── Edge case: pet with no tasks ──────────────────────────────────────────────

def test_scheduler_handles_pet_with_no_tasks():
    """All scheduler methods must work without raising when a pet has no tasks."""
    owner, pet, scheduler = make_scheduler()   # pet has no tasks

    assert scheduler.sort_by_time() == []
    assert scheduler.filter_tasks() == []
    assert scheduler.get_conflict_warnings() == []
    assert scheduler.get_upcoming_tasks() == []
    plan = scheduler.generate_daily_plan()
    assert plan == []
