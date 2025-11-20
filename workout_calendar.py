import calendar as cal
from datetime import date, timedelta

import streamlit as st
from streamlit import session_state as state

PRIMARY_COLOR = "#007A3D"


# ===================================================
#              WORKOUT SPLIT HANDLING
# ===================================================

def get_split_labels(split_option):
    """Return a list of workout labels based on dropdown selection."""
    if split_option == "Push / Pull / Legs":
        return ["Push", "Pull", "Legs"]
    elif split_option == "Push / Pull":
        return ["Push", "Pull"]
    elif split_option == "Upper / Lower":
        return ["Upper", "Lower"]
    elif split_option == "Full Body":
        return ["Full Body"]
    return ["Full Body"]


# ===================================================
#           WORKOUT CALENDAR LOGIC
# ===================================================

def generate_schedule(split_labels, hyper_per_week, cardio_per_week,
                      start_date: date, num_days: int = 60):
    """
    Build a list of dicts:
    {date, kind: 'Hypertrophy'/'Cardio'/'Rest', label, done}
    """
    hyper_per_week = max(0, min(7, int(hyper_per_week)))
    cardio_per_week = max(0, min(7 - hyper_per_week, int(cardio_per_week)))
    rest_per_week = 7 - hyper_per_week - cardio_per_week

    week_pattern = ["H"] * hyper_per_week + ["C"] * cardio_per_week + ["R"] * rest_per_week

    schedule = []
    label_idx = 0

    for offset in range(num_days):
        d = start_date + timedelta(days=offset)
        symbol = week_pattern[offset % 7]

        if symbol == "H":
            label = split_labels[label_idx % len(split_labels)]
            label_idx += 1
            schedule.append(
                {"date": d, "kind": "Hypertrophy", "label": label, "done": False}
            )
        elif symbol == "C":
            schedule.append(
                {"date": d, "kind": "Cardio", "label": "Cardio", "done": False}
            )
        else:
            schedule.append(
                {"date": d, "kind": "Rest", "label": "Rest", "done": False}
            )

    return schedule


def extend_schedule_if_needed(split_labels, hyper_per_week, cardio_per_week,
                              until_date: date):
    """Ensure the plan covers at least up to `until_date`."""
    if "plan" not in state or not state.plan:
        today = date.today()
        state.plan_start = today
        state.plan = generate_schedule(
            split_labels, hyper_per_week, cardio_per_week, today, num_days=60
        )

    last_day = state.plan[-1]["date"]

    if last_day < until_date:
        extra_start = last_day + timedelta(days=1)
        extra_days = (until_date - extra_start).days + 30
        extra = generate_schedule(
            split_labels, hyper_per_week, cardio_per_week, extra_start, num_days=extra_days
        )
        state.plan.extend(extra)


def show_today_control(split_labels, hyper_days, cardio_days):
    """UI: show today's workout and allow marking done (no shifting)."""
    today = date.today()
    extend_schedule_if_needed(split_labels, hyper_days, cardio_days, today + timedelta(days=30))

    todays_entries = [p for p in state.plan if p["date"] == today and p["kind"] != "Rest"]

    if not todays_entries:
        st.info("Today is a rest day. Enjoy it 😌")
        return

    entry = todays_entries[0]
    st.subheader("Today's Workout")
    st.write(f"**{entry['label']}** ({entry['kind']})")

    done_key = f"done_{today.isoformat()}"
    default_done = entry.get("done", False)
    done = st.checkbox("I completed this workout ✅", value=default_done, key=done_key)

    if st.button("Save today's result"):
        idx = state.plan.index(entry)
        state.plan[idx]["done"] = done
        st.success("Saved! ✔")
        st.rerun()


