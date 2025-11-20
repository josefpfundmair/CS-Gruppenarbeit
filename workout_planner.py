import math
import random
import pandas as pd
import streamlit as st
from streamlit import session_state as state

PRIMARY_COLOR = "#007A3D"


# ---------------------------------------------------
# LOAD DATA
# ---------------------------------------------------
@st.cache_data
def load_exercises(csv):
    df = pd.read_csv(csv)

    df.columns = [c.strip() for c in df.columns]

    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].astype(str).str.strip()

    rename = {}
    for c in df.columns:
        name = c.lower()
        if name.startswith("exercise"):
            rename[c] = "Exercise"
        elif name.startswith("equipment"):
            rename[c] = "Equipment Required"
        elif name.startswith("muscle"):
            rename[c] = "Muscle Group"
        elif name.startswith("link"):
            rename[c] = "Link"

    df = df.rename(columns=rename)

    df = df.dropna(subset=["Exercise", "Muscle Group"])
    df = df[df["Exercise"].str.lower() != "nan"]
    df = df[df["Muscle Group"].str.lower() != "nan"]

    return df


# ---------------------------------------------------
# MUSCLE INFERENCE
# ---------------------------------------------------
def infer_muscles_from_title(title, all_muscles):
    title = title.lower()

    mapping = {
        "push": ["Chest", "Triceps", "Shoulders"],
        "pull": ["Back", "Biceps"],
        "legs": ["Legs", "Quads", "Hamstrings", "Glutes"],
        "upper": ["Chest", "Shoulders", "Back", "Arms"],
        "lower": ["Legs", "Quads", "Hamstrings", "Glutes"],
        "arms": ["Biceps", "Triceps", "Forearms"],
        "chest": ["Chest"],
        "back": ["Back"],
        "shoulder": ["Shoulders"],
        "glute": ["Glutes"],
        "core": ["Abs", "Core"],
        "abs": ["Abs", "Core"],
    }

    found = set()
    for key, muscles in mapping.items():
        if key in title:
            found.update([m for m in muscles if m in all_muscles])

    if not found:
        return all_muscles[:3]

    return list(found)


# ---------------------------------------------------
# AI LOGIC
# ---------------------------------------------------
def compute_num_exercises(minutes, intensity):
    base = max(3, min(10, round(minutes / 8)))
    if intensity == "Light":
        return max(3, int(base * 0.8))
    if intensity == "Moderate":
        return base
    return min(12, int(base * 1.2))


def score_exercise(row, targets, soreness, intensity):
    mg = row["Muscle Group"]
    score = 0.0

    if mg in targets:
        score += 6.0

    score -= soreness.get(mg, 0) * 1.6
    score += random.uniform(-1, 1)

    return score


def sets_reps_rest(intensity):
    if intensity == "Light":
        return 2, "12–15", "45–60 sec"
    if intensity == "Moderate":
        return 3, "8–12", "60–90 sec"
    return 4, "6–10", "90–120 sec"


# ---------------------------------------------------
# BUILD WORKOUT
# ---------------------------------------------------
def build_workout_plan(df, title, minutes, wishes, soreness, intensity):
    targets = infer_muscles_from_title(title, sorted(df["Muscle Group"].unique()))

    very_sore = [m for m, s in soreness.items() if s >= 8]
    df = df[~df["Muscle Group"].isin(very_sore)]

    if df.empty:
        return []

    df = df.copy()
    df["score"] = df.apply(
        lambda r: score_exercise(r, targets, soreness, intensity), axis=1
    )
    df = df.sort_values("score", ascending=False)

    num = min(compute_num_exercises(minutes, intensity), len(df))
    sets, reps, rest = sets_reps_rest(intensity)

    exercises = []
    for _, r in df.head(num).iterrows():
        exercises.append(
            {
                "name": r["Exercise"],
                "muscle": r["Muscle Group"],
                "equipment": r.get("Equipment Required", "–"),
                "sets": sets,
                "reps": reps,
                "rest": rest,
                "link": r.get("Link", ""),
            }
        )

    return exercises


