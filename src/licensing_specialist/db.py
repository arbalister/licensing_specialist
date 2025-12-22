import re
import sqlite3
import contextlib
import logging
from pathlib import Path
from typing import Optional, List, Any, Dict, Union

logger = logging.getLogger(__name__)

class CRUDHelper:
    """
    Simple CRUD helper for a given table.
    Used for recruiter, trainee, class, exam, and license tables.
    """
    def __init__(self, table: str, id_col: str = "id"):
        self.table = table
        self.id_col = id_col

    def add(self, fields: Dict[str, Any], db_path: Optional[Path] = None) -> int:
        try:
            with get_db_connection(db_path) as conn:
                cur = conn.cursor()
                keys = ', '.join(fields.keys())
                qmarks = ', '.join(['?'] * len(fields))
                sql = f"INSERT INTO {self.table} ({keys}) VALUES ({qmarks})"
                cur.execute(sql, tuple(fields.values()))
                conn.commit()
                rowid = cur.lastrowid
                logger.info(f"Added record to {self.table} with ID {rowid}")
            return rowid
        except Exception as e:
            logger.error(f"Error adding record to {self.table}: {e}")
            raise

    def update(self, row_id: int, fields: Dict[str, Any], db_path: Optional[Path] = None) -> None:
        try:
            with get_db_connection(db_path) as conn:
                cur = conn.cursor()
                sets = ', '.join([f"{k}=?" for k in fields.keys()])
                sql = f"UPDATE {self.table} SET {sets} WHERE {self.id_col}=?"
                cur.execute(sql, tuple(fields.values()) + (row_id,))
                conn.commit()
                logger.info(f"Updated record in {self.table} with ID {row_id}")
        except Exception as e:
            logger.error(f"Error updating record in {self.table} ID {row_id}: {e}")
            raise

    def delete(self, row_id: int, db_path: Optional[Path] = None) -> None:
        try:
            with get_db_connection(db_path) as conn:
                cur = conn.cursor()
                sql = f"DELETE FROM {self.table} WHERE {self.id_col}=?"
                cur.execute(sql, (row_id,))
                conn.commit()
                logger.info(f"Deleted record from {self.table} with ID {row_id}")
        except Exception as e:
            logger.error(f"Error deleting record from {self.table} ID {row_id}: {e}")
            raise

    def get(self, row_id: int, db_path: Optional[Path] = None) -> Optional[sqlite3.Row]:
        try:
            with get_db_connection(db_path) as conn:
                cur = conn.cursor()
                sql = f"SELECT * FROM {self.table} WHERE {self.id_col}=?"
                cur.execute(sql, (row_id,))
                row = cur.fetchone()
            return row
        except Exception as e:
            logger.error(f"Error fetching record from {self.table} ID {row_id}: {e}")
            return None

    def list(self, order_by: Optional[str] = None, db_path: Optional[Path] = None) -> List[sqlite3.Row]:
        try:
            with get_db_connection(db_path) as conn:
                cur = conn.cursor()
                sql = f"SELECT * FROM {self.table}"
                if order_by:
                    sql += f" ORDER BY {order_by}"
                cur.execute(sql)
                rows = cur.fetchall()
            return rows
        except Exception as e:
            logger.error(f"Error listing records from {self.table}: {e}")
            return []

def link_trainee_to_class(trainee_id: int, class_id: int, db_path: Optional[Path] = None) -> None:
    """Link a trainee to a class by inserting into the trainee_class table."""
    with get_db_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO trainee_class (trainee_id, class_id) VALUES (?, ?)",
            (trainee_id, class_id)
        )
        conn.commit()


DEFAULT_DB = Path(__file__).resolve().parents[2] / "licensing.db"


def get_conn(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Raw connection factory. For most uses, prefer get_db_connection() context manager."""
    path = db_path or DEFAULT_DB
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    # Enable foreign key constraints to ensure cascading deletes work
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

@contextlib.contextmanager
def get_db_connection(db_path: Optional[Path] = None):
    """Context manager for database connections."""
    conn = get_conn(db_path)
    try:
        yield conn
    finally:
        conn.close()


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
    license_type TEXT,
    invoiced INTEGER DEFAULT 0,
    FOREIGN KEY(trainee_id) REFERENCES trainee(id) ON DELETE CASCADE
);
        """
    )
    # Ensure schema is up to date
    try:
        _migrate_db(db_path)
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to initialize or migrate database: {e}")
        raise
    finally:
        conn.close()


