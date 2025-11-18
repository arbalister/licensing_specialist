"""
Unit tests for exam tab functions and database interactions.
Tests the following:
- Adding exams
- Listing exams
- Fetching exams by trainee
- Practice exam status management
- Provincial exam info retrieval
"""

import sys
import os
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

import db


def setup_test_data(db_path):
    """Create a test database with sample recruiter, trainee, class, and exam data."""
    db.init_db(db_path)
    
    # Add a recruiter
    recruiter_id = db.add_recruiter(
        name="Test Recruiter",
        email="recruiter@test.com",
        phone="555-0001",
        rep_code="RC001",
        db_path=db_path
    )
    
    # Add a trainee
    trainee_id = db.add_trainee(
        first_name="Test",
        last_name="Trainee",
        recruiter_id=recruiter_id,
        db_path=db_path
    )
    
    # Add a class
    class_id = db.add_class(
        name="Life Sciences",
        db_path=db_path
    )
    
    return recruiter_id, trainee_id, class_id


def test_add_exam():
    """Test adding an exam."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tf:
        db_path = tf.name
    
    try:
        recruiter_id, trainee_id, class_id = setup_test_data(db_path)
        
        # Add an exam
        exam_id = db.add_exam(
            trainee_id=trainee_id,
            class_id=class_id,
            exam_date="2025-11-18",
            score="85",
            notes="Passed",
            db_path=db_path
        )
        
        assert exam_id is not None
        assert isinstance(exam_id, int)
        print(f"✓ test_add_exam: Added exam with ID {exam_id}")
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_list_exams():
    """Test listing all exams."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tf:
        db_path = tf.name
    
    try:
        recruiter_id, trainee_id, class_id = setup_test_data(db_path)
        
        # Add multiple exams
        exam_id_1 = db.add_exam(
            trainee_id=trainee_id,
            class_id=class_id,
            exam_date="2025-11-18",
            score="85",
            notes="Passed",
            db_path=db_path
        )
        
        exam_id_2 = db.add_exam(
            trainee_id=trainee_id,
            class_id=class_id,
            exam_date="2025-11-20",
            score="90",
            notes="Excellent",
            db_path=db_path
        )
        
        # List exams
        exams = db.list_exams(db_path)
        
        assert exams is not None
        assert len(exams) == 2
        # Check for expected fields (from JOIN query in db.py)
        assert all('trainee_id' in e.keys() for e in exams)
        print(f"✓ test_list_exams: Listed {len(exams)} exams")
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_filter_exams_by_trainee():
    """Test filtering exams by trainee_id."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tf:
        db_path = tf.name
    
    try:
        recruiter_id, trainee_id, class_id = setup_test_data(db_path)
        
        # Add another trainee
        trainee_id_2 = db.add_trainee(
            first_name="Test",
            last_name="Trainee2",
            recruiter_id=recruiter_id,
            db_path=db_path
        )
        
        # Add exams for both trainees
        db.add_exam(
            trainee_id=trainee_id,
            class_id=class_id,
            exam_date="2025-11-18",
            score="85",
            notes="Passed",
            db_path=db_path
        )
        
        db.add_exam(
            trainee_id=trainee_id_2,
            class_id=class_id,
            exam_date="2025-11-20",
            score="90",
            notes="Excellent",
            db_path=db_path
        )
        
        # Get all exams
        all_exams = db.list_exams(db_path)
        
        # Filter for trainee 1
        trainee_1_exams = [e for e in all_exams if e['trainee_id'] == trainee_id]
        trainee_2_exams = [e for e in all_exams if e['trainee_id'] == trainee_id_2]
        
        assert len(trainee_1_exams) == 1
        assert len(trainee_2_exams) == 1
        assert trainee_1_exams[0]['trainee_id'] == trainee_id
        assert trainee_2_exams[0]['trainee_id'] == trainee_id_2
        print(f"✓ test_filter_exams_by_trainee: Correctly filtered exams by trainee")
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_exam_data_structure():
    """Test that exam records have expected fields."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tf:
        db_path = tf.name
    
    try:
        recruiter_id, trainee_id, class_id = setup_test_data(db_path)
        
        # Add an exam
        exam_id = db.add_exam(
            trainee_id=trainee_id,
            class_id=class_id,
            exam_date="2025-11-18",
            score="85",
            notes="Passed",
            db_path=db_path
        )
        
        # Fetch the exam
        exams = db.list_exams(db_path)
        exam = exams[0] if exams else None
        
        assert exam is not None
        # Check expected fields (must use dictionary-style access, not .get())
        assert 'id' in exam.keys()
        assert 'trainee_id' in exam.keys()
        assert 'class_id' in exam.keys()
        assert 'exam_date' in exam.keys()
        assert 'score' in exam.keys()
        assert 'notes' in exam.keys()
        assert exam['trainee_id'] == trainee_id
        assert exam['class_id'] == class_id
        assert exam['exam_date'] == "2025-11-18"
        assert exam['score'] == "85"
        assert exam['notes'] == "Passed"
        
        print(f"✓ test_exam_data_structure: Exam has expected fields and values")
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_exam_with_nullable_fields():
    """Test exam creation with NULL fields."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tf:
        db_path = tf.name
    
    try:
        recruiter_id, trainee_id, class_id = setup_test_data(db_path)
        
        # Add an exam with minimal data
        exam_id = db.add_exam(
            trainee_id=trainee_id,
            class_id=None,
            exam_date=None,
            score=None,
            notes=None,
            db_path=db_path
        )
        
        # Fetch the exam
        exams = db.list_exams(db_path)
        exam = exams[0] if exams else None
        
        assert exam is not None
        # Verify nullable fields are handled correctly
        assert exam['trainee_id'] == trainee_id
        assert exam['class_id'] is None
        assert exam['exam_date'] is None
        assert exam['score'] is None
        assert exam['notes'] is None
        
        print(f"✓ test_exam_with_nullable_fields: Nullable fields handled correctly")
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_practice_exam_status_integration():
    """Test practice exam status functions work with exams."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tf:
        db_path = tf.name
    
    try:
        db.init_db(db_path)
        
        # Test practice exam status
        assert db.get_practice_exam_status('Life', db_path) is False
        
        db.update_practice_exam_status('Life', True, db_path)
        assert db.get_practice_exam_status('Life', db_path) is True
        
        status_dict = db.list_practice_exam_status(db_path)
        assert 'Life' in status_dict
        assert status_dict['Life'] is True
        
        print(f"✓ test_practice_exam_status_integration: Practice exam status works")
    finally:
        Path(db_path).unlink(missing_ok=True)


if __name__ == '__main__':
    print("\n=== Running Exam Tab Tests ===\n")
    
    test_add_exam()
    test_list_exams()
    test_filter_exams_by_trainee()
    test_exam_data_structure()
    test_exam_with_nullable_fields()
    test_practice_exam_status_integration()
    
    print("\n✓ All exam tab tests passed!\n")
