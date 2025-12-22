from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QComboBox, QPushButton, 
    QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem, QAbstractItemView, QHeaderView, 
    QDialog, QFormLayout, QMessageBox, QCheckBox, QLabel, QFileDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
import logging

logger = logging.getLogger(__name__)

from ..widgets import (
    log_and_show_error, create_form_section, create_button_row, 
    create_section_header, create_badge, _load_icon,
    setup_searchable_combobox
)
from ..styles import BADGE_SUCCESS, BADGE_ERROR, BADGE_WARNING, BADGE_INFO
from .. import db
from .. import services
from ..widgets import _load_icon

class LicenseTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._build_ui()

    def _build_ui(self) -> None:
        l = QHBoxLayout(self)
        # Form
        self.lic_trainee = QComboBox()
        self.lic_trainee.currentIndexChanged.connect(self._update_license_trainee_info)
        self.lic_type = QComboBox()
        self.lic_type.addItems(["", "Life", "Mutual Funds"])
        self.lic_app = QLineEdit()
        self.lic_approval = QLineEdit()
        self.lic_number = QLineEdit()
        self.lic_status = QLineEdit()
        
        # RVP Fields (updates trainee)
        self.lic_existing_rvp = QComboBox()
        self.lic_existing_rvp.currentIndexChanged.connect(self._on_existing_rvp_select)
        
        self.lic_rvp_name = QLineEdit()
        self.lic_rvp_rep_code = QLineEdit()
        
        form_fields = [
            ("Trainee", self.lic_trainee),
            ("License Type", self.lic_type),
            ("Application date", self.lic_app),
            ("Approval date", self.lic_approval),
            ("License number", self.lic_number),
            ("Status", self.lic_status),
            ("Select Existing RVP", self.lic_existing_rvp),
            ("RVP Name", self.lic_rvp_name),
            ("RVP Rep Code", self.lic_rvp_rep_code),
        ]
        left = create_form_section(form_fields)
        
        btns_layout = QHBoxLayout()
        add_btn = QPushButton("Add License")
        add_btn.setIcon(_load_icon("add"))
        add_btn.clicked.connect(self._add_license)
        inv_btn = QPushButton("RVP Invoices")
        inv_btn.setIcon(_load_icon("box"))
        inv_btn.clicked.connect(self._show_rvp_invoices)
        exp_btn = QPushButton("Export")
        exp_btn.setIcon(_load_icon("export"))
        exp_btn.clicked.connect(self._export_licenses)
        
        btns_layout.addWidget(add_btn)
        btns_layout.addWidget(inv_btn)
        btns_layout.addWidget(exp_btn)
        left.addLayout(btns_layout)
        
        l.addLayout(left, 1)
        right = QVBoxLayout()
        self.lic_list = QListWidget()
        self.lic_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.lic_list.itemSelectionChanged.connect(self._on_lic_select)
        right.addWidget(create_section_header("Licenses"))
        right.addWidget(self.lic_list)
        lic_btns = create_button_row([
            ("Edit", self._edit_license, "edit"),
            ("Delete", self._delete_selected_license, "delete"),
        ])
        right.addLayout(lic_btns)
        l.addLayout(right, 2)
        
        self.refresh()

    def refresh(self):
        self._refresh_license_dropdowns()
        self._refresh_licenses()

    def _on_existing_rvp_select(self) -> None:
        text = self.lic_existing_rvp.currentText()
        if not text:
            return
        try:
            name_part = text.rsplit(" (", 1)[0]
            code_part = text.rsplit(" (", 1)[1].rstrip(")")
            self.lic_rvp_name.setText(name_part)
            self.lic_rvp_rep_code.setText(code_part)
        except IndexError:
            pass

    def _add_license(self) -> None:
        t = self.lic_trainee.currentText()
        if not t:
            QMessageBox.warning(self, "Validation", "Select trainee")
            return
        tid = int(t.split(":", 1)[0])
        app_date = self.lic_app.text().strip() or None
        approval_date = self.lic_approval.text().strip() or None
        lic_num = self.lic_number.text().strip() or None
        status = self.lic_status.text().strip() or None
        ltype = self.lic_type.currentText() or None
        
        # Also update Trainee RVP info
        r_name = self.lic_rvp_name.text().strip() or None
        r_rep = self.lic_rvp_rep_code.text().strip() or None
        
        tr_curr = db.get_trainee(tid)
        if tr_curr:
            try:
                db.update_trainee(tid, tr_curr['first_name'], tr_curr['last_name'], tr_curr['dob'], 
                                  tr_curr['recruiter_id'], tr_curr['rep_code'], 
                                  rvp_name=r_name, rvp_rep_code=r_rep)
            except Exception as e:
                logger.error(f"Failed to update trainee RVP info for trainee {tid}: {e}")

        try:
            db.add_license(tid, app_date, approval_date, lic_num, status, None, 
                           license_type=ltype, invoiced=False)
            self.main_window._show_status(f"Added license for {t}")
        except Exception as exc:
            log_and_show_error(self, "Error", "Failed to add license", exc)
        self.refresh()

    def _show_rvp_invoices(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("RVP Invoices")
        dlg.resize(800, 600)
        layout = QVBoxLayout(dlg)
        
        tree = QTreeWidget()
        tree.setHeaderLabels(["Entity", "License Type", "Status"])
        tree.setColumnWidth(0, 400)
        layout.addWidget(tree)
        
        rows = db.get_rvp_invoice_summary()
        rvp_map = {}
        for r in rows:
            rvp_key = (r['rvp_name'], r['rvp_rep_code'] or "")
            if rvp_key not in rvp_map:
                rvp_item = QTreeWidgetItem(tree, [f"RVP: {r['rvp_name']} ({r['rvp_rep_code'] or '—'})"])
                rvp_map[rvp_key] = rvp_item
            
            parent = rvp_map[rvp_key]
            l_item = QTreeWidgetItem(parent, [f"{r['last_name']}, {r['first_name']}", r['license_type'] or "—"])
            
            cb = QCheckBox("Invoiced ($50)")
            cb.setChecked(bool(r['invoiced']))
            
            # Using nonlocal capture for lid because it's in a loop
            def make_toggle_fn(lid):
                return lambda state: db.update_license_invoice_status(lid, state == Qt.CheckState.Checked.value)
            
            cb.stateChanged.connect(make_toggle_fn(r['license_id']))
            tree.setItemWidget(l_item, 2, cb)
            parent.setExpanded(True)
            
        tree.expandAll()
        dlg.exec()
        self.refresh()

    def _refresh_license_dropdowns(self) -> None:
        trainees = db.list_trainees()
        tr_items = [f"{t['id']}: {t['last_name']}, {t['first_name']}" for t in trainees]
        setup_searchable_combobox(self.lic_trainee, tr_items, lambda _: self._update_license_trainee_info())
        
        rvps = db.list_unique_rvps()
        rvp_items = [f"{r['rvp_name']} ({r['rvp_rep_code'] or ''})" for r in rvps]
        setup_searchable_combobox(self.lic_existing_rvp, rvp_items, lambda _: self._on_existing_rvp_select())

    def _refresh_licenses(self) -> None:
        self.lic_list.clear()
        for l in db.list_licenses():
            item_widget = QWidget()
            layout = QHBoxLayout(item_widget)
            layout.setContentsMargins(5, 5, 5, 5)
            
            # Label
            inv = " ($)" if l['invoiced'] else ""
            ltype = f" [{l['license_type']}]" if l['license_type'] else ""
            label = QLabel(f"{l['id']}: {l['last_name']}, {l['first_name']} - {l['application_submitted_date'] or '—'}{ltype}{inv}")
            layout.addWidget(label)
            
            # Status Badge
            status = l['status'] or "Pending"
            badge_style = BADGE_INFO
            if status.lower() in ["approved", "issued", "active"]:
                badge_style = BADGE_SUCCESS
            elif status.lower() in ["rejected", "cancelled", "denied"]:
                badge_style = BADGE_ERROR
            elif status.lower() in ["pending", "waiting"]:
                badge_style = BADGE_WARNING
                
            badge = create_badge(status.upper(), badge_style)
            layout.addWidget(badge)
            layout.addStretch()
            
            list_item = QListWidgetItem(self.lic_list)
            list_item.setSizeHint(item_widget.sizeHint())
            self.lic_list.addItem(list_item)
            self.lic_list.setItemWidget(list_item, item_widget)

    def _export_licenses(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export Licenses", "licenses_export.csv", "CSV Files (*.csv)")
        if not path:
            return
            
        data = services.get_license_export_data()
        if not data:
            QMessageBox.information(self, "Export", "No license data to export.")
            return
            
        if services.export_to_csv(data, path):
            self.main_window._show_status(f"Exported to {path}")
        else:
            QMessageBox.critical(self, "Export", "Failed to export data. Check logs.")

    def _edit_license(self) -> None:
        sel = self.lic_list.currentRow()
        if sel < 0: return
        text = self.lic_list.item(sel).text(); lid = int(text.split(":", 1)[0])
        lic = db.get_license(lid)
        if not lic: return
        tr = db.get_trainee(lic['trainee_id'])
        
        dlg = QDialog(self); dlg.setWindowTitle(f"Edit License {lid}")
        form = QFormLayout(dlg)
        
        trainees = [f"{t['id']}: {t['last_name']}, {t['first_name']}" for t in db.list_trainees()]
        trainee_cb = QComboBox()
        trainee_cb.addItems(trainees)
        curr_t = f"{lic['trainee_id']}: {lic['last_name']}, {lic['first_name']}"
        trainee_cb.setCurrentText(curr_t)
        
        type_cb = QComboBox()
        type_cb.addItems(["", "Life", "Mutual Funds"])
        type_cb.setCurrentText(lic['license_type'] or "")
        
        app_e = QLineEdit(lic['application_submitted_date'] or ""); approval_e = QLineEdit(lic['approval_date'] or "")
        num_e = QLineEdit(lic['license_number'] or ""); status_e = QLineEdit(lic['status'] or "")
        invoiced_cb = QCheckBox("Invoiced"); invoiced_cb.setChecked(bool(lic['invoiced']))
        
        rvp_name_e = QLineEdit(tr['rvp_name'] or "")
        rvp_rep_e = QLineEdit(tr['rvp_rep_code'] or "")
        
        form.addRow("Trainee", trainee_cb)
        form.addRow("License Type", type_cb)
        form.addRow("Application date", app_e)
        form.addRow("Approval date", approval_e)
        form.addRow("License number", num_e)
        form.addRow("Status", status_e)
        form.addRow(invoiced_cb)
        form.addRow("RVP Name", rvp_name_e)
        form.addRow("RVP Rep Code", rvp_rep_e)
        
        btns = QHBoxLayout(); save = QPushButton("Save"); delete = QPushButton("Delete"); cancel = QPushButton("Cancel"); btns.addWidget(save); btns.addWidget(delete); btns.addWidget(cancel); form.addRow(btns)

        def do_save():
            tid_new = int(trainee_cb.currentText().split(":",1)[0])
            r_name = rvp_name_e.text().strip() or None
            r_rep = rvp_rep_e.text().strip() or None
            tr_curr = db.get_trainee(tid_new)
            if tr_curr:
                try:
                    db.update_trainee(tid_new, tr_curr['first_name'], tr_curr['last_name'], tr_curr['dob'],
                                      tr_curr['recruiter_id'], tr_curr['rep_code'],
                                      rvp_name=r_name, rvp_rep_code=r_rep)
                except Exception:
                    pass

            try:
                db.update_license(lid, tid_new, app_e.text().strip() or None, approval_e.text().strip() or None, 
                                  num_e.text().strip() or None, status_e.text().strip() or None, None,
                                  license_type=type_cb.currentText() or None,
                                  invoiced=invoiced_cb.isChecked())
            except Exception as exc:
                log_and_show_error(self, "Error", "Failed to update license", exc)
                return
            dlg.accept()

        def do_delete():
            if QMessageBox.question(self, 'Delete License', f'Delete license {lid}?') != QMessageBox.StandardButton.Yes:
                return
            db.license_crud.delete(lid)
            dlg.accept()

        save.clicked.connect(do_save); delete.clicked.connect(do_delete); cancel.clicked.connect(dlg.reject)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _delete_selected_license(self) -> None:
        selected_items = self.lic_list.selectedItems()
        if not selected_items:
            return
            
        # Extract IDs from the labels. This is a bit brittle since labels are complex.
        # Alternatively, we could store the ID in the item data.
        # For now, let's parse from the label widget.
        lids = []
        for item in selected_items:
            widget = self.lic_list.itemWidget(item)
            if not widget: continue
            lbl = widget.findChild(QLabel)
            if lbl:
                txt = lbl.text()
                # Label format: "{l['id']}: {l['last_name']}..."
                try:
                    lid = int(txt.split(":", 1)[0])
                    lids.append(lid)
                except ValueError: continue
                
        if not lids: return
        
        count = len(lids)
        msg = f"Are you sure you want to delete {count} selected license(s)?"
        if QMessageBox.question(self, "Delete", msg) == QMessageBox.StandardButton.Yes:
            try:
                for lid in lids:
                    db.delete_license(lid)
                self.main_window._show_status(f"Deleted {count} licenses.")
                self.refresh()
            except Exception as e:
                log_and_show_error(self, e, "Error deleting licenses")

    def _on_lic_select(self):
        # This method is connected but its implementation is not provided in the diff.
        # It's typically used to enable/disable buttons or update details based on selection.
        # For now, it can remain empty or be implemented as needed.
        pass

    def _update_license_trainee_info(self):
        t_text = self.lic_trainee.currentText()
        self.lic_rvp_name.clear()
        self.lic_rvp_rep_code.clear()
        if not t_text:
            return
        tid = int(t_text.split(":", 1)[0])
        trainee = db.get_trainee(tid)
        if trainee:
            self.lic_rvp_name.setText(trainee['rvp_name'] or "")
            self.lic_rvp_rep_code.setText(trainee['rvp_rep_code'] or "")
            
def setup_license_tab(self):
    tab = LicenseTab(self)
    self.license_tab = tab # Store reference
    self.tabs.addTab(tab, "Licenses")
