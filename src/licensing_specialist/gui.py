import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional
from . import db
from datetime import datetime


DATE_HELP = "Use YYYY-MM-DD format"


def _safe_get(row, key):
    """Safely get a field from sqlite3.Row or dict-like object."""
    if row is None:
        return None
    try:
        return row[key]
    except Exception:
        try:
            return row.get(key)
        except Exception:
            return None


class Autocomplete:
    """A small autocomplete popup bound to an Entry.

    fetch_suggestions(prefix) -> list of rows/objects
    on_select(row) -> called when a suggestion is chosen
    """
    def __init__(self, entry: tk.Entry, fetch_suggestions, on_select, max_items: int = 8):
        self.entry = entry
        self.fetch = fetch_suggestions
        self.on_select = on_select
        self.max_items = max_items
        self.popup = None
        self.listbox = None
        self._after_id = None
        # bind events
        self.entry.bind('<KeyRelease>', self._on_keyrelease)
        self.entry.bind('<Down>', self._on_down)
        self.entry.bind('<Up>', self._on_up)
        self.entry.bind('<Return>', self._on_return)
        self.entry.bind('<Escape>', self._on_escape)

    def _on_keyrelease(self, event):
        # ignore navigation keys here
        if event.keysym in ('Up', 'Down', 'Return', 'Escape'):
            return
        if self._after_id:
            try:
                self.entry.after_cancel(self._after_id)
            except Exception:
                pass
        # schedule suggestions (debounce 150ms)
        self._after_id = self.entry.after(150, self._show_suggestions)

    def _show_suggestions(self):
        self._after_id = None
        prefix = self.entry.get().strip()
        items = self.fetch(prefix)[: self.max_items]
        if not items:
            self._close_popup()
            return

        # build display strings and keep rows
        displays = []
        rows = []
        for it in items:
            # allow fetch to return either (display, row) or row
            if isinstance(it, tuple) and len(it) == 2:
                displays.append(it[0])
                rows.append(it[1])
            else:
                # try sqlite3.Row-like access
                r = it
                name = None
                if 'name' in r.keys():
                    name = r['name']
                    email = r['email'] if 'email' in r.keys() else ''
                    disp = f"{name} ({email or ''})"
                elif 'first_name' in r.keys() and 'last_name' in r.keys():
                    disp = f"{r['first_name']} {r['last_name']}"
                elif 'rep_code' in r.keys():
                    rep = r['rep_code'] if 'rep_code' in r.keys() else ''
                    nm = r['name'] if 'name' in r.keys() else ''
                    disp = f"{rep or ''} - {nm or ''}"
                else:
                    disp = str(r)
                displays.append(disp)
                rows.append(r)

        # create popup window
        if not self.popup or not tk.Toplevel.winfo_exists(self.popup):
            self.popup = tk.Toplevel(self.entry)
            self.popup.wm_overrideredirect(True)
            self.listbox = tk.Listbox(self.popup, height=min(len(displays), self.max_items), activestyle='dotbox')
            self.listbox.pack(side=tk.LEFT, fill=tk.BOTH)
            self.listbox.bind('<Double-Button-1>', lambda e: self._select_index(self.listbox.curselection()))
            self.listbox.bind('<Return>', lambda e: self._select_index(self.listbox.curselection()))
        else:
            self.listbox.delete(0, tk.END)

        for d in displays:
            self.listbox.insert(tk.END, d)

        # store rows for selection
        self._rows = rows

        # position popup under entry
        try:
            x = self.entry.winfo_rootx()
            y = self.entry.winfo_rooty() + self.entry.winfo_height()
            self.popup.wm_geometry(f"+{x}+{y}")
            self.popup.deiconify()
        except Exception:
            pass

        # focus listbox so arrow keys work
        try:
            self.listbox.focus_set()
            self.listbox.selection_set(0)
        except Exception:
            pass

    def _select_index(self, sel):
        try:
            if not sel:
                idx = self.listbox.curselection()
            else:
                idx = sel
            if not idx:
                return
            i = int(idx[0])
            row = self._rows[i]
            # call on_select with the row
            try:
                self.on_select(row)
            except Exception:
                pass
        finally:
            self._close_popup()

    def _on_down(self, event):
        if self.listbox and self.popup:
            cur = self.listbox.curselection()
            idx = int(cur[0]) if cur else -1
            idx = min(self.listbox.size() - 1, idx + 1)
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(idx)
            return 'break'

    def _on_up(self, event):
        if self.listbox and self.popup:
            cur = self.listbox.curselection()
            idx = int(cur[0]) if cur else 0
            idx = max(0, idx - 1)
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(idx)
            return 'break'

    def _on_return(self, event):
        if self.listbox and self.popup:
            self._select_index(self.listbox.curselection())
            return 'break'

    def _on_escape(self, event):
        self._close_popup()
        return 'break'

    def _close_popup(self):
        try:
            if self.popup:
                self.popup.destroy()
        except Exception:
            pass
        self.popup = None
        self.listbox = None
        self._rows = []

