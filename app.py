import streamlit as st
import sqlite3
import hashlib
import re  # used for password strength checks
import pandas as pd  # used for the demo chart on the progress page

# ---------- basic page setup ----------
st.set_page_config(
    page_title="Uni Gym Personal Trainer",
    page_icon="💪",
    layout="wide",
)

# ---------- custom CSS for green + glass look ----------
st.markdown(
    """
    <style>
    body {
        background: radial-gradient(circle at top left, #123824 0, #020b08 45%, #010504 100%);
    }

    [data-testid="stSidebar"] {
        background: rgba(5, 20, 12, 0.65);
        backdrop-filter: blur(18px);
        -webkit-backdrop-filter: blur(18px);
        border-right: 1px solid rgba(255, 255, 255, 0.06);
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1000px;
        margin: auto;
    }

    [data-testid="stSidebar"] .stButton > button {
        width: 100%;
        border-radius: 999px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        background: rgba(15, 40, 25, 0.7);
        color: #ECF0F1;
        padding: 0.5rem 1rem;
        margin-bottom: 0.25rem;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        border-color: #1ABC9C;
        background: rgba(22, 60, 36, 0.9);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# DATABASE + SECURITY
# =========================================================

def get_db():
    """Open a connection to the SQLite database file."""
    conn = sqlite3.connect("gym_app.db")
    conn.execute("PRAGMA foreign_keys = 1")
    return conn


def create_tables():
    """Create tables for users and profiles if they do not exist."""
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS profiles (
            user_id INTEGER UNIQUE,
            age INTEGER,
            weight REAL,
            height REAL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )

    conn.commit()
    conn.close()


def hash_password(password: str) -> str:
    """Hash a password string with SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()


# ---------- password + email validation ----------

def validate_password_strength(password: str):
    """
    Check if password is strong enough:
    - at least 8 characters
    - at least one lowercase letter
    - at least one uppercase letter
    - at least one digit
    - at least one special character
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one digit."
    if not re.search(r"[^A-Za-z0-9]", password):
        return False, "Password must contain at least one special character (e.g. !, ?, #, ...)."
    return True, ""


def is_valid_email(email: str) -> bool:
    """Simple email format validation."""
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return re.match(pattern, email) is not None


# =========================================================
# AUTHENTICATION LOGIC
# =========================================================

def register_user(email: str, password: str):
    """Create a new user and an empty profile."""
    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email, hash_password(password)),
        )
        user_id = cur.lastrowid

        # create empty profile row for the new user
        cur.execute(
            "INSERT INTO profiles (user_id, age, weight, height) VALUES (?, ?, ?, ?)",
            (user_id, None, None, None),
        )

        conn.commit()
        conn.close()
        return True, "Account created. You can now log in."
    except sqlite3.IntegrityError:
        conn.close()
        return False, "An account with this email already exists."


def verify_user(email: str, password: str):
    """Return user_id if email/password are correct, otherwise None."""
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT id, password_hash FROM users WHERE email = ?",
        (email,),
    )
    row = cur.fetchone()
    conn.close()

    if row is None:
        return None

    user_id, stored_hash = row
    if stored_hash == hash_password(password):
        return user_id
    return None


# =========================================================
# PROFILE DB ACCESS
# =========================================================

def get_profile(user_id: int):
    """Fetch age, weight, height for a given user_id."""
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT age, weight, height FROM profiles WHERE user_id = ?",
        (user_id,),
    )
    row = cur.fetchone()
    conn.close()

    if row:
        return {"age": row[0], "weight": row[1], "height": row[2]}
    return {"age": None, "weight": None, "height": None}


def update_profile(user_id: int, age: int, weight: float, height: float):
    """Update profile values for a given user_id."""
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE profiles
        SET age = ?, weight = ?, height = ?
        WHERE user_id = ?
        """,
        (age, weight, height, user_id),
    )
    conn.commit()
    conn.close()


# =========================================================
# AUTHENTICATION UI (LOGIN / REGISTER)
# =========================================================

