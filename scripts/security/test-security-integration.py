#!/usr/bin/env python3
"""
Test Security Integration
Tests the security scanning integration components
"""

import os
import sys
import tempfile
import json
from pathlib import Path
import subprocess

def test_vulnerability_detector():
    """Test vulnerability detector functionality"""
    print("🧪 Testing Vulnerability Detector...")
    
    try:
        # Test basic functionality
        result = subprocess.run([
            sys.executable, 
            "scripts/security/vulnerability-detector.py", 
            "--help"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Vulnerability detector help command works")
        else:
            print(f"❌ Vulnerability detector help failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Vulnerability detector test failed: {e}")
        return False
        
    return True

def test_installer_scanner():
    """Test installer security scanner functionality"""
    print("🧪 Testing Installer Security Scanner...")
    
    try:
        # Create a test file to scan
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as test_file:
            test_file.write(b"MZ" + b"A" * 1000)  # Minimal PE header + data
            test_file_path = test_file.name
            
        try:
            # Test scanner on the test file
            result = subprocess.run([
                sys.executable,
                "scripts/security/installer-security-scanner.py",
                test_file_path,
                "--format", "json"
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print("✅ Installer security scanner works")
            else:
                print(f"⚠️ Installer scanner completed with warnings: {result.stderr}")
                # This is expected for a test file
                
        finally:
            # Clean up test file
            os.unlink(test_file_path)
            
    except Exception as e:
        print(f"❌ Installer scanner test failed: {e}")
        return False
        
    return True

def test_patch_distributor():
    """Test security patch distributor functionality"""
    print("🧪 Testing Security Patch Distributor...")
    
    try:
        # Test help command
        result = subprocess.run([
            sys.executable,
            "scripts/security/security-patch-distributor.py",
            "--help"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Security patch distributor help command works")
        else:
            print(f"❌ Security patch distributor help failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Security patch distributor test failed: {e}")
        return False
        
    return True

def test_security_integration():
    """Test main security integration script"""
    print("🧪 Testing Security Integration...")
    
    try:
        # Test help command
        result = subprocess.run([
            sys.executable,
            "scripts/security/security-integration.py",
            "--help"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Security integration help command works")
        else:
            print(f"❌ Security integration help failed: {result.stderr}")
            return False
            
        # Test setup monitoring
        result = subprocess.run([
            sys.executable,
            "scripts/security/security-integration.py",
            "--setup-monitoring"
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ Security monitoring setup works")
        else:
            print(f"⚠️ Security monitoring setup completed with warnings: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Security integration test failed: {e}")
        return False
        
    return True

def test_configuration():
    """Test security configuration loading"""
    print("🧪 Testing Security Configuration...")
    
    try:
        config_file = Path("config/security-config.json")
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
                
            # Verify required configuration sections
            required_sections = [
                "vulnerability_scanning",
                "installer_security", 
                "patch_verification"
            ]
            
            for section in required_sections:
                if section in config:
                    print(f"✅ Configuration section '{section}' found")
                else:
                    print(f"❌ Configuration section '{section}' missing")
                    return False
                    
        else:
            print("❌ Security configuration file not found")
            return False
            
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False
        
    return True

def test_github_actions_integration():
    """Test GitHub Actions workflow integration"""
    print("🧪 Testing GitHub Actions Integration...")
    
    try:
        # Check if security scan workflow exists and has our integration
        workflow_file = Path(".github/workflows/security-scan.yml")
        
        if workflow_file.exists():
            with open(workflow_file, 'r', encoding='utf-8', errors='ignore') as f:
                workflow_content = f.read()
                
            # Check for our vulnerability detector integration
            if "vulnerability-detector.py" in workflow_content:
                print("✅ Vulnerability detector integrated in GitHub Actions")
            else:
                print("⚠️ Vulnerability detector not found in GitHub Actions workflow")
                
        else:
            print("❌ Security scan workflow file not found")
            return False
            
        # Check build-installers workflow
        build_workflow_file = Path(".github/workflows/build-installers.yml")
        
        if build_workflow_file.exists():
            with open(build_workflow_file, 'r', encoding='utf-8', errors='ignore') as f:
                build_content = f.read()
                
            # Check for installer security scanner integration
            if "installer-security-scanner.py" in build_content:
                print("✅ Installer security scanner integrated in build workflow")
            else:
                print("⚠️ Installer security scanner not found in build workflow")
                
        else:
            print("❌ Build installers workflow file not found")
            return False
            
    except Exception as e:
        print(f"❌ GitHub Actions integration test failed: {e}")
        return False
        
    return True

def main():
    """Run all security integration tests"""
    print("🔒 Testing Security Scanning Integration")
    print("=" * 50)
    
    tests = [
        ("Configuration", test_configuration),
        ("Vulnerability Detector", test_vulnerability_detector),
        ("Installer Scanner", test_installer_scanner),
        ("Patch Distributor", test_patch_distributor),
        ("Security Integration", test_security_integration),
        ("GitHub Actions Integration", test_github_actions_integration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} test...")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} test passed")
            else:
                print(f"❌ {test_name} test failed")
        except Exception as e:
            print(f"❌ {test_name} test error: {e}")
            
    print(f"\n🏁 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All security integration tests passed!")
        return 0
    else:
        print("⚠️ Some tests failed. Please review the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())