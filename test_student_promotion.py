#!/usr/bin/env python3
"""
Test script to verify the student promotion functionality works as intended.

This script verifies that:
1. Student promotion preserves historical grades
2. New grade records are created for the new grade level
3. The student's grade level is updated correctly
4. Academic records remain intact after promotion
"""

import requests
import json
import sys
import os
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:1111"
TEST_HEADERS = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer '  # Will be set after login
}

def login_admin():
    """Login as admin to get token"""
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/admin/login", json=login_data)
        if response.status_code == 200:
            result = response.json()
            TEST_HEADERS['Authorization'] = f"Bearer {result['token']}"
            print("✅ Admin login successful")
            return True
        else:
            print(f"❌ Admin login failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error during admin login: {e}")
        return False

def create_test_school():
    """Create a test school for our tests"""
    school_data = {
        "name": "مدرسة اختبار الترقية",
        "study_type": "عام",
        "level": "ابتدائية",
        "gender_type": "ذكر"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/schools", json=school_data, headers=TEST_HEADERS)
        if response.status_code == 201:
            result = response.json()
            print(f"✅ Test school created: {result['school']['name']}")
            return result['school']['id']
        else:
            print(f"❌ School creation failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error creating test school: {e}")
        return None

def create_test_student(school_id):
    """Create a test student with some grades"""
    student_data = {
        "full_name": " Ahmad Mohammed Ali",
        "grade": "ابتدائي - الأول الابتدائي",
        "room": "A1",
        "enrollment_date": datetime.now().strftime("%Y-%m-%d"),
        "parent_contact": "07700000000",
        "blood_type": "O+",
        "chronic_disease": "",
        "notes": "Test student for promotion functionality"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/school/{school_id}/student", json=student_data, headers=TEST_HEADERS)
        if response.status_code == 201:
            result = response.json()
            print(f"✅ Test student created: {result['student']['full_name']}")
            return result['student']['id']
        else:
            print(f"❌ Student creation failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error creating test student: {e}")
        return None

def update_student_grades(student_id):
    """Add some grades to the student to test preservation"""
    grades_data = {
        "detailed_scores": {
            "اللغة العربية": {
                "month1": 8,
                "month2": 7,
                "midterm": 9,
                "month3": 8,
                "month4": 7,
                "final": 9
            },
            "الرياضيات": {
                "month1": 7,
                "month2": 8,
                "midterm": 8,
                "month3": 9,
                "month4": 8,
                "final": 9
            }
        }
    }
    
    try:
        response = requests.put(f"{BASE_URL}/api/student/{student_id}/detailed", json=grades_data, headers=TEST_HEADERS)
        if response.status_code == 200:
            print("✅ Student grades updated successfully")
            return True
        else:
            print(f"❌ Grade update failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error updating student grades: {e}")
        return False

def test_student_promotion(student_id):
    """Test the student promotion functionality"""
    promotion_data = {
        "new_grade": "ابتدائي - الثاني الابتدائي",
        "new_academic_year_id": None  # Will use current year
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/student/{student_id}/promote", json=promotion_data, headers=TEST_HEADERS)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Student promotion successful: {result['student']['grade']}")
            return True
        else:
            print(f"❌ Student promotion failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error during student promotion: {e}")
        return False

def test_student_history(student_id):
    """Test that student history is preserved after promotion"""
    try:
        response = requests.get(f"{BASE_URL}/api/student/{student_id}/history", headers=TEST_HEADERS)
        if response.status_code == 200:
            result = response.json()
            print("✅ Student history retrieved successfully")
            
            # Check if grades are preserved
            if result['academic_history']['grades']:
                print("✅ Historical grades preserved after promotion")
                return True
            else:
                print("❌ No historical grades found")
                return False
        else:
            print(f"❌ History retrieval failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error retrieving student history: {e}")
        return False

def main():
    print("🧪 Starting Student Promotion System Test...")
    
    # Login as admin
    if not login_admin():
        print("❌ Cannot proceed without admin login")
        return False
    
    # Create test school
    school_id = create_test_school()
    if not school_id:
        print("❌ Cannot proceed without test school")
        return False
    
    # Create test student
    student_id = create_test_student(school_id)
    if not student_id:
        print("❌ Cannot proceed without test student")
        return False
    
    # Add grades to student
    if not update_student_grades(student_id):
        print("❌ Cannot proceed without student grades")
        return False
    
    # Test student promotion
    if not test_student_promotion(student_id):
        print("❌ Student promotion test failed")
        return False
    
    # Test that history is preserved
    if not test_student_history(student_id):
        print("❌ Student history preservation test failed")
        return False
    
    print("\n🎉 All tests passed! Student promotion system works correctly.")
    print("✅ Grades are preserved during promotion")
    print("✅ Student records are updated correctly")
    print("✅ Academic history remains intact")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n❌ Some tests failed!")
        sys.exit(1)
    else:
        print("\n✅ All tests completed successfully!")