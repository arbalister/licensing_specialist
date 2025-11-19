# License tab logic (to be filled in with refactored code)

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QComboBox, QPushButton, QListWidget, QTreeWidget, QTreeWidgetItem, QAbstractItemView, QHeaderView, QDialog, QFormLayout, QMessageBox
from PySide6.QtCore import Qt
from ..widgets import create_form_section, create_button_row, create_section_header
from .. import db

def setup_license_tab(self):
    w = QWidget(); l = QHBoxLayout(w)
    # Use helper for form section
    self.lic_trainee = QComboBox()
    self.lic_trainee.currentIndexChanged.connect(self._update_license_trainee_info)
    self.lic_app = QLineEdit()
    self.lic_approval = QLineEdit()
    self.lic_number = QLineEdit()
    self.lic_status = QLineEdit()
    form_fields = [
        ("Trainee", self.lic_trainee),
        ("Application date", self.lic_app),
        ("Approval date", self.lic_approval),
        ("License number", self.lic_number),
        ("Status", self.lic_status),
    ]
    left = create_form_section(form_fields)
    left.addWidget(QPushButton("Add License", clicked=self._add_license))
    l.addLayout(left, 1)
    right = QVBoxLayout()
    self.lic_list = QListWidget()
    right.addWidget(create_section_header("Licenses"))
    right.addWidget(self.lic_list)
    lic_btns = create_button_row([
        ("Edit", self._edit_license),
        ("Delete", self._delete_license),
    ])
    right.addLayout(lic_btns)
    l.addLayout(right, 2)
    self.tabs.addTab(w, "Licenses")
    self._refresh_license_dropdowns(); self._refresh_licenses()
