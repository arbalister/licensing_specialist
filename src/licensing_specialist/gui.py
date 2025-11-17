"""
Lightweight shim for the Licensing Specialist GUI.

This module provides a stable `run_app()` entrypoint used by `main.py`.
It delegates to the PySide6 implementation in `pyside_gui.py` when available
and raises a clear RuntimeError if PySide6 or the GUI module is not present.
"""
from __future__ import annotations

try:
    # Prefer the PySide6 implementation
    from .pyside_gui import run_pyside_app as run_app
except Exception as exc:  # pragma: no cover - runtime guard
    def run_app(_exc=exc) -> None:
        # capture the exception value as a default arg to avoid the
        # exception variable being cleared after the except block
        raise RuntimeError("PySide6 GUI is not available: " + str(_exc))


if __name__ == "__main__":
    # Allow running the shim directly for convenience
    run_app()
