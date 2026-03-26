"""
main.py — CLI demo for PawPal+ logic layer.
Run with: python main.py
"""

from datetime import datetime
from pawpal_system import Owner, Pet, Task, Scheduler

# ── Build sample data ────────────────────────────────────────────────────────

owner = Owner(name="Jordan", available_minutes=90)

mochi = Pet(id=1, name="Mochi", species="Dog", age=3)
luna  = Pet(id=2, name="Luna",  species="Cat", age=5)

owner.add_pet(mochi)
owner.add_pet(luna)

today = datetime.today().replace(second=0, microsecond=0)

mochi.add_task(Task(id=1, description="Morning walk",       due_time=today.replace(hour=7,  minute=0),  duration_mins=30, priority="High",   frequency="Daily"))
mochi.add_task(Task(id=2, description="Breakfast feeding",  due_time=today.replace(hour=7,  minute=30), duration_mins=10, priority="High",   frequency="Daily"))
mochi.add_task(Task(id=3, description="Enrichment puzzle",  due_time=today.replace(hour=10, minute=0),  duration_mins=20, priority="Low",    frequency="Once"))
mochi.add_task(Task(id=4, description="Flea treatment",     due_time=today.replace(hour=9,  minute=0),  duration_mins=15, priority="Medium", frequency="Weekly"))

luna.add_task( Task(id=5, description="Insulin injection",  due_time=today.replace(hour=8,  minute=0),  duration_mins=10, priority="High",   frequency="Daily"))
luna.add_task( Task(id=6, description="Litter box clean",   due_time=today.replace(hour=9,  minute=30), duration_mins=10, priority="Medium", frequency="Daily"))
luna.add_task( Task(id=7, description="Grooming session",   due_time=today.replace(hour=11, minute=0),  duration_mins=25, priority="Low",    frequency="Weekly"))

# ── Run scheduler ────────────────────────────────────────────────────────────

scheduler = Scheduler(owner)
plan = scheduler.generate_daily_plan()

# ── Print results ────────────────────────────────────────────────────────────

WIDTH = 68

print()
print("=" * WIDTH)
print(f"  🐾  PawPal+ Daily Schedule — {today.strftime('%A, %B %d %Y')}")
print(f"      Owner: {owner.name}  |  Time budget: {owner.available_minutes} min")
print("=" * WIDTH)

scheduled = [e for e in plan if e.scheduled]
skipped   = [e for e in plan if not e.scheduled]

if scheduled:
    print(f"\n  ✅  SCHEDULED  ({len(scheduled)} tasks)\n")
    for entry in scheduled:
        time_str = entry.task.due_time.strftime("%I:%M %p")
        print(f"  {time_str}  [{entry.pet_name:6}]  {entry.task.description:<25}  {entry.reason}")
else:
    print("\n  No tasks could be scheduled.")

if skipped:
    print(f"\n  ⏭   SKIPPED  ({len(skipped)} tasks)\n")
    for entry in skipped:
        time_str = entry.task.due_time.strftime("%I:%M %p")
        print(f"  {time_str}  [{entry.pet_name:6}]  {entry.task.description:<25}  {entry.reason}")

total_used = sum(e.task.duration_mins for e in scheduled)
print()
print("-" * WIDTH)
print(f"  Time used: {total_used} min / {owner.available_minutes} min available")
print("=" * WIDTH)
print()
