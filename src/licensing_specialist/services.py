from typing import Optional, List, Dict, Any
from pathlib import Path
import logging
import csv
from datetime import datetime, timedelta
from . import db

logger = logging.getLogger(__name__)
PRACTICE_MODULES = ["Life", "A&S", "Seg Funds", "Ethics"]
REQUIRED_PRACTICE_MODULES = PRACTICE_MODULES # For now, all modules are required

def check_seewhy_guarantee(trainee_id: int, first_provincial_exam_date: Optional[str], db_path: Optional[Path] = None) -> bool:
    """Check if trainee qualifies for SeeWhy Guarantee."""
    try:
        if not first_provincial_exam_date:
            return False
        
        completion_dates = db.get_all_practice_module_completion_dates(trainee_id, db_path)
        
        for module in REQUIRED_PRACTICE_MODULES:
            if module not in completion_dates:
                return False
                
        for module in REQUIRED_PRACTICE_MODULES:
            completion_date = completion_dates[module]
            if not completion_date:
                return False
            if completion_date.split('T')[0] >= first_provincial_exam_date:
                return False
        
        return True
    except Exception as e:
        logger.error(f"Error checking SeeWhy guarantee for trainee {trainee_id}: {e}")
        return False

def forms_practice_summary(trainee_id: int, db_path: Optional[Path] = None) -> Dict[str, bool]:
    """Return a summary of practice exam completion for a trainee."""
    try:
        status = db.get_practice_exam_status_for_trainee(trainee_id, db_path)
        return {mod: status.get(mod, False) for mod in REQUIRED_PRACTICE_MODULES}
    except Exception as e:
        logger.error(f"Error getting practice summary for trainee {trainee_id}: {e}")
        return {mod: False for mod in REQUIRED_PRACTICE_MODULES}

def is_ready_for_reimbursement(trainee_id: int, db_path: Optional[Path] = None) -> bool:
    """Check if trainee is ready for reimbursement based on practice exams."""
    try:
        passed_count = db.get_passed_practice_exam_count(trainee_id, db_path)
        if passed_count >= 4:
            return True
        
        completion_count = db.get_practice_module_completion_count(trainee_id, REQUIRED_PRACTICE_MODULES, db_path)
        return completion_count == len(REQUIRED_PRACTICE_MODULES)
    except Exception as e:
        logger.error(f"Error checking reimbursement readiness for trainee {trainee_id}: {e}")
        return False

def all_practice_modules_complete(trainee_id: int, db_path: Optional[Path] = None) -> bool:
    """Check if all required practice modules are complete."""
    try:
        cnt = db.get_practice_module_completion_count(trainee_id, REQUIRED_PRACTICE_MODULES, db_path)
        return cnt == len(REQUIRED_PRACTICE_MODULES)
    except Exception as e:
        logger.error(f"Error checking practice modules for trainee {trainee_id}: {e}")
        return False

def get_dashboard_stats(db_path: Optional[Path] = None) -> Dict[str, int]:
    """Aggregate high-level stats for the dashboard."""
    try:
        conn = db.get_conn(db_path)
        cur = conn.cursor()
        
        # Trainees
        cur.execute("SELECT COUNT(*) FROM trainee")
        total_trainees = cur.fetchone()[0]
        
        # Exams - Total and Recently passed (last 30 days)
        cur.execute("SELECT COUNT(*) FROM exam")
        total_exams = cur.fetchone()[0]
        
        now = datetime.now().isoformat()
        last_30 = (datetime.now() - timedelta(days=30)).isoformat()
        cur.execute("SELECT COUNT(*) FROM exam WHERE passed = 1 AND exam_date >= ?", (last_30,))
        recent_passes = cur.fetchone()[0]
        
        # Licenses - Pending
        cur.execute("SELECT COUNT(*) FROM license WHERE status != 'Approved' AND status != 'Issued'") # Adjusted logic
        pending_licenses = cur.fetchone()[0]

        # Classes
        cur.execute("SELECT COUNT(*) FROM class WHERE end_date >= ?", (now.split('T')[0],))
        active_classes = cur.fetchone()[0]
        
        # Readiness for Provincial
        cur.execute("SELECT COUNT(*) FROM trainee")
        # For efficiency in a real app, this would be a single SQL bit or a cached value.
        # But let's stay simple:
        cur.execute("SELECT id FROM trainee")
        t_ids = [r[0] for r in cur.fetchall()]
        ready_count = 0
        for tid in t_ids:
            if is_ready_for_provincial_exam(tid, db_path):
                ready_count += 1
        
        conn.close()
        return {
            "total_trainees": total_trainees,
            "total_exams": total_exams,
            "recent_passes": recent_passes,
            "pending_licenses": pending_licenses,
            "active_classes": active_classes,
            "ready_for_provincial": ready_count
        }
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        return {}