def show_login_page():
    """Login screen styled with centered card."""
    col_left, col_center, col_right = st.columns([1, 2, 1])

    with col_center:
        st.title("Login")
        st.caption("Access your personal training dashboard.")

        with st.container(border=True):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")

            if st.button("Login", use_container_width=True):
                if not email or not password:
                    st.error("Please enter both email and password.")
                else:
                    user_id = verify_user(email, password)
                    if user_id:
                        st.session_state.logged_in = True
                        st.session_state.user_id = user_id
                        st.session_state.user_email = email
                        st.rerun()
                    else:
                        st.error("Invalid email or password.")

        st.write("---")
        st.write("Don't have an account yet?")
        if st.button("Create a new account", use_container_width=True):
            st.session_state.login_mode = "register"
            st.rerun()


def show_register_page():
    """Registration screen styled with centered card and password rules."""
    col_left, col_center, col_right = st.columns([1, 2, 1])

    with col_center:
        st.title("Register")
        st.caption("Create an account for the Uni Gym personal trainer.")

        with st.container(border=True):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")

            st.markdown(
                """
                **Password must contain:**
                - at least 8 characters  
                - at least one lowercase letter  
                - at least one uppercase letter  
                - at least one digit  
                - at least one special character (e.g. `!`, `?`, `#`, `@`)
                """,
                unsafe_allow_html=False,
            )

            if st.button("Register", use_container_width=True):
                if not email or not password:
                    st.error("Please enter both email and password.")
                elif not is_valid_email(email):
                    st.error("Please enter a valid email address.")
                else:
                    ok_pw, msg_pw = validate_password_strength(password)
                    if not ok_pw:
                        st.error(msg_pw)
                    else:
                        ok, msg = register_user(email, password)
                        if ok:
                            st.success(msg)
                            st.session_state.login_mode = "login"
                        else:
                            st.error(msg)

        st.write("---")
        if st.button("Back to login", use_container_width=True):
            st.session_state.login_mode = "login"
            st.rerun()


# =========================================================
# APP PAGES (Profile / Trainer / Calorie tracker / Progress)
# =========================================================

def show_profile_page():
    """Profile page with inputs stored in the database."""
    user_id = st.session_state.user_id
    profile = get_profile(user_id)

    st.header("Profile")
    st.write("Basic information that can be used by the trainer logic later.")
    st.divider()

    col_left, col_center, col_right = st.columns([1, 2, 1])

    with col_center:
        with st.container(border=True):
            st.subheader("Your data")

            c1, c2 = st.columns(2)

            with c1:
                age = st.number_input(
                    "Age (years)",
                    min_value=0,
                    max_value=120,
                    value=profile["age"] if profile["age"] is not None else 0,
                    step=1,
                )

                height = st.number_input(
                    "Height (cm)",
                    min_value=0.0,
                    max_value=300.0,
                    value=profile["height"] if profile["height"] is not None else 0.0,
                    step=0.5,
                )

            with c2:
                weight = st.number_input(
                    "Weight (kg)",
                    min_value=0.0,
                    max_value=500.0,
                    value=profile["weight"] if profile["weight"] is not None else 0.0,
                    step=0.5,
                )

            if st.button("Save profile", use_container_width=True):
                update_profile(user_id, int(age), float(weight), float(height))
                st.success("Profile saved.")

        st.divider()
        st.subheader("Current profile data")

        # reload profile from DB (in case it changed)
        profile = get_profile(user_id)

        age_display = profile["age"] if profile["age"] not in (None, 0) else "Not set"
        weight_display = profile["weight"] if profile["weight"] not in (None, 0.0) else "Not set"
        height_display = profile["height"] if profile["height"] not in (None, 0.0) else "Not set"

        if age_display == weight_display == height_display == "Not set":
            st.info("No profile data saved yet.")
        else:
            st.write(f"**Age:** {age_display} years")
            st.write(f"**Weight:** {weight_display} kg")
            st.write(f"**Height:** {height_display} cm")

        # --- Profile completeness indicator ---
        filled_fields = sum(
            1
            for value in [profile["age"], profile["weight"], profile["height"]]
            if value not in (None, 0, 0.0)
        )
        completeness = filled_fields / 3

        st.write("")
        st.write("Profile completeness:")
        st.progress(completeness)


