import sqlite3
from datetime import datetime


DEFAULT_SKILLS = [
    "Python",
    "SQL",
    "SQLite",
    "API",
    "Telegram",
    "Git",
    "GitHub",
    "OpenCV",
]

DEFAULT_STATUSES = [
    "Geplant",
    "In Entwicklung",
    "Einsatzbereit",
    "Aktualisiert",
    "Abgeschlossen",
]


class PortfolioManager:
    def __init__(self, database):
        self.database = database

    def get_connection(self):
        conn = sqlite3.connect(self.database)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def create_tables(self):
        with self.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS status (
                    status_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    status_name TEXT NOT NULL UNIQUE
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS skills (
                    skill_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    skill_name TEXT NOT NULL UNIQUE
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    project_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    project_name TEXT NOT NULL,
                    description TEXT,
                    url TEXT,
                    status_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, project_name),
                    FOREIGN KEY(status_id) REFERENCES status(status_id)
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS project_skills (
                    project_id INTEGER NOT NULL,
                    skill_id INTEGER NOT NULL,
                    PRIMARY KEY(project_id, skill_id),
                    FOREIGN KEY(project_id)
                        REFERENCES projects(project_id)
                        ON DELETE CASCADE,
                    FOREIGN KEY(skill_id)
                        REFERENCES skills(skill_id)
                        ON DELETE CASCADE
                )
                """
            )

    def seed_defaults(self):
        with self.get_connection() as conn:
            conn.executemany(
                "INSERT OR IGNORE INTO status (status_name) VALUES (?)",
                [(status,) for status in DEFAULT_STATUSES],
            )
            conn.executemany(
                "INSERT OR IGNORE INTO skills (skill_name) VALUES (?)",
                [(skill,) for skill in DEFAULT_SKILLS],
            )

    def get_statuses(self):
        with self.get_connection() as conn:
            return conn.execute(
                "SELECT status_name FROM status ORDER BY status_id"
            ).fetchall()

    def get_status_id(self, status_name):
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT status_id FROM status WHERE status_name = ?",
                (status_name,),
            ).fetchone()
        return row[0] if row else None

    def get_skills(self):
        with self.get_connection() as conn:
            return conn.execute(
                "SELECT skill_id, skill_name FROM skills ORDER BY skill_name"
            ).fetchall()

    def add_skill_to_catalog(self, skill_name):
        skill_name = skill_name.strip()
        if not skill_name:
            return False

        with self.get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO skills (skill_name) VALUES (?)",
                (skill_name,),
            )
        return True

    def project_exists(self, user_id, project_name):
        with self.get_connection() as conn:
            row = conn.execute(
                """
                SELECT 1
                FROM projects
                WHERE user_id = ? AND LOWER(project_name) = LOWER(?)
                """,
                (user_id, project_name.strip()),
            ).fetchone()
        return row is not None

    def create_project(self, user_id, project_name, description, url, status_name):
        if self.project_exists(user_id, project_name):
            return None

        status_id = self.get_status_id(status_name)
        if status_id is None:
            raise ValueError("Unbekannter Projektstatus.")

        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO projects (
                    user_id,
                    project_name,
                    description,
                    url,
                    status_id,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    project_name.strip(),
                    description.strip(),
                    url.strip(),
                    status_id,
                    now,
                    now,
                ),
            )
            return cursor.lastrowid

    def get_projects(self, user_id, status_name=None):
        sql = """
            SELECT
                p.project_id,
                p.project_name,
                p.description,
                p.url,
                s.status_name,
                p.created_at,
                p.updated_at
            FROM projects p
            JOIN status s ON s.status_id = p.status_id
            WHERE p.user_id = ?
        """
        params = [user_id]

        if status_name and status_name != "Alle":
            sql += " AND s.status_name = ?"
            params.append(status_name)

        sql += " ORDER BY p.updated_at DESC, p.project_name"

        with self.get_connection() as conn:
            return conn.execute(sql, tuple(params)).fetchall()

    def get_project(self, user_id, project_id):
        with self.get_connection() as conn:
            return conn.execute(
                """
                SELECT
                    p.project_id,
                    p.project_name,
                    p.description,
                    p.url,
                    s.status_name,
                    p.created_at,
                    p.updated_at
                FROM projects p
                JOIN status s ON s.status_id = p.status_id
                WHERE p.user_id = ? AND p.project_id = ?
                """,
                (user_id, project_id),
            ).fetchone()

    def get_project_by_name(self, user_id, project_name):
        with self.get_connection() as conn:
            return conn.execute(
                """
                SELECT
                    p.project_id,
                    p.project_name,
                    p.description,
                    p.url,
                    s.status_name,
                    p.created_at,
                    p.updated_at
                FROM projects p
                JOIN status s ON s.status_id = p.status_id
                WHERE p.user_id = ? AND LOWER(p.project_name) = LOWER(?)
                """,
                (user_id, project_name.strip()),
            ).fetchone()

    def get_project_skills(self, project_id):
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT s.skill_name
                FROM project_skills ps
                JOIN skills s ON s.skill_id = ps.skill_id
                WHERE ps.project_id = ?
                ORDER BY s.skill_name
                """,
                (project_id,),
            ).fetchall()
        return [row[0] for row in rows]

    def add_project_skill(self, project_id, skill_name):
        with self.get_connection() as conn:
            skill = conn.execute(
                "SELECT skill_id FROM skills WHERE skill_name = ?",
                (skill_name,),
            ).fetchone()

            if not skill:
                cursor = conn.execute(
                    "INSERT INTO skills (skill_name) VALUES (?)",
                    (skill_name,),
                )
                skill_id = cursor.lastrowid
            else:
                skill_id = skill[0]

            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO project_skills (project_id, skill_id)
                VALUES (?, ?)
                """,
                (project_id, skill_id),
            )

        if cursor.rowcount:
            self.touch_project(project_id)
            return True
        return False

    def remove_project_skill(self, project_id, skill_name):
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                DELETE FROM project_skills
                WHERE project_id = ?
                  AND skill_id = (
                      SELECT skill_id
                      FROM skills
                      WHERE skill_name = ?
                  )
                """,
                (project_id, skill_name),
            )

        if cursor.rowcount:
            self.touch_project(project_id)
            return True
        return False

    def touch_project(self, project_id):
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE projects SET updated_at = ? WHERE project_id = ?",
                (now, project_id),
            )

    def update_project(self, user_id, project_id, field, value):
        allowed_fields = {
            "project_name",
            "description",
            "url",
            "status_id",
        }

        if field not in allowed_fields:
            raise ValueError("Ungültiges Feld.")

        if field == "project_name":
            existing = self.get_project_by_name(user_id, value)
            if existing and existing[0] != project_id:
                return False

        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        with self.get_connection() as conn:
            cursor = conn.execute(
                f"""
                UPDATE projects
                SET {field} = ?, updated_at = ?
                WHERE user_id = ? AND project_id = ?
                """,
                (value, now, user_id, project_id),
            )

        return cursor.rowcount > 0

    def delete_project(self, user_id, project_id):
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                DELETE FROM projects
                WHERE user_id = ? AND project_id = ?
                """,
                (user_id, project_id),
            )
        return cursor.rowcount > 0

    def get_statistics(self, user_id):
        with self.get_connection() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM projects WHERE user_id = ?",
                (user_id,),
            ).fetchone()[0]

            by_status = conn.execute(
                """
                SELECT s.status_name, COUNT(p.project_id)
                FROM status s
                LEFT JOIN projects p
                    ON p.status_id = s.status_id
                    AND p.user_id = ?
                GROUP BY s.status_id, s.status_name
                ORDER BY s.status_id
                """,
                (user_id,),
            ).fetchall()

            top_skills = conn.execute(
                """
                SELECT s.skill_name, COUNT(*) AS usage_count
                FROM project_skills ps
                JOIN projects p ON p.project_id = ps.project_id
                JOIN skills s ON s.skill_id = ps.skill_id
                WHERE p.user_id = ?
                GROUP BY s.skill_id, s.skill_name
                ORDER BY usage_count DESC, s.skill_name
                LIMIT 5
                """,
                (user_id,),
            ).fetchall()

        return {
            "total": total,
            "by_status": by_status,
            "top_skills": top_skills,
        }
