import sys
import os
import contextlib
from pathlib import Path
from typing import Optional, List, Dict

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTabWidget, QLabel, QToolBar, QMessageBox, QFileDialog, QCompleter
)
from PySide6.QtCore import Qt, QSize, QStringListModel
from PySide6.QtGui import QAction, QKeySequence, QIcon, QShortcut

from . import db
from . import services
from .styles import get_theme_qss
from .widgets import (
    _load_icon, create_form_section, create_button_row, 
    create_section_header, create_search_bar
)
from .tabs.recruiter_tab import setup_recruiter_tab
from .tabs.trainee_tab import setup_trainee_tab
from .tabs.class_tab import setup_class_tab
from .tabs.exam_tab import setup_exam_tab
from .tabs.license_tab import setup_license_tab
from .tabs.dashboard_tab import setup_dashboard_tab

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Licensing Specialist (PySide6)")
        self.setMinimumSize(1000, 700)
        self._dark_mode = False
        db.init_db()
        self._apply_theme()
        self._build()

    def _build(self) -> None:
        central = QWidget()
        main_layout = QVBoxLayout(central)
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        self.setCentralWidget(central)

        # Toolbar
        tb = QToolBar("Main")
        tb.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        
        add_act = QAction(_load_icon("add"), "Add (Ctrl+N)", self)
        add_act.setShortcut(QKeySequence("Ctrl+N"))
        add_act.triggered.connect(self._global_add)
        
        edit_act = QAction(_load_icon("edit"), "Edit (Ctrl+E)", self)
        edit_act.setShortcut(QKeySequence("Ctrl+E"))
        edit_act.triggered.connect(self._global_edit)
        
        del_act = QAction(_load_icon("delete"), "Delete (Del)", self)
        del_act.setShortcut(QKeySequence("Del"))
        del_act.triggered.connect(self._global_delete)
        
        theme_act = QAction(_load_icon("theme"), "Toggle Theme (Ctrl+T)", self)
        theme_act.setShortcut(QKeySequence("Ctrl+T"))
        theme_act.triggered.connect(self._toggle_theme)
        
        # Add actions to main window to preserve shortcuts
        self.addAction(add_act)
        self.addAction(edit_act)
        self.addAction(del_act)
        
        # Only add Theme button to toolbar
        tb.addAction(theme_act)
        self.addToolBar(tb)

        # Setup Tabs
        setup_dashboard_tab(self)
        setup_recruiter_tab(self)
        setup_trainee_tab(self)
        setup_class_tab(self)
        setup_exam_tab(self)
        setup_license_tab(self)
        
        self.tabs.setCurrentIndex(0) # Ensure Dashboard is selected

        # Status Bar
        self.statusBar().showMessage("Ready")

    def _apply_theme(self) -> None:
        self.setStyleSheet(get_theme_qss(self._dark_mode))

    def _toggle_theme(self) -> None:
        self._dark_mode = not self._dark_mode
        self._apply_theme()
        self._show_status(f"Switched to {'Dark' if self._dark_mode else 'Light'} mode")

    def _show_status(self, msg: str, timeout: int = 5000) -> None:
        self.statusBar().showMessage(msg, timeout)

    def _global_add(self) -> None:
        tab = self.tabs.currentWidget()
        if hasattr(tab, '_add_recruiter'): tab._add_recruiter()
        elif hasattr(tab, '_add_trainee'): tab._add_trainee()
        elif hasattr(tab, '_add_class'): tab._add_class()
        elif hasattr(tab, '_add_exam'): tab._add_exam()
        elif hasattr(tab, '_add_license'): tab._add_license()

    def _global_edit(self) -> None:
        tab = self.tabs.currentWidget()
        if hasattr(tab, '_edit_recruiter'): tab._edit_recruiter()
        elif hasattr(tab, '_edit_trainee'): tab._edit_trainee()
        elif hasattr(tab, '_edit_class'): tab._edit_class()
        elif hasattr(tab, '_edit_exam'): tab._edit_exam()
        elif hasattr(tab, '_edit_license'): tab._edit_license()

    def _global_delete(self) -> None:
        tab = self.tabs.currentWidget()
        if hasattr(tab, '_delete_recruiter'): tab._delete_recruiter()
        elif hasattr(tab, '_delete_trainee'): tab._delete_trainee()
        elif hasattr(tab, '_delete_selected_class'): tab._delete_selected_class()
        elif hasattr(tab, '_delete_selected_exam'): tab._delete_selected_exam()
        elif hasattr(tab, '_delete_license'): tab._delete_license()

    # Removed _attach_dynamic_completer as it's replaced by setup_searchable_combobox

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

run_pyside_app = main

if __name__ == "__main__":
    main()