def show_trainer_page():
    """Placeholder page for future trainer logic."""
    st.header("Trainer")

    user_id = st.session_state.user_id
    profile = get_profile(user_id)  # your teammates can use this

    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_center:
        with st.container(border=True):
            st.subheader("Personal training plan (coming soon)")
            st.write(
                "Here, the trainer module can use the logged-in user's profile "
                "to generate a personalized workout plan."
            )

            st.code(
                "Example:\n"
                "plan = generate_workout_plan(profile)\n"
                "st.write(plan)",
                language="python",
            )

            st.info("This area is reserved for the trainer logic.")


def show_calorie_tracker_page():
    """Placeholder page for future calorie tracker logic."""
    st.header("Calorie tracker")

    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_center:
        with st.container(border=True):
            st.subheader("Coming soon")
            st.write(
                "This page will later be used to track calories burned and possibly calories eaten."
            )
            st.info("Calorie tracking logic will be implemented by your teammates.")


def show_progress_page():
    """Simple placeholder progress page with a demo chart."""
    st.header("Progress")

    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_center:
        with st.container(border=True):
            st.subheader("Demo progress (to be replaced with real data)")

            st.write(
                "This simple chart is a placeholder. "
                "Later, your team can replace it with real workout or calorie data."
            )

            # example data: completed workouts per week
            data = {
                "Week": ["Week 1", "Week 2", "Week 3", "Week 4"],
                "Workouts": [2, 3, 4, 3],
            }
            df = pd.DataFrame(data).set_index("Week")

            st.bar_chart(df)

            st.info("Your teammates can plug real data into this chart later.")


# =========================================================
# MAIN APP
# =========================================================

def main():
    """Entry point: handle login state and page routing."""
    create_tables()  # make sure DB tables exist

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "login_mode" not in st.session_state:
        st.session_state.login_mode = "login"
    if "current_page" not in st.session_state:
        st.session_state.current_page = "Profile"

    # if not logged in, show auth pages only
    if not st.session_state.logged_in:
        st.title("Uni Gym Personal Trainer")
        st.caption("Train smarter. Track better. Stay consistent. 🌿")
        st.divider()

        if st.session_state.login_mode == "login":
            show_login_page()
        else:
            show_register_page()
        return

    # when logged in: sidebar navigation
    st.sidebar.title("Menu")

    # show logged-in email in the sidebar
    if "user_email" in st.session_state and st.session_state.user_email:
        st.sidebar.caption(f"Logged in as: {st.session_state.user_email}")
        st.sidebar.write("---")

    if st.sidebar.button("👤  Profile"):
        st.session_state.current_page = "Profile"
    if st.sidebar.button("🏋️‍♂️  Trainer"):
        st.session_state.current_page = "Trainer"
    if st.sidebar.button("🔥  Calorie tracker"):
        st.session_state.current_page = "Calorie tracker"
    if st.sidebar.button("📈  Progress"):
        st.session_state.current_page = "Progress"

    st.sidebar.write("---")
    if st.sidebar.button("Log out"):
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.user_email = None
        st.rerun()

    # main header visible when logged in
    st.title("Uni Gym Personal Trainer")
    st.caption("Train smarter. Track better. Stay consistent. 🌿")
    if "user_email" in st.session_state and st.session_state.user_email:
        st.write(f"Welcome back, **{st.session_state.user_email}** 👋")
    st.divider()

    page = st.session_state.current_page
    if page == "Profile":
        show_profile_page()
    elif page == "Trainer":
        show_trainer_page()
    elif page == "Calorie tracker":
        show_calorie_tracker_page()
    elif page == "Progress":
        show_progress_page()


if __name__ == "__main__":
    main()

