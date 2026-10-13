
import sqlite3
from datetime import date, datetime
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(__file__).parent / "cram_jam.db"
VALID_STATUSES = ("pending", "in_progress", "completed")
VALID_PRIORITIES = ("low", "medium", "high")



@contextmanager
def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def normalize_course_code(course_code):
    code = str(course_code).strip().upper()

    if not code:
        raise ValueError("Course code cannot be empty.")

    if any(char.isspace() for char in code):
        raise ValueError("Course codes cannot contain internal spaces.")

    return code


def normalize_datetime(value, field_name="datetime"):
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError(f"{field_name} is required.")

    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime.combine(value, datetime.min.time())
    else:
        text = str(value).strip()

        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        if " " in text and "T" not in text:
            text = text.replace(" ", "T", 1)

        if len(text) == 10 and text.count("-") == 2:
            text = f"{text}T00:00:00"

        try:
            dt = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError(
                f"Invalid {field_name} format. Use ISO 8601 such as "
                "'2026-10-13T18:00:00'."
            ) from exc

    return dt.isoformat(timespec="seconds")


def normalize_status(status):
    if status is None:
        return "pending"

    normalized = str(status).strip().lower()

    if normalized in {"pending", "todo", "not started", "open"}:
        return "pending"
    if normalized in {"in progress", "in_progress", "in-progress"}:
        return "in_progress"
    if normalized in {"done", "completed", "complete"}:
        return "completed"
    if normalized in VALID_STATUSES:
        return normalized

    raise ValueError(
        "Status must be one of: pending, in_progress, completed."
    )


def normalize_priority(priority):
    if priority is None:
        return "medium"

    normalized = str(priority).strip().lower()

    if normalized in {"low", "medium", "high"}:
        return normalized
    if normalized in {"urgent"}:
        return "high"

    raise ValueError("Priority must be one of: low, medium, high.")


def create_tasks_table_sql():
    return """
        CREATE TABLE tasks (
            task_id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_code TEXT NOT NULL,
            title TEXT NOT NULL,
            task_type TEXT NOT NULL,
            deadline TEXT NOT NULL,
            estimated_minutes INTEGER NOT NULL
                CHECK (estimated_minutes >= 0),
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'in_progress', 'completed')),
            priority TEXT NOT NULL DEFAULT 'medium'
                CHECK (priority IN ('low', 'medium', 'high')),
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
            FOREIGN KEY (course_code)
                REFERENCES courses(course_code)
        );
    """


def ensure_tasks_table(connection):
    table_exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'tasks'"
    ).fetchone()

    if table_exists is None:
        connection.execute(create_tasks_table_sql())
        return

    columns = [
        column["name"]
        for column in connection.execute("PRAGMA table_info(tasks)").fetchall()
    ]
    required_columns = {
        "task_id",
        "course_code",
        "title",
        "task_type",
        "deadline",
        "estimated_minutes",
        "status",
        "priority",
        "created_at",
    }

    if required_columns.issubset(columns):
        return

    migration_columns = connection.execute("PRAGMA table_info(tasks)").fetchall()
    migration_names = [column["name"] for column in migration_columns]

    connection.execute(
        """
        CREATE TABLE tasks_new (
            task_id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_code TEXT NOT NULL,
            title TEXT NOT NULL,
            task_type TEXT NOT NULL,
            deadline TEXT NOT NULL,
            estimated_minutes INTEGER NOT NULL
                CHECK (estimated_minutes >= 0),
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'in_progress', 'completed')),
            priority TEXT NOT NULL DEFAULT 'medium'
                CHECK (priority IN ('low', 'medium', 'high')),
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
            FOREIGN KEY (course_code)
                REFERENCES courses(course_code)
        );
        """
    )

    rows = connection.execute("SELECT * FROM tasks").fetchall()
    for row in rows:
        raw = dict(zip(migration_names, row))
        deadline_value = raw.get("deadline")
        if deadline_value is None or str(deadline_value).strip() == "":
            deadline_value = datetime.now().isoformat(timespec="seconds")

        estimated_minutes = raw.get("estimated_minutes")
        if estimated_minutes is None:
            raw_hours = raw.get("estimated_hours")
            if raw_hours in (None, ""):
                estimated_minutes = 0
            else:
                estimated_minutes = int(round(float(raw_hours) * 60))

        status = raw.get("status")
        if status is None:
            is_completed = raw.get("is_completed")
            status = "completed" if str(is_completed).strip() in {"1", "true", "True"} else "pending"
            status = normalize_status(status)
        else:
            status = normalize_status(status)

        priority = raw.get("priority")
        if priority is None:
            priority = "medium"
        priority = normalize_priority(priority)

        created_at = raw.get("created_at")
        if created_at is None or str(created_at).strip() == "":
            created_at = datetime.now().isoformat(timespec="seconds")

        connection.execute(
            """
            INSERT INTO tasks_new (
                task_id,
                course_code,
                title,
                task_type,
                deadline,
                estimated_minutes,
                status,
                priority,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                raw.get("task_id"),
                raw.get("course_code"),
                raw.get("title"),
                raw.get("task_type") or "General",
                normalize_datetime(deadline_value, "deadline"),
                int(estimated_minutes),
                status,
                priority,
                normalize_datetime(created_at, "created_at"),
            ),
        )

    connection.execute("DROP TABLE tasks")
    connection.execute("ALTER TABLE tasks_new RENAME TO tasks")


def initialize_database():
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS courses (
                course_code TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                credits REAL NOT NULL CHECK (credits > 0)
            );

            CREATE TABLE IF NOT EXISTS study_sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_code TEXT NOT NULL,
                session_date TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL
                    CHECK (duration_minutes > 0),
                FOREIGN KEY (course_code)
                    REFERENCES courses(course_code)
            );
            """
        )
        ensure_tasks_table(connection)


