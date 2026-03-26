# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

My initial UML design had three core classes:

- **`Task`** — holds a single care activity with attributes for `description`, `due_time`, `duration_mins`, `priority` (Low/Medium/High), `frequency` (Once/Daily/Weekly), and `is_completed`. Responsible only for representing data about one activity.
- **`Pet`** — holds a pet's profile (`name`, `species`, `age`) and owns a list of `Task` objects. Responsible for adding tasks and reporting its own schedule.
- **`Scheduler`** — the central "brain." Holds a list of `Pet` objects and is responsible for sorting tasks by priority and time, detecting time-slot conflicts across all pets, and generating the daily plan.

I initially also sketched an `Owner` class that would store preferences (e.g., available hours per day), but left it out of the first version to keep scope manageable.

**b. Design changes**

Yes — my design changed in two ways during implementation.

First, I moved conflict detection fully into `Scheduler` rather than `Pet`. My first sketch had `Pet.has_conflict(task)` as a method, but I realized conflicts can happen *across* pets (two pets need a walk at the same time), so only the `Scheduler` has the full picture needed to check conflicts correctly.

Second, I added a `priority_score()` helper method to `Task`. When I started implementing `get_upcoming_tasks()`, I found myself repeating the same priority-to-integer mapping (`"High" → 3`, `"Medium" → 2`, `"Low" → 1`) in multiple places. Moving it into `Task` made the sort key cleaner and centralized the logic.

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

---

## 3. AI Collaboration

**a. How you used AI**

I used AI tools in three main ways:

- **Design brainstorming** — I described the scenario to Claude and asked it to help me draft a UML diagram. That conversation surfaced the question of whether conflict detection belongs in `Pet` or `Scheduler`, which led directly to the design change described above.
- **Sorting logic** — I asked for help writing the `key` function for `sorted()` that combines priority and due time into a single comparable value. The AI suggested using a tuple `(-priority_score(), due_time)` as the sort key, which was clean and correct.
- **Debugging** — When my overlap check was giving false positives, I described the condition to the AI and it helped me spot that I was comparing `datetime` objects without normalizing timezone info.

The most helpful prompts were specific and concrete: "Here is my `check_conflicts` method — walk me through whether this condition correctly detects a partial overlap" was much more useful than "how do I detect conflicts?"

**b. Judgment and verification**

When I asked the AI to help implement `generate_recurring_tasks()`, it suggested using `datetime.timedelta` to add one day (for daily tasks) and then appending a new `Task` with the same attributes but an updated `due_time`. The suggestion looked right, but I noticed it did not copy the `is_completed` flag — it left the new task with `is_completed=True` if the original had been marked complete.

I caught this by tracing through a concrete example: if I complete today's feeding task and then call `generate_recurring_tasks()`, the next day's feeding task should start as *incomplete*. The AI's code would have pre-marked tomorrow's task as done. I fixed it by explicitly setting `is_completed=False` on each generated task, and added a test case that checks the flag on the generated task rather than just checking that a new task was created.

---

## 4. Testing and Verification

**a. What you tested**

I wrote tests for four behaviors:

1. **`Task.mark_complete()`** — verifies that calling the method sets `is_completed` to `True`.
2. **`Scheduler.get_upcoming_tasks()`** — creates three tasks with mixed priorities and verifies the returned list is ordered High → Medium → Low.
3. **`Scheduler.check_conflicts()`** — tests two cases: a new task that overlaps an existing task (should return `True`) and one that doesn't overlap (should return `False`).
4. **`Scheduler.generate_recurring_tasks()`** — verifies that a Daily task produces a new task scheduled one day later with `is_completed=False`.

These tests mattered because they cover the three methods that have the most logic and the most ways to be wrong. The conflict detection test in particular exercises the boundary condition (tasks that are adjacent but not overlapping should not be flagged).

**b. Confidence**

I'm fairly confident in the core happy-path cases. The edge cases I would test next given more time:

- Two tasks with the exact same `due_time` and `duration` — should be flagged as a conflict; currently borderline because the overlap check uses strict inequality on one end.
- A `duration_mins` of 0 — does the scheduler handle instantaneous tasks correctly?
- `generate_recurring_tasks()` called multiple times on the same pet — are duplicate tasks generated?
- A pet with no tasks — does `get_upcoming_tasks()` return an empty list without error?

---

## 5. Reflection

**a. What went well**

I'm most satisfied with the separation of concerns between `Task`, `Pet`, and `Scheduler`. Each class does one thing: `Task` holds data, `Pet` groups tasks by animal, and `Scheduler` makes decisions. This made the code easy to test in isolation and made it straightforward to add the `priority_score()` helper without touching the scheduler.

**b. What you would improve**

If I had another iteration, I would implement the `Owner` class I initially cut. Right now the scheduler has no concept of how much time an owner actually has in a day, so it will happily generate a schedule that requires six hours of care tasks for a two-hour morning window. Adding an `available_minutes` constraint to `Owner` and surfacing a warning (or pruning low-priority tasks) when the schedule exceeds it would make the output much more useful.

**c. Key takeaway**

The most important thing I learned is that **AI suggestions need to be tested against concrete examples, not just read and accepted**. The recurring-task bug was invisible when I read the AI's code — it looked correct. It only became visible when I traced through a specific scenario with actual values. Going forward I'll treat AI-generated logic the same way I treat code review: understand it line by line and construct at least one concrete test case before trusting it.
