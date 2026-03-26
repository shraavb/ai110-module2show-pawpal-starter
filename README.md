# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Testing PawPal+

Run the full test suite:

```bash
python -m pytest
```

27 automated tests across 5 categories:

| Category | Tests | What's covered |
|---|---|---|
| **Task** | 3 | `mark_complete()` correctness and idempotency; `priority_score()` values |
| **Pet** | 2 | Task count increases on add; completed tasks excluded from pending list |
| **Owner** | 1 | `get_all_tasks()` spans every pet |
| **Scheduler — core** | 5 | Priority sort; overlap detection; adjacent tasks not flagged; budget hard cutoff; recurring generation |
| **Scheduler — Phase 4** | 16 | `sort_by_time()` order and empty state; `filter_tasks()` by name, status, and no-match; `get_conflict_warnings()` for overlap, exact same time, adjacent, cross-pet, and empty; `mark_task_complete()` for Daily, Weekly, Once, and flag; pet-with-no-tasks edge case |

**Confidence: ★★★★☆**
Happy paths and most edge cases are covered. Gaps that would raise confidence to 5 stars: testing `generate_daily_plan()` with a cross-pet conflict in the plan output; testing `generate_recurring_tasks()` called twice (duplicate guard); and integration tests that exercise the full Owner → Scheduler → PlanEntry pipeline with realistic multi-pet data.

---

## Smarter Scheduling

PawPal+ includes four algorithmic features beyond basic task storage:

| Feature | Method | What it does |
|---|---|---|
| **Sort by time** | `Scheduler.sort_by_time()` | Returns all pending tasks in chronological order using `sorted()` with a `lambda x: x[1].due_time` key — ignores priority, useful for a timeline view |
| **Filter tasks** | `Scheduler.filter_tasks(pet_name, completed)` | Narrows the task list by pet name and/or completion status; both filters are optional and combinable |
| **Conflict warnings** | `Scheduler.get_conflict_warnings()` | Scans every pair of pending tasks for time-window overlap and returns human-readable warning strings — returns warnings rather than raising exceptions so the UI can surface them gracefully |
| **Auto-recurring** | `Scheduler.mark_task_complete(task)` | Marks a task done and immediately appends the next occurrence (today + 1 day for Daily, + 7 days for Weekly) so recurring care is never lost from the schedule |

The daily plan (`generate_daily_plan()`) uses a greedy algorithm: tasks are placed in priority → due-time order, skipping any that would exceed the owner's `available_minutes` budget or overlap an already-placed slot.

---

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.
