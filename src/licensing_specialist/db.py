
import re
import sqlite3
from pathlib import Path
from typing import Optional, List, Any, Dict

class CRUDHelper:
    """
    Simple CRUD helper for a given table.
    Used for recruiter, trainee, class, exam, and license tables.
    """
    def __init__(self, table: str, id_col: str = "id"):
        self.table = table
        self.id_col = id_col

    def add(self, fields: Dict[str, Any], db_path: Optional[Path] = None) -> int:
        conn = get_conn(db_path)
        cur = conn.cursor()
        keys = ', '.join(fields.keys())
        qmarks = ', '.join(['?'] * len(fields))
        sql = f"INSERT INTO {self.table} ({keys}) VALUES ({qmarks})"
        cur.execute(sql, tuple(fields.values()))
        conn.commit()
        rowid = cur.lastrowid
        conn.close()
        return rowid

    def update(self, row_id: int, fields: Dict[str, Any], db_path: Optional[Path] = None) -> None:
        conn = get_conn(db_path)
        cur = conn.cursor()
        sets = ', '.join([f"{k}=?" for k in fields.keys()])
        sql = f"UPDATE {self.table} SET {sets} WHERE {self.id_col}=?"
        cur.execute(sql, tuple(fields.values()) + (row_id,))
        conn.commit()
        conn.close()

    def delete(self, row_id: int, db_path: Optional[Path] = None) -> None:
        conn = get_conn(db_path)
        cur = conn.cursor()
        sql = f"DELETE FROM {self.table} WHERE {self.id_col}=?"
        cur.execute(sql, (row_id,))
        conn.commit()
        conn.close()

    def get(self, row_id: int, db_path: Optional[Path] = None) -> Optional[sqlite3.Row]:
        conn = get_conn(db_path)
        cur = conn.cursor()
        sql = f"SELECT * FROM {self.table} WHERE {self.id_col}=?"
        cur.execute(sql, (row_id,))
        row = cur.fetchone()
        conn.close()
        return row

    def list(self, order_by: Optional[str] = None, db_path: Optional[Path] = None) -> List[sqlite3.Row]:
        conn = get_conn(db_path)
        cur = conn.cursor()
        sql = f"SELECT * FROM {self.table}"
        if order_by:
            sql += f" ORDER BY {order_by}"
        cur.execute(sql)
        rows = cur.fetchall()
        conn.close()
        return rows

def link_trainee_to_class(trainee_id: int, class_id: int, db_path: Optional[Path] = None) -> None:
    """Link a trainee to a class by inserting into the trainee_class table."""
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO trainee_class (trainee_id, class_id) VALUES (?, ?)",
        (trainee_id, class_id)
    )
    conn.commit()
    conn.close()


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
    """Ensure a table exists to persist practice exam completion status per trainee per module with timestamps.

    Table schema:
        practice_exam_status(trainee_id INTEGER, module TEXT, completed INTEGER DEFAULT 0, completed_date TEXT, PRIMARY KEY (trainee_id, module))
    """
    conn = get_conn(db_path)
    cur = conn.cursor()
    
    try:
        # Check if the table exists and what columns it has
        cur.execute("PRAGMA table_info(practice_exam_status)")
        columns = [row[1] for row in cur.fetchall()]
        
        if len(columns) == 0:
            # Table doesn't exist, create with new schema
            # First clean up any leftover old table from previous migrations
            cur.execute("DROP TABLE IF EXISTS practice_exam_status_old")
            conn.commit()
            
            cur.execute(
                """
CREATE TABLE practice_exam_status (
    trainee_id INTEGER NOT NULL,
    module TEXT NOT NULL,
    completed INTEGER DEFAULT 0,
    completed_date TEXT,
    PRIMARY KEY (trainee_id, module),
    FOREIGN KEY(trainee_id) REFERENCES trainee(id) ON DELETE CASCADE
);
                """
            )
            conn.commit()
        elif 'completed_date' not in columns:
            # Old schema exists without completed_date column, need to migrate
            
            # First, drop any leftover old table from a previous failed migration
            cur.execute("DROP TABLE IF EXISTS practice_exam_status_old")
            conn.commit()
            
            # Rename old table
            cur.execute("ALTER TABLE practice_exam_status RENAME TO practice_exam_status_old")
            conn.commit()
            
            # Create new table with correct schema
            cur.execute(
                """
CREATE TABLE practice_exam_status (
    trainee_id INTEGER NOT NULL,
    module TEXT NOT NULL,
    completed INTEGER DEFAULT 0,
    completed_date TEXT,
    PRIMARY KEY (trainee_id, module),
    FOREIGN KEY(trainee_id) REFERENCES trainee(id) ON DELETE CASCADE
);
                """
            )
            conn.commit()
            
            # Migrate data from old table
            cur.execute(
                "INSERT OR IGNORE INTO practice_exam_status (trainee_id, module, completed) "
                "SELECT trainee_id, module, completed FROM practice_exam_status_old"
            )
            conn.commit()
            
            # Drop old table
            cur.execute("DROP TABLE IF EXISTS practice_exam_status_old")
            conn.commit()
        else:
            # Schema is already up to date, but clean up any leftover old table
            cur.execute("DROP TABLE IF EXISTS practice_exam_status_old")
            conn.commit()
    finally:
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



