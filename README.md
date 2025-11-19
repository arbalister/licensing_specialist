
# Licensing Specialist

This is a modular desktop application for managing trainees, recruiters, classes, exams, and licenses.

## Project Structure

- `src/licensing_specialist/pyside_gui.py`: Main PySide6 GUI logic (entry point)
- `src/licensing_specialist/tabs/`: Each tab's logic is modularized into its own file:
	- `recruiter_tab.py`, `trainee_tab.py`, `class_tab.py`, `exam_tab.py`, `license_tab.py`
- `src/licensing_specialist/widgets.py`: Shared widget helpers for UI construction
- `src/licensing_specialist/db.py`: Database logic and CRUD helpers (no external dependencies)
- `src/licensing_specialist/styles.py`, `constants.py`: Centralized styles and constants
- `src/licensing_specialist/test_*.py`: Unit tests for database and tab logic

## Running the GUI (PySide6)

## Running the GUI (PySide6)

This project now uses a PySide6-based GUI by default. To run the desktop application:

1. Activate your virtualenv and install dependencies (PySide6 is listed in `pyproject.toml`):

```bash
source .venv/bin/activate
pip install "PySide6>=6.10.0"
```

2. Launch the app from the project root (ensure `src` is on `PYTHONPATH`):

```bash
PYTHONPATH=src .venv/bin/python -m licensing_specialist.main
```

Or run the PySide6 module directly:

```bash
PYTHONPATH=src .venv/bin/python -m licensing_specialist.pyside_gui
```


## Running Tests

To run all tests:

```bash
PYTHONPATH=src pytest src/licensing_specialist/test_*.py
```

Tests cover all major database and tab logic, including CRUD operations and exam/practice status management.

## Notes

- All tab logic is modularized for maintainability.
- Shared widget helpers are in `widgets.py`.
- The codebase is free of legacy/orphaned code.