class App(tk.Tk):
    def __init__(self, db_path: Optional[str] = None):
        super().__init__()
        self.title("Licensing Specialist")
        self.geometry("800x600")
        self.db_path = db_path
        db.init_db()

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.recruiter_frame = ttk.Frame(self.notebook)
        self.trainee_frame = ttk.Frame(self.notebook)
        self.class_frame = ttk.Frame(self.notebook)
        self.exam_frame = ttk.Frame(self.notebook)
        self.license_frame = ttk.Frame(self.notebook)

        self.notebook.add(self.recruiter_frame, text="Recruiters")
        self.notebook.add(self.trainee_frame, text="Trainees")
        self.notebook.add(self.class_frame, text="Classes")
        self.notebook.add(self.exam_frame, text="Exams")
        self.notebook.add(self.license_frame, text="Licenses")

        self._build_recruiter_tab()
        self._build_trainee_tab()
        self._build_class_tab()
        self._build_exam_tab()
        self._build_license_tab()

    def _build_recruiter_tab(self):
        frm = self.recruiter_frame
        left = ttk.Frame(frm)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=8)

        ttk.Label(left, text="Name").pack()
        self.rec_name = ttk.Entry(left)
        self.rec_name.pack()
        # search/populate when user types an existing name
        self.rec_name.bind('<FocusOut>', lambda e: self._on_rec_name_search())
        self.rec_name.bind('<Return>', lambda e: self._on_rec_name_search())
        # live autocomplete for recruiter name
        self.rec_name_ac = Autocomplete(
            self.rec_name,
            lambda p: [(f"{r['name']} ({r['email'] or ''})", r) for r in db.search_recruiters_by_name(p)],
            lambda row: self._populate_recruiter_fields(row),
        )
        ttk.Label(left, text="Email").pack()
        self.rec_email = ttk.Entry(left)
        self.rec_email.pack()
        ttk.Label(left, text="Phone").pack()
        self.rec_phone = ttk.Entry(left)
        self.rec_phone.pack()
        ttk.Label(left, text="Rep code (5 alnum)").pack()
        self.rec_rep = ttk.Entry(left)
        self.rec_rep.pack()
        self.rec_rep.bind('<FocusOut>', lambda e: self._on_rec_rep_search())
        self.rec_rep.bind('<Return>', lambda e: self._on_rec_rep_search())
        # live autocomplete for rep code
        self.rec_rep_ac = Autocomplete(
            self.rec_rep,
            lambda p: [(f"{_safe_get(r,'rep_code') or ''} - {_safe_get(r,'name') or ''}", r) for r in db.search_recruiters_by_rep(p)],
            lambda row: self._populate_recruiter_fields(row),
        )
        ttk.Button(left, text="Add Recruiter", command=self._add_recruiter).pack(pady=6)

        right = ttk.Frame(frm)
        right.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        top = ttk.Frame(right)
        top.pack(fill=tk.X)
        ttk.Label(top, text="Recruiters").pack(side=tk.LEFT)
        ttk.Button(top, text="Edit", command=self._edit_selected_recruiter).pack(side=tk.RIGHT)

        self.recruiter_list = tk.Listbox(right, height=8)
        self.recruiter_list.pack(fill=tk.X)
        self.recruiter_list.bind('<<ListboxSelect>>', self._on_recruiter_select)
        self._refresh_recruiters()

        # details area to show connected info for selected recruiter using a Treeview
        ttk.Separator(right).pack(fill=tk.X, pady=6)
        ttk.Label(right, text="Details").pack()
        details_box = ttk.Frame(right)
        details_box.pack(fill=tk.BOTH, expand=True)

        # Use a Treeview with a dedicated 'Details' column for clearer layout
        self.recruiter_tree = ttk.Treeview(details_box, columns=("details",), show="tree headings")
        self.recruiter_tree.heading("details", text="Details")
        self.recruiter_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_sb = ttk.Scrollbar(details_box, orient=tk.VERTICAL, command=self.recruiter_tree.yview)
        tree_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.recruiter_tree.configure(yscrollcommand=tree_sb.set)
        self.recruiter_tree.bind('<Double-1>', self._on_tree_double_click)

    def _add_recruiter(self):
        name = self.rec_name.get().strip()
        if not name:
            messagebox.showwarning("Validation", "Name is required")
            return
        try:
            db.add_recruiter(name, self.rec_email.get().strip() or None, self.rec_phone.get().strip() or None, self.rec_rep.get().strip() or None)
        except ValueError as e:
            messagebox.showwarning("Validation", str(e))
            return
        self.rec_name.delete(0, tk.END)
        self.rec_email.delete(0, tk.END)
        self.rec_phone.delete(0, tk.END)
        self.rec_rep.delete(0, tk.END)
        self._refresh_recruiters()
        self._refresh_recruiter_dropdowns()

    def _populate_recruiter_fields(self, recruiter_row) -> None:
        """Populate recruiter entry fields from a recruiter row (sqlite3.Row)."""
        if not recruiter_row:
            return
        # set fields
        self.rec_name.delete(0, tk.END)
        self.rec_name.insert(0, recruiter_row['name'] or '')
        self.rec_email.delete(0, tk.END)
        self.rec_email.insert(0, recruiter_row['email'] or '')
        self.rec_phone.delete(0, tk.END)
        self.rec_phone.insert(0, recruiter_row['phone'] or '')
        self.rec_rep.delete(0, tk.END)
        self.rec_rep.insert(0, _safe_get(recruiter_row, 'rep_code') or '')

    def _on_rec_name_search(self, event=None):
        name = self.rec_name.get().strip()
        if not name:
            return
        r = db.find_recruiter_by_name(name)
        if r:
            self._populate_recruiter_fields(r)

    def _on_rec_rep_search(self, event=None):
        code = self.rec_rep.get().strip()
        if not code:
            return
        r = db.find_recruiter_by_rep_code(code)
        if r:
            self._populate_recruiter_fields(r)

    def _populate_trainee_fields(self, trainee_row) -> None:
        if not trainee_row:
            return
        self.tr_first.delete(0, tk.END)
        self.tr_first.insert(0, trainee_row['first_name'] or '')
        self.tr_last.delete(0, tk.END)
        self.tr_last.insert(0, trainee_row['last_name'] or '')
        self.tr_dob.delete(0, tk.END)
        self.tr_dob.insert(0, trainee_row['dob'] or '')
        self.tr_rep.delete(0, tk.END)
        self.tr_rep.insert(0, _safe_get(trainee_row, 'rep_code') or '')
        # set recruiter dropdown if recruiter exists
        if _safe_get(trainee_row, 'recruiter_id'):
            rid = trainee_row['recruiter_id']
            # ensure dropdown is refreshed
            self._refresh_recruiter_dropdowns()
            for v in self.rec_dropdown['values']:
                if str(rid) + ':' in v:
                    self.rec_dropdown.set(v)
                    break

    def _on_tr_name_search(self, event=None):
        first = self.tr_first.get().strip()
        last = self.tr_last.get().strip()
        if not first or not last:
            return
        t = db.find_trainee_by_name(first, last)
        if t:
            self._populate_trainee_fields(t)

    def _on_tr_rep_search(self, event=None):
        code = self.tr_rep.get().strip()
        if not code:
            return
        t = db.find_trainee_by_rep_code(code)
        if t:
            self._populate_trainee_fields(t)

    def _refresh_recruiters(self):
        self.recruiter_list.delete(0, tk.END)
        for r in db.list_recruiters():
            self.recruiter_list.insert(tk.END, f"{r['id']}: {r['name']} ({r['email'] or ''})")

    def _on_recruiter_select(self, event):
        sel = event.widget.curselection()
        if not sel:
            return
        text = event.widget.get(sel[0])
        try:
            rid = int(text.split(":", 1)[0])
        except Exception:
            return
        # gather recruiter + related trainees, their classes, exams, licenses
        conn = db.get_conn()
        cur = conn.cursor()

        cur.execute("SELECT * FROM recruiter WHERE id = ?", (rid,))
        recruiter = cur.fetchone()

        # populate tree
        self.recruiter_tree.delete(*self.recruiter_tree.get_children())
        root_id = self.recruiter_tree.insert('', 'end', text=f"Recruiter: {recruiter['name']} (ID: {recruiter['id']})", open=True)
        if recruiter and recruiter['email']:
            self.recruiter_tree.insert(root_id, 'end', text=f"Email: {recruiter['email']}")
        if recruiter and recruiter['phone']:
            self.recruiter_tree.insert(root_id, 'end', text=f"Phone: {recruiter['phone']}")
        if recruiter and _safe_get(recruiter, 'rep_code'):
            self.recruiter_tree.insert(root_id, 'end', text=f"Rep code: {recruiter['rep_code']}")

        # trainees
        cur.execute("SELECT * FROM trainee WHERE recruiter_id = ? ORDER BY last_name, first_name", (rid,))
        trainees = cur.fetchall()
        if not trainees:
            self.recruiter_tree.insert(root_id, 'end', text="No trainees associated with this recruiter.")
        else:
            trainees_parent = self.recruiter_tree.insert(root_id, 'end', text="Trainees", open=True)
            for t in trainees:
                tnode = self.recruiter_tree.insert(trainees_parent, 'end', text=f"{t['id']}: {t['last_name']}, {t['first_name']} (DOB: {t['dob'] or '—'})", values=("trainee", t['id']))
                # practice exams completion indicator
                try:
                    complete = db.practice_exams_complete(t['id'])
                    self.recruiter_tree.insert(tnode, 'end', text=f"Practice Exams Complete: {'Y' if complete else 'N'}")
                except Exception:
                    pass

                # classes for trainee
                cur.execute(
                    "SELECT c.* FROM class c JOIN trainee_class tc ON c.id = tc.class_id WHERE tc.trainee_id = ? ORDER BY c.start_date",
                    (t['id'],),
                )
                classes = cur.fetchall()
                if classes:
                    classes_parent = self.recruiter_tree.insert(tnode, 'end', text="Classes", open=False)
                    for c in classes:
                        self.recruiter_tree.insert(classes_parent, 'end', text=f"{c['id']}: {c['name']} ({c['start_date'] or '—'} → {c['end_date'] or '—'})")

                # exams
                cur.execute("SELECT * FROM exam WHERE trainee_id = ? ORDER BY exam_date DESC", (t['id'],))
                exams = cur.fetchall()
                if exams:
                    exams_parent = self.recruiter_tree.insert(tnode, 'end', text="Exams", open=False)
                    for e in exams:
                        mod = f"[{e['module']}] " if 'module' in e.keys() and e['module'] else ''
                        practice = "(practice) " if 'is_practice' in e.keys() and e['is_practice'] else ''
                        passed = 'Pass' if ('passed' in e.keys() and e['passed'] == 1) else ('Fail' if ('passed' in e.keys() and e['passed'] == 0) else '—')
                        reimb = ' [Reimb requested]' if ('reimbursement_requested' in e.keys() and e['reimbursement_requested']) else ''
                        self.recruiter_tree.insert(exams_parent, 'end', text=f"{e['id']}: {e['exam_date'] or '—'} | {mod}{practice}Score: {e['score'] or '—'} | {passed}{reimb}")

                # licenses
                cur.execute("SELECT * FROM license WHERE trainee_id = ? ORDER BY application_submitted_date DESC", (t['id'],))
                licenses = cur.fetchall()
                if licenses:
                    lic_parent = self.recruiter_tree.insert(tnode, 'end', text="Licenses", open=False)
                    for l in licenses:
                        self.recruiter_tree.insert(lic_parent, 'end', text=f"{l['id']}: Applied: {l['application_submitted_date'] or '—'} | Approved: {l['approval_date'] or '—'} | Status: {l['status'] or '—'}")

        conn.close()

        # ensure first column expands
        try:
            self.recruiter_tree.column('#0', width=300)
            self.recruiter_tree.column('details', width=400)
        except Exception:
            pass

    def _validate_date(self, date_str: str, field_name: str) -> Optional[str]:
        """Validate YYYY-MM-DD date. Return same string if valid, or None if empty. Raise ValueError if invalid."""
        s = (date_str or "").strip()
        if not s:
            return None
        try:
            # strict parsing
            datetime.strptime(s, "%Y-%m-%d")
            return s
        except Exception:
            raise ValueError(f"{field_name} must be YYYY-MM-DD (got '{date_str}')")

    def _on_tree_double_click(self, event):
        # open trainee edit dialog when double-clicking a trainee node
        item = self.recruiter_tree.identify('item', event.x, event.y)
        if not item:
            return
        vals = self.recruiter_tree.item(item)
        text = vals.get('text', '')
        # trainee nodes are formatted as "{id}: Last, First (...)"
        if text and text.split(':', 1)[0].strip().isdigit():
            tid = int(text.split(':', 1)[0])
            self._open_edit_trainee_dialog(tid)

    def _on_trainee_select(self, event):
        sel = event.widget.curselection()
        if not sel:
            return
        text = event.widget.get(sel[0])
        try:
            tid = int(text.split(":", 1)[0])
        except Exception:
            return

        conn = db.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM trainee WHERE id = ?", (tid,))
        t = cur.fetchone()
        # populate trainee tree
        self.trainee_tree.delete(*self.trainee_tree.get_children())
        root = self.trainee_tree.insert('', 'end', text=f"Trainee: {t['first_name']} {t['last_name']} (ID: {t['id']})", open=True)
        if t['dob']:
            self.trainee_tree.insert(root, 'end', text=f"DOB: {t['dob']}")
        # practice exams complete
        try:
            complete = db.practice_exams_complete(t['id'])
            self.trainee_tree.insert(root, 'end', text=f"Practice Exams Complete: {'Y' if complete else 'N'}")
        except Exception:
            pass
        # recruiter
        if t['recruiter_id']:
            r = db.get_recruiter(t['recruiter_id'])
            if r:
                self.trainee_tree.insert(root, 'end', text=f"Recruiter: {r['id']}: {r['name']} ({r['email'] or '—'})")

        # classes
        cur.execute("SELECT c.* FROM class c JOIN trainee_class tc ON c.id = tc.class_id WHERE tc.trainee_id = ? ORDER BY c.start_date", (tid,))
        classes = cur.fetchall()
        if classes:
            cp = self.trainee_tree.insert(root, 'end', text="Classes", open=False)
            for c in classes:
                self.trainee_tree.insert(cp, 'end', text=f"{c['id']}: {c['name']} ({c['start_date'] or '—'} → {c['end_date'] or '—'})")

        # exams
        cur.execute("SELECT * FROM exam WHERE trainee_id = ? ORDER BY exam_date DESC", (tid,))
        exams = cur.fetchall()
        if exams:
            ep = self.trainee_tree.insert(root, 'end', text="Exams", open=False)
            for e in exams:
                mod = f"[{e['module']}] " if 'module' in e.keys() and e['module'] else ''
                practice = "(practice) " if 'is_practice' in e.keys() and e['is_practice'] else ''
                passed = 'Pass' if ('passed' in e.keys() and e['passed'] == 1) else ('Fail' if ('passed' in e.keys() and e['passed'] == 0) else '—')
                reimb = ' [Reimb requested]' if ('reimbursement_requested' in e.keys() and e['reimbursement_requested']) else ''
                self.trainee_tree.insert(ep, 'end', text=f"{e['id']}: {e['exam_date'] or '—'} | {mod}{practice}Score: {e['score'] or '—'} | {passed}{reimb} | Notes: {e['notes'] or '—'}")

        # licenses
        cur.execute("SELECT * FROM license WHERE trainee_id = ? ORDER BY application_submitted_date DESC", (tid,))
        licenses = cur.fetchall()
        if licenses:
            lp = self.trainee_tree.insert(root, 'end', text="Licenses", open=False)
            for l in licenses:
                self.trainee_tree.insert(lp, 'end', text=f"{l['id']}: Applied: {l['application_submitted_date'] or '—'} | Approved: {l['approval_date'] or '—'} | Status: {l['status'] or '—'}")

        conn.close()

    def _on_class_select(self, event):
        sel = event.widget.curselection()
        if not sel:
            return
        text = event.widget.get(sel[0])
        try:
            cid = int(text.split(":", 1)[0])
        except Exception:
            return

        conn = db.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM class WHERE id = ?", (cid,))
        cls = cur.fetchone()

        self.class_tree.delete(*self.class_tree.get_children())
        root = self.class_tree.insert('', 'end', text=f"Class: {cls['name']} (ID: {cls['id']})", open=True)
        if cls['start_date'] or cls['end_date']:
            self.class_tree.insert(root, 'end', text=f"Dates: {cls['start_date'] or '—'} → {cls['end_date'] or '—'}")

        # trainees linked to this class
        cur.execute("SELECT t.* FROM trainee t JOIN trainee_class tc ON t.id = tc.trainee_id WHERE tc.class_id = ? ORDER BY t.last_name, t.first_name", (cid,))
        trainees = cur.fetchall()
        if not trainees:
            self.class_tree.insert(root, 'end', text="No trainees linked to this class.")
        else:
            tp = self.class_tree.insert(root, 'end', text="Trainees", open=True)
            for t in trainees:
                tnode = self.class_tree.insert(tp, 'end', text=f"{t['id']}: {t['last_name']}, {t['first_name']} (DOB: {t['dob'] or '—'})", values=("trainee", t['id']))
                # exams for trainee
                cur.execute("SELECT * FROM exam WHERE trainee_id = ? ORDER BY exam_date DESC", (t['id'],))
                exams = cur.fetchall()
                if exams:
                    ep = self.class_tree.insert(tnode, 'end', text="Exams", open=False)
                    for e in exams:
                        mod = f"[{e['module']}] " if 'module' in e.keys() and e['module'] else ''
                        practice = "(practice) " if 'is_practice' in e.keys() and e['is_practice'] else ''
                        passed = 'Pass' if ('passed' in e.keys() and e['passed'] == 1) else ('Fail' if ('passed' in e.keys() and e['passed'] == 0) else '—')
                        reimb = ' [Reimb requested]' if ('reimbursement_requested' in e.keys() and e['reimbursement_requested']) else ''
                        self.class_tree.insert(ep, 'end', text=f"{e['id']}: {e['exam_date'] or '—'} | {mod}{practice}Score: {e['score'] or '—'} | {passed}{reimb}")
                # licenses for trainee
                cur.execute("SELECT * FROM license WHERE trainee_id = ? ORDER BY application_submitted_date DESC", (t['id'],))
                licenses = cur.fetchall()
                if licenses:
                    lp = self.class_tree.insert(tnode, 'end', text="Licenses", open=False)
                    for l in licenses:
                        self.class_tree.insert(lp, 'end', text=f"{l['id']}: Applied: {l['application_submitted_date'] or '—'} | Approved: {l['approval_date'] or '—'} | Status: {l['status'] or '—'}")

        conn.close()

    def _edit_selected_recruiter(self):
        sel = self.recruiter_list.curselection()
        if not sel:
            messagebox.showwarning('Edit Recruiter', 'Select a recruiter to edit')
            return
        text = self.recruiter_list.get(sel[0])
        rid = int(text.split(':', 1)[0])
        self._open_edit_recruiter_dialog(rid)

    def _open_edit_recruiter_dialog(self, recruiter_id: int):
        dialog = EditRecruiterDialog(self, recruiter_id)
        self.wait_window(dialog.top)
        # refresh after possible edit
        self._refresh_recruiters()
        self._refresh_recruiter_dropdowns()

    def _open_edit_trainee_dialog(self, trainee_id: int):
        dialog = EditTraineeDialog(self, trainee_id)
        self.wait_window(dialog.top)
        # refresh views
        self._refresh_trainees()
        self._refresh_tc_dropdowns()
        self._refresh_exam_dropdowns()

    def _build_trainee_tab(self):
        frm = self.trainee_frame
        left = ttk.Frame(frm)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=8)

        ttk.Label(left, text="First name").pack()
        self.tr_first = ttk.Entry(left)
        self.tr_first.pack()
        # populate when existing trainee name typed
        self.tr_first.bind('<FocusOut>', lambda e: self._on_tr_name_search())
        self.tr_first.bind('<Return>', lambda e: self._on_tr_name_search())
        # live autocomplete for trainee name
        self.tr_first_ac = Autocomplete(
            self.tr_first,
            lambda p: [(f"{t['first_name']} {t['last_name']}", t) for t in db.search_trainees_by_name(p)],
            lambda row: self._populate_trainee_fields(row),
        )
        ttk.Label(left, text="Last name").pack()
        self.tr_last = ttk.Entry(left)
        self.tr_last.pack()
        self.tr_last.bind('<FocusOut>', lambda e: self._on_tr_name_search())
        self.tr_last.bind('<Return>', lambda e: self._on_tr_name_search())
        self.tr_last_ac = Autocomplete(
            self.tr_last,
            lambda p: [(f"{t['first_name']} {t['last_name']}", t) for t in db.search_trainees_by_name(p)],
            lambda row: self._populate_trainee_fields(row),
        )
        ttk.Label(left, text="DOB (YYYY-MM-DD)").pack()
        self.tr_dob = ttk.Entry(left)
        self.tr_dob.pack()
        ttk.Label(left, text="Rep code (5 alnum)").pack()
        self.tr_rep = ttk.Entry(left)
        self.tr_rep.pack()
        self.tr_rep.bind('<FocusOut>', lambda e: self._on_tr_rep_search())
        self.tr_rep.bind('<Return>', lambda e: self._on_tr_rep_search())
        self.tr_rep_ac = Autocomplete(
            self.tr_rep,
            lambda p: [(f"{_safe_get(t,'rep_code') or ''} - {_safe_get(t,'first_name') or ''} {_safe_get(t,'last_name') or ''}", t) for t in db.search_trainees_by_rep(p)],
            lambda row: self._populate_trainee_fields(row),
        )
        ttk.Label(left, text="Recruiter").pack()
        self.rec_var = tk.StringVar()
        self.rec_dropdown = ttk.Combobox(left, textvariable=self.rec_var)
        self.rec_dropdown.pack()
        ttk.Button(left, text="Add Trainee", command=self._add_trainee).pack(pady=6)

        right = ttk.Frame(frm)
        right.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        top = ttk.Frame(right)
        top.pack(fill=tk.X)
        ttk.Label(top, text="Trainees").pack(side=tk.LEFT)
        ttk.Button(top, text="Edit Trainee", command=self._edit_selected_trainee).pack(side=tk.RIGHT)

        self.trainee_list = tk.Listbox(right, height=8)
        self.trainee_list.pack(fill=tk.X)
        self.trainee_list.bind('<<ListboxSelect>>', self._on_trainee_select)
        self._refresh_recruiter_dropdowns()
        self._refresh_trainees()

        # details view for trainee
        ttk.Separator(right).pack(fill=tk.X, pady=6)
        ttk.Label(right, text="Details").pack()
        tbox = ttk.Frame(right)
        tbox.pack(fill=tk.BOTH, expand=True)
        self.trainee_tree = ttk.Treeview(tbox, columns=("details",), show="tree headings")
        self.trainee_tree.heading("details", text="Details")
        self.trainee_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        t_sb = ttk.Scrollbar(tbox, orient=tk.VERTICAL, command=self.trainee_tree.yview)
        t_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.trainee_tree.configure(yscrollcommand=t_sb.set)
        self.trainee_tree.bind('<Double-1>', lambda e: self._on_tree_double_click(e))

    def _edit_selected_trainee(self):
        sel = self.trainee_list.curselection()
        if not sel:
            messagebox.showwarning('Edit Trainee', 'Select a trainee to edit')
            return
        text = self.trainee_list.get(sel[0])
        tid = int(text.split(':', 1)[0])
        self._open_edit_trainee_dialog(tid)

    def _add_trainee(self):
        first = self.tr_first.get().strip()
        last = self.tr_last.get().strip()
        if not first or not last:
            messagebox.showwarning("Validation", "First and last names are required")
            return
        recruiter_id = None
        rec = self.rec_var.get()
        if rec:
            recruiter_id = int(rec.split(":", 1)[0])
        # validate DOB
        try:
            dob = self._validate_date(self.tr_dob.get().strip(), "DOB")
        except ValueError as e:
            messagebox.showwarning("Validation", str(e))
            return
        try:
            db.add_trainee(first, last, dob, recruiter_id, self.tr_rep.get().strip() or None)
        except ValueError as e:
            messagebox.showwarning("Validation", str(e))
            return
        self.tr_first.delete(0, tk.END)
        self.tr_last.delete(0, tk.END)
        self.tr_dob.delete(0, tk.END)
        self.tr_rep.delete(0, tk.END)
        self._refresh_trainees()

    def _refresh_recruiter_dropdowns(self):
        items = [f"{r['id']}:{r['name']}" for r in db.list_recruiters()]
        # show nicer label
        nicer = [f"{r['id']}: {r['name']}" for r in db.list_recruiters()]
        self.rec_dropdown['values'] = nicer

    def _refresh_trainees(self):
        self.trainee_list.delete(0, tk.END)
        for t in db.list_trainees():
            self.trainee_list.insert(tk.END, f"{t['id']}: {t['last_name']}, {t['first_name']} (Recruiter: {t['recruiter_name'] or '—'})")

    def _build_class_tab(self):
        frm = self.class_frame
        left = ttk.Frame(frm)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=8)
        ttk.Label(left, text="Class name").pack()
        self.class_name = ttk.Entry(left)
        self.class_name.pack()
        ttk.Label(left, text="Start date (YYYY-MM-DD)").pack()
        self.class_start = ttk.Entry(left)
        self.class_start.pack()
        ttk.Label(left, text="End date (YYYY-MM-DD)").pack()
        self.class_end = ttk.Entry(left)
        self.class_end.pack()
        ttk.Button(left, text="Add Class", command=self._add_class).pack(pady=6)

        ttk.Separator(left).pack(fill=tk.X, pady=8)
        ttk.Label(left, text="Link trainee to class").pack()
        self.tc_trainee_var = tk.StringVar()
        self.tc_class_var = tk.StringVar()
        self.tc_trainee = ttk.Combobox(left, textvariable=self.tc_trainee_var)
        self.tc_class = ttk.Combobox(left, textvariable=self.tc_class_var)
        self.tc_trainee.pack()
        self.tc_class.pack()
        ttk.Button(left, text="Link", command=self._link_trainee_class).pack(pady=6)

        right = ttk.Frame(frm)
        right.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        top = ttk.Frame(right)
        top.pack(fill=tk.X)
        ttk.Label(top, text="Classes").pack(side=tk.LEFT)
        ttk.Button(top, text="Delete", command=self._delete_selected_class).pack(side=tk.RIGHT)
        self.class_list = tk.Listbox(right, height=8)
        self.class_list.pack(fill=tk.X)
        self.class_list.bind('<<ListboxSelect>>', self._on_class_select)
        self._refresh_classes()
        self._refresh_tc_dropdowns()

        # details view for class
        ttk.Separator(right).pack(fill=tk.X, pady=6)
        ttk.Label(right, text="Details").pack()
        cbox = ttk.Frame(right)
        cbox.pack(fill=tk.BOTH, expand=True)
        self.class_tree = ttk.Treeview(cbox, columns=("details",), show="tree headings")
        self.class_tree.heading("details", text="Details")
        self.class_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        c_sb = ttk.Scrollbar(cbox, orient=tk.VERTICAL, command=self.class_tree.yview)
        c_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.class_tree.configure(yscrollcommand=c_sb.set)

    def _add_class(self):
        name = self.class_name.get().strip()
        if not name:
            messagebox.showwarning("Validation", "Class name required")
            return
        # validate dates
        try:
            start = self._validate_date(self.class_start.get().strip(), "Start date")
            end = self._validate_date(self.class_end.get().strip(), "End date")
            if start and end:
                if datetime.strptime(start, "%Y-%m-%d") > datetime.strptime(end, "%Y-%m-%d"):
                    messagebox.showwarning("Validation", "Start date must be before or equal to End date")
                    return
        except ValueError as e:
            messagebox.showwarning("Validation", str(e))
            return

        db.add_class(name, start, end)
        self.class_name.delete(0, tk.END)
        self.class_start.delete(0, tk.END)
        self.class_end.delete(0, tk.END)
        self._refresh_classes()
        self._refresh_tc_dropdowns()

    def _refresh_classes(self):
        self.class_list.delete(0, tk.END)
        for c in db.list_classes():
            self.class_list.insert(tk.END, f"{c['id']}: {c['name']} ({c['start_date'] or '—'} → {c['end_date'] or '—'})")

    def _refresh_tc_dropdowns(self):
        trainees = [f"{t['id']}: {t['last_name']}, {t['first_name']}" for t in db.list_trainees()]
        classes = [f"{c['id']}: {c['name']}" for c in db.list_classes()]
        self.tc_trainee['values'] = trainees
        self.tc_class['values'] = classes

    def _link_trainee_class(self):
        t = self.tc_trainee_var.get()
        c = self.tc_class_var.get()
        if not t or not c:
            messagebox.showwarning("Validation", "Select trainee and class")
            return
        tid = int(t.split(":", 1)[0])
        cid = int(c.split(":", 1)[0])
        db.link_trainee_to_class(tid, cid)
        messagebox.showinfo("Linked", "Trainee linked to class")

    def _delete_selected_class(self):
        sel = self.class_list.curselection()
        if not sel:
            messagebox.showwarning('Delete Class', 'Select a class to delete')
            return
        text = self.class_list.get(sel[0])
        try:
            cid = int(text.split(":", 1)[0])
        except Exception:
            messagebox.showwarning('Delete Class', 'Could not determine class id')
            return
        if not messagebox.askyesno('Delete Class', f'Delete class {cid}? Trainee links will be removed.'):
            return
        try:
            db.delete_class(cid)
        except Exception as e:
            messagebox.showerror('Delete Class', f'Error deleting class: {e}')
            return
        self._refresh_classes()
        self._refresh_tc_dropdowns()

    def _build_exam_tab(self):
        frm = self.exam_frame
        left = ttk.Frame(frm)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=8)

        ttk.Label(left, text="Trainee").pack()
        self.exam_trainee_var = tk.StringVar()
        self.exam_trainee = ttk.Combobox(left, textvariable=self.exam_trainee_var)
        self.exam_trainee.pack()
        ttk.Label(left, text="Class (optional)").pack()
        self.exam_class_var = tk.StringVar()
        self.exam_class = ttk.Combobox(left, textvariable=self.exam_class_var)
        self.exam_class.pack()
        ttk.Label(left, text="Module").pack()
        self.exam_module = tk.StringVar()
        self.exam_module_cb = ttk.Combobox(left, textvariable=self.exam_module)
        self.exam_module_cb['values'] = ["Life", "A&S", "Seg Funds", "Ethics"]
        self.exam_module_cb.pack()

        self.is_practice_var = tk.IntVar(value=0)
        ttk.Checkbutton(left, text="Practice exam", variable=self.is_practice_var).pack()

        ttk.Label(left, text="Exam date (YYYY-MM-DD)").pack()
        self.exam_date = ttk.Entry(left)
        self.exam_date.pack()

        ttk.Label(left, text="Score (numeric)").pack()
        self.exam_score = ttk.Entry(left)
        self.exam_score.pack()

        ttk.Label(left, text="Result").pack()
        self.exam_result = tk.StringVar()
        self.exam_result_cb = ttk.Combobox(left, textvariable=self.exam_result)
        self.exam_result_cb['values'] = ["Unknown", "Pass", "Fail"]
        self.exam_result_cb.set("Unknown")
        self.exam_result_cb.pack()

        ttk.Label(left, text="Notes").pack()
        self.exam_notes = tk.Text(left, height=4, width=30)
        self.exam_notes.pack()
        ttk.Button(left, text="Add Exam", command=self._add_exam).pack(pady=6)

        right = ttk.Frame(frm)
        right.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        ttk.Label(right, text="Exams").pack()
        self.exam_list = tk.Listbox(right)
        self.exam_list.pack(fill=tk.BOTH, expand=True)
        ttk.Button(right, text="Delete Exam", command=self._delete_selected_exam).pack(pady=4)
        self._refresh_exam_dropdowns()
        self._refresh_exams()

    def _add_exam(self):
        t = self.exam_trainee_var.get()
        if not t:
            messagebox.showwarning("Validation", "Select a trainee")
            return
        tid = int(t.split(":", 1)[0])
        cid = None
        c = self.exam_class_var.get()
        if c:
            cid = int(c.split(":", 1)[0])
        # validate exam date
        try:
            exam_date = self._validate_date(self.exam_date.get().strip(), "Exam date")
        except ValueError as e:
            messagebox.showwarning("Validation", str(e))
            return

        # module
        module = self.exam_module.get().strip() or None
        is_practice = bool(self.is_practice_var.get())

        # score
        score_raw = self.exam_score.get().strip()
        score = None
        if score_raw:
            try:
                score = float(score_raw)
            except Exception:
                messagebox.showwarning("Validation", "Score must be numeric")
                return

        # determine passed
        result = self.exam_result.get()
        if result == 'Pass':
            passed = True
        elif result == 'Fail':
            passed = False
        else:
            # infer from score if available (threshold 70)
            passed = None
            if score is not None:
                passed = score >= 70.0

        # add exam record using new API
        # if failed and not practice, check practice-exam completion and prompt reimbursement
        reimbursement = False
        if passed is False and not is_practice and db.practice_exams_complete(tid):
            if messagebox.askyesno("Reimbursement", "Trainee completed practice exams. Apply for reimbursement for rewrite?"):
                reimbursement = True

        db.add_exam_v2(tid, cid, exam_date, module, is_practice, passed, score, self.exam_notes.get("1.0", tk.END).strip() or None, reimbursement_requested=reimbursement)
        self._refresh_exams()

    def _refresh_exam_dropdowns(self):
        trainees = [f"{t['id']}: {t['last_name']}, {t['first_name']}" for t in db.list_trainees()]
        classes = [f"{c['id']}: {c['name']}" for c in db.list_classes()]
        self.exam_trainee['values'] = trainees
        self.exam_class['values'] = classes

    def _refresh_exams(self):
        self.exam_list.delete(0, tk.END)
        for e in db.list_exams():
            mod = f"[{e['module']}] " if 'module' in e.keys() and e['module'] else ''
            practice = "(practice) " if 'is_practice' in e.keys() and e['is_practice'] else ''
            passed = 'Pass' if ('passed' in e.keys() and e['passed'] == 1) else ('Fail' if ('passed' in e.keys() and e['passed'] == 0) else '—')
            reimb = ' [Reimb requested]' if ('reimbursement_requested' in e.keys() and e['reimbursement_requested']) else ''
            self.exam_list.insert(tk.END, f"{e['id']}: {e['exam_date'] or '—'} - {mod}{practice}{e['first_name']} {e['last_name']} - {passed}{reimb}")

    def _delete_selected_exam(self):
        sel = self.exam_list.curselection()
        if not sel:
            messagebox.showwarning('Delete Exam', 'Select an exam to delete')
            return
        text = self.exam_list.get(sel[0])
        try:
            eid = int(text.split(":", 1)[0])
        except Exception:
            messagebox.showwarning('Delete Exam', 'Could not determine exam id')
            return
        if not messagebox.askyesno('Delete Exam', f'Delete exam {eid}?'):
            return
        try:
            db.delete_exam(eid)
        except Exception as e:
            messagebox.showerror('Delete Exam', f'Error deleting exam: {e}')
            return
        self._refresh_exams()

    def _build_license_tab(self):
        frm = self.license_frame
        left = ttk.Frame(frm)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=8)
        ttk.Label(left, text="Trainee").pack()
        self.lic_trainee_var = tk.StringVar()
        self.lic_trainee = ttk.Combobox(left, textvariable=self.lic_trainee_var)
        self.lic_trainee.pack()
        ttk.Label(left, text="Application submitted (YYYY-MM-DD)").pack()
        self.lic_app = ttk.Entry(left)
        self.lic_app.pack()
        ttk.Label(left, text="Approval date (YYYY-MM-DD)").pack()
        self.lic_approval = ttk.Entry(left)
        self.lic_approval.pack()
        ttk.Label(left, text="License number").pack()
        self.lic_number = ttk.Entry(left)
        self.lic_number.pack()
        ttk.Label(left, text="Status").pack()
        self.lic_status = ttk.Entry(left)
        self.lic_status.pack()
        ttk.Button(left, text="Add License", command=self._add_license).pack(pady=6)

        right = ttk.Frame(frm)
        right.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        ttk.Label(right, text="Licenses").pack()
        self.lic_list = tk.Listbox(right)
        self.lic_list.pack(fill=tk.BOTH, expand=True)
        self._refresh_license_dropdowns()
        self._refresh_licenses()

    def _add_license(self):
        t = self.lic_trainee_var.get()
        if not t:
            messagebox.showwarning("Validation", "Select trainee")
            return
        tid = int(t.split(":", 1)[0])
        # validate dates
        try:
            app_date = self._validate_date(self.lic_app.get().strip(), "Application date")
            approval_date = self._validate_date(self.lic_approval.get().strip(), "Approval date")
            if app_date and approval_date:
                if datetime.strptime(app_date, "%Y-%m-%d") > datetime.strptime(approval_date, "%Y-%m-%d"):
                    messagebox.showwarning("Validation", "Approval date must be on or after application date")
                    return
        except ValueError as e:
            messagebox.showwarning("Validation", str(e))
            return

        db.add_license(tid, app_date, approval_date, self.lic_number.get().strip() or None, self.lic_status.get().strip() or None, None)
        self._refresh_licenses()

    def _refresh_license_dropdowns(self):
        trainees = [f"{t['id']}: {t['last_name']}, {t['first_name']}" for t in db.list_trainees()]
        self.lic_trainee['values'] = trainees

    def _refresh_licenses(self):
        self.lic_list.delete(0, tk.END)
        for l in db.list_licenses():
            self.lic_list.insert(tk.END, f"{l['id']}: {l['application_submitted_date'] or '—'} - {l['first_name']} {l['last_name']} - {l['status'] or '—'}")