def add_recruiter(name: str, email: Optional[str] = None, phone: Optional[str] = None, rep_code: Optional[str] = None, db_path: Optional[Path] = None) -> int:
    # validate rep_code
    try:
        rc = _validate_rep_code(rep_code)
    except ValueError:
        raise
    return recruiter_crud.add({
        "name": name,
        "email": email,
        "phone": phone,
        "rep_code": rc
    }, db_path=db_path)

def update_recruiter(recruiter_id: int, name: str, email: Optional[str], phone: Optional[str], rep_code: Optional[str] = None, db_path: Optional[Path] = None) -> None:
    rc = None
    if rep_code is not None:
        rc = _validate_rep_code(rep_code)
    recruiter_crud.update(recruiter_id, {
        "name": name,
        "email": email,
        "phone": phone,
        "rep_code": rc
    }, db_path=db_path)

def delete_recruiter(recruiter_id: int, db_path: Optional[Path] = None) -> None:
    recruiter_crud.delete(recruiter_id, db_path=db_path)

def get_recruiter(recruiter_id: int, db_path: Optional[Path] = None) -> Optional[sqlite3.Row]:
    return recruiter_crud.get(recruiter_id, db_path=db_path)

def list_recruiters(db_path: Optional[Path] = None) -> List[sqlite3.Row]:
    return recruiter_crud.list(order_by="name", db_path=db_path)


def add_trainee(first_name: str, last_name: str, dob: Optional[str] = None,
                recruiter_id: Optional[int] = None, rep_code: Optional[str] = None, db_path: Optional[Path] = None) -> int:
    try:
        rc = _validate_rep_code(rep_code)
    except ValueError:
        raise
    return trainee_crud.add({
        "first_name": first_name,
        "last_name": last_name,
        "dob": dob,
        "recruiter_id": recruiter_id,
        "rep_code": rc
    }, db_path=db_path)


def update_trainee(trainee_id: int, first_name: str, last_name: str, dob: Optional[str], recruiter_id: Optional[int], rep_code: Optional[str] = None, db_path: Optional[Path] = None) -> None:
    rc = None
    if rep_code is not None:
        rc = _validate_rep_code(rep_code)
    trainee_crud.update(trainee_id, {
        "first_name": first_name,
        "last_name": last_name,
        "dob": dob,
        "recruiter_id": recruiter_id,
        "rep_code": rc
    }, db_path=db_path)

