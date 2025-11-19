# Shared widgets/utilities for Licensing Specialist

from PySide6.QtWidgets import QLabel, QFormLayout, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QWidget
from .styles import SECTION_HEADER_STYLE



def create_section_header(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet(SECTION_HEADER_STYLE)
    return label

def create_form_section(fields):
    layout = QFormLayout()
    for label, widget in fields:
        layout.addRow(label, widget)
    container = QVBoxLayout()
    container.addLayout(layout)
    return container

def create_button_row(buttons):
    layout = QHBoxLayout()
    for label, slot in buttons:
        btn = QPushButton(label)
        btn.clicked.connect(slot)
        layout.addWidget(btn)
    return layout

def create_search_bar(placeholder, slot):
    search = QLineEdit()
    search.setPlaceholderText(placeholder)
    search.textChanged.connect(slot)
    return search
