# PawPal+ (Module 2 Project)

**PawPal+** is a Streamlit app that helps a busy pet owner plan daily care tasks across multiple pets, using priority-based scheduling, conflict detection, and automatic recurrence.

## 📸 Demo

<a href="/course_images/ai110/pawpal_screenshot.png" target="_blank"><img src='/course_images/ai110/pawpal_screenshot.png' title='PawPal App' width='' alt='PawPal App' class='center-block' /></a>

---

## Features

| Feature | Description |
|---|---|
| **Multi-pet management** | Add any number of pets (dog, cat, rabbit, bird, etc.) under one owner |
| **Task entry** | Each task has a description, due time, duration, priority (Low/Medium/High), and frequency (Once/Daily/Weekly) |
| **Priority-based scheduling** | `generate_daily_plan()` places High-priority tasks first, using due time as a tiebreaker |
| **Time budget hard cutoff** | Owner sets `available_minutes`; the planner never exceeds it — low-priority tasks are dropped, not the owner's sanity |
| **Conflict warnings** | `get_conflict_warnings()` scans all pending tasks for overlapping time windows and surfaces named warnings before a plan is generated |
| **Sort by time** | `sort_by_time()` returns tasks in chronological order regardless of priority — shown in the "By time" tab |
| **Filter by pet** | `filter_tasks(pet_name, completed)` narrows the task list by pet or completion status — shown in the "Filter by pet" tab |
| **Auto-recurring tasks** | `mark_task_complete()` marks a task done and immediately queues the next occurrence: +1 day (Daily) or +7 days (Weekly) |
| **Explained plan** | Every entry in the daily plan includes a reason — scheduled tasks show priority + time, skipped tasks explain why (budget or conflict) |

---

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

To run the CLI demo without the UI:

```bash
python main.py
```

---

## Testing PawPal+

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
| **Scheduler — algorithmic** | 16 | `sort_by_time()` order and empty state; `filter_tasks()` by name, status, and no-match; `get_conflict_warnings()` for overlap, exact same time, adjacent, cross-pet, and empty; `mark_task_complete()` for Daily, Weekly, Once, and flag; pet-with-no-tasks edge case |

**Confidence: ★★★★☆** — happy paths and most edge cases covered. Gaps that would reach 5 stars: cross-pet conflict in `generate_daily_plan()` output; duplicate guard in `generate_recurring_tasks()` called twice; full Owner → Scheduler → PlanEntry integration tests.

---

## Challenge Extensions

### Challenge 1 — Next Available Slot (Agent Mode)

`Scheduler.find_next_slot(duration_mins, after)` was designed and implemented using Agent Mode with the prompt:

> *"Based on `#file:pawpal_system.py`, add a `find_next_slot` method to the Scheduler that scans forward in 15-minute increments from a given datetime and returns the first window of `duration_mins` minutes that doesn't overlap any pending task. Return `None` if no slot is found before midnight."*

Agent Mode explored the existing `get_conflict_warnings()` overlap logic, reused the same `(start, end)` window comparison pattern, and proposed the 15-minute step granularity to match the task form's minute selector. The main human decision was choosing 15-minute steps over 1-minute steps — coarser but sufficient for pet care scheduling and much faster to scan.

### Challenge 2 — JSON Persistence (Agent Mode)

Data persistence was added using Agent Mode with the prompt:

> *"Add `save_to_json` and `load_from_json` methods to the Owner class in `#file:pawpal_system.py`, then update Streamlit state in `#file:app.py` to load this data on startup."*

Agent Mode identified that `datetime` fields needed custom serialization (ISO 8601 strings via `.isoformat()` / `datetime.fromisoformat()`) rather than a third-party library like marshmallow, keeping dependencies minimal. It also proposed resuming the ID counter from `max(all_ids) + 1` on load, preventing collisions after a reload. The human review caught one gap: the agent's draft didn't add `data.json` to `.gitignore`, which was added manually.

### Challenge 3 — Priority Emojis (Challenge 3)

Priority emojis (🔴 High · 🟡 Medium · 🟢 Low) appear in all three task table tabs in the Streamlit UI and in the daily plan output in `main.py`. Implemented via a `PRIORITY_ICON` dict mapping applied at render time — no changes to the data model needed.

### Challenge 4 — Tabulate CLI Output

`main.py` uses the `tabulate` library (`simple` format) for all task and plan tables. Priority emojis prefix each plan row for at-a-glance readability.

---

## Smarter Scheduling

The daily plan (`generate_daily_plan()`) uses a **greedy algorithm**: tasks are walked in priority → due-time order. Each task is placed in the plan if it fits within the owner's time budget *and* doesn't overlap an already-placed slot. Tasks that fail either check are skipped with a reason rather than crashing.

Two separate conflict systems serve different purposes:
- **`get_conflict_warnings()`** — diagnostic, scans *all* pending tasks, tells the owner what's currently impossible
- **`generate_daily_plan()`** — optimizer, tracks only committed slots, resolves conflicts by dropping lower-priority tasks

---

## Project structure

```
pawpal_system.py   — all backend classes (Task, Pet, Owner, Scheduler, PlanEntry)
app.py             — Streamlit UI
main.py            — CLI demo script
tests/
  test_pawpal.py   — 27 pytest unit tests
uml_diagram.md     — final Mermaid.js class diagram
reflection.md      — design decisions and AI collaboration notes
```

---

## Suggested workflow (for contributors)

1. Read the scenario and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.