def delete_trainee(trainee_id: int, db_path: Optional[Path] = None) -> None:
    trainee_crud.delete(trainee_id, db_path=db_path)

def get_trainee(trainee_id: int, db_path: Optional[Path] = None) -> Optional[sqlite3.Row]:
    return trainee_crud.get(trainee_id, db_path=db_path)

def list_trainees(db_path: Optional[Path] = None) -> List[sqlite3.Row]:
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT t.*, r.name as recruiter_name FROM trainee t LEFT JOIN recruiter r ON t.recruiter_id = r.id ORDER BY t.last_name, t.first_name"
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def add_class(name: str, start_date: Optional[str] = None, end_date: Optional[str] = None, db_path: Optional[Path] = None) -> int:
    return class_crud.add({
        "name": name,
        "start_date": start_date,
        "end_date": end_date
    }, db_path=db_path)

def update_class(class_id: int, name: str, start_date: Optional[str], end_date: Optional[str], db_path: Optional[Path] = None) -> None:
    class_crud.update(class_id, {
        "name": name,
        "start_date": start_date,
        "end_date": end_date
    }, db_path=db_path)

def delete_class(class_id: int, db_path: Optional[Path] = None) -> None:
    class_crud.delete(class_id, db_path=db_path)

def get_class(class_id: int, db_path: Optional[Path] = None) -> Optional[sqlite3.Row]:
    return class_crud.get(class_id, db_path=db_path)

def list_classes(db_path: Optional[Path] = None) -> List[sqlite3.Row]:
    return class_crud.list(order_by="start_date", db_path=db_path)


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


def update_practice_exam_status(trainee_id: int, module: str, completed: bool, db_path: Optional[Path] = None) -> None:
    """Set the completion flag for a practice exam module for a specific trainee (insert or replace).
    
    When completed=True, sets completed_date to current timestamp.
    When completed=False, clears the completed_date.
    """
    _ensure_practice_status_table(db_path)
    conn = get_conn(db_path)
    cur = conn.cursor()
    if completed:
        cur.execute(
            "INSERT OR REPLACE INTO practice_exam_status (trainee_id, module, completed, completed_date) VALUES (?, ?, 1, CURRENT_TIMESTAMP)",
            (trainee_id, module)
        )
    else:
        cur.execute(
            "INSERT OR REPLACE INTO practice_exam_status (trainee_id, module, completed, completed_date) VALUES (?, ?, 0, NULL)",
            (trainee_id, module)
        )
    conn.commit()
    conn.close()


def get_practice_exam_status(trainee_id: int, module: str, db_path: Optional[Path] = None) -> bool:
    """Return True if the module is marked complete for the trainee in the practice_exam_status table."""
    _ensure_practice_status_table(db_path)
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT completed FROM practice_exam_status WHERE trainee_id = ? AND module = ?", (trainee_id, module))
    row = cur.fetchone()
    conn.close()
    if not row:
        return False
    try:
        return bool(row['completed'])
    except Exception:
        return bool(row[0])


def get_practice_exam_status_for_trainee(trainee_id: int, db_path: Optional[Path] = None) -> dict:
    """Return a mapping module -> bool for all practice exam statuses for a specific trainee."""
    _ensure_practice_status_table(db_path)
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT module, completed FROM practice_exam_status WHERE trainee_id = ?", (trainee_id,))
    rows = cur.fetchall()
    conn.close()
    return {r['module']: bool(r['completed']) for r in rows}


def reset_practice_exam_statuses_for_trainee(trainee_id: int, db_path: Optional[Path] = None) -> None:
    """Reset all practice exam statuses to incomplete (0) for a specific trainee."""
    _ensure_practice_status_table(db_path)
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("UPDATE practice_exam_status SET completed = 0, completed_date = NULL WHERE trainee_id = ?", (trainee_id,))
    conn.commit()
    conn.close()


