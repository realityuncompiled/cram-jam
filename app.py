
from datetime import datetime

import pandas as pd
import streamlit as st

from database import (
    add_courses,
    add_task,
    add_study_session,
    get_courses,
    get_study_sessions,
    get_tasks,
    initialize_database,
)

st.set_page_config(
    page_title="Cram Jam",
    page_icon="📚",
    layout="wide",
)

initialize_database()

st.title("Cram Jam")
st.subheader("Your academic pressure, made visible.")

st.write(
    "Register your semester courses once. "
    "You can add academic tasks to each course later."
)

st.divider()

st.header("Semester Setup")

st.write(
    "Enter your courses below. You can add multiple rows "
    "and save them together."
)

if "course_rows" not in st.session_state:
    st.session_state.course_rows = pd.DataFrame(
        [
            {"Course Code": "", "Course Name": "", "Credits": 3.0},
        ]
    )

with st.form("course_registration_form"):
    edited_courses = st.data_editor(
        st.session_state.course_rows,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "Course Code": st.column_config.TextColumn(
                "Course Code",
                help="Example: CSE4107",
            ),
            "Course Name": st.column_config.TextColumn(
                "Course Name",
            ),
            "Credits": st.column_config.NumberColumn(
                "Credits",
                min_value=0.1,
                max_value=30.0,
                step=0.5,
                format="%.1f",
            ),
        },
    )

    submitted = st.form_submit_button("Save Courses")

if submitted:
    valid_courses = []
    errors = []
    seen_codes = set()

    for row_number, row in enumerate(
        edited_courses.to_dict("records"), start=1
    ):
        raw_code = str(row.get("Course Code", "") or "").strip()
        raw_name = str(row.get("Course Name", "") or "").strip()
        raw_credits = row.get("Credits")

        if not raw_code and not raw_name:
            continue

        if not raw_code:
            errors.append(f"Row {row_number}: course code is required.")
            continue

        if not raw_name:
            errors.append(f"Row {row_number}: course name is required.")
            continue

        code = raw_code.upper()

        if any(char.isspace() for char in code):
            errors.append(
                f"Row {row_number}: {code} contains internal spaces."
            )
            continue

        if code in seen_codes:
            errors.append(
                f"Row {row_number}: {code} appears more than once "
                "in this batch."
            )
            continue

        seen_codes.add(code)

        if pd.isna(raw_credits) or raw_credits <= 0:
            errors.append(
                f"Row {row_number}: credits must be positive."
            )
            continue

        valid_courses.append(
            {
                "course_code": code,
                "name": raw_name,
                "credits": float(raw_credits),
            }
        )

    if errors:
        st.error("Please fix these issues before saving:")
        for error in errors:
            st.write(f"- {error}")

    elif not valid_courses:
        st.warning("Enter at least one course before saving.")

    else:
        try:
            skipped = add_courses(valid_courses)
            added_count = len(valid_courses) - len(skipped)

            if added_count:
                st.success(f"Added {added_count} course(s).")

            if skipped:
                st.warning(
                    "Already registered; left unchanged: "
                    + ", ".join(skipped)
                )

            if not added_count and not skipped:
                st.info("No new courses were added.")

            st.session_state.course_rows = pd.DataFrame(
                [{"Course Code": "", "Course Name": "", "Credits": 3.0}]
            )

        except (ValueError, KeyError, TypeError) as error:
            st.error(f"Could not save courses: {error}")

        except Exception:
            st.error(
                "A database error occurred. "
                "The batch was not saved. Check the terminal for details."
            )
            raise

st.divider()

st.header("Registered Courses")

courses = get_courses()

if courses:
    course_table = pd.DataFrame(
        [dict(course) for course in courses]
    ).rename(
        columns={
            "course_code": "Course Code",
            "name": "Course Name",
            "credits": "Credits",
        }
    )

    st.dataframe(
        course_table,
        use_container_width=True,
        hide_index=True,
    )

    st.caption(f"{len(courses)} course(s) registered.")
else:
    st.info(
        "No courses registered yet. Add your semester courses above."
    )

st.divider()

st.header("Task Planner")

