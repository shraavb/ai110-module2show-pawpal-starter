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
