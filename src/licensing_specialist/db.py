import re
import sqlite3
from pathlib import Path
from typing import Optional, List


DEFAULT_DB = Path(__file__).resolve().parents[2] / "licensing.db"


def get_conn(db_path: Optional[Path] = None) -> sqlite3.Connection:
    path = db_path or DEFAULT_DB
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    # Enable foreign key constraints to ensure cascading deletes work
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.executescript(
        """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS recruiter (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT
);

CREATE TABLE IF NOT EXISTS trainee (
    id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    dob TEXT,
    recruiter_id INTEGER,
    FOREIGN KEY(recruiter_id) REFERENCES recruiter(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS class (
    id INTEGER PRIMARY KEY,
    name TEXT,
    start_date TEXT,
    end_date TEXT
);

CREATE TABLE IF NOT EXISTS trainee_class (
    trainee_id INTEGER NOT NULL,
    class_id INTEGER NOT NULL,
    PRIMARY KEY (trainee_id, class_id),
    FOREIGN KEY(trainee_id) REFERENCES trainee(id) ON DELETE CASCADE,
    FOREIGN KEY(class_id) REFERENCES class(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS exam (
    id INTEGER PRIMARY KEY,
    trainee_id INTEGER NOT NULL,
    class_id INTEGER,
    exam_date TEXT,
    score TEXT,
    notes TEXT,
    FOREIGN KEY(trainee_id) REFERENCES trainee(id) ON DELETE CASCADE,
    FOREIGN KEY(class_id) REFERENCES class(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS license (
    id INTEGER PRIMARY KEY,
    trainee_id INTEGER NOT NULL,
    application_submitted_date TEXT,
    approval_date TEXT,
    license_number TEXT,
    status TEXT,
    notes TEXT,
    FOREIGN KEY(trainee_id) REFERENCES trainee(id) ON DELETE CASCADE
);
        """
    )
    # Ensure rep_code columns exist on existing DBs
    _ensure_rep_code_columns(db_path)
    # Ensure practice exam status table exists
    _ensure_practice_status_table(db_path)
    conn.commit()
    conn.close()


def _ensure_exam_columns(db_path: Optional[Path] = None) -> None:
    """Ensure new columns exist on exam table: module, is_practice, passed, reimbursement_requested"""
    conn = get_conn(db_path)
    cur = conn.cursor()
    # SQLite ALTER TABLE ADD COLUMN is safe if column doesn't exist; check via PRAGMA table_info
    cur.execute("PRAGMA table_info(exam)")
    cols = {r['name'] for r in cur.fetchall()}
    if 'module' not in cols:
        cur.execute("ALTER TABLE exam ADD COLUMN module TEXT")
    if 'is_practice' not in cols:
        cur.execute("ALTER TABLE exam ADD COLUMN is_practice INTEGER DEFAULT 0")
    if 'passed' not in cols:
        cur.execute("ALTER TABLE exam ADD COLUMN passed INTEGER")
    if 'reimbursement_requested' not in cols:
        cur.execute("ALTER TABLE exam ADD COLUMN reimbursement_requested INTEGER DEFAULT 0")
    conn.commit()
    conn.close()


def _ensure_rep_code_columns(db_path: Optional[Path] = None) -> None:
    """Ensure recruiter and trainee tables have a rep_code column for existing DBs."""
    conn = get_conn(db_path)
    cur = conn.cursor()
    # recruiter
    cur.execute("PRAGMA table_info(recruiter)")
    cols = {r['name'] for r in cur.fetchall()}
    if 'rep_code' not in cols:
        cur.execute("ALTER TABLE recruiter ADD COLUMN rep_code TEXT")
    # trainee
    cur.execute("PRAGMA table_info(trainee)")
    cols = {r['name'] for r in cur.fetchall()}
    if 'rep_code' not in cols:
        cur.execute("ALTER TABLE trainee ADD COLUMN rep_code TEXT")
    conn.commit()
    conn.close()


