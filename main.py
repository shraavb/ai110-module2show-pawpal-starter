"""
main.py — CLI demo for PawPal+ logic layer.
Run with: python main.py

Demonstrates:
  - Sort by time / filter tasks
  - Conflict warnings
  - Mark complete + auto-recurring
  - find_next_slot (Challenge 1)
  - JSON save/load persistence (Challenge 2)
  - tabulate for clean terminal output (Challenge 4)
"""

from datetime import datetime
from tabulate import tabulate
from pawpal_system import Owner, Pet, Task, Scheduler

W = 68
today = datetime.today().replace(second=0, microsecond=0)


def t(hour, minute=0):
    return today.replace(hour=hour, minute=minute)


def section(title):
    print(f"\n{'─' * W}\n  {title}\n{'─' * W}")


# ── Build sample data ─────────────────────────────────────────────────────────

owner = Owner(name="Jordan", available_minutes=90)
mochi = Pet(id=1, name="Mochi", species="Dog", age=3)
luna  = Pet(id=2, name="Luna",  species="Cat", age=5)
owner.add_pet(mochi)
owner.add_pet(luna)

mochi.add_task(Task(id=1, description="Enrichment puzzle",  due_time=t(10),     duration_mins=20, priority="Low",    frequency="Once"))
mochi.add_task(Task(id=2, description="Morning walk",       due_time=t(7),      duration_mins=30, priority="High",   frequency="Daily"))
mochi.add_task(Task(id=3, description="Flea treatment",     due_time=t(9),      duration_mins=15, priority="Medium", frequency="Weekly"))
mochi.add_task(Task(id=4, description="Breakfast feeding",  due_time=t(7, 30),  duration_mins=10, priority="High",   frequency="Daily"))

luna.add_task( Task(id=5, description="Grooming session",   due_time=t(11),     duration_mins=25, priority="Low",    frequency="Weekly"))
luna.add_task( Task(id=6, description="Litter box clean",   due_time=t(9, 30),  duration_mins=10, priority="Medium", frequency="Daily"))
luna.add_task( Task(id=7, description="Insulin injection",  due_time=t(7, 15),  duration_mins=10, priority="High",   frequency="Daily"))

scheduler = Scheduler(owner)

# ── 1. Sort by time ───────────────────────────────────────────────────────────

section("1. SORT BY TIME")
rows = [[t.due_time.strftime("%I:%M %p"), n, t.description, f"{t.duration_mins} min", t.priority]
        for n, t in scheduler.sort_by_time()]
print(tabulate(rows, headers=["Due", "Pet", "Task", "Duration", "Priority"], tablefmt="simple"))

# ── 2. Filter ─────────────────────────────────────────────────────────────────

section("2. FILTER — Mochi only")
rows = [[t.due_time.strftime("%I:%M %p"), t.description, t.priority, t.frequency]
        for _, t in scheduler.filter_tasks(pet_name="Mochi")]
print(tabulate(rows, headers=["Due", "Task", "Priority", "Frequency"], tablefmt="simple"))

# ── 3. Conflict warnings ──────────────────────────────────────────────────────

section("3. CONFLICT WARNINGS")
for w in scheduler.get_conflict_warnings() or ["  No conflicts."]:
    print(f"  {w}")

# ── 4. Mark complete + auto-recurring ────────────────────────────────────────

section("4. MARK COMPLETE — Morning walk (Daily)")
walk = mochi.tasks[1]
print(f"  Before: {len(mochi.tasks)} tasks")
scheduler.mark_task_complete(walk)
print(f"  After:  {len(mochi.tasks)} tasks")
new_walk = mochi.tasks[-1]
print(f"  Next occurrence: '{new_walk.description}' due {new_walk.due_time.strftime('%a %I:%M %p')}, completed={new_walk.is_completed}")

# ── 5. Challenge 1: Find next available slot ──────────────────────────────────

section("5. FIND NEXT AVAILABLE SLOT  (Challenge 1)")
for duration in [15, 30, 60]:
    slot = scheduler.find_next_slot(duration_mins=duration, after=today.replace(hour=7))
    label = slot.strftime("%I:%M %p") if slot else "none available today"
    print(f"  {duration:>3} min slot → {label}")

# ── 6. Challenge 2: JSON persistence ─────────────────────────────────────────

section("6. JSON PERSISTENCE  (Challenge 2)")
owner.save_to_json("data.json")
print("  Saved to data.json")

reloaded = Owner.load_from_json("data.json")
total_tasks = sum(len(p.tasks) for p in reloaded.pets)
print(f"  Loaded: Owner='{reloaded.owner_summary()}', pets={len(reloaded.pets)}, total tasks={total_tasks}")

# ── 7. Daily plan ─────────────────────────────────────────────────────────────

section("7. DAILY PLAN  (priority-ordered, budget-capped)")
print(f"  Owner: {owner.name}  |  Budget: {owner.available_minutes} min\n")

plan      = scheduler.generate_daily_plan()
scheduled = [e for e in plan if e.scheduled]
skipped   = [e for e in plan if not e.scheduled]

PRIORITY_ICON = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}

sched_rows = [
    [PRIORITY_ICON.get(e.task.priority, ""), e.task.due_time.strftime("%I:%M %p"),
     e.pet_name, e.task.description, e.reason]
    for e in scheduled
]
print(tabulate(sched_rows, headers=["", "Time", "Pet", "Task", "Reason"], tablefmt="simple"))

if skipped:
    print(f"\n  Skipped ({len(skipped)}):")
    skip_rows = [[e.task.due_time.strftime("%I:%M %p"), e.pet_name, e.task.description, e.reason]
                 for e in skipped]
    print(tabulate(skip_rows, headers=["Time", "Pet", "Task", "Reason"], tablefmt="simple"))

total = sum(e.task.duration_mins for e in scheduled)
print(f"\n  Time used: {total} / {owner.available_minutes} min")
print(f"{'═' * W}\n")
