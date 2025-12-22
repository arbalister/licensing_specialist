from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QComboBox, QPushButton, 
    QTreeWidget, QAbstractItemView, QHeaderView, QTreeWidgetItem, QDialog, 
    QFormLayout, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
import logging

logger = logging.getLogger(__name__)
logger = logging.getLogger(__name__)
from ..widgets import (
    log_and_show_error, create_form_section, create_button_row, 
    create_section_header, create_search_bar, create_badge, ModernProfileView,
    setup_searchable_combobox
)
from ..styles import BADGE_SUCCESS, BADGE_ERROR, BADGE_WARNING, BADGE_INFO
from .. import db
from .. import services

class TraineeTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._build_ui()

    def _build_ui(self) -> None:
        l = QHBoxLayout(self)

        self.tr_first = QLineEdit()
        self.tr_last = QComboBox() # Changed to ComboBox
        self.tr_dob = QLineEdit()
        self.tr_rep = QLineEdit()
        self.tr_recruiter = QComboBox()
        form_fields = [
            ("First name", self.tr_first),
            ("Last name", self.tr_last),
            ("IBA Date (YYYY-MM-DD)", self.tr_dob),
            ("Rep code (5)", self.tr_rep),
            ("Recruiter", self.tr_recruiter),
        ]
        left = create_form_section(form_fields)
        btns = create_button_row([
            ("Add Trainee", self._add_trainee, "add"),
            ("Edit Trainee", self._edit_trainee, "edit"),
            ("Delete Trainee", self._delete_trainee, "delete"),
            ("Export", self._export_trainees, "export"),
        ])
        left.addLayout(btns)
        l.addLayout(left, 1)

        right = QVBoxLayout()
        self.tr_search = create_search_bar("Search trainees...", self._filter_trainees)
        right.addWidget(self.tr_search)

        self.tr_table = QTreeWidget()
        self.tr_table.setColumnCount(4)
        self.tr_table.setHeaderLabels(["ID", "Last", "First", "Recruiter"])
        self.tr_table.itemSelectionChanged.connect(self._on_tr_select)
        self.tr_table.setAlternatingRowColors(True)
        self.tr_table.setSelectionMode(QAbstractItemView.ExtendedSelection) # Added this line
        self.tr_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        try:
            self.tr_table.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        except Exception:
            pass
        right.addWidget(create_section_header("Trainees"))
        right.addWidget(self.tr_table)
        right.addWidget(create_section_header("Details"))
        self.tr_details = ModernProfileView()
        right.addWidget(self.tr_details)

        l.addLayout(right, 2)
        
        # Old completer logic removed

        self.refresh()

    def refresh(self):
        self._refresh_tr_dropdowns()
        self._refresh_trainees()

    def _add_trainee(self) -> None:
        first = self.tr_first.text().strip()
        last = self.tr_last.currentText().strip()
        if not first or not last:
            QMessageBox.warning(self, "Validation", "First and Last name required")
            return
        rec_id = None
        if self.tr_recruiter.currentText():
            rec_id = int(self.tr_recruiter.currentText().split(":", 1)[0])
        try:
            db.add_trainee(first, last, self.tr_dob.text().strip() or None, rec_id, self.tr_rep.text().strip() or None)
            self.main_window._show_status(f"Added trainee: {first} {last}")
            self.main_window._show_status(f"Added trainee: {first} {last}")
            self.tr_first.clear(); self.tr_last.setCurrentText(""); self.tr_dob.clear(); self.tr_rep.clear()
            self.refresh()
        except Exception as exc:
            log_and_show_error(self, "Error", "Failed to add trainee", exc)

    def _refresh_tr_dropdowns(self) -> None:
        recs = [f"{r['id']}: {r['name']}" for r in db.list_recruiters()]
        self.tr_recruiter.clear()
        self.tr_recruiter.addItem("")
        self.tr_recruiter.addItems(recs)
        
        # Populate Last Name Searchable Combobox
        # Using format "Last, First (ID)" for uniqueness and searchability
        trainees = db.list_trainees()
        tr_items = [f"{t['last_name']}, {t['first_name']} ({t['id']})" for t in trainees]
        setup_searchable_combobox(self.tr_last, tr_items, self._on_tr_last_selected)

    def _on_tr_last_selected(self, text: str) -> None:
        """Fill form when existing trainee is selected."""
        if not text or "(" not in text or ")" not in text:
            return # Likely a new entry being typed
            
        try:
            tid_str = text.split("(")[-1].strip(")")
            tid = int(tid_str)
            t = db.get_trainee(tid)
            if t:
                self.tr_first.setText(t['first_name'])
                self.tr_dob.setText(t['dob'] or "")
                self.tr_rep.setText(t['rep_code'] or "")
                
                # Select recruiter if applicable
                if t['recruiter_id']:
                    r = db.get_recruiter(t['recruiter_id'])
                    if r:
                        self.tr_recruiter.setCurrentText(f"{r['id']}: {r['name']}")
                else:
                    self.tr_recruiter.setCurrentIndex(0)
                        
                self.main_window._show_status(f"Loaded details for {t['first_name']} {t['last_name']}")
                # Optional: trigger selection in the table too?
                # For now just filling the "Add/Edit" form fields as requested.
        except Exception as e:
            logger.error(f"Error filling trainee details: {e}")

    def _refresh_trainees(self) -> None:
        self.tr_table.clear()
        self._tr_rows = db.list_trainees()
        for t in self._tr_rows:
            rec_name = "—"
            if t['recruiter_id']:
                r = db.get_recruiter(t['recruiter_id'])
                if r: rec_name = r['name']
            QTreeWidgetItem(self.tr_table, [str(t['id']), t['last_name'], t['first_name'], rec_name])

    def _filter_trainees(self) -> None:
        txt = self.tr_search.text().lower()
        for i in range(self.tr_table.topLevelItemCount()):
            item = self.tr_table.topLevelItem(i)
            match = any(txt in item.text(col).lower() for col in [1, 2, 3])
            item.setHidden(not match)

    def _on_tr_select(self) -> None:
        sel = self.tr_table.selectedItems()
        self.tr_details.clear()
        if not sel: return
        # If multiple items are selected, only show details for the first one
        tid = int(sel[0].text(0))
        t = db.get_trainee(tid)
        if not t: return
        
        self.tr_details.add_header(f"{t['first_name']} {t['last_name']}", f"Trainee ID: {t['id']}")
        
        basic_info = []
        if t['dob']: basic_info.append(("IBA Date", t['dob'], "search"))
        if t['rep_code']: basic_info.append(("Rep Code", t['rep_code'], "box"))
        
        if t['recruiter_id']:
            r = db.get_recruiter(t['recruiter_id'])
            if r: basic_info.append(("Recruiter", r['name'], "search"))
            
        if basic_info:
            self.tr_details.add_section("Basic Information", basic_info)

        # Status Badges
        try:
            modules_complete = services.all_practice_modules_complete(tid)
            conn = db.get_conn(); cur = conn.cursor()
            cur.execute("SELECT MIN(exam_date) as first_date FROM exam WHERE trainee_id = ? AND is_practice = 0", (tid,))
            first_exam_row = cur.fetchone(); conn.close()
            first_exam_date = first_exam_row['first_date'] if first_exam_row else None
            seewhy = services.check_seewhy_guarantee(tid, first_exam_date) if first_exam_date else False
            
            badge_container = QWidget()
            badge_layout = QHBoxLayout(badge_container)
            badge_layout.setContentsMargins(0, 5, 0, 5)
            
            pe_color = BADGE_SUCCESS if modules_complete else BADGE_ERROR
            pe_text = "Practice: Complete" if modules_complete else "Practice: Pending"
            badge_layout.addWidget(create_badge(pe_text, pe_color))
            
            if seewhy:
                badge_layout.addWidget(create_badge("SeeWhy Qualified", BADGE_SUCCESS))
            
            badge_layout.addStretch()
            self.tr_details.add_section("Status", []) # Just the header
            self.tr_details.add_custom_widget(badge_container)
        except Exception:
            pass

        # Classes
        conn = db.get_conn(); cur = conn.cursor()
        cur.execute("SELECT c.* FROM class c JOIN trainee_class tc ON c.id = tc.class_id WHERE tc.trainee_id = ? ORDER BY c.start_date", (tid,))
        classes_info = []
        for c in cur.fetchall():
            classes_info.append((c['name'], f"{c['start_date'] or '—'} to {c['end_date'] or '—'}", "box"))
        if classes_info:
            self.tr_details.add_section("Classes", classes_info)
        
        # Exams
        cur.execute("SELECT * FROM exam WHERE trainee_id = ? ORDER BY exam_date DESC", (tid,))
        exams_info = []
        for e in cur.fetchall():
            mod = f"[{e['module']}] " if 'module' in e.keys() and e['module'] else ''
            pass_str = "Pass" if e['passed'] == 1 else "Fail" if e['passed'] == 0 else "—"
            exams_info.append((f"{e['exam_date'] or '—'}", f"{mod}{pass_str} (Score: {e['score'] or '—'})", "edit"))
        if exams_info:
            self.tr_details.add_section("Exams", exams_info)
            
        # Licenses
        cur.execute("SELECT * FROM license WHERE trainee_id = ? ORDER BY application_submitted_date DESC", (tid,))
        lic_info = []
        for l in cur.fetchall():
            lic_info.append((f"{l['application_submitted_date'] or '—'}", f"Status: {l['status'] or '—'}", "check"))
        if lic_info:
            self.tr_details.add_section("Licenses", lic_info)
        conn.close()

    def _edit_trainee(self) -> None:
        sel = self.tr_table.selectedItems()
        if not sel: return
        # Only allow editing of a single trainee
        if len(sel) > 1:
            QMessageBox.information(self, "Edit Trainee", "Please select only one trainee to edit.")
            return
        tid = int(sel[0].text(0))
        t = db.get_trainee(tid)
        if not t: return
        
        dlg = QDialog(self); dlg.setWindowTitle(f"Edit Trainee {tid}")
        form = QFormLayout(dlg)
        first_e = QLineEdit(t['first_name']); last_e = QLineEdit(t['last_name']); dob_e = QLineEdit(t['dob'] or ''); rep_e = QLineEdit(t['rep_code'] or '')
        rec_cb = QComboBox()
        recs = [f"{r['id']}: {r['name']}" for r in db.list_recruiters()]
        rec_cb.addItem("")
        rec_cb.addItems(recs)
        if t['recruiter_id']:
            r = db.get_recruiter(t['recruiter_id'])
            if r: rec_cb.setCurrentText(f"{r['id']}: {r['name']}")
            
        form.addRow("First Name", first_e); form.addRow("Last Name", last_e); form.addRow("IBA Date", dob_e); form.addRow("Rep Code", rep_e); form.addRow("Recruiter", rec_cb)
        btns = QHBoxLayout(); save = QPushButton("Save"); cancel = QPushButton("Cancel"); btns.addWidget(save); btns.addWidget(cancel); form.addRow(btns)

        def do_save():
            rec_id_new = None
            if rec_cb.currentText(): rec_id_new = int(rec_cb.currentText().split(":", 1)[0])
            try:
                db.update_trainee(tid, first_e.text(), last_e.text(), dob_e.text(), rec_id_new, rep_e.text())
                dlg.accept()
            except Exception as exc:
                log_and_show_error(self, "Error", "Failed to update trainee", exc)

        save.clicked.connect(do_save); cancel.clicked.connect(dlg.reject)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _delete_trainee(self) -> None:
        selected_items = self.tr_table.selectedItems()
        if not selected_items:
            return
            
        tids = [int(item.text(0)) for item in selected_items]
        count = len(tids)
        msg = f"Are you sure you want to delete {count} selected trainee(s)?"
        if QMessageBox.question(self, "Delete", msg) == QMessageBox.StandardButton.Yes:
            try:
                for tid in tids:
                    db.delete_trainee(tid)
                self.main_window._show_status(f"Deleted {count} trainees.")
                self.refresh()
            except Exception as e:
                log_and_show_error(self, "Error", "Failed to delete trainees", e)

    def _on_tr_name_completer(self, text: str) -> None:
        self.tr_search.setText(text)
        self._filter_trainees()

    def _on_tr_rep_completer(self, text: str) -> None:
        self.tr_search.setText(text)
        self._filter_trainees()

    def _export_trainees(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export Trainees", "trainees_export.csv", "CSV Files (*.csv)")
        if not path:
            return
            
        data = services.get_trainee_export_data()
        if not data:
            QMessageBox.information(self, "Export", "No trainee data to export.")
            return
            
        if services.export_to_csv(data, path):
            self.main_window._show_status(f"Exported to {path}")
        else:
            QMessageBox.critical(self, "Export", "Failed to export data. Check logs.")

def setup_trainee_tab(main_window):
    tab = TraineeTab(main_window)
    main_window.trainee_tab = tab
    main_window.tabs.addTab(tab, "Trainees")
