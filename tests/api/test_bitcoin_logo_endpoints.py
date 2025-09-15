"""
Test Bitcoin Logo API Endpoints

Tests for the /bitcoin-symbol.svg and /bitcoin-symbol.png endpoints
to ensure they serve the official Bitcoin logos correctly.
"""

import pytest
import requests
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


def test_bitcoin_symbol_svg_endpoint():
    """Test that the SVG endpoint serves the Bitcoin symbol correctly."""
    test_server_is_running()  # Ensure server is running
    
    response = requests.get(f"{BASE_URL}/bitcoin-symbol.svg", timeout=5)
    
    # Check status code
    assert response.status_code == 200
    
    # Check content type
    assert response.headers["content-type"] == "image/svg+xml"
    
    # Check caching headers
    assert "cache-control" in response.headers
    assert "public" in response.headers["cache-control"]
    assert "max-age=31536000" in response.headers["cache-control"]
    
    # Check ETag header
    assert "etag" in response.headers
    
    # Check content is not empty
    assert len(response.content) > 0
    
    # Check that it's actually SVG content
    content = response.text
    assert content.startswith('<?xml') or content.startswith('<svg') or '<svg' in content


def test_bitcoin_symbol_png_endpoint():
    """Test that the PNG endpoint serves the Bitcoin symbol correctly."""
    test_server_is_running()  # Ensure server is running
    
    response = requests.get(f"{BASE_URL}/bitcoin-symbol.png", timeout=5)
    
    # Check status code
    assert response.status_code == 200
    
    # Check content type
    assert response.headers["content-type"] == "image/png"
    
    # Check caching headers
    assert "cache-control" in response.headers
    assert "public" in response.headers["cache-control"]
    assert "max-age=31536000" in response.headers["cache-control"]
    
    # Check ETag header
    assert "etag" in response.headers
    
    # Check content is not empty
    assert len(response.content) > 0
    
    # Check PNG magic bytes
    assert response.content.startswith(b'\x89PNG\r\n\x1a\n')


def test_bitcoin_logo_files_exist():
    """Test that the Bitcoin logo files exist in the assets directory."""
    # Import here to avoid module path issues
    try:
        from src.backend.utils.app_paths import get_app_paths
        app_paths = get_app_paths()
        base_path = app_paths.base_path
    except ImportError:
        # Fallback to relative path from test file
        base_path = Path(__file__).parent.parent.parent
    
    svg_path = base_path / "assets" / "bitcoin-symbol.svg"
    png_path = base_path / "assets" / "bitcoin-symbol.png"
    
    assert svg_path.exists(), f"Bitcoin SVG not found at {svg_path}"
    assert png_path.exists(), f"Bitcoin PNG not found at {png_path}"
    
    # Check file sizes are reasonable
    assert svg_path.stat().st_size > 100, "SVG file seems too small"
    assert png_path.stat().st_size > 1000, "PNG file seems too small"


def test_bitcoin_logo_404_handling():
    """Test 404 handling when Bitcoin logo files don't exist."""
    test_server_is_running()  # Ensure server is running
    
    # Test non-existent file that should trigger the SPA handler's 404 for static files
    response = requests.get(f"{BASE_URL}/nonexistent-file.svg", timeout=5)
    assert response.status_code == 404
    
    # Test non-existent PNG file
    response = requests.get(f"{BASE_URL}/nonexistent-file.png", timeout=5)
    assert response.status_code == 404


def test_bitcoin_logo_caching_headers():
    """Test that caching headers are set correctly for performance."""
    test_server_is_running()  # Ensure server is running
    
    # Test SVG caching
    response = requests.get(f"{BASE_URL}/bitcoin-symbol.svg", timeout=5)
    assert response.status_code == 200
    
    cache_control = response.headers.get("cache-control", "")
    assert "public" in cache_control
    assert "max-age=31536000" in cache_control  # 1 year
    
    # Test PNG caching
    response = requests.get(f"{BASE_URL}/bitcoin-symbol.png", timeout=5)
    assert response.status_code == 200
    
    cache_control = response.headers.get("cache-control", "")
    assert "public" in cache_control
    assert "max-age=31536000" in cache_control  # 1 year


def test_bitcoin_logo_etag_support():
    """Test that ETag headers are provided for efficient caching."""
    test_server_is_running()  # Ensure server is running
    
    # Test SVG ETag
    response = requests.get(f"{BASE_URL}/bitcoin-symbol.svg", timeout=5)
    assert response.status_code == 200
    assert "etag" in response.headers
    assert len(response.headers["etag"]) > 0
    
    # Test PNG ETag
    response = requests.get(f"{BASE_URL}/bitcoin-symbol.png", timeout=5)
    assert response.status_code == 200
    assert "etag" in response.headers
    assert len(response.headers["etag"]) > 0


def run_simple_tests():
    """Run tests without pytest for debugging."""
    print("Running simple Bitcoin logo endpoint tests...")
    
    # Test file existence
    try:
        test_bitcoin_logo_files_exist()
        print("✅ Bitcoin logo files exist")
    except Exception as e:
        print(f"❌ File existence test failed: {e}")
    
    # Test API endpoints using requests
    try:
        import requests
        
        # Test server connectivity
        try:
            response = requests.get(f"{BASE_URL}/api/health", timeout=5)
            print("✅ Server is accessible")
        except requests.exceptions.ConnectionError:
            print("❌ Server is not running. Start with 'python run.py'")
            return
        
        # Test SVG endpoint
        response = requests.get(f"{BASE_URL}/bitcoin-symbol.svg", timeout=5)
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/svg+xml"
        assert "cache-control" in response.headers
        assert "etag" in response.headers
        print("✅ SVG endpoint test passed")
        
        # Test PNG endpoint
        response = requests.get(f"{BASE_URL}/bitcoin-symbol.png", timeout=5)
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert "cache-control" in response.headers
        assert "etag" in response.headers
        print("✅ PNG endpoint test passed")
        
        # Test 404 handling
        response = requests.get(f"{BASE_URL}/nonexistent-file.svg", timeout=5)
        assert response.status_code == 404
        print("✅ 404 handling test passed")
        
        print("🎉 All tests passed!")
        
    except Exception as e:
        print(f"❌ API tests failed: {e}")
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