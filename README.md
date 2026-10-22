# Cram Jam

An offline academic-demand monitor built with Python, SQLite, and Streamlit.

**The idea:** Make academic demand visible. Keep track of upcoming work, see which deadlines need attention, and understand what needs to happen next.

## What it does

- **Course management** — Register your semester courses and credit hours.
- **Task and assessment tracking** — Record assignments, quizzes, deadlines, estimated work, priorities, and completion status.
- **Weekly routine** — Schedule recurring lectures, labs, tutorials, and other sessions, including bi-weekly routines.
- **Study log** — Record study sessions by course and track time spent studying.
- **The Commander's Office** — Get a workload overview, identify overdue and approaching deadlines, and see which task should come first.

Cram Jam uses rule-based logic to prioritize outstanding tasks. Deadline urgency comes first, followed by priority, deadline, and task ID.

## Built with

- **Python** — Application logic
- **SQLite** — Local database
- **Streamlit** — User interface
- **Pandas** — Tabular data and course registration

## Run locally

You'll need Python installed.

### Windows (recommended)

Double-click `Launch Cram Jam.bat` in the project folder. It launches Cram Jam using the local setup.

### Manual launch

If you prefer to start the app from the terminal:

```powershell
python -m pip install streamlit pandas
streamlit run app.py
```

Cram Jam stores its data in a local SQLite database. It is designed for single-user, offline use and does not require cloud storage, authentication, or an online service.

## Development

Cram Jam is a work in progress. The goal is to build something genuinely useful while understanding the tools, logic, and database design behind it.

Yes, I used AI. But **only after learning the skills needed to build this particular thing-a-magic.**

The goal is to build something useful, understand how it works under the hood, and have something to show for the inevitable academic chaos.