def _migrate_db(db_path: Optional[Path] = None) -> None:
    """Central entry point for database migrations."""
    # Table-specific column maps: {column_name: definition}
    migrations = {
        "exam": {
            "module": "TEXT",
            "is_practice": "INTEGER DEFAULT 0",
            "passed": "INTEGER",
            "reimbursement_requested": "INTEGER DEFAULT 0"
        },
        "recruiter": {
            "rep_code": "TEXT"
        },
        "trainee": {
            "rep_code": "TEXT",
            "rvp_name": "TEXT",
            "rvp_rep_code": "TEXT"
        },
        "license": {
            "license_type": "TEXT",
            "invoiced": "INTEGER DEFAULT 0"
        }
    }

    logger.info("Starting database migrations...")
    for table, cols in migrations.items():
        _ensure_columns(table, cols, db_path)

    # Special table handling
    _ensure_practice_status_table(db_path)


def _ensure_columns(table_name: str, column_definitions: Dict[str, str], db_path: Optional[Path] = None) -> None:
    """Utility to ensure specified columns exist in a table."""
    conn = get_conn(db_path)
    cur = conn.cursor()
    try:
        cur.execute(f"PRAGMA table_info({table_name})")
        existing_cols = {r['name'] for r in cur.fetchall()}
        for col_name, col_def in column_definitions.items():
            if col_name not in existing_cols:
                cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def}")
        conn.commit()
    finally:
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
                recruiter_id: Optional[int] = None, rep_code: Optional[str] = None, 
                rvp_name: Optional[str] = None, rvp_rep_code: Optional[str] = None,
                db_path: Optional[Path] = None) -> int:
    try:
        rc = _validate_rep_code(rep_code)
    except ValueError:
        raise
    return trainee_crud.add({
        "first_name": first_name,
        "last_name": last_name,
        "dob": dob,
        "recruiter_id": recruiter_id,
        "rep_code": rc,
        "rvp_name": rvp_name,
        "rvp_rep_code": rvp_rep_code
    }, db_path=db_path)


def update_trainee(trainee_id: int, first_name: str, last_name: str, dob: Optional[str], recruiter_id: Optional[int], 
                   rep_code: Optional[str] = None, rvp_name: Optional[str] = None, rvp_rep_code: Optional[str] = None,
                   db_path: Optional[Path] = None) -> None:
    rc = None
    if rep_code is not None:
        rc = _validate_rep_code(rep_code)
    trainee_crud.update(trainee_id, {
        "first_name": first_name,
        "last_name": last_name,
        "dob": dob,
        "recruiter_id": recruiter_id,
        "rep_code": rc,
        "rvp_name": rvp_name,
        "rvp_rep_code": rvp_rep_code
    }, db_path=db_path)

def delete_trainee(trainee_id: int, db_path: Optional[Path] = None) -> None:
    trainee_crud.delete(trainee_id, db_path=db_path)

def get_trainee(trainee_id: int, db_path: Optional[Path] = None) -> Optional[sqlite3.Row]:
    return trainee_crud.get(trainee_id, db_path=db_path)

def list_trainees(db_path: Optional[Path] = None) -> List[sqlite3.Row]:
    with get_db_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT t.*, r.name as recruiter_name FROM trainee t LEFT JOIN recruiter r ON t.recruiter_id = r.id ORDER BY t.last_name, t.first_name"
        )
        rows = cur.fetchall()
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


def add_exam(trainee_id: int, class_id: Optional[int], exam_date: Optional[str], score: Optional[str], notes: Optional[str], 
             module: Optional[str] = None, is_practice: bool = False, passed: Optional[bool] = None, 
             reimbursement_requested: bool = False, db_path: Optional[Path] = None) -> int:
    return exam_crud.add({
        "trainee_id": trainee_id,
        "class_id": class_id,
        "exam_date": exam_date,
        "score": score,
        "notes": notes,
        "module": module,
        "is_practice": int(bool(is_practice)),
        "passed": (1 if passed else (0 if passed is False else None)),
        "reimbursement_requested": int(bool(reimbursement_requested)),
    }, db_path=db_path)


def update_practice_exam_status(trainee_id: int, module: str, completed: bool, db_path: Optional[Path] = None) -> None:
    """Set the completion flag for a practice exam module for a specific trainee (insert or replace).
    
    When completed=True, sets completed_date to current timestamp.
    """
    with get_db_connection(db_path) as conn:
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


