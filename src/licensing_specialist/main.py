try:
    from .gui import run_app
except Exception:
    # Allow running this file directly (python main.py) by ensuring the
    # parent `src` directory is on sys.path so `licensing_specialist` can be imported.
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from licensing_specialist.gui import run_app
import logging
import traceback
from pathlib import Path


LOG_FILE = Path(__file__).resolve().parents[2] / "licensing_app.log"


def _setup_logging() -> None:
    logging.basicConfig(
        filename=str(LOG_FILE),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def main():
    _setup_logging()
    logging.info("Starting Licensing Specialist GUI")
    try:
        run_app()
    except Exception as exc:  # catch unexpected errors and log them
        logging.exception("Unhandled exception in application")
        # Try to show a friendly message to the user using tkinter if possible
        try:
            import tkinter as tk
            from tkinter import messagebox

            root = tk.Tk()
            root.withdraw()
            tb = traceback.format_exc()
            messagebox.showerror(
                "Application Error",
                f"An unexpected error occurred and the application must close.\n\nA log was written to: {LOG_FILE}\n\nError:\n{exc}",
            )
            root.destroy()
        except Exception:
            # If tkinter can't be used (no display), just print a concise message
            print(f"Fatal error; see log: {LOG_FILE}")
        # Re-raise so that test harnesses or callers can still observe the failure if needed
        raise


if __name__ == "__main__":
    main()
