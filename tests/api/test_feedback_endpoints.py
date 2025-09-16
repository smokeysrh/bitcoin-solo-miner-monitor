"""
API tests for feedback endpoints.
"""

import pytest
import requests
import json
import tempfile
import shutil
from pathlib import Path


# Use the live server for testing since TestClient has compatibility issues
BASE_URL = "http://localhost:8000"


def test_server_is_running():
    """Test that the server is running and accessible."""
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        assert response.status_code in [200, 404]  # Either endpoint exists or 404 is fine
    except requests.exceptions.ConnectionError:
        pytest.skip("Server is not running. Start the server with 'python run.py' to run these tests.")


def test_submit_feedback_success():
    """Test successful feedback submission"""
    test_server_is_running()  # Ensure server is running
    
    feedback_data = {
        "category": "installation",
        "message": "Test feedback message for installation issues",
        "user_id": "test_user_123",
        "installer_version": "1.0.0",
        "system_info": {"os": "Windows 10", "arch": "x64"},
        "severity": "medium"
    }
    
    response = requests.post(f"{BASE_URL}/api/feedback/submit", json=feedback_data, timeout=5)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "feedback_id" in data["data"]


def test_submit_feedback_invalid_category():
    """Test feedback submission with invalid category"""
    test_server_is_running()  # Ensure server is running
    
    feedback_data = {
        "category": "invalid_category",
        "message": "Test feedback message",
        "user_id": "test_user"
    }
    
    response = requests.post(f"{BASE_URL}/api/feedback/submit", json=feedback_data, timeout=5)
    
    assert response.status_code == 422  # Validation error


def test_submit_feedback_missing_field():
    """Test feedback submission with missing required field"""
    test_server_is_running()  # Ensure server is running
    
    feedback_data = {
        "category": "installation",
        "message": "Test feedback message"
        # Missing user_id
    }
    
    response = requests.post(f"{BASE_URL}/api/feedback/submit", json=feedback_data, timeout=5)
    
    assert response.status_code == 422  # Validation error


def test_get_feedback_summary():
    """Test getting feedback summary"""
    test_server_is_running()  # Ensure server is running
    
    # Submit test feedback first
    feedback_data = {
        "category": "bugs",
        "message": "Test bug report for summary test",
        "user_id": "test_user_summary",
        "severity": "high"
    }
    
    requests.post(f"{BASE_URL}/api/feedback/submit", json=feedback_data, timeout=5)
    
    # Get summary
    response = requests.get(f"{BASE_URL}/api/feedback/summary", timeout=5)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "total_feedback" in data["data"]
    assert "categories" in data["data"]


def test_get_feedback_by_category():
    """Test getting feedback by category"""
    test_server_is_running()  # Ensure server is running
    
    # Submit feedback in installation category
    feedback_data = {
        "category": "installation",
        "message": "Installation issue for category test",
        "user_id": "test_user_category"
    }
    
    requests.post(f"{BASE_URL}/api/feedback/submit", json=feedback_data, timeout=5)
    
    # Get installation feedback
    response = requests.get(f"{BASE_URL}/api/feedback/category/installation", timeout=5)
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Check if our feedback is in the results (there might be other feedback too)
    installation_feedback = [item for item in data if item.get("user_id") == "test_user_category"]
    assert len(installation_feedback) >= 1


def test_feedback_endpoints_exist():
    """Test that feedback endpoints are properly registered"""
    test_server_is_running()  # Ensure server is running
    
    # Test that endpoints exist (even if they return errors due to missing data/auth)
    endpoints_to_test = [
        "/api/feedback/summary",
        "/api/feedback/category/installation",
        "/api/feedback/export"
    ]
    
    for endpoint in endpoints_to_test:
        response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
        # Should not return 404 (endpoint not found)
        assert response.status_code != 404, f"Endpoint {endpoint} not found"


def run_simple_tests():
    """Run tests without pytest for debugging."""
    print("Running simple feedback endpoint tests...")
    
    try:
        # Test server connectivity
        try:
            response = requests.get(f"{BASE_URL}/api/health", timeout=5)
            print("✅ Server is accessible")
        except requests.exceptions.ConnectionError:
            print("❌ Server is not running. Start with 'python run.py'")
            return
        
        # Test feedback submission
        feedback_data = {
            "category": "installation",
            "message": "Simple test feedback message",
            "user_id": "simple_test_user"
        }
        
        response = requests.post(f"{BASE_URL}/api/feedback/submit", json=feedback_data, timeout=5)
        if response.status_code == 200:
            print("✅ Feedback submission test passed")
        else:
            print(f"❌ Feedback submission failed: {response.status_code} - {response.text}")
        
        # Test feedback summary
        response = requests.get(f"{BASE_URL}/api/feedback/summary", timeout=5)
        if response.status_code == 200:
            print("✅ Feedback summary test passed")
        else:
            print(f"❌ Feedback summary failed: {response.status_code} - {response.text}")
        
        # Test feedback by category
        response = requests.get(f"{BASE_URL}/api/feedback/category/installation", timeout=5)
        if response.status_code == 200:
            print("✅ Feedback by category test passed")
        else:
            print(f"❌ Feedback by category failed: {response.status_code} - {response.text}")
        
        print("🎉 All simple tests completed!")
        
    except Exception as e:
        print(f"❌ Simple tests failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Add the project root to the path for imports
    import sys
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    # Try pytest first, fall back to simple tests
    try:
        pytest.main([__file__, "-v"])
    except ImportError:
        print("Pytest not available, running simple tests...")
        run_simple_tests()