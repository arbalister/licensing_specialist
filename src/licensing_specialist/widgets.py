# Shared widgets/utilities for Licensing Specialist

import os
from typing import Optional, List, Tuple, Dict
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QLabel, QFormLayout, QVBoxLayout, QHBoxLayout, QLineEdit, 
    QPushButton, QWidget, QMessageBox, QScrollArea, QFrame, QGridLayout,
    QComboBox, QCompleter
)
from PySide6.QtCore import QTimer, Qt, QObject, QEvent, QStringListModel, QCoreApplication, QSortFilterProxyModel
import logging

logger = logging.getLogger(__name__)

from .styles import SECTION_HEADER_STYLE



def _load_icon(name: str) -> QIcon:
    """Load an icon from the assets directory."""
    base_path = os.path.dirname(__file__)
    icon_path = os.path.join(base_path, "assets", "icons", f"{name}.svg")
    if not os.path.exists(icon_path):
        # Fallback for missing icon or if testing without assets
        return QIcon.fromTheme(name)
    return QIcon(icon_path)


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

class ModernProfileView(QScrollArea):
    """A clean, structured view for entity details (Trainee, License, etc)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setObjectName("ProfileView")
        
        self.content = QWidget()
        self.layout = QVBoxLayout(self.content)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(10)
        self.layout.setAlignment(Qt.AlignTop)
        self.setWidget(self.content)

    def clear(self):
        """Clear all content widgets."""
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def add_header(self, title: str, subtitle: Optional[str] = None):
        header_container = QWidget()
        header_layout = QVBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 10)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: {PRIMARY_COLOR};") # Will be themed
        header_layout.addWidget(title_label)
        
        if subtitle:
            sub_label = QLabel(subtitle)
            sub_label.setStyleSheet("font-size: 10pt; color: #64748b;")
            header_layout.addWidget(sub_label)
            
        self.layout.addWidget(header_container)

    def add_section(self, title: str, items: List[Tuple[str, str, Optional[str]]]):
        """Add a section with a title and list of (label, value, icon_name) tuples."""
        self.layout.addWidget(create_section_header(title))
        
        container = QFrame()
        container.setStyleSheet("background-color: transparent; border: none;")
        grid = QGridLayout(container)
        grid.setContentsMargins(5, 5, 5, 5)
        grid.setHorizontalSpacing(20)
        
        for i, (label_txt, value_txt, icon) in enumerate(items):
            if icon:
                icon_label = QLabel()
                icon_label.setPixmap(_load_icon(icon).pixmap(16, 16))
                grid.addWidget(icon_label, i, 0)
            
            label = QLabel(f"<b>{label_txt}:</b>")
            label.setStyleSheet("color: #64748b;")
            grid.addWidget(label, i, 1)
            
            value = QLabel(value_txt)
            value.setWordWrap(True)
            grid.addWidget(value, i, 2)
            grid.setColumnStretch(2, 1)
            
        self.layout.addWidget(container)

    def add_custom_widget(self, widget: QWidget):
        self.layout.addWidget(widget)

def create_button_row(buttons):
    """buttons: list of (label, slot, optional_icon_name)"""
    layout = QHBoxLayout()
    for item in buttons:
        label = item[0]
        slot = item[1]
        icon_name = item[2] if len(item) > 2 else None
        
        btn = QPushButton(label)
        if icon_name:
            btn.setIcon(_load_icon(icon_name))
        btn.clicked.connect(slot)
        layout.addWidget(btn)
    return layout

def create_search_bar(placeholder, slot, debounce_ms=300):
    search = QLineEdit()
    search.setPlaceholderText(placeholder)
    
    timer = QTimer(search)
    timer.setSingleShot(True)
    timer.timeout.connect(slot)
    
    def on_text_changed():
        timer.start(debounce_ms)
        
    search.textChanged.connect(on_text_changed)
    return search

def create_badge(text: str, badge_style: str) -> QLabel:
    """Create a styled badge label."""
    label = QLabel(text)
    label.setStyleSheet(badge_style)
    label.setAlignment(Qt.AlignCenter)
    return label

def log_and_show_error(parent, title, message, exception=None):
    """Log an error and show a message box to the user."""
    full_msg = f"{message}: {exception}" if exception else message
    logger.error(f"{title}: {full_msg}")
    QMessageBox.critical(parent, title, full_msg)

from PySide6.QtCore import (
    QTimer, Qt, QObject, QEvent, QStringListModel, 
    QCoreApplication, QSortFilterProxyModel
)

class ComboBoxEventFilter(QObject):
    """Ensures the combobox popup closes on mouse release, solving some Linux artifacting."""
    def __init__(self, combobox):
        super().__init__(combobox)
        self.combobox = combobox
        
    def eventFilter(self, watched, event):
        if event.type() == QEvent.MouseButtonRelease:
            if self.combobox.isPopupOpen():
                QTimer.singleShot(10, self.combobox.hidePopup)
        return super().eventFilter(watched, event)

def setup_searchable_combobox(combobox: QComboBox, items: List[str], on_select_callback) -> None:
    """
    Configure a QComboBox to be editable and searchable using a proxy model.
    This avoids QCompleter which is prone to 'ghost' artifacts on some Linux setups.
    """
    combobox.setEditable(True)
    combobox.setInsertPolicy(QComboBox.NoInsert)
    
    # Use a proxy model for filtering the dropdown list
    proxy_model = QSortFilterProxyModel(combobox)
    # Filter on any part of the string
    proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
    
    # Source model contains all items
    source_model = QStringListModel(items, combobox)
    proxy_model.setSourceModel(source_model)
    
    combobox.setModel(proxy_model)
    
    # Ensure the completer is OFF to avoid its problematic popups
    combobox.setCompleter(None)

    # Install event filter on the view to force close on mouse release (User suggestion)
    if not hasattr(combobox, '_event_filter'):
        combobox._event_filter = ComboBoxEventFilter(combobox)
        combobox.view().installEventFilter(combobox._event_filter)

    def on_text_changed(text: str):
        # Update the filter as the user types
        proxy_model.setFilterFixedString(text)
        # If the dropdown isn't showing and they started typing, show it
        if text and not combobox.view().isVisible():
            combobox.showPopup()

    def on_activated(text: str):
        # 1. Hide dropdown immediately
        combobox.hidePopup()
        # 2. Reset the filter so that clicking the arrow next time shows all items
        proxy_model.setFilterFixedString("")
        # 3. Process events to ensure clean UI state
        QCoreApplication.processEvents()
        # 4. Trigger actual business logic
        on_select_callback(text)
        # 5. Blur focus
        combobox.clearFocus()

    # Disconnect previous if exists
    if hasattr(combobox, '_on_activated_conn'):
        try: combobox.textActivated.disconnect(combobox._on_activated_conn)
        except: pass
    if hasattr(combobox, '_on_changed_conn'):
        try: combobox.lineEdit().textChanged.disconnect(combobox._on_changed_conn)
        except: pass

    combobox._on_activated_conn = combobox.textActivated.connect(on_activated)
    combobox._on_changed_conn = combobox.lineEdit().textChanged.connect(on_text_changed)
