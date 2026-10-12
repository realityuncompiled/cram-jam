
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "cram_jam.db"


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    with get_connection() as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS courses (
                course_code TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                credits REAL NOT NULL CHECK (credits > 0)
            );

            CREATE TABLE IF NOT EXISTS tasks (
                task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_code TEXT NOT NULL,
                title TEXT NOT NULL,
                task_type TEXT NOT NULL,
                deadline TEXT NOT NULL,
                estimated_hours REAL NOT NULL
                    CHECK (estimated_hours >= 0),
                is_completed INTEGER NOT NULL DEFAULT 0
                    CHECK (is_completed IN (0, 1)),
                FOREIGN KEY (course_code)
                    REFERENCES courses(course_code)
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
        """)


if __name__ == "__main__":
    initialize_database()
    print(f"Database initialized at: {DB_PATH}")