def _ensure_practice_status_table(db_path: Optional[Path] = None) -> None:
    """Ensure a simple table exists to persist practice exam completion status per module.

    Table schema:
        practice_exam_status(module TEXT PRIMARY KEY, completed INTEGER DEFAULT 0)
    """
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute(
        """
CREATE TABLE IF NOT EXISTS practice_exam_status (
    module TEXT PRIMARY KEY,
    completed INTEGER DEFAULT 0
);
        """
    )
    conn.commit()
    conn.close()


def _validate_rep_code(rep_code: Optional[str]) -> Optional[str]:
    """Validate rep_code is 5 alphanumeric characters. Return uppercased code or raise ValueError.

    Accepts None/empty -> returns None.
    """
    if rep_code is None:
        return None
    s = (rep_code or "").strip()
    if not s:
        return None
    if len(s) != 5 or not re.match(r'^[A-Za-z0-9]{5}$', s):
        raise ValueError("rep_code must be exactly 5 alphanumeric characters")
    return s.upper()



def add_recruiter(name: str, email: Optional[str] = None, phone: Optional[str] = None, rep_code: Optional[str] = None,
                  db_path: Optional[Path] = None) -> int:
    conn = get_conn(db_path)
    cur = conn.cursor()
    # validate rep_code
    try:
        rc = _validate_rep_code(rep_code)
    except ValueError:
        conn.close()
        raise
    cur.execute("INSERT INTO recruiter (name, email, phone, rep_code) VALUES (?, ?, ?, ?)", (name, email, phone, rc))
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    return rid


def list_recruiters(db_path: Optional[Path] = None) -> List[sqlite3.Row]:
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM recruiter ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return rows


def find_recruiter_by_name(name: str, db_path: Optional[Path] = None) -> Optional[sqlite3.Row]:
    """Find recruiter by exact name (case-insensitive). Returns first match or None."""
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM recruiter WHERE LOWER(name) = LOWER(?) LIMIT 1", (name,))
    row = cur.fetchone()
    conn.close()
    return row


def find_recruiter_by_rep_code(rep_code: str, db_path: Optional[Path] = None) -> Optional[sqlite3.Row]:
    if not rep_code:
        return None
    code = rep_code.strip().upper()
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM recruiter WHERE rep_code = ? LIMIT 1", (code,))
    row = cur.fetchone()
    conn.close()
    return row


def search_recruiters_by_name(prefix: str, limit: int = 10, db_path: Optional[Path] = None) -> List[sqlite3.Row]:
    """Return recruiters whose name starts with prefix (case-insensitive)."""
    if not prefix:
        return []
    conn = get_conn(db_path)
    cur = conn.cursor()
    like = prefix.strip() + '%'
    cur.execute("SELECT * FROM recruiter WHERE name LIKE ? COLLATE NOCASE ORDER BY name LIMIT ?", (like, limit))
    rows = cur.fetchall()
    conn.close()
    return rows


def search_recruiters_by_rep(prefix: str, limit: int = 10, db_path: Optional[Path] = None) -> List[sqlite3.Row]:
    if not prefix:
        return []
    conn = get_conn(db_path)
    cur = conn.cursor()
    like = prefix.strip().upper() + '%'
    cur.execute("SELECT * FROM recruiter WHERE rep_code LIKE ? ORDER BY rep_code LIMIT ?", (like, limit))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_recruiter(recruiter_id: int, db_path: Optional[Path] = None) -> Optional[sqlite3.Row]:
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM recruiter WHERE id = ?", (recruiter_id,))
    row = cur.fetchone()
    conn.close()
    return row


