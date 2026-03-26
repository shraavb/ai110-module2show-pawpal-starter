# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

My UML design has four classes:

- **`Task`** — a `@dataclass` holding a single care activity. Attributes: `id`, `description`, `due_time`, `duration_mins`, `priority` (Low/Medium/High), `frequency` (Once/Daily/Weekly), `is_completed`. Methods: `mark_complete()` sets the flag; `priority_score()` maps priority to an integer (High→3, Medium→2, Low→1) so tasks can be sorted. Responsible only for representing and scoring one activity.
- **`Pet`** — a `@dataclass` holding a pet's profile (`id`, `name`, `species`, `age`) and owning a `List[Task]`. Methods: `add_task()` appends a task; `get_pending_tasks()` filters to incomplete ones. Responsible for grouping tasks by animal.
- **`Owner`** — a `@dataclass` holding the human's `name`, `available_minutes` (hard cap on daily care time, default 120), and `List[Pet]`. Methods: `add_pet()` adds a pet; `total_task_minutes()` sums duration across all pending tasks to show whether the owner is overloaded. Responsible for expressing real-world capacity.
- **`Scheduler`** — the central "brain." Takes an `Owner` and reaches all pets and tasks through it. Methods: `get_upcoming_tasks()` returns all pending tasks sorted by `(-priority_score, due_time)`; `check_conflicts()` checks time-window overlap across all pets; `generate_daily_plan()` greedily places tasks in priority order, enforcing both the `available_minutes` hard cutoff and no time-slot overlap; `generate_recurring_tasks()` creates next occurrences of Daily/Weekly tasks.

Relationships: `Owner` → many `Pet`s → many `Task`s. `Scheduler` depends on `Owner` only.

**b. Design changes**

Three changes came out of implementation and an AI review of the skeleton:

**1. `Owner` included from the start (not cut).** Early brainstorming treated `Owner` as optional, but adding `available_minutes` as a hard cutoff in `generate_daily_plan()` immediately made the scheduler more realistic — it now stops adding tasks once the owner's time budget is full rather than generating an impossible schedule.

**2. Conflict detection lives in `Scheduler`, not `Pet`.** An early sketch put `has_conflict()` on `Pet`, but conflicts can happen *across* pets (two pets scheduled for a walk at the same time), so `Scheduler` is the only object with the full picture needed to check correctly.

**3. Two bottlenecks found during AI review, one fixed:**
- *Dual conflict systems*: `check_conflicts()` scans all pending tasks across all pets, while `generate_daily_plan()` maintains its own internal `scheduled_tasks` list — they are disconnected. `check_conflicts()` is now documented as an interactive helper (for validating a new task before adding it), while `generate_daily_plan()` uses its own tracking during plan construction. A future refactor could unify them.
- *Fragile ID generation*: `generate_recurring_tasks()` used `sum(len(pet.tasks)...)` to pick the next task ID, which produces duplicate IDs on repeated calls. Fixed by introducing a simple incrementing counter based on the current total at call time — acceptable for now, but a global ID counter or UUID would be more robust at scale.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers three constraints:

1. **Priority** — High-priority tasks (medications, feeding) are scheduled before lower-priority ones.
2. **Due time** — Among tasks with equal priority, earlier due times are scheduled first.
3. **No time-slot overlap** — `check_conflicts()` checks whether a new task's time window (`due_time` to `due_time + duration`) overlaps with any already-scheduled task for any pet.

I decided priority mattered most because missing a medication dose has a direct health consequence, whereas skipping enrichment for a day is much lower risk. I used due time as the tiebreaker because it reflects real-world urgency — a walk due at 8 AM should happen before one due at 5 PM even if both are "Medium."

**b. Tradeoffs**

The main tradeoff is that the scheduler is **greedy and non-backtracking**: it places tasks in priority order and skips any task that conflicts with an already-placed task, rather than trying to rearrange the schedule to fit more tasks in.

This is reasonable here because the alternative — exhaustively searching for an optimal packing — is much more complex to implement and explain, and for a single owner with a handful of pets the greedy approach will almost always produce a good-enough result. The cost is that in rare dense schedules the greedy approach might skip a high-priority task that could have been fit in if a lower-priority task had been moved; a future version could add a swap step to handle this.

A second tradeoff is in **conflict detection scope**. `get_conflict_warnings()` checks for overlaps across *all pets*, while `generate_daily_plan()` only checks against tasks it has already committed to the plan. This means the two conflict systems can give different answers for the same task pair. The design choice was deliberate: `get_conflict_warnings()` is a diagnostic tool for the owner ("here's what's impossible"), while `generate_daily_plan()` is an optimizer ("here's the best achievable schedule"). Unifying them into one method would make the code simpler but would collapse two meaningfully different questions into one.

A third tradeoff concerns **recurring task generation**. `mark_task_complete()` creates the next occurrence immediately when a task is completed, using `task.due_time + timedelta(days=1)`. This means if a task is completed early (e.g., the morning walk at 6 AM instead of 7 AM), the next occurrence is still scheduled for 7 AM tomorrow — it uses the *original* due time, not the actual completion time. This is simpler and more predictable for the owner (the schedule stays consistent), but it ignores the real rhythm of when care actually happened.

---

## 3. AI Collaboration

**a. Which Copilot features were most effective**

Three Copilot features made the biggest difference:

