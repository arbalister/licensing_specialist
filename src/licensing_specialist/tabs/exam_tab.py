# Exam tab logic (to be filled in with refactored code)

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QComboBox, QPushButton, QListWidget, QTreeWidget, QTreeWidgetItem, QAbstractItemView, QHeaderView, QDialog, QFormLayout, QMessageBox, QCheckBox, QTextEdit, QLabel, QGroupBox
from PySide6.QtCore import Qt
from ..widgets import create_form_section, create_button_row, create_section_header
from .. import db

def setup_exam_tab(self):
    w = QWidget()
    l = QHBoxLayout(w)
    # Use helper for form section
    self.exam_trainee = QComboBox()
    self.exam_class = QComboBox()
    self.exam_module = QComboBox()
    self.exam_module.addItems(["", "Life", "A&S", "Seg Funds", "Ethics"])
    self.is_practice = QCheckBox("Practice exam")
    self.exam_date = QLineEdit()
    self.exam_result = QComboBox()
    self.exam_result.addItems(["Unknown", "Pass", "Fail"])
    self.exam_notes = QTextEdit()
    form_fields = [
        ("Trainee", self.exam_trainee),
        ("Class (optional)", self.exam_class),
        ("Module", self.exam_module),
        ("", self.is_practice),
        ("Exam date (YYYY-MM-DD)", self.exam_date),
        ("Result", self.exam_result),
        ("Notes", self.exam_notes),
    ]
    left = create_form_section(form_fields)
    left.addWidget(QPushButton("Add Exam", clicked=self._add_exam))
    l.addLayout(left, 1)

    right = QVBoxLayout()
    self.exam_list = QListWidget()
    right.addWidget(create_section_header("Exams"))
    right.addWidget(self.exam_list)
    exam_btns = create_button_row([
        ("Edit", self._edit_exam),
        ("Delete", self._delete_selected_exam),
    ])
    right.addLayout(exam_btns)
    right.addWidget(create_section_header("Provincial Exam Data for Selected Trainee"))
    self.prov_exam_info = QTreeWidget()
    self.prov_exam_info.setHeaderLabels(["Exam Date", "Module", "Score", "Result", "Notes"])
    self.prov_exam_info.setAlternatingRowColors(True)
    self.prov_exam_info.setRootIsDecorated(False)
    right.addWidget(self.prov_exam_info)
    l.addLayout(right, 2)
    self.tabs.addTab(w, "Exams")
    self._refresh_exam_dropdowns()
    self._refresh_exams()
    # Add practice exam status panel
    self._build_practice_exam_status_panel()
    # Connect trainee selection to info panel update (moved from _build)
    self.exam_trainee.currentIndexChanged.connect(self._update_prov_exam_info)
    self._update_prov_exam_info()