def update_recruiter(recruiter_id: int, name: str, email: Optional[str], phone: Optional[str], rep_code: Optional[str] = None, db_path: Optional[Path] = None) -> None:
    conn = get_conn(db_path)
    cur = conn.cursor()
    # validate rep_code
    rc = None
    if rep_code is not None:
        rc = _validate_rep_code(rep_code)
    cur.execute("UPDATE recruiter SET name = ?, email = ?, phone = ?, rep_code = ? WHERE id = ?", (name, email, phone, rc, recruiter_id))
    conn.commit()
    conn.close()


def add_trainee(first_name: str, last_name: str, dob: Optional[str] = None,
                recruiter_id: Optional[int] = None, rep_code: Optional[str] = None, db_path: Optional[Path] = None) -> int:
    conn = get_conn(db_path)
    cur = conn.cursor()
    # validate rep_code
    try:
        rc = _validate_rep_code(rep_code)
    except ValueError:
        conn.close()
        raise
    cur.execute(
        "INSERT INTO trainee (first_name, last_name, dob, recruiter_id, rep_code) VALUES (?, ?, ?, ?, ?)",
        (first_name, last_name, dob, recruiter_id, rc),
    )
    conn.commit()
    tid = cur.lastrowid
    conn.close()
    return tid


def list_trainees(db_path: Optional[Path] = None) -> List[sqlite3.Row]:
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT t.*, r.name as recruiter_name FROM trainee t LEFT JOIN recruiter r ON t.recruiter_id = r.id ORDER BY t.last_name, t.first_name"
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def find_trainee_by_name(first_name: str, last_name: str, db_path: Optional[Path] = None) -> Optional[sqlite3.Row]:
    """Find trainee by exact first+last name (case-insensitive). Returns first match or None."""
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM trainee WHERE LOWER(first_name)=LOWER(?) AND LOWER(last_name)=LOWER(?) LIMIT 1", (first_name, last_name))
    row = cur.fetchone()
    conn.close()
    return row


def find_trainee_by_rep_code(rep_code: str, db_path: Optional[Path] = None) -> Optional[sqlite3.Row]:
    if not rep_code:
        return None
    code = rep_code.strip().upper()
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM trainee WHERE rep_code = ? LIMIT 1", (code,))
    row = cur.fetchone()
    conn.close()
    return row


