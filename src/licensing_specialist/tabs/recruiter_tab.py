# Recruiter tab logic (to be filled in with refactored code)

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QPushButton, QTreeWidget, QAbstractItemView, QHeaderView, QTreeWidgetItem, QFormLayout, QDialog, QMessageBox, QToolBar, QLabel
from PySide6.QtGui import QShortcut, QAction
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtGui import QColor, QBrush
from ..widgets import create_form_section, create_search_bar, create_button_row, create_section_header
from .. import db

def setup_recruiter_tab(main_window):
    # --- Build Recruiters Tab ---
    w = QWidget()
    l = QHBoxLayout(w)

    main_window.rec_name = QLineEdit()
    main_window.rec_email = QLineEdit()
    main_window.rec_phone = QLineEdit()
    main_window.rec_rep = QLineEdit()
    add_btn = QPushButton("Add Recruiter")
    add_btn.clicked.connect(main_window._add_recruiter)
    form_fields = [
        ("Name", main_window.rec_name),
        ("Email", main_window.rec_email),
        ("Phone", main_window.rec_phone),
        ("Rep code (5 alnum)", main_window.rec_rep),
    ]
    left = create_form_section(form_fields)
    left.addWidget(add_btn)

    try:
        main_window._rec_name_completer = main_window._attach_dynamic_completer(main_window.rec_name, lambda p: [r['name'] for r in db.search_recruiters_by_name(p)])
        main_window._rec_name_completer.activated.connect(main_window._on_rec_name_completer)
    except Exception:
        main_window._rec_name_completer = None
    try:
        main_window._rec_rep_completer = main_window._attach_dynamic_completer(main_window.rec_rep, lambda p: [r['rep_code'] for r in db.search_recruiters_by_rep(p)])
        main_window._rec_rep_completer.activated.connect(main_window._on_rec_rep_completer)
    except Exception:
        main_window._rec_rep_completer = None

    l.addLayout(left, 1)

    right = QVBoxLayout()
    main_window.rec_search = create_search_bar("Search recruiters...", main_window._filter_recruiters)
    right.addWidget(main_window.rec_search)

    main_window.rec_table = QTreeWidget()
    main_window.rec_table.setColumnCount(4)
    main_window.rec_table.setHeaderLabels(["ID", "Name", "Email", "Rep"])
    main_window.rec_table.itemSelectionChanged.connect(main_window._on_rec_select)
    main_window.rec_table.setAlternatingRowColors(True)
    main_window.rec_table.setSelectionBehavior(QAbstractItemView.SelectRows)
    try:
        main_window.rec_table.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    except Exception:
        try:
            main_window.rec_table.header().setSectionResizeMode(QHeaderView.Stretch)
        except Exception:
            pass
    right.addWidget(main_window.rec_table)

    btns = create_button_row([
        ("Edit", main_window._edit_recruiter),
        ("Delete", main_window._delete_recruiter),
    ])
    right.addLayout(btns)

    main_window.rec_details = QTreeWidget()
    main_window.rec_details.setHeaderHidden(True)
    right.addWidget(create_section_header("Details"))
    right.addWidget(main_window.rec_details)

    l.addLayout(right, 2)
    main_window.tabs.addTab(w, "Recruiters")
    main_window._refresh_recruiters()
