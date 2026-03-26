"""
main.py — CLI demo for PawPal+ logic layer.
Run with: python main.py
"""

from datetime import datetime
from pawpal_system import Owner, Pet, Task, Scheduler

W = 68
today = datetime.today().replace(second=0, microsecond=0)


def t(hour, minute=0):
    """Shorthand: build a datetime for today at the given hour:minute."""
    return today.replace(hour=hour, minute=minute)


def section(title):
    print(f"\n{'─' * W}")
    print(f"  {title}")
    print(f"{'─' * W}")


# ── Build sample data (tasks added OUT OF ORDER on purpose) ───────────────────

owner = Owner(name="Jordan", available_minutes=90)

mochi = Pet(id=1, name="Mochi", species="Dog", age=3)
luna  = Pet(id=2, name="Luna",  species="Cat", age=5)
owner.add_pet(mochi)
owner.add_pet(luna)

# Tasks added in scrambled time order to demonstrate sort_by_time()
mochi.add_task(Task(id=1, description="Enrichment puzzle",  due_time=t(10),     duration_mins=20, priority="Low",    frequency="Once"))
mochi.add_task(Task(id=2, description="Morning walk",       due_time=t(7),      duration_mins=30, priority="High",   frequency="Daily"))
mochi.add_task(Task(id=3, description="Flea treatment",     due_time=t(9),      duration_mins=15, priority="Medium", frequency="Weekly"))
mochi.add_task(Task(id=4, description="Breakfast feeding",  due_time=t(7, 30),  duration_mins=10, priority="High",   frequency="Daily"))

luna.add_task( Task(id=5, description="Grooming session",   due_time=t(11),     duration_mins=25, priority="Low",    frequency="Weekly"))
luna.add_task( Task(id=6, description="Litter box clean",   due_time=t(9, 30),  duration_mins=10, priority="Medium", frequency="Daily"))
# Intentional conflict: overlaps Mochi's Morning walk (07:00–07:30)
luna.add_task( Task(id=7, description="Insulin injection",  due_time=t(7, 15),  duration_mins=10, priority="High",   frequency="Daily"))

scheduler = Scheduler(owner)

# ── 1. Sort by time ───────────────────────────────────────────────────────────

section("1. SORT BY TIME  (tasks in chronological order, ignoring priority)")
for pet_name, task in scheduler.sort_by_time():
    print(f"  {task.due_time.strftime('%I:%M %p')}  [{pet_name:6}]  {task.description}")

# ── 2. Filter tasks ───────────────────────────────────────────────────────────

section("2. FILTER — Mochi's tasks only")
for pet_name, task in scheduler.filter_tasks(pet_name="Mochi"):
    status = "✓" if task.is_completed else "○"
    print(f"  {status}  {task.due_time.strftime('%I:%M %p')}  {task.description}")

section("2. FILTER — pending tasks only (all pets)")
for pet_name, task in scheduler.filter_tasks(completed=False):
    print(f"  [{pet_name:6}]  {task.description}")

# ── 3. Conflict detection ─────────────────────────────────────────────────────

section("3. CONFLICT WARNINGS")
warnings = scheduler.get_conflict_warnings()
if warnings:
    for w in warnings:
        print(f"  {w}")
else:
    print("  No conflicts detected.")

# ── 4. Mark complete + auto-recurring ────────────────────────────────────────

section("4. MARK COMPLETE — Morning walk (Daily) → auto-creates tomorrow's task")
walk = mochi.tasks[1]   # Morning walk
print(f"  Before: Mochi has {len(mochi.tasks)} tasks")
scheduler.mark_task_complete(walk)
print(f"  After:  Mochi has {len(mochi.tasks)} tasks")
new_walk = mochi.tasks[-1]
print(f"  New task: '{new_walk.description}' due {new_walk.due_time.strftime('%A %I:%M %p')}, completed={new_walk.is_completed}")

# ── 5. Full daily plan ────────────────────────────────────────────────────────

section("5. DAILY PLAN  (priority-ordered, budget-capped, conflict-aware)")
print(f"  Owner: {owner.name}  |  Budget: {owner.available_minutes} min\n")

plan      = scheduler.generate_daily_plan()
scheduled = [e for e in plan if e.scheduled]
skipped   = [e for e in plan if not e.scheduled]

print(f"  ✅  SCHEDULED ({len(scheduled)} tasks)")
for e in scheduled:
    print(f"     {e.task.due_time.strftime('%I:%M %p')}  [{e.pet_name:6}]  {e.task.description:<25}  {e.reason}")

print(f"\n  ⏭   SKIPPED ({len(skipped)} tasks)")
for e in skipped:
    print(f"     {e.task.due_time.strftime('%I:%M %p')}  [{e.pet_name:6}]  {e.task.description:<25}  {e.reason}")

total = sum(e.task.duration_mins for e in scheduled)
print(f"\n  Time used: {total} / {owner.available_minutes} min")
print(f"{'═' * W}\n")
