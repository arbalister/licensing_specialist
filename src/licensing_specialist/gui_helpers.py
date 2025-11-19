from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QWidget, QComboBox, QTreeWidget, QListWidget, QGroupBox
from typing import List, Tuple, Optional


def create_labeled_input(label: str, widget: QWidget) -> QHBoxLayout:
    layout = QHBoxLayout()
    layout.addWidget(QLabel(label))
    layout.addWidget(widget)
    return layout


def create_button_row(buttons: List[Tuple[str, callable]]) -> QHBoxLayout:
    layout = QHBoxLayout()
    for text, slot in buttons:
        btn = QPushButton(text)
        btn.clicked.connect(slot)
        layout.addWidget(btn)
    return layout


def create_search_bar(placeholder: str, on_text_changed) -> QLineEdit:
    search = QLineEdit()
    search.setPlaceholderText(placeholder)
    search.textChanged.connect(on_text_changed)
    return search


def create_section_header(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet("font-weight: bold; font-size: 12pt; margin-top: 10px;")
    return label


def create_list_section(title: str, widget: QWidget) -> QVBoxLayout:
    layout = QVBoxLayout()
    layout.addWidget(create_section_header(title))
    layout.addWidget(widget)
    return layout


def create_form_section(fields: List[Tuple[str, QWidget]]) -> QVBoxLayout:
    layout = QVBoxLayout()
    for label, widget in fields:
        layout.addLayout(create_labeled_input(label, widget))
    return layout
