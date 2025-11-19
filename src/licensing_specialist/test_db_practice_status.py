import sys
import os
import tempfile
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import db

def test_practice_exam_status():
    """Test practice exam status CRUD for a single trainee."""
    with tempfile.NamedTemporaryFile(suffix='.db') as tf:
        db_path = tf.name
        db.init_db(db_path)
        # Add a trainee
        trainee_id = db.add_trainee("Test", "User", db_path=db_path)
        # Should be incomplete by default
        assert db.get_practice_exam_status(trainee_id, 'Life', db_path) is False
        # Set to complete
        db.update_practice_exam_status(trainee_id, 'Life', True, db_path)
        assert db.get_practice_exam_status(trainee_id, 'Life', db_path) is True
        # Set to incomplete
        db.update_practice_exam_status(trainee_id, 'Life', False, db_path)
        assert db.get_practice_exam_status(trainee_id, 'Life', db_path) is False
        # List status
        db.update_practice_exam_status(trainee_id, 'A&S', True, db_path)
        status = db.get_practice_exam_status_for_trainee(trainee_id, db_path)
        assert status['A&S'] is True
        assert status['Life'] is False
        # Reset all
        db.reset_practice_exam_statuses_for_trainee(trainee_id, db_path)
        status = db.get_practice_exam_status_for_trainee(trainee_id, db_path)
        assert all(not v for v in status.values())

if __name__ == '__main__':
    test_practice_exam_status()
    print('Practice exam status DB tests passed.')