# ---------------------------------------------------
# FLASHCARDS WITH LEFT/RIGHT BUTTONS
# ---------------------------------------------------
def show_flashcards():
    exercises = state.workout
    idx = state.current_card
    total = len(exercises)
    ex = exercises[idx]

    st.write(f"### Exercise {idx + 1} of {total}")
    st.progress((idx + 1) / total)

    st.markdown(
        f"""
<div style="padding:25px; border-radius:22px; background:white;
            box-shadow:0 6px 14px rgba(0,0,0,0.12); margin-top:20px;">
  <h2 style="color:{PRIMARY_COLOR}; margin-top:0;">{ex['name']}</h2>
  <ul style="font-size:16px; line-height:1.7;">
    <li><b>Muscle trained:</b> {ex['muscle']}</li>
    <li><b>Equipment needed:</b> {ex['equipment']}</li>
    <li><b>Your goal:</b> {ex['sets']} sets × {ex['reps']}</li>
    <li><b>Rest between sets:</b> {ex['rest']}</li>
  </ul>
  {f'<a href="{ex["link"]}" target="_blank" style="color:{PRIMARY_COLOR}; font-weight:bold;">Video exercise demonstration</a>'
      if isinstance(ex["link"], str) and ex["link"].startswith("http") else ""}
</div>
""",
        unsafe_allow_html=True,
    )

    # LAYOUT: Previous (far left) — big spacer — Next/Finish (far right)
    col_left, col_spacer, col_right = st.columns([1, 4, 1])

    # previous button (hidden on first exercise)
    with col_left:
        if idx > 0:
            if st.button("⬅️ Previous Exercise"):
                state.current_card -= 1
                st.rerun()
        else:
            st.write("")

    # next / finish button
    with col_right:
        button_label = "Next Exercise 👉"
        if idx == total - 1:
            button_label = "Finish Workout 🎉"

        if st.button(button_label):
            state.current_card += 1
            if state.current_card >= total:
                state.finished = True
            st.rerun()


# ---------------------------------------------------
# COMPLETION SCREEN
# ---------------------------------------------------
def show_completion():
    st.markdown(
        f"<h2 style='color:{PRIMARY_COLOR};'>Workout Completed! 🎉</h2>",
        unsafe_allow_html=True,
    )
    st.success("Joe the Pumpfessor is proud of you! 💪🔥")

    st.write("### Your full workout summary:")

    for ex in state.workout:
        st.markdown(
            f"""
<div style="padding:18px; border-radius:16px; border:2px solid {PRIMARY_COLOR};
            background:#F4FFF7; margin:10px 0;">
  <h4 style='color:{PRIMARY_COLOR}; margin-top:0;'>{ex['name']}</h4>
  <p><b>Muscle:</b> {ex['muscle']}</p>
  <p><b>Equipment:</b> {ex['equipment']}</p>
  <p><b>Sets/Reps:</b> {ex['sets']} × {ex['reps']}</p>
  <p><b>Rest:</b> {ex['rest']}</p>
  {f'<a href="{ex["link"]}" target="_blank">Video exercise demonstration</a>'
      if isinstance(ex["link"], str) and ex["link"].startswith("http") else ""}
</div>
""",
            unsafe_allow_html=True,
        )

    if st.button("Back to workout builder ↩️"):
        for key in ["workout", "current_card", "finished"]:
            if key in state:
                del state[key]
        st.rerun()


# ---------------------------------------------------
# MAIN
# ---------------------------------------------------
def main():
    st.set_page_config(page_title="Pumpfessor Joe Workout Builder", layout="centered")

    st.markdown(
        f"<h1 style='color:{PRIMARY_COLOR};'>Build a workout with Pumpfessor Joe</h1>",
        unsafe_allow_html=True,
    )

    df = load_exercises("CS Workout Exercises Database CSV.csv")
    muscles = sorted(df["Muscle Group"].unique())

    if "workout" in state and not state.get("finished", False):
        show_flashcards()
        return

    if state.get("finished", False):
        show_completion()
        return

    title = st.text_input("Workout name:", "Push Day")
    minutes = st.slider("How many minutes do you have?", 15, 120, 45, 5)

    st.markdown(
        f"<p style='color:{PRIMARY_COLOR};'><b>Are you sore anywhere?</b></p>",
        unsafe_allow_html=True,
    )

    soreness = {}
    sore_groups = st.multiselect("Select sore muscle groups:", muscles)
    for m in sore_groups:
        soreness[m] = st.slider(f"Soreness in {m}", 1, 10, 5)

    wishes = st.text_area("Additional wishes (optional):")
    intensity = st.selectbox("Intensity:", ["Light", "Moderate", "Max effort"], 1)

    if st.button("Generate Workout"):
        workout = build_workout_plan(df, title, minutes, wishes, soreness, intensity)
        if not workout:
            st.warning("No suitable exercises found.")
        else:
            state.workout = workout
            state.current_card = 0
            state.finished = False
            st.rerun()


if __name__ == "__main__":
    main()


