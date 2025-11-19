# Class tab logic (to be filled in with refactored code)

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QComboBox, QPushButton, QListWidget, QTreeWidget, QTreeWidgetItem, QAbstractItemView, QHeaderView, QDialog, QFormLayout, QMessageBox
from PySide6.QtCore import Qt
from ..widgets import create_form_section, create_button_row, create_section_header
from .. import db

def setup_class_tab(self):
    w = QWidget(); l = QHBoxLayout(w)
    # Use helper for form section
    self.class_name = QLineEdit(); self.class_start = QLineEdit(); self.class_end = QLineEdit()
    form_fields = [
        ("Class name", self.class_name),
        ("Start date (YYYY-MM-DD)", self.class_start),
        ("End date (YYYY-MM-DD)", self.class_end),
    ]
    left = create_form_section(form_fields)
    left.addWidget(QPushButton("Add Class", clicked=self._add_class))
    left.addWidget(create_section_header("Link trainee to class"))
    self.tc_trainee = QComboBox(); self.tc_class = QComboBox()
    left.addWidget(self.tc_trainee); left.addWidget(self.tc_class)
    left.addWidget(QPushButton("Link", clicked=self._link_trainee_class))
    l.addLayout(left, 1)

    right = QVBoxLayout()
    self.class_list = QListWidget(); self.class_list.itemSelectionChanged.connect(self._on_class_select)
    right.addWidget(create_section_header("Classes")); right.addWidget(self.class_list)
    class_btns = create_button_row([
        ("Edit", self._edit_class),
        ("Delete", self._delete_selected_class),
    ])
    right.addLayout(class_btns)
    self.class_details = QTreeWidget(); self.class_details.setHeaderHidden(True)
    right.addWidget(create_section_header("Details")); right.addWidget(self.class_details)
    l.addLayout(right, 2)
    self.tabs.addTab(w, "Classes")
    self._refresh_classes(); self._refresh_tc_dropdowns()