def show_calendar(split_labels, hyper_days, cardio_days):
    """Classic month grid calendar with navigation and coloring."""
    today = date.today()

    if "cal_year" not in state or "cal_month" not in state:
        state.cal_year = today.year
        state.cal_month = today.month

    first_of_month = date(state.cal_year, state.cal_month, 1)
    _, last_day_num = cal.monthrange(state.cal_year, state.cal_month)
    last_of_month = date(state.cal_year, state.cal_month, last_day_num)

    extend_schedule_if_needed(split_labels, hyper_days, cardio_days, last_of_month)

    st.markdown("### Calendar")

    col_prev, col_label, col_next = st.columns([1, 3, 1])

    # previous month
    with col_prev:
        if st.button("◀ Previous month"):
            pm = state.cal_month - 1
            py = state.cal_year
            if pm == 0:
                pm = 12
                py -= 1

            earliest_month = date(state.plan_start.year, state.plan_start.month, 1)
            prev_month = date(py, pm, 1)

            if prev_month >= earliest_month:
                state.cal_month, state.cal_year = pm, py
                st.rerun()

    # next month
    with col_next:
        if st.button("Next month ▶"):
            nm = state.cal_month + 1
            ny = state.cal_year
            if nm == 13:
                nm = 1
                ny += 1

            state.cal_month, state.cal_year = nm, ny
            st.rerun()

    with col_label:
        st.markdown(
            f"<h4 style='text-align:center;'>{cal.month_name[state.cal_month]} {state.cal_year}</h4>",
            unsafe_allow_html=True,
        )

    st.markdown("""
**Legend**  
🟩 done • 🟧 planned workout • ⬜ rest day • 🔺 today
""")

    c = cal.Calendar(firstweekday=0)
    weeks = c.monthdatescalendar(state.cal_year, state.cal_month)

    weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    cols = st.columns(7)
    for i, name in enumerate(weekday_names):
        cols[i].markdown(f"**{name}**")

    for week in weeks:
        row = st.columns(7)
        for i, day in enumerate(week):
            with row[i]:
                if day.month != state.cal_month:
                    st.write(" ")
                    continue

                entry = next((p for p in state.plan if p["date"] == day), None)

                if entry:
                    if entry["kind"] == "Rest":
                        icon = "⬜"
                        label = "Rest"
                    else:
                        icon = "🟩" if entry["done"] else "🟧"
                        label = entry["label"]
                else:
                    icon, label = "", ""

                today_mark = " 🔺" if day == today else ""

                st.markdown(
                    f"**{day.day}**{today_mark}<br>{icon} {label}",
                    unsafe_allow_html=True,
                )


# ===================================================
#                     MAIN
# ===================================================

def main():
    st.set_page_config(page_title="Pumpfessor Joe Calendar", layout="centered")

    st.markdown(
        f"<h1 style='color:{PRIMARY_COLOR};'>Pumpfessor Joe Calendar</h1>",
        unsafe_allow_html=True,
    )

    st.write("Set up your training split and weekly training frequency:")

    # 🔽 NEW: Dropdown split selector
    split_option = st.selectbox(
        "Workout Split:",
        ["Push / Pull / Legs", "Push / Pull", "Upper / Lower", "Full Body"],
        index=0,
    )

    split_labels = get_split_labels(split_option)

    col_h, col_c = st.columns(2)
    hyper_days = col_h.slider("Hypertrophy days per week", 0, 7, 4)
    cardio_days = col_c.slider("Cardio days per week", 0, 7, 2)

    if hyper_days + cardio_days > 7:
        st.warning("Training days per week cannot exceed 7. Extra days will be ignored.")

    if st.button("Generate / Reset Plan"):
        state.plan_start = date.today()
        state.plan = generate_schedule(
            split_labels, hyper_days, cardio_days, state.plan_start, num_days=60
        )
        state.cal_year = state.plan_start.year
        state.cal_month = state.plan_start.month
        st.rerun()

    # Today workout + calendar
    show_today_control(split_labels, hyper_days, cardio_days)
    st.markdown("---")
    show_calendar(split_labels, hyper_days, cardio_days)


if __name__ == "__main__":
    main()