if courses:
    with st.form("task_registration_form"):
        task_course = st.selectbox(
            "Course",
            options=[course["course_code"] for course in courses],
        )
        task_title = st.text_input("Task title")
        task_type = st.selectbox(
            "Task type",
            options=["Assignment", "Reading", "Quiz", "Project", "Exam", "Other"],
        )
        deadline_date = st.date_input("Deadline date")
        deadline_time = st.time_input("Deadline time", value=datetime.strptime("18:00", "%H:%M").time())
        estimated_minutes = st.number_input(
            "Estimated minutes",
            min_value=0,
            max_value=1440,
            value=60,
            step=15,
        )
        task_priority = st.selectbox(
            "Priority",
            options=["Low", "Medium", "High"],
        )
        task_status = st.selectbox(
            "Status",
            options=["Pending", "In Progress", "Completed"],
        )
        task_submitted = st.form_submit_button("Save Task")

    if task_submitted:
        if not task_title.strip():
            st.warning("Task title is required.")
        else:
            deadline = datetime.combine(deadline_date, deadline_time).isoformat(timespec="seconds")
            task_payload = {
                "course_code": task_course,
                "title": task_title,
                "task_type": task_type,
                "deadline": deadline,
                "estimated_minutes": int(estimated_minutes),
                "priority": task_priority.lower(),
                "status": task_status.lower().replace(" ", "_"),
            }
            try:
                task = add_task(task_payload)
                st.success(f"Saved task #{task['task_id']}: {task['title']}")
            except ValueError as error:
                st.error(f"Could not save task: {error}")

    tasks = get_tasks()
    if tasks:
        task_rows = [dict(task) for task in tasks]
        task_table = pd.DataFrame(task_rows).rename(
            columns={
                "task_id": "Task ID",
                "course_code": "Course",
                "title": "Title",
                "task_type": "Type",
                "deadline": "Deadline",
                "estimated_minutes": "Estimated Minutes",
                "status": "Status",
                "priority": "Priority",
                "created_at": "Created At",
            }
        )
        st.dataframe(task_table, use_container_width=True, hide_index=True)
    else:
        st.info("No tasks yet. Add one above.")
else:
    st.info("Add at least one course before creating tasks.")

st.divider()

st.header("Study Sessions")

st.write(
    "Record the time you spend studying. "
    "Your sessions will be saved locally."
)

if courses:
    with st.form("study_session_form"):
        session_course = st.selectbox(
            "Course",
            options=[course["course_code"] for course in courses],
            key="session_course",
        )

        session_date = st.date_input(
            "Study date",
            key="session_date",
        )

        duration_minutes = st.number_input(
            "Duration (minutes)",
            min_value=1,
            max_value=1440,
            value=50,
            step=5,
            key="session_duration",
        )

        session_submitted = st.form_submit_button(
            "Save Study Session"
        )

    if session_submitted:
        session_payload = {
            "course_code": session_course,
            "session_date": session_date,
            "duration_minutes": int(duration_minutes),
        }

        try:
            session = add_study_session(session_payload)
            st.success(
                f"Saved study session #{session['session_id']} "
                f"for {session['course_code']} "
                f"({session['duration_minutes']} minutes)."
            )
        except (ValueError, KeyError, TypeError) as error:
            st.error(f"Could not save study session: {error}")

    st.subheader("Study History")

    history_filter = st.selectbox(
        "Filter by course",
        options=["All courses"] + [
            course["course_code"] for course in courses
        ],
        key="history_filter",
    )

    selected_course = (
        None if history_filter == "All courses"
        else history_filter
    )

    sessions = get_study_sessions(selected_course)

    if sessions:
        session_table = pd.DataFrame(
            [dict(session) for session in sessions]
        ).rename(
            columns={
                "session_id": "Session ID",
                "course_code": "Course",
                "session_date": "Study Date",
                "duration_minutes": "Duration (minutes)",
            }
        )

        st.dataframe(
            session_table,
            use_container_width=True,
            hide_index=True,
        )

        total_minutes = sum(
            session["duration_minutes"] for session in sessions
        )

        st.caption(
            f"{len(sessions)} session(s) · "
            f"{total_minutes} minutes recorded"
        )
    else:
        st.info("No study sessions recorded for this selection yet.")

else:
    st.info("Add at least one course before recording study sessions.")
