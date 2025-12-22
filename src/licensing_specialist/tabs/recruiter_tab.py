from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QPushButton, 
    QTreeWidget, QAbstractItemView, QHeaderView, QTreeWidgetItem, 
    QFormLayout, QDialog, QMessageBox, QFileDialog, QComboBox
)
from PySide6.QtCore import Qt
import logging

logger = logging.getLogger(__name__)
from ..widgets import (
    log_and_show_error, create_form_section, create_search_bar, 
    create_button_row, create_section_header, ModernProfileView, _load_icon,
    setup_searchable_combobox
)
from .. import db
from .. import services

class RecruiterTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._build_ui()

    def _build_ui(self) -> None:
        l = QHBoxLayout(self)

        self.rec_name = QComboBox() # Changed to ComboBox
        self.rec_email = QLineEdit()
        self.rec_phone = QLineEdit()
        self.rec_rep = QLineEdit()
        add_btn = QPushButton("Add Recruiter")
        add_btn.setIcon(_load_icon("add"))
        add_btn.clicked.connect(self._add_recruiter)
        form_fields = [
            ("Name", self.rec_name),
            ("Email", self.rec_email),
            ("Phone", self.rec_phone),
            ("Rep code", self.rec_rep),
        ]
        left = create_form_section(form_fields)
        left.addWidget(add_btn)

        # Old completers removed

        l.addLayout(left, 1)

        right = QVBoxLayout()
        self.rec_search = create_search_bar("Search recruiters...", self._filter_recruiters)
        right.addWidget(self.rec_search)

        self.rec_table = QTreeWidget()
        self.rec_table.setColumnCount(4)
        self.rec_table.setHeaderLabels(["ID","Name", "Email", "Rep"])
        self.rec_table.itemSelectionChanged.connect(self._on_rec_select)
        self.rec_table.setAlternatingRowColors(True)
        self.rec_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.rec_table.setSelectionMode(QAbstractItemView.ExtendedSelection) # Added this line
        try:
            self.rec_table.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        except Exception:
            pass
        right.addWidget(self.rec_table)

        btns = create_button_row([
            ("Edit", self._edit_recruiter, "edit"),
            ("Delete", self._delete_recruiter, "delete"),
            ("Export", self._export_recruiters, "export"),
        ])
        right.addLayout(btns)

        self.rec_details = ModernProfileView()
        right.addWidget(create_section_header("Details"))
        right.addWidget(self.rec_details)

        l.addLayout(right, 2)
        self.refresh()

    def refresh(self):
        self._refresh_recruiters()

    def _add_recruiter(self) -> None:
        name = self.rec_name.currentText().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Name is required")
            return
        try:
            db.add_recruiter(name, self.rec_email.text(), self.rec_phone.text(), self.rec_rep.text())
            self.main_window._show_status(f"Added recruiter: {name}")
            self.rec_name.setCurrentText(""); self.rec_email.clear(); self.rec_phone.clear(); self.rec_rep.clear()
            self.refresh()
        except Exception as exc:
            log_and_show_error(self, "Error", "Failed to add recruiter", exc)

    def _refresh_recruiters(self) -> None:
        self.rec_table.clear()
        self._rec_rows = db.list_recruiters()
        
        # Populate Name Searchable Combobox
        rec_items = [f"{r['name']} ({r['id']})" for r in self._rec_rows]
        setup_searchable_combobox(self.rec_name, rec_items, self._on_rec_name_selected)

    def _on_rec_name_selected(self, text: str) -> None:
        if not text or "(" not in text or ")" not in text: return
        try:
            rid_str = text.split("(")[-1].strip(")")
            rid = int(rid_str)
            r = db.get_recruiter(rid)
            if r:
                self.rec_email.setText(r['email'] or "")
                self.rec_phone.setText(r['phone'] or "")
                self.rec_rep.setText(r['rep_code'] or "")
                self.main_window._show_status(f"Loaded details for {r['name']}")
        except Exception as e:
            logger.error(f"Error filling recruiter details: {e}")
        for r in self._rec_rows:
            QTreeWidgetItem(self.rec_table, [str(r['id']), r['name'], r['email'] or '', r['rep_code'] or ''])

    def _filter_recruiters(self) -> None:
        txt = self.rec_search.text().lower()
        for i in range(self.rec_table.topLevelItemCount()):
            item = self.rec_table.topLevelItem(i)
            # Match name or email or rep
            match = any(txt in item.text(col).lower() for col in [1, 2, 3])
            item.setHidden(not match)

    def _on_rec_select(self) -> None:
        sel = self.rec_table.selectedItems()
        self.rec_details.clear()
        if not sel: return
        rid = int(sel[0].text(0))
        r = next((x for x in self._rec_rows if x['id'] == rid), None)
        if not r: return
        
        self.rec_details.add_header(r['name'], f"Recruiter ID: {r['id']}")
        
        info = []
        if r['email']: info.append(("Email", r['email'], "search"))
        if r['phone']: info.append(("Phone", r['phone'], "search"))
        if r['rep_code']: info.append(("Rep Code", r['rep_code'], "box"))
        
        if info:
            self.rec_details.add_section("Contact Information", info)

    def _edit_recruiter(self) -> None:
        sel = self.rec_table.selectedItems()
        if not sel: return
        rid = int(sel[0].text(0))
        r = db.get_recruiter(rid)
        if not r: return
        
        dlg = QDialog(self); dlg.setWindowTitle(f"Edit Recruiter {rid}")
        form = QFormLayout(dlg)
        name_e = QLineEdit(r['name']); email_e = QLineEdit(r['email'] or ''); phone_e = QLineEdit(r['phone'] or ''); rep_e = QLineEdit(r['rep_code'] or '')
        form.addRow("Name", name_e); form.addRow("Email", email_e); form.addRow("Phone", phone_e); form.addRow("Rep code", rep_e)
        btns = QHBoxLayout(); save = QPushButton("Save"); delete = QPushButton("Delete"); cancel = QPushButton("Cancel"); btns.addWidget(save); btns.addWidget(delete); btns.addWidget(cancel); form.addRow(btns)

        def do_save():
            try:
                db.update_recruiter(rid, name_e.text(), email_e.text(), phone_e.text(), rep_e.text())
                dlg.accept()
            except Exception as exc:
                log_and_show_error(self, "Error", "Failed to update recruiter", exc)

        def do_delete():
            if QMessageBox.question(self, 'Delete', f'Delete recruiter {rid}?') == QMessageBox.StandardButton.Yes:
                db.delete_recruiter(rid)
                dlg.accept()

        save.clicked.connect(do_save); delete.clicked.connect(do_delete); cancel.clicked.connect(dlg.reject)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _delete_recruiter(self) -> None:
        selected_items = self.rec_table.selectedItems()
        if not selected_items:
            return
            
        rids = [int(item.text(0)) for item in selected_items]
        count = len(rids)
        msg = f"Are you sure you want to delete {count} selected recruiter(s)?"
        if QMessageBox.question(self, "Delete", msg) == QMessageBox.StandardButton.Yes:
            try:
                for rid in rids:
                    db.delete_recruiter(rid)
                self.main_window._show_status(f"Deleted {count} recruiters.")
                self.refresh()
            except Exception as e:
                log_and_show_error(self, e, "Error deleting recruiters")

    def _export_recruiters(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export Recruiters", "recruiters_export.csv", "CSV Files (*.csv)")
        if not path:
            return
            
        data = services.get_recruiter_export_data()
        if not data:
            QMessageBox.information(self, "Export", "No recruiter data to export.")
            return
            
        if services.export_to_csv(data, path):
            self.main_window._show_status(f"Exported to {path}")
        else:
            QMessageBox.critical(self, "Export", "Failed to export data. Check logs.")

    def _on_rec_name_completer(self, text: str) -> None:
        self.rec_search.setText(text)
        self._filter_recruiters()

    def _on_rec_rep_completer(self, text: str) -> None:
        self.rec_search.setText(text)
        self._filter_recruiters()

def setup_recruiter_tab(main_window):
    tab = RecruiterTab(main_window)
    main_window.recruiter_tab = tab
    main_window.tabs.addTab(tab, "Recruiters")
