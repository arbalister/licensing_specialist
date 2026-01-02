# Centralized style definitions for the application

# Refined Color Palette tokens
LIGHT_BG = "#f8fafc"
DARK_BG = "#1e293b"
PRIMARY_COLOR = "#3b82f6"
SUCCESS_COLOR = "#10b981"
ERROR_COLOR = "#ef4444"
WARNING_COLOR = "#f59e0b"
TEXT_LIGHT = "#2c3e50"
TEXT_DARK = "#f1f2f6"

SECTION_HEADER_STYLE = f"font-weight: bold; font-size: 14pt; margin-top: 2px; margin-bottom: 2px; color: {PRIMARY_COLOR};"

# Common QSS fragments
GLOBAL_STYLES = """
    QMainWindow {{
        background-color: {bg_color};
        font-family: 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
        font-size: 10pt;
    }}
    
    /* Modern Scrollbars */
    QScrollBar:vertical {{
        border: none;
        background: transparent;
        width: 10px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {border_color};
        min-height: 20px;
        border-radius: 5px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {primary};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    
    QScrollBar:horizontal {{
        border: none;
        background: transparent;
        height: 10px;
        margin: 0px;
    }}
    QScrollBar::handle:horizontal {{
        background: {border_color};
        min-width: 20px;
        border-radius: 5px;
        margin: 2px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {primary};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}
    QTabWidget::pane {{
        border: 1px solid {border_color};
        background-color: {bg_color};
        border-radius: 4px;
    }}
    QTabBar::tab {{
        background-color: {tab_bg};
        padding: 10px 15px;
        margin-right: 2px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        color: {tab_text};
    }}
    QTabBar::tab:selected {{
        background-color: {card_bg};
        color: {primary};
        border-bottom: 2px solid {primary};
    }}
    QLineEdit, QComboBox, QTextEdit, QTreeWidget, QListWidget {{
        padding: 8px;
        border: 1px solid {border_color};
        border-radius: 6px;
        background-color: {card_bg};
        color: {text_color};
    }}
    QTreeWidget, QListWidget {{
        alternate-background-color: {alt_row};
    }}
    QLineEdit:focus, QComboBox:focus {{
        border: 1px solid {primary};
    }}
    QPushButton {{
        padding: 8px 16px;
        border-radius: 6px;
        font-weight: bold;
        background-color: {tab_bg};
        color: {text_color};
    }}
    QPushButton:hover {{
        background-color: {alt_row};
    }}
    
    /* Dashboard Cards */
    QFrame#DashboardCard {{
        background-color: {card_bg};
        border: 1px solid {border_color};
        border-radius: 12px;
    }}
    QFrame#DashboardCard:hover {{
        border: 1px solid {primary};
    }}
"""

def get_theme_qss(dark_mode=False):
    bg = DARK_BG if dark_mode else LIGHT_BG
    text = TEXT_DARK if dark_mode else TEXT_LIGHT
    card_bg = "#2d3748" if dark_mode else "white"
    border = "#4a5568" if dark_mode else "#dcdde1"
    tab_bg = "#334155" if dark_mode else "#f1f2f6"
    tab_text = "#94a3b8" if dark_mode else "#7f8c8d"
    alt_row = "#1a202c" if dark_mode else "#f8fafc"
    
    return GLOBAL_STYLES.format(
        bg_color=bg, 
        text_color=text, 
        primary=PRIMARY_COLOR,
        card_bg=card_bg,
        border_color=border,
        tab_bg=tab_bg,
        tab_text=tab_text,
        alt_row=alt_row
    )

# Dashboard Labels (passed as inline styles for now)
CARD_STYLE = f"background-color: white; border-radius: 12px; border: 1px solid #e2e8f0;" # Fallback/Inline
CARD_TITLE_STYLE = "font-size: 10pt; color: #94a3b8; font-weight: 600;"
CARD_VALUE_STYLE = f"font-size: 20pt; color: {PRIMARY_COLOR}; font-weight: 800;"

# Activity/Table Badge Styles
BADGE_BASE = "padding: 4px 10px; border-radius: 12px; font-weight: bold; font-size: 9pt; color: white;"
BADGE_SUCCESS = f"{BADGE_BASE} background-color: {SUCCESS_COLOR};"
BADGE_WARNING = f"{BADGE_BASE} background-color: {WARNING_COLOR};"
BADGE_ERROR = f"{BADGE_BASE} background-color: {ERROR_COLOR};"
BADGE_INFO = f"{BADGE_BASE} background-color: {PRIMARY_COLOR};"

ACTIVITY_ITEM_STYLE = "border-bottom: 1px solid #4a5568; padding: 0px;" # Need to make this dynamic too?
ACTIVITY_TYPE_STYLE = f"font-size: 8pt; font-weight: bold; color: {PRIMARY_COLOR};"
ACTIVITY_LABEL_STYLE = "font-size: 10pt;"
ACTIVITY_TIME_STYLE = "font-size: 8pt; color: #94a3b8;"

# Legacy compatibility (optional, can refactor callers later)
BUTTON_SUCCESS_STYLE = f"background-color: {SUCCESS_COLOR}; color: white; border-radius: 4px;"
BUTTON_ERROR_STYLE = f"background-color: {ERROR_COLOR}; color: white; border-radius: 4px;"
BUTTON_INFO_STYLE = f"background-color: {PRIMARY_COLOR}; color: white; border-radius: 4px;"