def get_practice_exam_status(trainee_id: int, module: str, db_path: Optional[Path] = None) -> bool:
    """Return True if the module is marked complete for the trainee in the practice_exam_status table."""
    with get_db_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT completed FROM practice_exam_status WHERE trainee_id = ? AND module = ?", (trainee_id, module))
        row = cur.fetchone()
    if not row:
        return False
    try:
        return bool(row['completed'])
    except Exception:
        return bool(row[0])


def get_practice_exam_status_for_trainee(trainee_id: int, db_path: Optional[Path] = None) -> Dict[str, bool]:
    """Return a dictionary mapping module names to completion status (True/False)."""
    with get_db_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT module, completed FROM practice_exam_status WHERE trainee_id = ?", (trainee_id,))
        rows = cur.fetchall()
    return {r['module']: bool(r['completed']) for r in rows}


def reset_practice_exam_statuses_for_trainee(trainee_id: int, db_path: Optional[Path] = None) -> None:
    """Reset all practice exam statuses to incomplete (0) for a specific trainee."""
    with get_db_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute("UPDATE practice_exam_status SET completed = 0, completed_date = NULL WHERE trainee_id = ?", (trainee_id,))
        conn.commit()


def get_practice_module_completion_date(trainee_id: int, module: str, db_path: Optional[Path] = None) -> Optional[str]:
    """Return the completion date (ISO format string) for a practice exam module, or None if not completed."""
    with get_db_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT completed_date FROM practice_exam_status WHERE trainee_id = ? AND module = ? AND completed = 1",
            (trainee_id, module)
        )
        row = cur.fetchone()
    if not row:
        return None
    return row['completed_date']


def get_all_practice_module_completion_dates(trainee_id: int, db_path: Optional[Path] = None) -> Dict[str, str]:
    """Return a map of module -> completion_date (ISO string)."""
    with get_db_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT module, completed_date FROM practice_exam_status WHERE trainee_id = ? AND completed = 1",
            (trainee_id,)
        )
        rows = cur.fetchall()
    return {r['module']: r['completed_date'] for r in rows if r['completed_date']}


def update_exam(exam_id: int, trainee_id: int, class_id: Optional[int], exam_date: Optional[str], score: Optional[str], notes: Optional[str],
                module: Optional[str] = None, is_practice: bool = False, passed: Optional[bool] = None, 
                reimbursement_requested: bool = False, db_path: Optional[Path] = None) -> None:
    exam_crud.update(exam_id, {
        "trainee_id": trainee_id,
        "class_id": class_id,
        "exam_date": exam_date,
        "score": score,
        "notes": notes,
        "module": module,
        "is_practice": int(bool(is_practice)),
        "passed": (1 if passed else (0 if passed is False else None)),
        "reimbursement_requested": int(bool(reimbursement_requested)),
    }, db_path=db_path)

def delete_exam(exam_id: int, db_path: Optional[Path] = None) -> None:
    exam_crud.delete(exam_id, db_path=db_path)

def get_exam(exam_id: int, db_path: Optional[Path] = None) -> Optional[sqlite3.Row]:
    return exam_crud.get(exam_id, db_path=db_path)

def list_exams(db_path: Optional[Path] = None) -> List[sqlite3.Row]:
    with get_db_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT e.*, t.first_name, t.last_name, c.name as class_name FROM exam e JOIN trainee t ON e.trainee_id = t.id LEFT JOIN class c ON e.class_id = c.id ORDER BY e.exam_date DESC")
        rows = cur.fetchall()
    return rows


def add_license(trainee_id: int, application_submitted_date: Optional[str], approval_date: Optional[str], 
                license_number: Optional[str], status: Optional[str], notes: Optional[str], 
                license_type: Optional[str] = None, invoiced: bool = False, db_path: Optional[Path] = None) -> int:
    return license_crud.add({
        "trainee_id": trainee_id,
        "application_submitted_date": application_submitted_date,
        "approval_date": approval_date,
        "license_number": license_number,
        "status": status,
        "notes": notes,
        "license_type": license_type,
        "invoiced": 1 if invoiced else 0
    }, db_path=db_path)

