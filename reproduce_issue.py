
import sys
import os
import sqlite3
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from PySide6.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem
from PySide6.QtCore import Qt
from licensing_specialist.tabs.license_tab import LicenseTab
from licensing_specialist import db

# Mock main window
class MockMainWindow:
    def __init__(self):
        self.tabs = None
    
    def _show_status(self, msg):
        print(f"STATUS: {msg}")

def reproduce():
    app = QApplication.instance() or QApplication(sys.argv)
    
    # Setup DB
    db_path = Path("repro.db")
    if db_path.exists():
        db_path.unlink()
    
    db.init_db(db_path)
    # Add dummy trainee with RVP info
    db.add_recruiter("Rec1", db_path=db_path)
    db.add_trainee("John", "Doe", recruiter_id=1, rvp_name="RVP One", rvp_rep_code="RVP1", db_path=db_path)
    db.add_license(1, "2025-01-01", "2025-01-02", "L123", "Issued", "Notes", "Life", db_path=db_path)
    
    # Override DEFAULT_DB for the session
    # We can't easily override it globally without patching, but db methods accept db_path.
    # However, LicenseTab calls db functions without db_path, using DEFAULT_DB.
    # So we must patch db.DEFAULT_DB
    
    original_db = db.DEFAULT_DB
    db.DEFAULT_DB = db_path
    
    try:
        mw = MockMainWindow()
        tab = LicenseTab(mw)
        
        # Verify RVP Tree population
        tab._refresh_rvp_panel()
        root = tab.rvp_tree.invisibleRootItem()
        print(f"Tree Top Level Count: {tab.rvp_tree.topLevelItemCount()}")
        
        # Expect "All RVPs" and "RVP One"
        # Item 0 is "All RVPs" usually?
        # Code: 
        # all_item = QTreeWidgetItem(self.rvp_tree, ["All RVPs", ""])
        # for s in stats: ...
        
        # Let's find "RVP One"
        rvp_item = None
        for i in range(tab.rvp_tree.topLevelItemCount()):
            item = tab.rvp_tree.topLevelItem(i)
            print(f"Item {i}: {item.text(0)}")
            if "RVP One" in item.text(0):
                rvp_item = item
                break
        
        if not rvp_item:
            print("FAILURE: RVP One not found in tree")
            return
            
        print("Selecting RVP One...")
        tab.rvp_tree.setCurrentItem(rvp_item)
        
        # Check current details
        # The logic is in _update_rvp_profile which is connected to selection change
        # tab._on_rvp_select()
        
        # Verify what _update_rvp_profile does
        # We can inspect the internal method logic or the profile view content
        
        # Let's inspect data first
        data = rvp_item.data(0, Qt.UserRole)
        print(f"Data type: {type(data)}")
        print(f"Data value: {data}")
        
        # Check if profile populated (Header + Content)
        # If it failed/returned early, it might have 1 item or 0 depending on implementation.
        # But if successful, it has multiple items (Header, Section, etc.)
        
        # Access the layout of the scroll area's widget
        start_count = tab.rvp_profile.layout.count()
        print(f"Profile layout item count: {start_count}")
        
        # Valid profile should have at least: Header + Performance Summary (Section) -> 2 items
        if start_count >= 2:
             print("SUCCESS: RVP Profile Loaded.")
        else:
             print("FAILURE: RVP Profile Empty or Default.")
        
    finally:
        db.DEFAULT_DB = original_db
        if db_path.exists():
            try:
                os.remove(db_path)
            except:
                pass

if __name__ == "__main__":
    reproduce()
