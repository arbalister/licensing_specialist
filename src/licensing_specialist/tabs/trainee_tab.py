# Trainee tab logic (to be filled in with refactored code)

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QComboBox, QPushButton, QTreeWidget, QAbstractItemView, QHeaderView, QTreeWidgetItem, QDialog, QFormLayout, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from ..widgets import create_form_section, create_button_row, create_section_header, create_search_bar
from .. import db

def setup_trainee_tab(self):
    w = QWidget()
    l = QHBoxLayout(w)

    # Use helper for form section
    self.tr_first = QLineEdit()
    self.tr_last = QLineEdit()
    self.tr_dob = QLineEdit()
    self.tr_rep = QLineEdit()
    self.tr_recruiter = QComboBox()
    form_fields = [
        ("First name", self.tr_first),
        ("Last name", self.tr_last),
        ("IBA Date (YYYY-MM-DD)", self.tr_dob),
        ("Rep code (5 alnum)", self.tr_rep),
        ("Recruiter", self.tr_recruiter),
    ]
    left = create_form_section(form_fields)
    btns = create_button_row([
        ("Add Trainee", self._add_trainee),
        ("Edit Trainee", self._edit_trainee),
        ("Delete Trainee", self._delete_trainee),
    ])
    left.addLayout(btns)
    l.addLayout(left, 1)

    right = QVBoxLayout()
    self.tr_search = create_search_bar("Search trainees...", self._filter_trainees)
    right.addWidget(self.tr_search)

    self.tr_table = QTreeWidget()
    self.tr_table.setColumnCount(4)
    self.tr_table.setHeaderLabels(["ID", "Last", "First", "Recruiter"])
    self.tr_table.itemSelectionChanged.connect(self._on_tr_select)
    self.tr_table.setAlternatingRowColors(True)
    self.tr_table.setSelectionBehavior(QAbstractItemView.SelectRows)
    try:
        self.tr_table.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    except Exception:
        try:
            self.tr_table.header().setSectionResizeMode(QHeaderView.Stretch)
        except Exception:
            pass
    right.addWidget(create_section_header("Trainees"))
    right.addWidget(self.tr_table)
    right.addWidget(create_section_header("Details"))
    self.tr_details = QTreeWidget()
    self.tr_details.setHeaderHidden(True)
    right.addWidget(self.tr_details)

    l.addLayout(right, 2)
    self.tabs.addTab(w, "Trainees")
    self._refresh_tr_dropdowns()
    self._refresh_trainees()
    # setup simple completers for trainee name/rep fields
    try:
        self._tr_name_completer = self._attach_dynamic_completer(self.tr_first, lambda p: [f"{t['first_name']} {t['last_name']}" for t in db.search_trainees_by_name(p)])
        self._tr_name_completer.activated.connect(self._on_tr_name_completer)
    except Exception:
        self._tr_name_completer = None
    try:
        self._tr_rep_completer = self._attach_dynamic_completer(self.tr_rep, lambda p: [t['rep_code'] for t in db.search_trainees_by_rep(p)])
        self._tr_rep_completer.activated.connect(self._on_tr_rep_completer)
    except Exception:
        self._tr_rep_completer = None