def update_license(license_id: int, trainee_id: int, application_submitted_date: Optional[str], approval_date: Optional[str], 
                   license_number: Optional[str], status: Optional[str], notes: Optional[str],
                   license_type: Optional[str] = None, invoiced: bool = False, db_path: Optional[Path] = None) -> None:
    license_crud.update(license_id, {
        "trainee_id": trainee_id,
        "application_submitted_date": application_submitted_date,
        "approval_date": approval_date,
        "license_number": license_number,
        "status": status,
        "notes": notes,
        "license_type": license_type,
        "invoiced": 1 if invoiced else 0
    }, db_path=db_path)

def delete_license(license_id: int, db_path: Optional[Path] = None) -> None:
    license_crud.delete(license_id, db_path=db_path)

def get_license(license_id: int, db_path: Optional[Path] = None) -> Optional[sqlite3.Row]:
    return license_crud.get(license_id, db_path=db_path)

def list_licenses(db_path: Optional[Path] = None) -> List[sqlite3.Row]:
    with get_db_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT l.*, t.first_name, t.last_name FROM license l JOIN trainee t ON l.trainee_id = t.id ORDER BY l.application_submitted_date DESC")
        rows = cur.fetchall()
    return rows


def get_practice_module_completion_count(trainee_id: int, required_modules: List[str], db_path: Optional[Path] = None) -> int:
    """Return count of required practice modules marked as complete for the trainee."""
    with get_db_connection(db_path) as conn:
        cur = conn.cursor()
        # Create dynamic placeholder string
        placeholders = ', '.join(['?'] * len(required_modules))
        query = f"SELECT COUNT(*) FROM practice_exam_status WHERE trainee_id = ? AND module IN ({placeholders}) AND completed = 1"
        cur.execute(query, (trainee_id, *required_modules))
        cnt = cur.fetchone()[0]
    return cnt

def get_passed_practice_exam_count(trainee_id: int, db_path: Optional[Path] = None) -> int:
    """Return count of practice exams marked as passed in the exam table."""
    with get_db_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM exam WHERE trainee_id = ? AND is_practice = 1 AND passed = 1", (trainee_id,))
        cnt = cur.fetchone()[0]
    return cnt





def update_license_invoice_status(license_id: int, invoiced: bool, db_path: Optional[Path] = None) -> None:
    """Update only the invoice status of a license."""
    with get_db_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute("UPDATE license SET invoiced = ? WHERE id = ?", (1 if invoiced else 0, license_id))
        conn.commit()

def get_rvp_invoice_summary(db_path: Optional[Path] = None) -> List[sqlite3.Row]:
    """Get all licenses with RVP info for invoice display."""
    with get_db_connection(db_path) as conn:
        cur = conn.cursor()
        sql = """
            SELECT l.id as license_id, l.license_type, l.invoiced,
                   t.first_name, t.last_name, t.rvp_name, t.rvp_rep_code 
            FROM license l
            JOIN trainee t ON l.trainee_id = t.id
            WHERE t.rvp_name IS NOT NULL AND t.rvp_name != ''
            ORDER BY t.rvp_name, t.last_name, t.first_name
        """
        cur.execute(sql)
        rows = cur.fetchall()
    return rows

def list_unique_rvps(db_path: Optional[Path] = None) -> List[sqlite3.Row]:
    """Get list of unique RVPs (name, rep_code) from existing trainees."""
    with get_db_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT rvp_name, rvp_rep_code FROM trainee WHERE rvp_name IS NOT NULL AND rvp_name != '' ORDER BY rvp_name")
        rows = cur.fetchall()
    return rows

def get_license_info_for_trainee(trainee_id: int, db_path: Optional[Path] = None) -> Optional[dict]:
    """Retrieve license information for a specific trainee."""
    with get_db_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT application_submitted_date, approval_date, license_number, status, license_type, invoiced "
            "FROM license WHERE trainee_id = ? ORDER BY application_submitted_date DESC LIMIT 1",
            (trainee_id,)
        )
        row = cur.fetchone()
    if not row:
        return None
    return {
        "application_submitted_date": row["application_submitted_date"],
        "approval_date": row["approval_date"],
        "license_number": row["license_number"],
        "status": row["status"],
        "license_type": row["license_type"],
        "invoiced": bool(row["invoiced"])
    }
# Example usage for recruiter CRUD
recruiter_crud = CRUDHelper("recruiter")
trainee_crud = CRUDHelper("trainee")
class_crud = CRUDHelper("class")
exam_crud = CRUDHelper("exam")
license_crud = CRUDHelper("license")

