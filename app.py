import streamlit as st
from datetime import datetime
from pawpal_system import Owner, Pet, Task, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

# ── Session state bootstrap ───────────────────────────────────────────────────
if "owner" not in st.session_state:
    st.session_state.owner = None
if "next_id" not in st.session_state:
    st.session_state.next_id = 1


def next_id() -> int:
    """Return a unique id and advance the counter."""
    id_ = st.session_state.next_id
    st.session_state.next_id += 1
    return id_


# ── Header ────────────────────────────────────────────────────────────────────

st.title("🐾 PawPal+")
st.caption("A daily care planner for busy pet owners.")
st.divider()

# ── 1. Owner setup ────────────────────────────────────────────────────────────

st.subheader("1. Owner")

with st.form("owner_form"):
    col1, col2 = st.columns([2, 1])
    with col1:
        owner_name = st.text_input("Your name", value="Jordan")
    with col2:
        available = st.number_input("Available minutes today", min_value=10, max_value=480, value=120)
    submitted = st.form_submit_button("Save owner")

if submitted:
    existing_pets = st.session_state.owner.pets if st.session_state.owner else []
    st.session_state.owner = Owner(name=owner_name, available_minutes=available, pets=existing_pets)
    st.success(f"Owner saved: {owner_name} ({available} min available today)")

if st.session_state.owner is None:
    st.info("Fill in your name and save to get started.")
    st.stop()

owner: Owner = st.session_state.owner

# ── 2. Add a pet ──────────────────────────────────────────────────────────────

st.divider()
st.subheader("2. Pets")

with st.form("pet_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        pet_name = st.text_input("Pet name", value="Mochi")
    with col2:
        species = st.selectbox("Species", ["Dog", "Cat", "Rabbit", "Bird", "Other"])
    with col3:
        age = st.number_input("Age (years)", min_value=0, max_value=30, value=3)
    add_pet = st.form_submit_button("Add pet")

if add_pet:
    existing_names = [p.name.lower() for p in owner.pets]
    if pet_name.lower() in existing_names:
        st.warning(f"A pet named '{pet_name}' already exists.")
    else:
        owner.add_pet(Pet(id=next_id(), name=pet_name, species=species, age=age))
        st.success(f"Added {species} '{pet_name}' (age {age}).")

if owner.pets:
    st.table([{"Name": p.name, "Species": p.species, "Age": p.age} for p in owner.pets])
else:
    st.info("No pets yet. Add one above.")

# ── 3. Add a task ─────────────────────────────────────────────────────────────

st.divider()
st.subheader("3. Tasks")

if not owner.pets:
    st.info("Add a pet first before adding tasks.")
else:
    with st.form("task_form"):
        col1, col2 = st.columns(2)
        with col1:
            task_pet  = st.selectbox("For which pet?", [p.name for p in owner.pets])
            task_desc = st.text_input("Task description", value="Morning walk")
            task_freq = st.selectbox("Frequency", ["Once", "Daily", "Weekly"])
        with col2:
            task_hour = st.slider("Due hour", 0, 23, 8)
            task_min  = st.selectbox("Due minute", [0, 15, 30, 45])
            task_dur  = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=30)
            task_pri  = st.selectbox("Priority", ["Low", "Medium", "High"], index=2)
        add_task = st.form_submit_button("Add task")

    if add_task:
        pet = next(p for p in owner.pets if p.name == task_pet)
        due = datetime.today().replace(hour=task_hour, minute=int(task_min), second=0, microsecond=0)
        task = Task(
            id=next_id(),
            description=task_desc,
            due_time=due,
            duration_mins=int(task_dur),
            priority=task_pri,
            frequency=task_freq,
        )
        pet.add_task(task)
        st.success(f"Added '{task_desc}' to {task_pet} at {due.strftime('%I:%M %p')} ({task_pri} priority).")

    # ── Conflict warnings ─────────────────────────────────────────────────────
    # Run before showing the task table so the owner sees problems immediately.
    if owner.get_all_tasks():
        scheduler = Scheduler(owner)
        warnings = scheduler.get_conflict_warnings()
        if warnings:
            st.markdown("**⚠️ Scheduling conflicts detected — resolve before generating a plan:**")
            for w in warnings:
                st.warning(w)

    # ── Task table: two views via tabs ────────────────────────────────────────
    all_tasks = owner.get_all_tasks()
    if all_tasks:
        tab_priority, tab_time, tab_filter = st.tabs(
            ["By priority", "By time", "Filter by pet"]
        )

        with tab_priority:
            s = Scheduler(owner)
            rows = s.get_upcoming_tasks()
            st.table([
                {"Pet": n, "Task": t.description, "Due": t.due_time.strftime("%I:%M %p"),
                 "Duration": f"{t.duration_mins} min", "Priority": t.priority, "Repeat": t.frequency}
                for n, t in rows
            ])

        with tab_time:
            s = Scheduler(owner)
            rows = s.sort_by_time()
            st.caption("Tasks in chronological order, regardless of priority.")
            st.table([
                {"Due": t.due_time.strftime("%I:%M %p"), "Pet": n, "Task": t.description,
                 "Duration": f"{t.duration_mins} min", "Priority": t.priority}
                for n, t in rows
            ])

        with tab_filter:
            pet_options = ["All pets"] + [p.name for p in owner.pets]
            chosen_pet = st.selectbox("Show tasks for:", pet_options, key="filter_pet")
            s = Scheduler(owner)
            filter_name = None if chosen_pet == "All pets" else chosen_pet
            rows = s.filter_tasks(pet_name=filter_name, completed=False)
            if rows:
                st.table([
                    {"Pet": n, "Task": t.description, "Due": t.due_time.strftime("%I:%M %p"),
                     "Priority": t.priority, "Repeat": t.frequency}
                    for n, t in rows
                ])
            else:
                st.info("No pending tasks match that filter.")
    else:
        st.info("No tasks yet. Add one above.")