class EditRecruiterDialog:
    def __init__(self, parent, recruiter_id: int):
        import tkinter as tk
        from tkinter import ttk
        self.parent = parent
        self.recruiter_id = recruiter_id
        self.top = tk.Toplevel(parent)
        self.top.title('Edit Recruiter')
        self.top.grab_set()

        rec = db.get_recruiter(recruiter_id) or {}

        ttk.Label(self.top, text='Name').pack()
        self.name_e = ttk.Entry(self.top)
        self.name_e.insert(0, _safe_get(rec, 'name') or '')
        self.name_e.pack()
        # bind search
        self.name_e.bind('<FocusOut>', lambda e: self._on_name_search())
        self.name_e.bind('<Return>', lambda e: self._on_name_search())
        # live autocomplete on dialog name
        self.name_ac = Autocomplete(
            self.name_e,
            lambda p: [(f"{r['name']} ({_safe_get(r,'email') or ''})", r) for r in db.search_recruiters_by_name(p)],
            lambda row: (self.name_e.delete(0, tk.END), self.name_e.insert(0, _safe_get(row,'name') or ''), self.email_e.delete(0, tk.END), self.email_e.insert(0, _safe_get(row,'email') or ''), self.phone_e.delete(0, tk.END), self.phone_e.insert(0, _safe_get(row,'phone') or ''), self.rep_e.delete(0, tk.END), self.rep_e.insert(0, _safe_get(row,'rep_code') or '')),
        )

        ttk.Label(self.top, text='Email').pack()
        self.email_e = ttk.Entry(self.top)
        self.email_e.insert(0, _safe_get(rec, 'email') or '')
        self.email_e.pack()

        ttk.Label(self.top, text='Phone').pack()
        self.phone_e = ttk.Entry(self.top)
        self.phone_e.insert(0, _safe_get(rec, 'phone') or '')
        self.phone_e.pack()

        ttk.Label(self.top, text='Rep code (5 alnum)').pack()
        self.rep_e = ttk.Entry(self.top)
        self.rep_e.insert(0, _safe_get(rec, 'rep_code') or '')
        self.rep_e.pack()
        self.rep_e.bind('<FocusOut>', lambda e: self._on_rep_search())
        self.rep_e.bind('<Return>', lambda e: self._on_rep_search())
        self.rep_ac = Autocomplete(
            self.rep_e,
            lambda p: [(f"{_safe_get(r,'rep_code') or ''} - {_safe_get(r,'name') or ''}", r) for r in db.search_recruiters_by_rep(p)],
            lambda row: (self.name_e.delete(0, tk.END), self.name_e.insert(0, _safe_get(row,'name') or ''), self.email_e.delete(0, tk.END), self.email_e.insert(0, _safe_get(row,'email') or ''), self.phone_e.delete(0, tk.END), self.phone_e.insert(0, _safe_get(row,'phone') or ''), self.rep_e.delete(0, tk.END), self.rep_e.insert(0, _safe_get(row,'rep_code') or '')),
        )

        btns = ttk.Frame(self.top)
        btns.pack(pady=6)
        ttk.Button(btns, text='Save', command=self._save).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text='Delete', command=self._delete).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text='Cancel', command=self.top.destroy).pack(side=tk.LEFT, padx=4)

    def _save(self):
        name = self.name_e.get().strip()
        email = self.email_e.get().strip() or None
        phone = self.phone_e.get().strip() or None
        if not name:
            messagebox.showwarning('Validation', 'Name is required')
            return
        try:
            db.update_recruiter(self.recruiter_id, name, email, phone, self.rep_e.get().strip() or None)
        except ValueError as e:
            messagebox.showwarning('Validation', str(e))
            return
        self.top.destroy()

    def _on_name_search(self):
        name = self.name_e.get().strip()
        if not name:
            return
        r = db.find_recruiter_by_name(name)
        if r:
            self.email_e.delete(0, tk.END)
            self.email_e.insert(0, r['email'] or '')
            self.phone_e.delete(0, tk.END)
            self.phone_e.insert(0, r['phone'] or '')
            self.rep_e.delete(0, tk.END)
            self.rep_e.insert(0, r.get('rep_code') or '')

    def _on_rep_search(self):
        code = self.rep_e.get().strip()
        if not code:
            return
        r = db.find_recruiter_by_rep_code(code)
        if r:
            self.name_e.delete(0, tk.END)
            self.name_e.insert(0, r['name'] or '')
            self.email_e.delete(0, tk.END)
            self.email_e.insert(0, r['email'] or '')
            self.phone_e.delete(0, tk.END)
            self.phone_e.insert(0, r['phone'] or '')

    def _delete(self):
        if not messagebox.askyesno('Delete Recruiter', 'Delete this recruiter? Trainees will not be deleted, but their recruiter assignment will be cleared.'):
            return
        db.delete_recruiter(self.recruiter_id)
        self.top.destroy()


