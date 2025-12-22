from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QScrollArea, QFrame, QPushButton
)
from PySide6.QtCore import Qt
from ..widgets import create_section_header, _load_icon
from .. import services
from ..styles import (
    CARD_STYLE, CARD_TITLE_STYLE, CARD_VALUE_STYLE,
    ACTIVITY_ITEM_STYLE, ACTIVITY_TYPE_STYLE, 
    ACTIVITY_LABEL_STYLE, ACTIVITY_TIME_STYLE
)

class DashboardCard(QFrame):
    """A reusable card for the dashboard summary stats."""
    def __init__(self, title: str, value: str, parent=None):
        super().__init__(parent)
        self.setObjectName("DashboardCard")
        # Removed hardcoded self.setStyleSheet(CARD_STYLE) as it's now in global QSS
        
        layout = QVBoxLayout(self)
        
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(CARD_TITLE_STYLE)
        self.title_label.setAlignment(Qt.AlignCenter)
        
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(CARD_VALUE_STYLE)
        self.value_label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)

class ActivityItem(QWidget):
    """A single item in the recent activity feed."""
    def __init__(self, activity_type: str, label: str, timestamp: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(ACTIVITY_ITEM_STYLE)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        type_label = QLabel(activity_type.upper())
        type_label.setStyleSheet(ACTIVITY_TYPE_STYLE)
        
        desc_label = QLabel(label)
        desc_label.setStyleSheet(ACTIVITY_LABEL_STYLE)
        desc_label.setWordWrap(True)
        
        time_label = QLabel(timestamp if timestamp else "Recent")
        time_label.setStyleSheet(ACTIVITY_TIME_STYLE)
        time_label.setAlignment(Qt.AlignRight)
        
        layout.addWidget(type_label)
        layout.addWidget(desc_label)
        layout.addWidget(time_label)

class DashboardTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._build_ui()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Header
        header = create_section_header("Dashboard Overview")
        main_layout.addWidget(header)

        # Stats Grid
        self.stats_grid = QGridLayout()
        self.stats_grid.setSpacing(15)
        main_layout.addLayout(self.stats_grid)

        # Module Performance Section (NEW)
        self.module_stats_layout = QVBoxLayout()
        self.module_stats_layout.addWidget(create_section_header("Module Performance (Pass Rates)"))
        self.module_stats_grid = QGridLayout()
        self.module_stats_grid.setSpacing(10)
        self.module_stats_layout.addLayout(self.module_stats_grid)
        main_layout.addLayout(self.module_stats_layout)

        # Bottom row: Recent Activity & Shortcuts
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(20)
        
        # Recent Activity (Left)
        activity_container = QVBoxLayout()
        activity_container.addWidget(create_section_header("Recent Activity"))
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.activity_list = QWidget()
        self.activity_layout = QVBoxLayout(self.activity_list)
        self.activity_layout.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.activity_list)
        
        activity_container.addWidget(self.scroll)
        bottom_layout.addLayout(activity_container, 2)

        # Shortcuts (Right)
        shortcuts_container = QVBoxLayout()
        shortcuts_container.setAlignment(Qt.AlignTop)
        shortcuts_container.addWidget(create_section_header("Quick Actions"))
        
        self.add_trainee_btn = QPushButton("Add New Trainee")
        self.add_trainee_btn.setIcon(_load_icon("add"))
        self.add_trainee_btn.clicked.connect(lambda: self.main_window.tabs.setCurrentIndex(2)) # Index 2 is Trainees
        
        self.add_exam_btn = QPushButton("Record Exam Result")
        self.add_exam_btn.setIcon(_load_icon("edit"))
        self.add_exam_btn.clicked.connect(lambda: self.main_window.tabs.setCurrentIndex(4)) # Index 4 is Exams
        
        shortcuts_container.addWidget(self.add_trainee_btn)
        shortcuts_container.addWidget(self.add_exam_btn)
        
        bottom_layout.addLayout(shortcuts_container, 1)
        
        main_layout.addLayout(bottom_layout, 1)

        self.refresh()

    def refresh(self):
        """Update stats and activity feed."""
        # 1. Clear and rebuild stats grid
        for i in reversed(range(self.stats_grid.count())): 
            self.stats_grid.itemAt(i).widget().setParent(None)

        stats = services.get_dashboard_stats()
        if stats:
            self.stats_grid.addWidget(DashboardCard("Total Trainees", str(stats.get("total_trainees", 0))), 0, 0)
            self.stats_grid.addWidget(DashboardCard("Pending Licenses", str(stats.get("pending_licenses", 0))), 0, 1)
            self.stats_grid.addWidget(DashboardCard("Passes (30d)", str(stats.get("recent_passes", 0))), 0, 2)
            self.stats_grid.addWidget(DashboardCard("Ready for Prov.", str(stats.get("ready_for_provincial", 0))), 0, 3)

        # 1b. Clear and rebuild module stats
        for i in reversed(range(self.module_stats_grid.count())):
            self.module_stats_grid.itemAt(i).widget().setParent(None)
            
        mod_stats = services.get_exam_module_stats()
        for idx, ms in enumerate(mod_stats):
            col = idx % 4
            row = idx // 4
            # Reuse DashboardCard for consistent styling
            card = DashboardCard(ms['module'], ms['pass_rate'])
            self.module_stats_grid.addWidget(card, row, col)

        # 2. Clear and rebuild activity list
        for i in reversed(range(self.activity_layout.count())): 
            self.activity_layout.itemAt(i).widget().setParent(None)

        activities = services.get_recent_activity()
        for act in activities:
            self.activity_layout.addWidget(ActivityItem(act['type'], act['label'], act['timestamp']))

def setup_dashboard_tab(main_window):
    tab = DashboardTab(main_window)
    main_window.dashboard_tab = tab
    main_window.tabs.insertTab(0, tab, "🏠 Dashboard")