def get_practice_module_completion_date(trainee_id: int, module: str, db_path: Optional[Path] = None) -> Optional[str]:
    """Return the completion date (ISO format string) for a practice exam module, or None if not completed."""
    _ensure_practice_status_table(db_path)
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT completed_date FROM practice_exam_status WHERE trainee_id = ? AND module = ? AND completed = 1",
        (trainee_id, module)
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return row['completed_date']


def get_all_practice_module_completion_dates(trainee_id: int, db_path: Optional[Path] = None) -> dict:
    """Return a mapping module -> completion_date (ISO format string) for all completed modules."""
    _ensure_practice_status_table(db_path)
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT module, completed_date FROM practice_exam_status WHERE trainee_id = ? AND completed = 1",
        (trainee_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return {r['module']: r['completed_date'] for r in rows if r['completed_date']}


def add_exam_v2(trainee_id: int, class_id: Optional[int], exam_date: Optional[str], module: Optional[str], is_practice: bool, passed: Optional[bool], notes: Optional[str], reimbursement_requested: bool = False, db_path: Optional[Path] = None) -> int:
    return exam_crud.add({
        "trainee_id": trainee_id,
        "class_id": class_id,
        "exam_date": exam_date,
        "module": module,
        "is_practice": int(bool(is_practice)),
        "passed": (1 if passed else (0 if passed is False else None)),
        "notes": notes,
        "reimbursement_requested": int(bool(reimbursement_requested)),
    }, db_path=db_path)

def update_exam(exam_id: int, trainee_id: int, class_id: Optional[int], exam_date: Optional[str], module: Optional[str], is_practice: bool, passed: Optional[bool], notes: Optional[str], reimbursement_requested: bool = False, db_path: Optional[Path] = None) -> None:
    exam_crud.update(exam_id, {
        "trainee_id": trainee_id,
        "class_id": class_id,
        "exam_date": exam_date,
        "module": module,
        "is_practice": int(bool(is_practice)),
        "passed": (1 if passed else (0 if passed is False else None)),
        "notes": notes,
        "reimbursement_requested": int(bool(reimbursement_requested)),
    }, db_path=db_path)

def delete_exam(exam_id: int, db_path: Optional[Path] = None) -> None:
    exam_crud.delete(exam_id, db_path=db_path)

def get_exam(exam_id: int, db_path: Optional[Path] = None) -> Optional[sqlite3.Row]:
    return exam_crud.get(exam_id, db_path=db_path)

def list_exams(db_path: Optional[Path] = None) -> List[sqlite3.Row]:
    _ensure_exam_columns(db_path)
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT e.*, t.first_name, t.last_name, c.name as class_name FROM exam e JOIN trainee t ON e.trainee_id = t.id LEFT JOIN class c ON e.class_id = c.id ORDER BY e.exam_date DESC")
    rows = cur.fetchall()
    conn.close()
    return rows


def add_license(trainee_id: int, application_submitted_date: Optional[str], approval_date: Optional[str], license_number: Optional[str], status: Optional[str], notes: Optional[str], db_path: Optional[Path] = None) -> int:
    return license_crud.add({
        "trainee_id": trainee_id,
        "application_submitted_date": application_submitted_date,
        "approval_date": approval_date,
        "license_number": license_number,
        "status": status,
        "notes": notes
    }, db_path=db_path)

def update_license(license_id: int, trainee_id: int, application_submitted_date: Optional[str], approval_date: Optional[str], license_number: Optional[str], status: Optional[str], notes: Optional[str], db_path: Optional[Path] = None) -> None:
    license_crud.update(license_id, {
        "trainee_id": trainee_id,
        "application_submitted_date": application_submitted_date,
        "approval_date": approval_date,
        "license_number": license_number,
        "status": status,
        "notes": notes
    }, db_path=db_path)

def delete_license(license_id: int, db_path: Optional[Path] = None) -> None:
    license_crud.delete(license_id, db_path=db_path)

def get_license(license_id: int, db_path: Optional[Path] = None) -> Optional[sqlite3.Row]:
    return license_crud.get(license_id, db_path=db_path)

def list_licenses(db_path: Optional[Path] = None) -> List[sqlite3.Row]:
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT l.*, t.first_name, t.last_name FROM license l JOIN trainee t ON l.trainee_id = t.id ORDER BY l.application_submitted_date DESC")
    rows = cur.fetchall()
    conn.close()
    return rows


def practice_exams_complete(trainee_id: int, required_count: int = 4, db_path: Optional[Path] = None) -> bool:
    """Return True if trainee has at least `required_count` practice exams marked as passed."""
    _ensure_exam_columns(db_path)
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM exam WHERE trainee_id = ? AND is_practice = 1 AND passed = 1", (trainee_id,))
    cnt = cur.fetchone()[0]
    conn.close()
    return cnt >= required_count


def all_practice_modules_marked_complete(trainee_id: int, db_path: Optional[Path] = None) -> bool:
    """Return True if all 4 practice exam modules (Life, A&S, Seg Funds, Ethics) are marked complete for the trainee."""
    _ensure_practice_status_table(db_path)
    conn = get_conn(db_path)
    cur = conn.cursor()
    required_modules = ["Life", "A&S", "Seg Funds", "Ethics"]
    cur.execute("SELECT COUNT(*) FROM practice_exam_status WHERE trainee_id = ? AND module IN (?, ?, ?, ?) AND completed = 1", 
                (trainee_id, required_modules[0], required_modules[1], required_modules[2], required_modules[3]))
    cnt = cur.fetchone()[0]
    conn.close()
    return cnt == len(required_modules)


def check_seewhy_guarantee(trainee_id: int, first_provincial_exam_date: Optional[str], db_path: Optional[Path] = None) -> bool:
    """Check if trainee qualifies for SeeWhy Guarantee.
    
    A trainee qualifies if all 4 practice exam modules (Life, A&S, Seg Funds, Ethics) 
    were completed before their first provincial exam date.
    
    Args:
        trainee_id: The ID of the trainee
        first_provincial_exam_date: ISO format date string of first provincial exam (e.g., "2024-01-15")
        db_path: Optional path to the database file
    
    Returns:
        True if all 4 modules were completed before the provincial exam date, False otherwise.
        Returns False if first_provincial_exam_date is None.
    """
    if not first_provincial_exam_date:
        return False
    
    completion_dates = get_all_practice_module_completion_dates(trainee_id, db_path)
    required_modules = ["Life", "A&S", "Seg Funds", "Ethics"]
    
    # Check if all required modules are in completion_dates
    if len(completion_dates) < len(required_modules):
        return False
    
    # Check if all modules are in the dict
    for module in required_modules:
        if module not in completion_dates:
            return False
    
    # Check if all completion dates are before the provincial exam date
    for module in required_modules:
        completion_date = completion_dates[module]
        if not completion_date:
            return False
        # Compare as strings (ISO format sorts correctly lexicographically)
        if completion_date.split('T')[0] >= first_provincial_exam_date:
            return False
    
    return True


def get_license_info_for_trainee(trainee_id: int, db_path: Optional[Path] = None) -> Optional[dict]:
    """Retrieve license information for a specific trainee."""
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT application_submitted_date, approval_date, license_number, status "
        "FROM license WHERE trainee_id = ? ORDER BY application_submitted_date DESC LIMIT 1",
        (trainee_id,)
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "application_submitted_date": row["application_submitted_date"],
        "approval_date": row["approval_date"],
        "license_number": row["license_number"],
        "status": row["status"],
    }
# Example usage for recruiter CRUD
recruiter_crud = CRUDHelper("recruiter")
trainee_crud = CRUDHelper("trainee")
class_crud = CRUDHelper("class")
exam_crud = CRUDHelper("exam")
license_crud = CRUDHelper("license")