class EditTraineeDialog:
    def __init__(self, parent, trainee_id: int):
        import tkinter as tk
        from tkinter import ttk
        self.parent = parent
        self.trainee_id = trainee_id
        self.top = tk.Toplevel(parent)
        self.top.title('Edit Trainee')
        self.top.grab_set()

        tr = db.get_trainee(trainee_id) or {}

        ttk.Label(self.top, text='First name').pack()
        self.first_e = ttk.Entry(self.top)
        self.first_e.insert(0, _safe_get(tr, 'first_name') or '')
        self.first_e.pack()
        self.first_e.bind('<FocusOut>', lambda e: self._on_name_search())
        self.first_e.bind('<Return>', lambda e: self._on_name_search())
        self.first_ac = Autocomplete(
            self.first_e,
            lambda p: [(f"{t['first_name']} {t['last_name']}", t) for t in db.search_trainees_by_name(p)],
            lambda row: self._populate_trainee_fields(row),
        )

        ttk.Label(self.top, text='Last name').pack()
        self.last_e = ttk.Entry(self.top)
        self.last_e.insert(0, _safe_get(tr, 'last_name') or '')
        self.last_e.pack()
        self.last_e.bind('<FocusOut>', lambda e: self._on_name_search())
        self.last_e.bind('<Return>', lambda e: self._on_name_search())
        self.last_ac = Autocomplete(
            self.last_e,
            lambda p: [(f"{t['first_name']} {t['last_name']}", t) for t in db.search_trainees_by_name(p)],
            lambda row: self._populate_trainee_fields(row),
        )

        ttk.Label(self.top, text='DOB (YYYY-MM-DD)').pack()
        self.dob_e = ttk.Entry(self.top)
        self.dob_e.insert(0, _safe_get(tr, 'dob') or '')
        self.dob_e.pack()

        ttk.Label(self.top, text='Rep code (5 alnum)').pack()
        self.rep_e = ttk.Entry(self.top)
        self.rep_e.insert(0, _safe_get(tr, 'rep_code') or '')
        self.rep_e.pack()
        self.rep_e.bind('<FocusOut>', lambda e: self._on_rep_search())
        self.rep_e.bind('<Return>', lambda e: self._on_rep_search())
        self.rep_ac = Autocomplete(
            self.rep_e,
            lambda p: [(f"{_safe_get(t,'rep_code') or ''} - {_safe_get(t,'first_name') or ''} {_safe_get(t,'last_name') or ''}", t) for t in db.search_trainees_by_rep(p)],
            lambda row: self._populate_trainee_fields(row),
        )

        ttk.Label(self.top, text='Recruiter').pack()
        self.rec_var_local = tk.StringVar()
        self.rec_combo = ttk.Combobox(self.top, textvariable=self.rec_var_local)
        recs = [f"{r['id']}: {r['name']}" for r in db.list_recruiters()]
        self.rec_combo['values'] = recs
        if _safe_get(tr, 'recruiter_id'):
            for r in recs:
                if r.startswith(str(tr['recruiter_id']) + ':'):
                    self.rec_combo.set(r)
                    break
        self.rec_combo.pack()

        btns = ttk.Frame(self.top)
        btns.pack(pady=6)
        ttk.Button(btns, text='Save', command=self._save).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text='Delete', command=self._delete).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text='Cancel', command=self.top.destroy).pack(side=tk.LEFT, padx=4)

    def _save(self):
        first = self.first_e.get().strip()
        last = self.last_e.get().strip()
        if not first or not last:
            messagebox.showwarning('Validation', 'First and last names are required')
            return
        dob = self.dob_e.get().strip() or None
        try:
            dob = self.parent._validate_date(dob, 'DOB')
        except ValueError as e:
            messagebox.showwarning('Validation', str(e))
            return

        rec = self.rec_var_local.get()
        recruiter_id = None
        if rec:
            recruiter_id = int(rec.split(':', 1)[0])
        try:
            db.update_trainee(self.trainee_id, first, last, dob, recruiter_id, self.rep_e.get().strip() or None)
        except ValueError as e:
            messagebox.showwarning('Validation', str(e))
            return
        self.top.destroy()

    def _on_name_search(self):
        first = self.first_e.get().strip()
        last = self.last_e.get().strip()
        if not first or not last:
            return
        t = db.find_trainee_by_name(first, last)
        if t:
            self.first_e.delete(0, tk.END)
            self.first_e.insert(0, t['first_name'] or '')
            self.last_e.delete(0, tk.END)
            self.last_e.insert(0, t['last_name'] or '')
            self.dob_e.delete(0, tk.END)
            self.dob_e.insert(0, _safe_get(t, 'dob') or '')
            self.rep_e.delete(0, tk.END)
            self.rep_e.insert(0, _safe_get(t, 'rep_code') or '')
            if _safe_get(t, 'recruiter_id'):
                rid = t['recruiter_id']
                for r in self.rec_combo['values']:
                    if r.startswith(str(rid) + ':'):
                        self.rec_combo.set(r)
                        break

    def _on_rep_search(self):
        code = self.rep_e.get().strip()
        if not code:
            return
        t = db.find_trainee_by_rep_code(code)
        if t:
            self.first_e.delete(0, tk.END)
            self.first_e.insert(0, t['first_name'] or '')
            self.last_e.delete(0, tk.END)
            self.last_e.insert(0, t['last_name'] or '')
            self.dob_e.delete(0, tk.END)
            self.dob_e.insert(0, _safe_get(t, 'dob') or '')
            if _safe_get(t, 'recruiter_id'):
                rid = t['recruiter_id']
                for r in self.rec_combo['values']:
                    if r.startswith(str(rid) + ':'):
                        self.rec_combo.set(r)
                        break

    def _delete(self):
        if not messagebox.askyesno('Delete Trainee', 'Delete this trainee? Exams, licenses and class links will be removed.'):
            return
        db.delete_trainee(self.trainee_id)
        self.top.destroy()
    


def run_app():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    run_app()