# ── 4. Generate schedule ──────────────────────────────────────────────────────

st.divider()
st.subheader("4. Today's Plan")

if st.button("Generate schedule", type="primary"):
    if not owner.get_all_tasks():
        st.warning("Add at least one task before generating a schedule.")
    else:
        scheduler = Scheduler(owner)

        # Surface any conflicts as a heads-up before showing the plan
        warnings = scheduler.get_conflict_warnings()
        if warnings:
            with st.expander(f"⚠️ {len(warnings)} conflict(s) found — the planner will resolve them automatically", expanded=False):
                for w in warnings:
                    st.warning(w)

        plan      = scheduler.generate_daily_plan()
        scheduled = [e for e in plan if e.scheduled]
        skipped   = [e for e in plan if not e.scheduled]
        total_used = sum(e.task.duration_mins for e in scheduled)

        st.markdown(f"**{owner.name}'s plan — {datetime.today().strftime('%A, %B %d')}**")

        # Progress bar shows budget consumption at a glance
        budget_pct = min(total_used / owner.available_minutes, 1.0)
        st.progress(budget_pct, text=f"Time used: {total_used} / {owner.available_minutes} min")

        if scheduled:
            st.markdown("#### ✅ Scheduled")
            for entry in scheduled:
                time_str = entry.task.due_time.strftime("%I:%M %p")
                st.success(
                    f"**{time_str}** · [{entry.pet_name}] {entry.task.description} "
                    f"— _{entry.reason}_"
                )

        if skipped:
            st.markdown("#### ⏭ Skipped")
            for entry in skipped:
                time_str = entry.task.due_time.strftime("%I:%M %p")
                st.warning(
                    f"**{time_str}** · [{entry.pet_name}] {entry.task.description} "
                    f"— _{entry.reason}_"
                )