- **Inline Chat on specific methods** was the most valuable tool. Asking "walk me through whether this overlap condition correctly handles partial overlaps" on my `check_conflicts()` method gave immediate, targeted feedback I could act on right away. Broad questions in regular chat ("how do I detect conflicts?") produced generic answers; inline questions on actual code produced precise ones.
- **Generate tests smart action** accelerated the test-writing phase. It drafted the happy-path cases quickly, freeing me to focus on edge cases (exact same start time, cross-pet overlaps, pet with no tasks) that required domain reasoning rather than boilerplate.
- **Separate chat sessions per phase** was more useful than expected. Keeping the UML design session separate from the implementation session and the testing session meant each conversation had a focused context. When I asked "what edge cases matter for a scheduler?" in the testing session, Copilot had no noise from earlier design debates — it gave sharper answers.

**b. One AI suggestion I rejected or modified**

When I asked Copilot to suggest how `get_conflict_warnings()` should work, it returned a version that raised a `ValueError` when a conflict was detected, stopping execution. I rejected this entirely. A warning system that crashes the program on the first conflict is the wrong mental model for a UI tool — the owner needs to *see* all conflicts at once so they can decide which tasks to reschedule. I rewrote the method to collect every overlapping pair into a list of strings and return it, so the UI can display all warnings without interrupting the flow. The AI's suggestion was technically valid but was designed for a CLI validation tool, not a live Streamlit app.

**c. Being the "lead architect"**

The main lesson from this project is that **AI is a fast junior collaborator, not a lead designer**. It can draft a method stub, suggest a sort key, or point out an off-by-one in an overlap condition very quickly. But it doesn't know that conflict warnings should be non-crashing, that `Owner.available_minutes` should be a hard cutoff rather than a suggestion, or that `is_completed=False` must be explicitly set on recurring task copies. Those decisions required understanding the *intent* of the system, not just the syntax. Staying in the lead architect role meant treating every AI suggestion as a starting point to evaluate, not a final answer to accept.

---

## 4. Testing and Verification

**a. What you tested**

The final test suite has 27 tests across 5 categories:

1. **`Task`** — `mark_complete()` sets the flag; calling it twice is safe; `priority_score()` returns 3/2/1 for High/Medium/Low.
2. **`Pet`** — adding a task increases the count; `get_pending_tasks()` excludes completed tasks.
3. **`Owner`** — `get_all_tasks()` collects tasks across all pets.
4. **`Scheduler` core** — priority sort order; overlap detected; adjacent tasks not flagged; budget hard cutoff; recurring generation.
5. **`Scheduler` algorithmic** — `sort_by_time()` (order, empty, ignores priority); `filter_tasks()` (by name, by status, no match); `get_conflict_warnings()` (overlap, exact same time, adjacent, cross-pet, empty); `mark_task_complete()` (Daily +1 day, Weekly +7 days, Once no recurrence, flag set); pet with no tasks returns empty safely from all methods.

The most important tests were the boundary cases: adjacent tasks that must *not* trigger a conflict, and exact-same-time tasks that must. These are the conditions most likely to be wrong in a naive implementation.

**b. Confidence**

**★★★★☆** — high confidence in all core behaviors and most edge cases. Three gaps remain:
- `generate_daily_plan()` with a cross-pet conflict in the committed plan (the plan's internal conflict tracker vs. `get_conflict_warnings()` producing different results)
- `generate_recurring_tasks()` called twice on the same pet (potential duplicate tasks)
- Full end-to-end integration test: Owner → add pets → add tasks → generate plan → verify `PlanEntry` reasons match expected logic

---

## 5. Reflection

**a. What went well**

The separation of concerns held up across all six phases. `Task` never needed to know about `Pet`, `Pet` never needed to know about `Scheduler`, and `Owner.get_all_tasks()` gave `Scheduler` a clean single point of access to all data. This meant that when Phase 4 added four new methods to `Scheduler`, none of the other classes needed to change. The design absorbed new features without fracturing — that's the sign that the initial architecture was sound.

The `PlanEntry` dataclass was the single best structural decision. Returning structured objects with a `reason` field rather than plain tuples made the UI section trivial to write — the display logic just reads `entry.reason` and picks `st.success` vs `st.warning` based on `entry.scheduled`. No string parsing, no guessing.

**b. What you would improve**

Two things:

First, **task IDs should use UUIDs**, not manual integers. The current `max(all_ids) + 1` approach is safe for single-session use but fragile if tasks are ever stored, loaded, or deleted out of order. Switching to `uuid.uuid4()` would cost one import and remove an entire class of potential bugs.

Second, **the Streamlit UI has no "mark complete" button**. The `mark_task_complete()` method works correctly (verified by tests), but there's no way to call it from the browser. A real user would need a way to check off tasks during the day and see tomorrow's recurring tasks appear automatically. This is the biggest missing feature between the current app and a genuinely useful tool.

**c. Key takeaway**

The most important thing I learned is that **AI is most useful when you already know what you want and need help with *how* to get there**. When I had a clear design (sort by priority then time, return a list of `PlanEntry` objects, never crash on conflicts), AI helped me write the implementation quickly. When I didn't have a clear design yet, AI suggestions pulled me toward generic solutions that didn't fit the specific problem. The investment in UML and step-by-step planning before writing code wasn't just busywork — it was what made AI collaboration productive instead of distracting.
