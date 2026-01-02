from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QComboBox, QPushButton, 
    QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem, QAbstractItemView, QHeaderView, 
    QDialog, QFormLayout, QMessageBox, QCheckBox, QLabel, QFileDialog, QSplitter
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
        
        # --- Left Side: Form ---
        left_container = QWidget()
        left = QVBoxLayout(left_container)
        
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
        
        # License Details Section
        left.addWidget(create_section_header("License Details"))
        lic_fields = [
            ("Trainee", self.lic_trainee),
            ("License Type", self.lic_type),
            ("App. Date", self.lic_app),
            ("Appr. Date", self.lic_approval),
            ("License #", self.lic_number),
            ("Status", self.lic_status),
        ]
        left.addLayout(create_form_section(lic_fields))
        
        # RVP Section
        left.addSpacing(10)
        left.addWidget(create_section_header("RVP Assignment"))
        rvp_fields = [
            ("Existing RVP", self.lic_existing_rvp),
            ("RVP Name", self.lic_rvp_name),
            ("Rep Code", self.lic_rvp_rep_code),
        ]
        left.addLayout(create_form_section(rvp_fields))
        
        left.addSpacing(20)
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
        left.addStretch()
        
        # --- Middle Side: Splitter for List and RVP Info ---
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Top: License List
        list_container = QWidget()
        list_layout = QVBoxLayout(list_container)
        
        # Search & Filter Box
        filter_layout = QHBoxLayout()
        self.lic_search = QLineEdit()
        self.lic_search.setPlaceholderText("Search trainee or license number...")
        self.lic_search.setClearButtonEnabled(True)
        self.lic_search.textChanged.connect(self._refresh_licenses)
        
        self.type_filter = QComboBox()
        self.type_filter.addItems(["All Types", "Life", "Mutual Funds"])
        self.type_filter.currentIndexChanged.connect(self._refresh_licenses)
        
        clear_btn = QPushButton()
        clear_btn.setIcon(_load_icon("delete"))
        clear_btn.setToolTip("Clear all filters")
        clear_btn.clicked.connect(self._clear_filters)
        
        search_icon = QLabel()
        search_icon.setPixmap(_load_icon("search").pixmap(16, 16))
        
        filter_layout.addWidget(search_icon)
        filter_layout.addWidget(self.lic_search, 3)
        filter_layout.addWidget(self.type_filter, 1)
        filter_layout.addWidget(clear_btn)
        list_layout.addLayout(filter_layout)
        
        # List
        self.lic_list = QListWidget()
        self.lic_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.lic_list.itemSelectionChanged.connect(self._on_lic_select)
        list_layout.addWidget(create_section_header("Licenses"))
        list_layout.addWidget(self.lic_list)
        
        edit_btn = QPushButton("Edit")
        edit_btn.setIcon(_load_icon("edit"))
        edit_btn.clicked.connect(self._edit_license)
        edit_btn.setEnabled(False)
        self.btn_edit = edit_btn
        
        del_btn = QPushButton("Delete")
        del_btn.setIcon(_load_icon("delete"))
        del_btn.clicked.connect(self._delete_selected_license)
        del_btn.setEnabled(False)
        self.btn_delete = del_btn
        
        lic_btns = QHBoxLayout()
        lic_btns.addWidget(edit_btn)
        lic_btns.addWidget(del_btn)
        list_layout.addLayout(lic_btns)
        
        right_splitter.addWidget(list_container)
        
        # Bottom: RVP Panel (Split horizontally for Tree and Profile)
        bottom_container = QWidget()
        bottom_layout = QHBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        rvp_tree_container = QWidget()
        rvp_tree_layout = QVBoxLayout(rvp_tree_container)
        rvp_tree_layout.addWidget(create_section_header("Select RVP"))
        self.rvp_tree = QTreeWidget()
        self.rvp_tree.setHeaderLabels(["RVP", "Total"])
        self.rvp_tree.setAlternatingRowColors(True)
        self.rvp_tree.itemSelectionChanged.connect(self._on_rvp_select)
        self.rvp_tree.itemDoubleClicked.connect(self._on_rvp_double_click)
        rvp_tree_layout.addWidget(self.rvp_tree)
        
        from ..widgets import ModernProfileView
        self.rvp_profile = ModernProfileView()
        
        bottom_layout.addWidget(rvp_tree_container, 1)
        bottom_layout.addWidget(self.rvp_profile, 2)
        
        right_splitter.addWidget(bottom_container)
        right_splitter.setStretchFactor(0, 3) # List takes more space
        right_splitter.setStretchFactor(1, 2)
        
        l.addWidget(left_container, 2)
        l.addWidget(right_splitter, 3)
        
        self.refresh()



    def refresh(self):
        self._refresh_license_dropdowns()
        self._refresh_rvp_panel()
        self._refresh_licenses()

    def _clear_filters(self):
        self.lic_search.clear()
        self.type_filter.setCurrentIndex(0)
        self.rvp_tree.setCurrentItem(self.rvp_tree.topLevelItem(0))
        self._refresh_licenses()

    def _refresh_rvp_panel(self) -> None:
        self.rvp_tree.clear()
        stats = db.get_rvp_stats()
        
        # Add "All RVPs" item
        all_item = QTreeWidgetItem(self.rvp_tree, ["All RVPs", ""])
        all_item.setData(0, Qt.UserRole, "ALL")
        
        for s in stats:
            name = f"{s['rvp_name']} ({s['rvp_rep_code'] or '—'})"
            item = QTreeWidgetItem(self.rvp_tree, [
                name,
                str(s['total_licenses'] or 0)
            ])
            item.setTextAlignment(1, Qt.AlignmentFlag.AlignCenter)
            item.setData(0, Qt.UserRole, (s['rvp_name'], s['rvp_rep_code']))
            # Store full stats in the item for quick profile access
            item.setData(1, Qt.UserRole, s)
        
        self.rvp_tree.setCurrentItem(all_item)

    def _on_rvp_select(self) -> None:
        self._refresh_licenses()
        self._update_rvp_profile()

    def _update_rvp_profile(self) -> None:
        self.rvp_profile.clear()
        sel_items = self.rvp_tree.selectedItems()
        if not sel_items:
            self.rvp_profile.add_header("No RVP Selected")
            return
            
        data = sel_items[0].data(0, Qt.UserRole)
        if data == "ALL":
            self.rvp_profile.add_header("All RVPs View", "Select an individual RVP for detailed info.")
            return
            
        name_code = data
        if not isinstance(name_code, (tuple, list)):
             self.rvp_profile.add_header("All RVPs View", "Select an individual RVP for detailed info.")
             return
             
        name, code = name_code
        stats = sel_items[0].data(1, Qt.UserRole)
        
        self.rvp_profile.add_header(name, f"Rep Code: {code or '—'}")
        
        metrics = [
            ("Issued Licenses", str(stats['issued_count']), "check"),
            ("Pending Licenses", str(stats['pending_count']), "history"),
            ("Invoiced", str(stats['invoiced_count']), "box"),
            ("Total Records", str(stats['total_licenses']), "list"),
        ]
        self.rvp_profile.add_section("Performance Summary", metrics)
        
        # Trainees list
        trainees = db.get_trainees_by_rvp(name, code)
        if trainees:
            tr_names = [f"{t['first_name']} {t['last_name']}" for t in trainees]
            self.rvp_profile.add_section("Assigned Trainees", [("", n, "user") for n in tr_names])
        
        # Action
        view_inv_btn = QPushButton(f"View Invoices for {name}")
        view_inv_btn.setIcon(_load_icon("box"))
        view_inv_btn.clicked.connect(lambda: self._show_rvp_invoices(filter_rvp=(name, code)))
        self.rvp_profile.add_custom_widget(view_inv_btn)

    def _on_rvp_double_click(self, item: QTreeWidgetItem, column: int) -> None:
        data = item.data(0, Qt.UserRole)
        if data == "ALL":
            self._show_rvp_invoices()
            return
        
        name, code = data
        self._show_rvp_invoices(filter_rvp=(name, code))

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

    def _show_rvp_invoices(self, filter_rvp=None) -> None:
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QCheckBox
        from PySide6.QtCore import Qt
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
            if filter_rvp:
                if (r['rvp_name'], r['rvp_rep_code']) != filter_rvp:
                    continue

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
        setup_searchable_combobox(self.lic_trainee, tr_items, lambda text: self._update_license_trainee_info())
        
        rvps = db.list_unique_rvps()
        rvp_items = [f"{r['rvp_name']} ({r['rvp_rep_code'] or ''})" for r in rvps]
        setup_searchable_combobox(self.lic_existing_rvp, rvp_items, lambda text: self._on_existing_rvp_select())

    def _refresh_licenses(self) -> None:
        self.lic_list.clear()
        search_text = self.lic_search.text().lower()
        type_filter = self.type_filter.currentText()
        
        # Get current RVP filter
        sel_items = self.rvp_tree.selectedItems()
        rvp_filter = None
        if sel_items:
            data = sel_items[0].data(0, Qt.UserRole)
            if data != "ALL":
                rvp_filter = data # (name, rep_code)

        for l in db.list_licenses():
            # Apply RVP Filter
            if rvp_filter:
                trainee = db.get_trainee(l['trainee_id'])
                if not trainee or (trainee['rvp_name'], trainee['rvp_rep_code']) != rvp_filter:
                    continue

            # Apply Type Filter
            l_type = l['license_type'] or ""
            if type_filter != "All Types" and type_filter != l_type:
                continue

            # Apply Search Filter (Trainee Name or License Number)
            name_text = f"{l['last_name']}, {l['first_name']}".lower()
            lnum = (l['license_number'] or "").lower()
            if search_text and (search_text not in name_text and search_text not in lnum):
                continue

            item_widget = QWidget()
            # Use a slightly more complex layout for the "Card"
            main_v = QVBoxLayout(item_widget)
            main_v.setContentsMargins(15, 12, 15, 12)
            main_v.setSpacing(6)
            
            top_h = QHBoxLayout()
            
            # Trainee Name (Prominent)
            name_lbl = QLabel(f"<b>{l['last_name']}, {l['first_name']}</b>")
            name_lbl.setStyleSheet("font-size: 11pt;")
            top_h.addWidget(name_lbl)
            
            top_h.addStretch()
            
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
            top_h.addWidget(badge)
            main_v.addLayout(top_h)
            
            # Sub-info row (Type, Date, License Number)
            info_h = QHBoxLayout()
            info_h.setSpacing(15)
            
            type_text = l['license_type'] or "—"
            type_lbl = QLabel(f"[{type_text}]")
            type_lbl.setStyleSheet("color: #64748b; font-weight: 600;")
            info_h.addWidget(type_lbl)
            
            date_val = l['application_submitted_date'] or "—"
            date_lbl = QLabel(f"📅 {date_val}")
            date_lbl.setStyleSheet("color: #94a3b8; font-size: 9pt;")
            info_h.addWidget(date_lbl)
            
            if l['license_number']:
                num_lbl = QLabel(f"ID: {l['license_number']}")
                num_lbl.setStyleSheet("color: #94a3b8; font-size: 9pt;")
                info_h.addWidget(num_lbl)
                
            if l['invoiced']:
                inv_icon = QLabel("💰")
                inv_icon.setToolTip("Invoiced")
                info_h.addWidget(inv_icon)
                
            info_h.addStretch()
            main_v.addLayout(info_h)
            
            list_item = QListWidgetItem(self.lic_list)
            # Store ID in data for reliable retrieval
            list_item.setData(Qt.UserRole, l['id'])
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
        item = self.lic_list.item(sel)
        lid = item.data(Qt.UserRole)
        if lid is None: return
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
            
        lids = []
        for item in selected_items:
            lid = item.data(Qt.UserRole)
            if lid is not None:
                lids.append(lid)
                
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
        # Enable/Disable buttons based on selection
        sel_count = len(self.lic_list.selectedItems())
        self.btn_edit.setEnabled(sel_count == 1)
        self.btn_delete.setEnabled(sel_count > 0)

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
