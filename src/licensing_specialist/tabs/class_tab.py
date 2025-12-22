from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QComboBox, QPushButton, 
    QListWidget, QTreeWidget, QTreeWidgetItem, QAbstractItemView, QHeaderView, 
    QDialog, QFormLayout, QMessageBox
)
from PySide6.QtCore import Qt
import logging

logger = logging.getLogger(__name__)
from ..widgets import (
    log_and_show_error, create_form_section, create_button_row, 
    create_section_header, ModernProfileView, _load_icon,
    setup_searchable_combobox
)
from .. import db

class ClassTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._build_ui()

    def _build_ui(self) -> None:
        l = QHBoxLayout(self)

        self.class_name = QComboBox(); self.class_start = QLineEdit(); self.class_end = QLineEdit()
        form_fields = [
            ("Class name", self.class_name),
            ("Start date (YYYY-MM-DD)", self.class_start),
            ("End date (YYYY-MM-DD)", self.class_end),
        ]
        left = create_form_section(form_fields)
        add_btn = QPushButton("Add Class")
        add_btn.setIcon(_load_icon("add"))
        add_btn.clicked.connect(self._add_class)
        left.addWidget(add_btn)
        
        left.addWidget(create_section_header("Link trainee to class"))
        self.tc_trainee = QComboBox(); self.tc_class = QComboBox()
        left.addWidget(self.tc_trainee); left.addWidget(self.tc_class)
        link_btn = QPushButton("Link")
        link_btn.setIcon(_load_icon("check"))
        link_btn.clicked.connect(self._link_trainee_class)
        left.addWidget(link_btn)
        l.addLayout(left, 1)

        right = QVBoxLayout()
        self.class_list = QListWidget(); self.class_list.itemSelectionChanged.connect(self._on_class_select)
        right.addWidget(create_section_header("Classes")); right.addWidget(self.class_list)
        class_btns = create_button_row([
            ("Edit", self._edit_class, "edit"),
            ("Delete", self._delete_selected_class, "delete"),
        ])
        right.addLayout(class_btns)
        self.class_details = ModernProfileView()
        right.addWidget(create_section_header("Details")); right.addWidget(self.class_details)
        l.addLayout(right, 2)
        
        self.refresh()

    def refresh(self):
        self._refresh_classes()
        self._refresh_tc_dropdowns()

    def _add_class(self) -> None:
        name = self.class_name.currentText().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Name required")
            return
        try:
            db.add_class(name, self.class_start.text() or None, self.class_end.text() or None)
            self.main_window._show_status(f"Added class: {name}")
            self.main_window._show_status(f"Added class: {name}")
            self.class_name.setCurrentText(""); self.class_start.clear(); self.class_end.clear()
            self.refresh()
        except Exception as exc:
            log_and_show_error(self, "Error", "Failed to add class", exc)

    def _link_trainee_class(self) -> None:
        t_text = self.tc_trainee.currentText()
        c_text = self.tc_class.currentText()
        if not t_text or not c_text:
            QMessageBox.warning(self, "Validation", "Select both trainee and class")
            return
        tid = int(t_text.split(":", 1)[0])
        cid = int(c_text.split(":", 1)[0])
        try:
            db.link_trainee_to_class(tid, cid)
            self.main_window._show_status("Linked trainee to class")
            self.refresh()
            self._on_class_select()
        except Exception as exc:
            log_and_show_error(self, "Error", "Failed to link trainee to class", exc)

    def _refresh_classes(self) -> None:
        self.class_list.clear()
        self._class_rows = db.list_classes()
        
        # Populate Class Searchable Combobox
        class_items = [f"{c['name']} ({c['id']})" for c in self._class_rows]
        setup_searchable_combobox(self.class_name, class_items, self._on_class_name_selected)

        for c in self._class_rows:
            self.class_list.addItem(f"{c['id']}: {c['name']} ({c['start_date'] or '—'})")

    def _on_class_name_selected(self, text: str) -> None:
        if not text or "(" not in text or ")" not in text: return
        try:
            cid_str = text.split("(")[-1].strip(")")
            cid = int(cid_str)
            c = db.class_crud.get(cid)
            if c:
                self.class_start.setText(c['start_date'] or "")
                self.class_end.setText(c['end_date'] or "")
                self.main_window._show_status(f"Loaded details for {c['name']}")
        except Exception as e:
            logger.error(f"Error filling class details: {e}")

    def _refresh_tc_dropdowns(self) -> None:
        trainees = [f"{t['id']}: {t['last_name']}, {t['first_name']}" for t in db.list_trainees()]
        self.tc_trainee.clear(); self.tc_trainee.addItems(trainees)
        classes = [f"{c['id']}: {c['name']}" for c in db.list_classes()]
        self.tc_class.clear(); self.tc_class.addItems(classes)

    def _on_class_select(self) -> None:
        sel = self.class_list.currentRow()
        self.class_details.clear()
        if sel < 0: return
        cid = int(self.class_list.item(sel).text().split(":", 1)[0])
        c = next((x for x in self._class_rows if x['id'] == cid), None)
        if not c: return
        
        self.class_details.add_header(c['name'], f"Class ID: {c['id']}")
        
        info = []
        if c['start_date']: info.append(("Start Date", c['start_date'], "search"))
        if c['end_date']: info.append(("End Date", c['end_date'], "search"))
        if info:
            self.class_details.add_section("Class Schedule", info)
        
        # Link trainees in services/db
        conn = db.get_conn(); cur = conn.cursor()
        cur.execute("SELECT t.* FROM trainee t JOIN trainee_class tc ON t.id = tc.trainee_id WHERE tc.class_id = ? ORDER BY t.last_name", (cid,))
        trainees = cur.fetchall(); conn.close()
        
        if trainees:
            tr_info = []
            for t in trainees:
                tr_info.append((f"{t['last_name']}, {t['first_name']}", f"ID: {t['id']}", "search"))
            self.class_details.add_section("Registered Trainees", tr_info)

    def _edit_class(self) -> None:
        sel = self.class_list.currentRow()
        if sel < 0: return
        cid = int(self.class_list.item(sel).text().split(":", 1)[0])
        c = db.class_crud.get(cid)
        if not c: return
        dlg = QDialog(self); dlg.setWindowTitle(f"Edit Class {cid}")
        form = QFormLayout(dlg)
        name_e = QLineEdit(c['name']); start_e = QLineEdit(c['start_date'] or ''); end_e = QLineEdit(c['end_date'] or '')
        form.addRow("Name", name_e); form.addRow("Start", start_e); form.addRow("End", end_e)
        btns = QHBoxLayout(); save = QPushButton("Save"); delete = QPushButton("Delete"); cancel = QPushButton("Cancel"); btns.addWidget(save); btns.addWidget(delete); btns.addWidget(cancel); form.addRow(btns)

        def do_save():
            try:
                db.update_class(cid, name_e.text(), start_e.text(), end_e.text())
                dlg.accept()
            except Exception as exc:
                log_and_show_error(self, "Error", "Failed to update class", exc)

        def do_delete():
            if QMessageBox.question(self, 'Delete', f'Delete class {cid}?') == QMessageBox.StandardButton.Yes:
                db.delete_class(cid)
                dlg.accept()

        save.clicked.connect(do_save); delete.clicked.connect(do_delete); cancel.clicked.connect(dlg.reject)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _delete_selected_class(self) -> None:
        sel = self.class_list.currentRow()
        if sel < 0: return
        cid = int(self.class_list.item(sel).text().split(":",1)[0])
        if QMessageBox.question(self, 'Delete', f'Delete class {cid}?') == QMessageBox.StandardButton.Yes:
            db.delete_class(cid)
            self.refresh()

def setup_class_tab(main_window):
    tab = ClassTab(main_window)
    main_window.class_tab = tab
    main_window.tabs.addTab(tab, "Classes")