def get_recent_activity(db_path: Optional[Path] = None) -> List[Dict[str, str]]:
    """Fetch the latest activity across the app."""
    activities = []
    try:
        conn = db.get_conn(db_path)
        cur = conn.cursor()
        
        # Latest 5 Trainees
        cur.execute("SELECT first_name, last_name, id FROM trainee ORDER BY id DESC LIMIT 5")
        for r in cur.fetchall():
            activities.append({
                "type": "Trainee",
                "label": f"{r['first_name']} {r['last_name']}",
                "timestamp": "" # IDs don't have timestamps, but sort order works
            })
            
        # Latest 5 Exams
        cur.execute("""
            SELECT e.exam_date, e.module, t.last_name, e.passed 
            FROM exam e 
            JOIN trainee t ON e.trainee_id = t.id 
            ORDER BY e.exam_date DESC, e.id DESC LIMIT 5
        """)
        for r in cur.fetchall():
            res = "Passed" if r['passed'] == 1 else "Failed" if r['passed'] == 0 else "Taken"
            activities.append({
                "type": "Exam",
                "label": f"{r['last_name']} ({r['module']}): {res}",
                "timestamp": r['exam_date'] or ""
            })
            
        # Latest 5 Licenses
        cur.execute("""
            SELECT l.application_submitted_date, t.last_name, l.status 
            FROM license l 
            JOIN trainee t ON l.trainee_id = t.id 
            ORDER BY l.id DESC LIMIT 5
        """)
        for r in cur.fetchall():
            activities.append({
                "type": "License",
                "label": f"{r['last_name']}: {r['status']}",
                "timestamp": r['application_submitted_date'] or ""
            })
            
        conn.close()
        
        # Sort by timestamp if available, else by current order (recent first)
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        return activities[:10]
    except Exception as e:
        logger.error(f"Error getting recent activity: {e}")
        return []
def export_to_csv(data: List[Dict[str, Any]], filename: str) -> bool:
    """Export a list of dictionaries to a CSV file."""
    try:
        if not data:
            return False
            
        keys = data[0].keys()
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(data)
        logger.info(f"Successfully exported {len(data)} records to {filename}")
        return True
    except Exception as e:
        logger.error(f"Error exporting to CSV: {e}")
        return False

def get_trainee_export_data(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Fetch all trainee data formatted for export."""
    try:
        rows = db.list_trainees(db_path)
        # Convert row objects to plain dicts for csv.DictWriter
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Error getting trainee export data: {e}")
        return []

def get_license_export_data(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Fetch all license data formatted for export."""
    try:
        rows = db.list_licenses(db_path)
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Error getting license export data: {e}")
        return []

def get_recruiter_export_data(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Fetch all recruiter data formatted for export."""
    try:
        rows = db.list_recruiters(db_path)
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Error getting recruiter export data: {e}")
        return []

def get_recruiter_performance_report(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Calculate pass rates and stats per recruiter."""
    try:
        conn = db.get_conn(db_path); cur = conn.cursor()
        # Join recruiter with trainees and exams
        sql = """
            SELECT r.id, r.name, 
                   COUNT(DISTINCT t.id) as trainee_count,
                   SUM(CASE WHEN e.result = 'Pass' THEN 1 ELSE 0 END) as pass_count,
                   COUNT(e.id) as total_exams
            FROM recruiter r
            LEFT JOIN trainee t ON r.id = t.recruiter_id
            LEFT JOIN exam e ON t.id = e.trainee_id
            GROUP BY r.id, r.name
        """
        cur.execute(sql)
        rows = cur.fetchall(); conn.close()
        
        report = []
        for r in rows:
            pass_count = r['pass_count'] or 0
            total_exams = r['total_exams'] or 0
            pass_rate = (pass_count / total_exams * 100) if total_exams > 0 else 0
            report.append({
                'id': r['id'],
                'name': r['name'],
                'trainees': r['trainee_count'],
                'passes': pass_count,
                'total_exams': total_exams,
                'pass_rate': f"{pass_rate:.1f}%"
            })
        return report
    except Exception as e:
        logger.error(f"Error generating recruiter report: {e}")
        return []

def get_exam_module_stats(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Calculate statistics per exam module to identify difficulty."""
    try:
        conn = db.get_conn(db_path); cur = conn.cursor()
        sql = """
            SELECT module,
                   COUNT(*) as total,
                   SUM(passed) as passes
            FROM exam
            GROUP BY module
        """
        cur.execute(sql)
        rows = cur.fetchall(); conn.close()
        
        # Prepare default stats for all modules
        module_stats = {mod: {'module': mod, 'total': 0, 'passes': 0} for mod in PRACTICE_MODULES}
        
        for r in rows:
            mod = r['module']
            if not mod or mod not in module_stats: 
                continue # Skip unknown modules or nulls
            
            module_stats[mod]['total'] = r['total'] or 0
            module_stats[mod]['passes'] = r['passes'] or 0
            
        # Convert to list and calculate rates
        stats = []
        for mod in PRACTICE_MODULES:
            data = module_stats[mod]
            total = data['total']
            passes = data['passes']
            pct = (passes / total * 100) if total > 0 else 0
            # If no exams taken, maybe show "N/A" or "0.0%"? Let's stick to 0.0% for now or "-"
            # But the UI expects a string. Let's use "N/A" if total is 0 to distinguish from 0% pass rate.
            rate_str = f"{pct:.1f}%" if total > 0 else "N/A"
            
            stats.append({
                'module': mod,
                'total': total,
                'passes': passes,
                'pass_rate': rate_str
            })
        return stats
    except Exception as e:
        logger.error(f"Error getting module stats: {e}")
        return []

def is_ready_for_provincial_exam(trainee_id: int, db_path: Optional[Path] = None) -> bool:
    """Check if trainee has completed all required practice modules."""
    try:
        summary = forms_practice_summary(trainee_id, db_path)
        # All modules must be True
        return all(summary.values()) if summary else False
    except Exception as e:
        logger.error(f"Error checking provincial readiness for trainee {trainee_id}: {e}")
        return False
