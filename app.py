
from datetime import date, datetime, time
from commander import audit_workload

import pandas as pd  # type: ignore[reportMissingModuleSource]
import streamlit as st  # type: ignore[reportMissingImports]

from database import (
    add_courses,
    add_task,
    add_study_session,
    update_task,
    get_courses,
    get_study_sessions,
    get_tasks,
    initialize_database,
    add_schedule_entry,
    delete_schedule_entry,
    get_schedule_entries,
    delete_course,
)

st.set_page_config(
    page_title="Cram Jam",
    page_icon="📚",
    layout="wide",
)

st.markdown(
    """
    <style>
    /* The Chancellor's visual language */
    h1, h2, h3 {
        font-family: Georgia, "Times New Roman", serif !important;
        letter-spacing: 0.02em;
    }

    h1 {
        color: #F0E8DC;
        font-weight: 500;
    }

    h2, h3 {
        color: #D9C5B0;
        font-weight: 500;
    }

    /* Restrained gold for labels and milestones */
    [data-testid="stMetricLabel"] {
        color: #C69B58;
    }

    [data-testid="stMetricValue"] {
        color: #F0E8DC;
    }

    /* Structured tabs */
    button[data-baseweb="tab"] {
        font-weight: 600;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        color: #E1B66C;
    }

    /* Burgundy actions, without flooding the screen */
    .stButton > button[kind="primary"],
    .stFormSubmitButton > button {
        border-radius: 5px;
        font-weight: 600;
    }

    /* Quiet borders around secondary work areas */
    [data-testid="stExpander"] {
        border: 1px solid #40363B;
        border-radius: 6px;
    }

    /* Keep the page readable and avoid overly wide text */
    [data-testid="stAppViewContainer"] {
        font-size: 15px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)

initialize_database()

st.title("Cram Jam")
st.subheader("Your academic pressure, made visible.")

st.write(
    "Register your semester courses once. "
    "You can add academic tasks to each course later."
)

tab_command, tab_routine, tab_tasks, tab_study, tab_courses = st.tabs(
    [
        "Command",
        "Weekly Routine",
        "Tasks",
        "Study Log",
        "Courses",
    ]
)


# THE COMMANDER
with tab_command:
    commander_report = audit_workload(get_tasks())

    state_styles = {
        "MONITORING": "info",
        "COMMANDING": "info",
        "STRATEGIZING": "warning",
        "ENRAGED": "error",
    }

    state = commander_report["state"]
    state_style = state_styles[state]

    st.header("The Commander's Office")
    st.caption(f"CURRENT STATE: {state}")

    if state_style == "error":
        st.error(commander_report["message"])
    elif state_style == "warning":
        st.warning(commander_report["message"])
    else:
        st.info(commander_report["message"])

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Outstanding tasks",
        commander_report["outstanding_count"],
    )
    col2.metric(
        "Overdue",
        commander_report["overdue_count"],
    )
    col3.metric(
        "Deadlines within 72h",
        commander_report["approaching_count"],
    )

    next_task = commander_report["next_task"]

    if next_task:
        st.subheader("Your next directive")

        st.markdown(f"**{next_task['title']}**")
        st.caption(
            f"{next_task['course_code']} · "
            f"{next_task['task_type']} · "
            f"{next_task['priority'].title()} priority"
        )

        if next_task["is_overdue"]:
            st.write(
                "The deadline has passed. This task remains outstanding. "
                "Assess what can still be submitted and act accordingly."
            )
        else:
            hours = next_task["hours_remaining"]

            if hours <= 24:
                deadline_text = "Due within 24 hours."
            elif hours <= 72:
                deadline_text = "Due within 3 days."
            elif hours <= 168:
                deadline_text = "Due within 7 days."
            else:
                deadline_text = "More than 7 days remain."

            st.write(deadline_text)

        minutes = next_task["estimated_minutes"]
        st.write(
            f"Estimated work: {minutes // 60}h {minutes % 60}m."
        )

        st.caption(
            "Why this task? It ranks first under the current rules: "
            "deadline urgency, then priority, then deadline and task ID."
        )

    else:
        st.write(
            "Nothing outstanding. Enjoy the quiet. "
            "The ledger will be reviewed again when you add work."
        )

    st.caption(
        f"Total estimated outstanding work: "
        f"{commander_report['estimated_minutes'] // 60}h "
        f"{commander_report['estimated_minutes'] % 60}m"
    )

    st.divider()

with tab_courses:
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

    st.subheader("Remove a Course")

    if courses:
        st.warning(
            "Deleting a course permanently removes its tasks, "
            "study history, and weekly routine entries too."
        )

        course_options = {
            f"{course['course_code']} — {course['name']}": (
                course["course_code"]
            )
            for course in courses
        }

        with st.form("delete_course_form"):
            selected_course_label = st.selectbox(
                "Course to delete",
                options=list(course_options.keys()),
            )

            confirm_delete = st.checkbox(
                "I understand that this action cannot be undone."
            )

            delete_submitted = st.form_submit_button(
                "Delete Course",
                type="primary",
            )

        if delete_submitted:
            if not confirm_delete:
                st.error("Confirm the deletion before proceeding.")
            else:
                selected_code = course_options[
                    selected_course_label
                ]

                try:
                    deleted = delete_course(selected_code)

                    st.success(
                        f"Deleted {selected_code}. "
                        f"Also removed {deleted['tasks']} task(s), "
                        f"{deleted['study_sessions']} study "
                        f"session(s), and "
                        f"{deleted['weekly_schedule']} routine "
                        f"entry/entries."
                    )
                    st.rerun()

                except ValueError as error:
                    st.error(str(error))

                except Exception:
                    st.error(
                        "Could not delete the course. "
                        "The database transaction was rolled back. "
                        "Check the terminal for details."
                    )
    else:
        st.info("There are no courses to delete.")

    st.divider()

with tab_routine:
    st.header("Weekly Routine")

    st.write(
        "Add recurring lectures, labs, and tutorials. "
        "For bi-weekly sessions, choose the date of the first meeting."
    )

    if courses:
        day_names = [
            "Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday",
        ]

        with st.form("weekly_schedule_form"):
            schedule_course = st.selectbox(
                "Course",
                options=[course["course_code"] for course in courses],
                key="schedule_course",
            )

            schedule_type = st.selectbox(
                "Session type",
                options=["Lecture", "Lab", "Tutorial", "Other"],
                key="schedule_type",
            )

            schedule_day_name = st.selectbox(
                "Day",
                options=day_names,
                key="schedule_day",
            )
            schedule_day = day_names.index(schedule_day_name)

            schedule_start = st.time_input(
                "Start time",
                value=time(9, 0),
                key="schedule_start",
            )
            schedule_end = st.time_input(
                "End time",
                value=time(10, 0),
                key="schedule_end",
            )

            schedule_recurrence_label = st.selectbox(
                "Repeats",
                options=["Every week", "Every 2 weeks"],
                key="schedule_recurrence",
            )
            schedule_recurrence = (
                1 if schedule_recurrence_label == "Every week" else 2
            )

            schedule_start_date = st.date_input(
                "Date of first occurrence",
                value=date.today(),
                key="schedule_start_date",
            )

            schedule_submitted = st.form_submit_button(
                "Save Routine Entry"
            )

        if schedule_submitted:
            schedule_payload = {
                "course_code": schedule_course,
                "day_of_week": schedule_day,
                "start_time": schedule_start.strftime("%H:%M"),
                "end_time": schedule_end.strftime("%H:%M"),
                "session_type": schedule_type,
                "recurrence_weeks": schedule_recurrence,
                "start_date": schedule_start_date.isoformat(),
            }

            try:
                entry = add_schedule_entry(schedule_payload)
                st.success(
                    f"Saved routine entry #{entry['schedule_id']}."
                )
            except (ValueError, KeyError, TypeError) as error:
                st.error(f"Could not save routine entry: {error}")

        schedule_entries = get_schedule_entries()

        st.subheader("Saved Routine")

        if schedule_entries:
            schedule_rows = []

            for entry in schedule_entries:
                schedule_rows.append({
                    "ID": entry["schedule_id"],
                    "Course": entry["course_code"],
                    "Day": day_names[entry["day_of_week"]],
                    "Start": entry["start_time"],
                    "End": entry["end_time"],
                    "Type": entry["session_type"],
                    "Repeats": (
                        "Every week"
                        if entry["recurrence_weeks"] == 1
                        else "Every 2 weeks"
                    ),
                    "First occurrence": entry["start_date"],
                })

            st.dataframe(
                pd.DataFrame(schedule_rows),
                use_container_width=True,
                hide_index=True,
            )

            schedule_ids = [
                entry["schedule_id"] for entry in schedule_entries
            ]
            schedule_labels = {
                entry["schedule_id"]: (
                    f"#{entry['schedule_id']} — {entry['course_code']}"
                )
                for entry in schedule_entries
            }

            with st.form("delete_schedule_form"):
                selected_schedule_id = st.selectbox(
                    "Routine entry to remove",
                    options=schedule_ids,
                    format_func=lambda entry_id: schedule_labels[entry_id],
                )

                delete_submitted = st.form_submit_button(
                    "Remove Routine Entry"
                )

            if delete_submitted:
                delete_schedule_entry(selected_schedule_id)
                st.success(
                    f"Removed routine entry #{selected_schedule_id}."
                )
                st.rerun()

        else:
            st.info("No routine entries yet. Add your first class above.")

    else:
        st.info("Register your courses before creating a weekly routine.")

    st.divider()

with tab_tasks:
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

            with st.expander("Edit a task"):
                st.subheader("Edit Existing Task")

                task_lookup = {
                    f"#{task['task_id']} — {task['title']} ({task['course_code']})": task
                    for task in tasks
                }

                selected_task_label = st.selectbox(
                    "Select a task to edit",
                    options=list(task_lookup.keys()),
                    key="edit_task_selector",
                )
                selected_task = task_lookup[selected_task_label]

                with st.form("edit_task_form"):
                    edit_course = st.selectbox(
                        "Course",
                        options=[course["course_code"] for course in courses],
                        index=[
                            course["course_code"] for course in courses
                        ].index(selected_task["course_code"]),
                    )
                    edit_title = st.text_input(
                        "Task title",
                        value=selected_task["title"],
                    )

                    task_types = [
                        "Assignment", "Reading", "Quiz", "Project", "Exam", "Other"
                    ]
                    current_type = selected_task["task_type"]
                    if current_type not in task_types:
                        task_types.append(current_type)

                    edit_type = st.selectbox(
                        "Task type",
                        options=task_types,
                        index=task_types.index(current_type),
                    )

                    current_deadline = datetime.fromisoformat(
                        selected_task["deadline"]
                    )
                    edit_deadline_date = st.date_input(
                        "Deadline date",
                        value=current_deadline.date(),
                    )
                    edit_deadline_time = st.time_input(
                        "Deadline time",
                        value=current_deadline.time(),
                    )

                    edit_minutes = st.number_input(
                        "Estimated minutes",
                        min_value=0,
                        max_value=100000,
                        value=int(selected_task["estimated_minutes"]),
                        step=15,
                    )

                    priorities = ["Low", "Medium", "High"]
                    current_priority = selected_task["priority"].title()

                    edit_priority = st.selectbox(
                        "Priority",
                        options=priorities,
                        index=priorities.index(current_priority),
                    )

                    statuses = ["Pending", "In Progress", "Completed"]
                    current_status = selected_task["status"].replace("_", " ").title()

                    edit_status = st.selectbox(
                        "Status",
                        options=statuses,
                        index=statuses.index(current_status),
                    )

                    edit_submitted = st.form_submit_button("Update Task")

                if edit_submitted:
                    if not edit_title.strip():
                        st.warning("Task title is required.")
                    else:
                        edit_deadline = datetime.combine(
                            edit_deadline_date,
                            edit_deadline_time,
                        ).isoformat(timespec="seconds")

                        edit_payload = {
                            "course_code": edit_course,
                            "title": edit_title,
                            "task_type": edit_type,
                            "deadline": edit_deadline,
                            "estimated_minutes": int(edit_minutes),
                            "priority": edit_priority.lower(),
                            "status": edit_status.lower().replace(" ", "_"),
                        }

                        try:
                            updated_task = update_task(
                                selected_task["task_id"],
                                edit_payload,
                            )
                            st.success(
                                f"Updated task #{updated_task['task_id']}: "
                                f"{updated_task['title']}"
                            )
                            st.rerun()
                        except (ValueError, TypeError) as error:
                            st.error(f"Could not update task: {error}")
        else:
            st.info("No tasks yet. Add one above.")
    else:
        st.info("Add at least one course before creating tasks.")

    st.divider()

with tab_study:
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