def search_trainees_by_name(prefix: str, limit: int = 10, db_path: Optional[Path] = None) -> List[sqlite3.Row]:
    """Search trainees by first or last name prefix (case-insensitive). Returns rows with first_name and last_name."""
    if not prefix:
        return []
    conn = get_conn(db_path)
    cur = conn.cursor()
    like = prefix.strip() + '%'
    cur.execute(
        "SELECT * FROM trainee WHERE first_name LIKE ? COLLATE NOCASE OR last_name LIKE ? COLLATE NOCASE ORDER BY last_name, first_name LIMIT ?",
        (like, like, limit),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def search_trainees_by_rep(prefix: str, limit: int = 10, db_path: Optional[Path] = None) -> List[sqlite3.Row]:
    if not prefix:
        return []
    conn = get_conn(db_path)
    cur = conn.cursor()
    like = prefix.strip().upper() + '%'
    cur.execute("SELECT * FROM trainee WHERE rep_code LIKE ? ORDER BY rep_code LIMIT ?", (like, limit))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_trainee(trainee_id: int, db_path: Optional[Path] = None) -> Optional[sqlite3.Row]:
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM trainee WHERE id = ?", (trainee_id,))
    row = cur.fetchone()
    conn.close()
    return row


def update_trainee(trainee_id: int, first_name: str, last_name: str, dob: Optional[str], recruiter_id: Optional[int], rep_code: Optional[str] = None, db_path: Optional[Path] = None) -> None:
    conn = get_conn(db_path)
    cur = conn.cursor()
    rc = None
    if rep_code is not None:
        rc = _validate_rep_code(rep_code)
    cur.execute("UPDATE trainee SET first_name = ?, last_name = ?, dob = ?, recruiter_id = ?, rep_code = ? WHERE id = ?", (first_name, last_name, dob, recruiter_id, rc, trainee_id))
    conn.commit()
    conn.close()


def delete_recruiter(recruiter_id: int, db_path: Optional[Path] = None) -> None:
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM recruiter WHERE id = ?", (recruiter_id,))
    conn.commit()
    conn.close()


def delete_trainee(trainee_id: int, db_path: Optional[Path] = None) -> None:
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM trainee WHERE id = ?", (trainee_id,))
    conn.commit()
    conn.close()


def delete_class(class_id: int, db_path: Optional[Path] = None) -> None:
    """Delete a class by id. Trainee links will be removed by FK cascade."""
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM class WHERE id = ?", (class_id,))
    conn.commit()
    conn.close()


def update_class(class_id: int, name: str, start_date: Optional[str], end_date: Optional[str], db_path: Optional[Path] = None) -> None:
    """Update class record fields."""
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("UPDATE class SET name = ?, start_date = ?, end_date = ? WHERE id = ?", (name, start_date, end_date, class_id))
    conn.commit()
    conn.close()


def add_class(name: str, start_date: Optional[str] = None, end_date: Optional[str] = None,
              db_path: Optional[Path] = None) -> int:
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("INSERT INTO class (name, start_date, end_date) VALUES (?, ?, ?)", (name, start_date, end_date))
    conn.commit()
    cid = cur.lastrowid
    conn.close()
    return cid


def list_classes(db_path: Optional[Path] = None) -> List[sqlite3.Row]:
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM class ORDER BY start_date")
    rows = cur.fetchall()
    conn.close()
    return rows


def link_trainee_to_class(trainee_id: int, class_id: int, db_path: Optional[Path] = None) -> None:
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO trainee_class (trainee_id, class_id) VALUES (?, ?)", (trainee_id, class_id))
    conn.commit()
    conn.close()


def add_exam(trainee_id: int, class_id: Optional[int], exam_date: Optional[str], score: Optional[str], notes: Optional[str], db_path: Optional[Path] = None) -> int:
    # Ensure we have updated columns
    _ensure_exam_columns(db_path)
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("INSERT INTO exam (trainee_id, class_id, exam_date, score, notes) VALUES (?, ?, ?, ?, ?)", (trainee_id, class_id, exam_date, score, notes))
    conn.commit()
    eid = cur.lastrowid
    conn.close()
    return eid


def update_practice_exam_status(module: str, completed: bool, db_path: Optional[Path] = None) -> None:
    """Set the completion flag for a practice exam module (insert or replace)."""
    _ensure_practice_status_table(db_path)
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO practice_exam_status (module, completed) VALUES (?, ?)", (module, int(bool(completed))))
    conn.commit()
    conn.close()


def get_practice_exam_status(module: str, db_path: Optional[Path] = None) -> bool:
    """Return True if the module is marked complete in the practice_exam_status table."""
    _ensure_practice_status_table(db_path)
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT completed FROM practice_exam_status WHERE module = ?", (module,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return False
    try:
        return bool(row['completed'])
    except Exception:
        return bool(row[0])


def list_practice_exam_status(db_path: Optional[Path] = None) -> dict:
    """Return a mapping module -> bool for all stored practice exam statuses."""
    _ensure_practice_status_table(db_path)
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT module, completed FROM practice_exam_status")
    rows = cur.fetchall()
    conn.close()
    return {r['module']: bool(r['completed']) for r in rows}


def reset_practice_exam_statuses(db_path: Optional[Path] = None) -> None:
    """Reset all practice exam statuses to incomplete (0)."""
    _ensure_practice_status_table(db_path)
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("UPDATE practice_exam_status SET completed = 0")
    conn.commit()
    conn.close()


def delete_exam(exam_id: int, db_path: Optional[Path] = None) -> None:
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM exam WHERE id = ?", (exam_id,))
    conn.commit()
    conn.close()


def update_exam(exam_id: int, trainee_id: int, class_id: Optional[int], exam_date: Optional[str], module: Optional[str], is_practice: bool, passed: Optional[bool], score: Optional[float], notes: Optional[str], reimbursement_requested: bool = False, db_path: Optional[Path] = None) -> None:
    """Update an exam record with the provided fields."""
    _ensure_exam_columns(db_path)
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute(
        "UPDATE exam SET trainee_id = ?, class_id = ?, exam_date = ?, module = ?, is_practice = ?, passed = ?, score = ?, notes = ?, reimbursement_requested = ? WHERE id = ?",
        (trainee_id, class_id, exam_date, module, int(bool(is_practice)), (1 if passed else (0 if passed is False else None)), score, notes, int(bool(reimbursement_requested)), exam_id),
    )
    conn.commit()
    conn.close()


def add_exam_v2(trainee_id: int, class_id: Optional[int], exam_date: Optional[str], module: Optional[str], is_practice: bool, passed: Optional[bool], score: Optional[float], notes: Optional[str], reimbursement_requested: bool = False, db_path: Optional[Path] = None) -> int:
    """Add an exam record with module, practice flag, pass/fail, numeric score, and reimbursement flag."""
    _ensure_exam_columns(db_path)
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO exam (trainee_id, class_id, exam_date, module, is_practice, passed, score, notes, reimbursement_requested) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (trainee_id, class_id, exam_date, module, int(bool(is_practice)), (1 if passed else (0 if passed is False else None)), score, notes, int(bool(reimbursement_requested))),
    )
    conn.commit()
    eid = cur.lastrowid
    conn.close()
    return eid


