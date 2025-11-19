import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_DB = Path(__file__).resolve().parents[2] / "licensing.db"

def get_conn(db_path: Optional[Path] = None) -> sqlite3.Connection:
    path = db_path or DEFAULT_DB
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

class CRUDHelper:
    def __init__(self, table: str, id_col: str = "id"):
        self.table = table
        self.id_col = id_col

    def add(self, fields: Dict[str, Any], db_path: Optional[Path] = None) -> int:
        keys = ', '.join(fields.keys())
        placeholders = ', '.join(['?'] * len(fields))
        values = list(fields.values())
        sql = f"INSERT INTO {self.table} ({keys}) VALUES ({placeholders})"
        conn = get_conn(db_path)
        cur = conn.cursor()
        cur.execute(sql, values)
        conn.commit()
        rid = cur.lastrowid
        conn.close()
        return rid

    def update(self, row_id: int, fields: Dict[str, Any], db_path: Optional[Path] = None) -> None:
        set_clause = ', '.join([f"{k} = ?" for k in fields.keys()])
        values = list(fields.values()) + [row_id]
        sql = f"UPDATE {self.table} SET {set_clause} WHERE {self.id_col} = ?"
        conn = get_conn(db_path)
        cur = conn.cursor()
        cur.execute(sql, values)
        conn.commit()
        conn.close()

    def delete(self, row_id: int, db_path: Optional[Path] = None) -> None:
        sql = f"DELETE FROM {self.table} WHERE {self.id_col} = ?"
        conn = get_conn(db_path)
        cur = conn.cursor()
        cur.execute(sql, (row_id,))
        conn.commit()
        conn.close()

    def get(self, row_id: int, db_path: Optional[Path] = None) -> Optional[sqlite3.Row]:
        sql = f"SELECT * FROM {self.table} WHERE {self.id_col} = ?"
        conn = get_conn(db_path)
        cur = conn.cursor()
        cur.execute(sql, (row_id,))
        row = cur.fetchone()
        conn.close()
        return row

    def list(self, order_by: Optional[str] = None, db_path: Optional[Path] = None) -> List[sqlite3.Row]:
        sql = f"SELECT * FROM {self.table}"
        if order_by:
            sql += f" ORDER BY {order_by}"
        conn = get_conn(db_path)
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        conn.close()
        return rows