def add_courses(courses):
    """
    Add a batch of courses.

    Each course must contain:
    course_code, name, credits

    Returns a list of skipped duplicate course codes.
    """
    skipped = []

    with get_connection() as connection:
        for course in courses:
            code = normalize_course_code(course["course_code"])
            name = str(course["name"]).strip()
            credits = course["credits"]

            if not name:
                raise ValueError(f"{code}: course name cannot be empty.")

            if credits <= 0:
                raise ValueError(f"{code}: credits must be positive.")

            exists = connection.execute(
                "SELECT 1 FROM courses WHERE course_code = ?",
                (code,),
            ).fetchone()

            if exists:
                skipped.append(code)
                continue

            connection.execute(
                """
                INSERT INTO courses (course_code, name, credits)
                VALUES (?, ?, ?)
                """,
                (code, name, credits),
            )

    return skipped


def get_courses():
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT course_code, name, credits
            FROM courses
            ORDER BY course_code
            """
        ).fetchall()


def add_task(task):
    required_fields = ("course_code", "title", "task_type", "deadline")
    for field_name in required_fields:
        if field_name not in task or task[field_name] in (None, ""):
            raise ValueError(f"{field_name} is required.")

    course_code = normalize_course_code(task["course_code"])
    title = str(task["title"]).strip()
    if not title:
        raise ValueError("Task title cannot be empty.")

    task_type = str(task["task_type"]).strip() or "General"
    deadline = normalize_datetime(task["deadline"], "deadline")
    estimated_minutes = int(task.get("estimated_minutes", 0))
    if estimated_minutes < 0:
        raise ValueError("Estimated minutes cannot be negative.")

    status = normalize_status(task.get("status", "pending"))
    priority = normalize_priority(task.get("priority", "medium"))
    created_at = normalize_datetime(
        task.get("created_at") or datetime.now(), "created_at"
    )

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO tasks (
                course_code,
                title,
                task_type,
                deadline,
                estimated_minutes,
                status,
                priority,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                course_code,
                title,
                task_type,
                deadline,
                estimated_minutes,
                status,
                priority,
                created_at,
            ),
        )
        task_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        return connection.execute(
            "SELECT * FROM tasks WHERE task_id = ?",
            (task_id,),
        ).fetchone()


def get_tasks(course_code=None):
    query = "SELECT * FROM tasks"
    params = []

    if course_code is not None:
        query += " WHERE course_code = ?"
        params.append(normalize_course_code(course_code))

    query += " ORDER BY deadline ASC, created_at DESC"

    with get_connection() as connection:
        return connection.execute(query, params).fetchall()


if __name__ == "__main__":
    initialize_database()
    print(f"Database initialized at: {DB_PATH}")