def add_license(trainee_id: int, application_submitted_date: Optional[str], approval_date: Optional[str], license_number: Optional[str], status: Optional[str], notes: Optional[str], db_path: Optional[Path] = None) -> int:
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("INSERT INTO license (trainee_id, application_submitted_date, approval_date, license_number, status, notes) VALUES (?, ?, ?, ?, ?, ?)", (trainee_id, application_submitted_date, approval_date, license_number, status, notes))
    conn.commit()
    lid = cur.lastrowid
    conn.close()
    return lid


def update_license(license_id: int, trainee_id: int, application_submitted_date: Optional[str], approval_date: Optional[str], license_number: Optional[str], status: Optional[str], notes: Optional[str], db_path: Optional[Path] = None) -> None:
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("UPDATE license SET trainee_id = ?, application_submitted_date = ?, approval_date = ?, license_number = ?, status = ?, notes = ? WHERE id = ?", (trainee_id, application_submitted_date, approval_date, license_number, status, notes, license_id))
    conn.commit()
    conn.close()


def list_exams(db_path: Optional[Path] = None) -> List[sqlite3.Row]:
    _ensure_exam_columns(db_path)
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT e.*, t.first_name, t.last_name, c.name as class_name FROM exam e JOIN trainee t ON e.trainee_id = t.id LEFT JOIN class c ON e.class_id = c.id ORDER BY e.exam_date DESC")
    rows = cur.fetchall()
    conn.close()
    return rows


def list_licenses(db_path: Optional[Path] = None) -> List[sqlite3.Row]:
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT l.*, t.first_name, t.last_name FROM license l JOIN trainee t ON l.trainee_id = t.id ORDER BY l.application_submitted_date DESC")
    rows = cur.fetchall()
    conn.close()
    return rows


def practice_exams_complete(trainee_id: int, min_score: float = 60.0, required_count: int = 4, db_path: Optional[Path] = None) -> bool:
    """Return True if trainee has at least `required_count` practice exams with score >= min_score."""
    _ensure_exam_columns(db_path)
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM exam WHERE trainee_id = ? AND is_practice = 1 AND score IS NOT NULL AND score >= ?", (trainee_id, min_score))
    cnt = cur.fetchone()[0]
    conn.close()
    return cnt >= required_count
