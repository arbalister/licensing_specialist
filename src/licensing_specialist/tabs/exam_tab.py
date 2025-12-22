from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QComboBox, QPushButton, 
    QListWidget, QTreeWidget, QTreeWidgetItem, QDialog, QFormLayout, 
    QMessageBox, QCheckBox, QTextEdit, QGroupBox, QLabel
)
from PySide6.QtCore import Qt
import logging

logger = logging.getLogger(__name__)
from ..widgets import (
    log_and_show_error, create_form_section, create_button_row, 
    create_section_header, _load_icon, create_badge,
    setup_searchable_combobox
)
from ..styles import BADGE_SUCCESS, BADGE_ERROR
from .. import db
from .. import services

class ExamTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._build_ui()

    def _build_ui(self) -> None:
        l = QHBoxLayout(self)
        
        # Form
        self.exam_trainee = QComboBox()
        self.exam_trainee.currentIndexChanged.connect(self._update_prov_exam_info)
        self.exam_class = QComboBox()
        self.exam_module = QComboBox()
        self.exam_module.addItems(["", "Life", "A&S", "Seg Funds", "Ethics"])
        self.is_practice = QCheckBox("Practice exam")
        self.exam_date = QLineEdit()
        self.exam_result = QComboBox()
        self.exam_result.addItems(["Unknown", "Pass", "Fail"])
        self.exam_notes = QTextEdit()
        
        form_fields = [
            ("Trainee", self.exam_trainee),
            ("Class (optional)", self.exam_class),
            ("Module", self.exam_module),
            ("", self.is_practice),
            ("Exam date (YYYY-MM-DD)", self.exam_date),
            ("Result", self.exam_result),
            ("Notes", self.exam_notes),
        ]
        left = create_form_section(form_fields)
        add_btn = QPushButton("Add Exam")
        add_btn.setIcon(_load_icon("add"))
        add_btn.clicked.connect(self._add_exam)
        left.addWidget(add_btn)
        l.addLayout(left, 1)

        right = QVBoxLayout()
        self.exam_list = QListWidget()
        right.addWidget(create_section_header("Exams"))
        right.addWidget(self.exam_list)
        exam_btns = create_button_row([
            ("Edit", self._edit_exam, "edit"),
            ("Delete", self._delete_selected_exam, "delete"),
        ])
        right.addLayout(exam_btns)
        
        # Provincial info
        right.addWidget(create_section_header("Provincial Exam Data for Selected Trainee"))
        self.prov_exam_info = QTreeWidget()
        self.prov_exam_info.setHeaderLabels(["Exam Date", "Module", "Score", "Result", "Notes"])
        self.prov_exam_info.setAlternatingRowColors(True)
        self.prov_exam_info.setRootIsDecorated(False)
        right.addWidget(self.prov_exam_info)
        
        # Practice Status Group
        self.practice_group = QGroupBox("Practice Exam Completion Status")
        pg_layout = QVBoxLayout(self.practice_group)
        self.practice_status_containers = {}
        for mod in ["Life", "A&S", "Seg Funds", "Ethics"]:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 2, 0, 2)
            row_layout.addWidget(QLabel(f"<b>{mod}:</b>"))
            badge = create_badge("PENDING", BADGE_ERROR)
            row_layout.addWidget(badge)
            row_layout.addStretch()
            pg_layout.addWidget(row)
            self.practice_status_containers[mod] = badge
        right.addWidget(self.practice_group)
        
        l.addLayout(right, 2)
        
        self.refresh()

    def refresh(self):
        self._refresh_exam_dropdowns()
        self._refresh_exams()
        self._update_prov_exam_info()

    def _add_exam(self) -> None:
        t_text = self.exam_trainee.currentText()
        if not t_text:
            QMessageBox.warning(self, "Validation", "Select trainee")
            return
        tid = int(t_text.split(":", 1)[0])
        cid = None
        if self.exam_class.currentText():
            cid = int(self.exam_class.currentText().split(":", 1)[0])
        
        res = self.exam_result.currentText()
        passed = 1 if res == "Pass" else 0 if res == "Fail" else None
        
        try:
            db.add_exam(tid, cid, self.exam_date.text().strip() or None, None, self.exam_notes.toPlainText().strip() or None,
                        module=self.exam_module.currentText() or None, 
                        is_practice=1 if self.is_practice.isChecked() else 0,
                        passed=passed)
            self.main_window._show_status("Added exam")
            self.refresh()
        except Exception as exc:
            log_and_show_error(self, "Error", "Failed to add exam", exc)

    def _refresh_exam_dropdowns(self) -> None:
        trainees = db.list_trainees()
        tr_items = [f"{t['id']}: {t['last_name']}, {t['first_name']}" for t in trainees]
        setup_searchable_combobox(self.exam_trainee, tr_items, lambda _: self._update_prov_exam_info())
        
        classes = [f"{c['id']}: {c['name']}" for c in db.list_classes()]
        self.exam_class.clear(); self.exam_class.addItem(""); self.exam_class.addItems(classes)

    def _refresh_exams(self) -> None:
        self.exam_list.clear()
        self._exam_rows = db.exam_crud.list(order_by="exam_date DESC")
        for e in self._exam_rows:
            t = db.get_trainee(e['trainee_id'])
            tname = f"{t['last_name']}, {t['first_name']}" if t else "Unknown"
            mod = f"[{e['module']}] " if e['module'] else ""
            prac = "(P) " if e['is_practice'] else ""
            self.exam_list.addItem(f"{e['id']}: {tname} - {e['exam_date'] or '—'} {mod}{prac}")

    def _update_prov_exam_info(self) -> None:
        self.prov_exam_info.clear()
        for mod in self.practice_status_containers:
            self.practice_status_containers[mod].setText("PENDING")
            self.practice_status_containers[mod].setStyleSheet(BADGE_ERROR)
            
        t_text = self.exam_trainee.currentText()
        if not t_text: return
        tid = int(t_text.split(":", 1)[0])
        
        # Update practice status
        status = services.forms_practice_summary(tid)
        for mod, completed in status.items():
            if mod in self.practice_status_containers:
                badge = self.practice_status_containers[mod]
                badge.setText("COMPLETE" if completed else "PENDING")
                badge.setStyleSheet(BADGE_SUCCESS if completed else BADGE_ERROR)

        # Update provincial list
        conn = db.get_conn(); cur = conn.cursor()
        cur.execute("SELECT * FROM exam WHERE trainee_id = ? AND is_practice = 0 ORDER BY exam_date DESC", (tid,))
        for e in cur.fetchall():
            res = "Pass" if e['passed'] == 1 else "Fail" if e['passed'] == 0 else "—"
            QTreeWidgetItem(self.prov_exam_info, [
                e['exam_date'] or "—",
                e['module'] or "—",
                e['score'] or "—",
                res,
                e['notes'] or ""
            ])
        conn.close()

    def _edit_exam(self) -> None:
        sel = self.exam_list.currentRow()
        if sel < 0: return
        eid = int(self.exam_list.item(sel).text().split(":",1)[0])
        e = db.exam_crud.get(eid)
        if not e: return
        
        dlg = QDialog(self); dlg.setWindowTitle(f"Edit Exam {eid}")
        form = QFormLayout(dlg)
        
        trainee_cb = QComboBox()
        trainees = [f"{t['id']}: {t['last_name']}, {t['first_name']}" for t in db.list_trainees()]
        trainee_cb.addItems(trainees)
        # find current
        t = db.get_trainee(e['trainee_id'])
        if t: trainee_cb.setCurrentText(f"{t['id']}: {t['last_name']}, {t['first_name']}")
        
        mod_cb = QComboBox(); mod_cb.addItems(["", "Life", "A&S", "Seg Funds", "Ethics"])
        mod_cb.setCurrentText(e['module'] or "")
        
        prac_cb = QCheckBox("Practice exam"); prac_cb.setChecked(bool(e['is_practice']))
        date_e = QLineEdit(e['exam_date'] or ""); score_e = QLineEdit(e['score'] or "")
        
        res_cb = QComboBox(); res_cb.addItems(["Unknown", "Pass", "Fail"])
        curr_res = "Pass" if e['passed'] == 1 else "Fail" if e['passed'] == 0 else "Unknown"
        res_cb.setCurrentText(curr_res)
        
        notes_e = QTextEdit(e['notes'] or "")
        
        form.addRow("Trainee", trainee_cb); form.addRow("Module", mod_cb); form.addRow(prac_cb)
        form.addRow("Date", date_e); form.addRow("Score", score_e); form.addRow("Result", res_cb); form.addRow("Notes", notes_e)
        
        btns = QHBoxLayout(); save = QPushButton("Save"); delete = QPushButton("Delete"); cancel = QPushButton("Cancel"); btns.addWidget(save); btns.addWidget(delete); btns.addWidget(cancel); form.addRow(btns)

        def do_save():
            tid_new = int(trainee_cb.currentText().split(":",1)[0])
            res_new = res_cb.currentText()
            passed_new = 1 if res_new == "Pass" else 0 if res_new == "Fail" else None
            try:
                db.update_exam(eid, tid_new, None, date_e.text().strip() or None, score_e.text().strip() or None, 
                               notes_e.toPlainText().strip() or None,
                               module=mod_cb.currentText() or None,
                               is_practice=1 if prac_cb.isChecked() else 0,
                               passed=passed_new)
                dlg.accept()
            except Exception as exc:
                log_and_show_error(self, "Error", "Failed to update exam", exc)

        def do_delete():
            if QMessageBox.question(self, 'Delete', f'Delete exam {eid}?') == QMessageBox.StandardButton.Yes:
                db.delete_exam(eid)
                dlg.accept()

        save.clicked.connect(do_save); delete.clicked.connect(do_delete); cancel.clicked.connect(dlg.reject)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _delete_selected_exam(self) -> None:
        sel = self.exam_list.currentRow()
        if sel < 0: return
        eid = int(self.exam_list.item(sel).text().split(":",1)[0])
        if QMessageBox.question(self, 'Delete', f'Delete exam {eid}?') == QMessageBox.StandardButton.Yes:
            db.delete_exam(eid)
            self.refresh()

def setup_exam_tab(main_window):
    tab = ExamTab(main_window)
    main_window.exam_tab = tab
    main_window.tabs.addTab(tab, "Exams")
