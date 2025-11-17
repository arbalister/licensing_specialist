-- SQLite schema for licensing specialist
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS recruiter (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    rep_code TEXT
);

CREATE TABLE IF NOT EXISTS trainee (
    id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    dob TEXT,
    rep_code TEXT,
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
