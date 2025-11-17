(Project README)

licensing-specialist

This is a small desktop application for managing trainees, recruiters, classes, exams, and licenses.

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

If you prefer the original Tkinter implementation, `gui.py` acts as a shim that delegates to the PySide6 implementation.

