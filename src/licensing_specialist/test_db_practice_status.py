import sys
import os
import tempfile
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db import *

def test_practice_exam_status():
    # Use a temp DB file
    with tempfile.NamedTemporaryFile(suffix='.db') as tf:
        db_path = tf.name
        init_db(db_path)
        # Should be incomplete by default
        assert get_practice_exam_status('Life', db_path) is False
        # Set to complete
        update_practice_exam_status('Life', True, db_path)
        assert get_practice_exam_status('Life', db_path) is True
        # Set to incomplete
        update_practice_exam_status('Life', False, db_path)
        assert get_practice_exam_status('Life', db_path) is False
        # List status
        update_practice_exam_status('A&S', True, db_path)
        status = list_practice_exam_status(db_path)
        assert status['A&S'] is True
        assert status['Life'] is False
        # Reset all
        reset_practice_exam_statuses(db_path)
        status = list_practice_exam_status(db_path)
        assert all(not v for v in status.values())

if __name__ == '__main__':
    test_practice_exam_status()
    print('Practice exam status DB tests passed.')
