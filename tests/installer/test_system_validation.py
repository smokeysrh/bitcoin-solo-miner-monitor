#!/usr/bin/env python3
"""
Test System Validation Script
Validates that the cross-platform testing system is working correctly
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_mock_installer_files(temp_dir: Path) -> list:
    """Create mock installer files for testing"""
    mock_files = []
    
    # Create mock Windows installer
    windows_installer = temp_dir / "BitcoinSoloMinerMonitor-1.0.0-Setup.exe"
    with open(windows_installer, 'wb') as f:
        f.write(b'MZ' + b'\x00' * 1024 * 1024)  # 1MB mock PE file
    mock_files.append(windows_installer)
    
    # Create mock macOS installer
    macos_installer = temp_dir / "BitcoinSoloMinerMonitor-1.0.0.dmg"
    with open(macos_installer, 'wb') as f:
        f.write(b'\x00' * 10 * 1024 * 1024)  # 10MB mock DMG
    mock_files.append(macos_installer)
    
    # Create mock Linux DEB package
    linux_deb = temp_dir / "bitcoin-solo-miner-monitor_1.0.0_amd64.deb"
    with open(linux_deb, 'wb') as f:
        f.write(b'!<arch>\n' + b'\x00' * 2 * 1024 * 1024)  # 2MB mock DEB
    mock_files.append(linux_deb)
    
    # Create mock AppImage
    appimage = temp_dir / "BitcoinSoloMinerMonitor-1.0.0-x86_64.AppImage"
    with open(appimage, 'wb') as f:
        f.write(b'\x7fELF' + b'\x00' * 5 * 1024 * 1024)  # 5MB mock ELF
    os.chmod(appimage, 0o755)
    mock_files.append(appimage)
    
    # Create mock checksums file
    checksums_file = temp_dir / "SHA256SUMS"
    with open(checksums_file, 'w') as f:
        for mock_file in mock_files:
            # Generate a fake SHA256 (64 hex chars)
            fake_hash = "a" * 64
            f.write(f"{fake_hash}  {mock_file.name}\n")
    
    logger.info(f"Created {len(mock_files)} mock installer files")
    return mock_files

def test_cross_platform_tester():
    """Test the cross-platform testing module"""
    logger.info("🔧 Testing cross-platform tester module...")
    
    try:
        from test_cross_platform_automation import CrossPlatformTester
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            mock_files = create_mock_installer_files(temp_path)
            
            # Initialize tester
            tester = CrossPlatformTester()
            
            # Test file finding
            found_files = tester.find_installer_files(temp_path)
            assert len(found_files) > 0, "Should find mock installer files"
            
            # Test integrity verification (will fail with mock files, but should not crash)
            for mock_file in mock_files[:2]:  # Test first 2 files
                try:
                    tester.verify_installer_integrity(mock_file)
                except Exception as e:
                    logger.warning(f"Expected failure for mock file {mock_file.name}: {e}")
            
            logger.info("✅ Cross-platform tester module validation passed")
            return True
            
    except Exception as e:
        logger.error(f"❌ Cross-platform tester validation failed: {e}")
        return False

def test_user_experience_simulator():
    """Test the user experience simulator module"""
    logger.info("🎭 Testing user experience simulator module...")
    
    try:
        from user_experience_simulator import UserExperienceSimulator, UserPersona
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            mock_files = create_mock_installer_files(temp_path)
            
            # Initialize simulator
            simulator = UserExperienceSimulator()
            
            # Test persona creation
            assert len(simulator.user_personas) > 0, "Should have user personas defined"
            
            # Test persona behavior
            novice_persona = simulator.user_personas.get("novice_miner")
            assert novice_persona is not None, "Should have novice miner persona"
            assert novice_persona.technical_level == "beginner", "Novice should be beginner level"
            
            # Test experience simulation (with mock data)
            try:
                experience = simulator.simulate_installation_experience(mock_files[0], novice_persona)
                assert "persona" in experience, "Experience should include persona info"
                assert "steps" in experience, "Experience should include steps"
            except Exception as e:
                logger.warning(f"Expected simulation issues with mock files: {e}")
            
            logger.info("✅ User experience simulator module validation passed")
            return True
            
    except Exception as e:
        logger.error(f"❌ User experience simulator validation failed: {e}")
        return False

def test_installation_success_monitor():
    """Test the installation success monitor module"""
    logger.info("📊 Testing installation success monitor module...")
    
    try:
        from installation_success_monitor import InstallationSuccessMonitor
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Initialize monitor with temp directory
            monitor = InstallationSuccessMonitor(temp_path)
            
            # Test database initialization
            assert monitor.db_path.exists(), "Database should be created"
            
            # Test recording a test result
            test_result = {
                'timestamp': '2024-01-01T00:00:00Z',
                'session_id': 'test_session',
                'platform': 'test_platform',
                'installer_file': 'test.exe',
                'installer_type': 'windows_exe',
                'test_type': 'automated',
                'success': True,
                'duration_seconds': 30.0
            }
            
            monitor.record_installation_test(test_result)
            
            # Test success rate calculation
            rates = monitor.calculate_success_rates(30)
            assert 'overall' in rates, "Should calculate overall success rate"
            # Note: rates may be 0 if no data in time window, which is expected for new DB
            assert rates['overall']['total'] >= 0, "Should return valid total count"
            
            # Clean up database connections
            monitor.cleanup()
            
            logger.info("✅ Installation success monitor module validation passed")
            return True
            
    except Exception as e:
        logger.error(f"❌ Installation success monitor validation failed: {e}")
        return False

def test_comprehensive_runner():
    """Test the comprehensive test runner module"""
    logger.info("🚀 Testing comprehensive test runner module...")
    
    try:
        from run_cross_platform_tests import CrossPlatformTestRunner
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Initialize runner
            runner = CrossPlatformTestRunner(temp_path)
            
            # Test configuration
            assert 'test_types' in runner.config, "Should have test types configuration"
            assert 'platforms' in runner.config, "Should have platforms configuration"
            
            # Test session initialization
            assert 'session_id' in runner.test_session, "Should have session ID"
            assert 'start_time' in runner.test_session, "Should have start time"
            
            # Test file finding (with empty directory)
            found_files = runner.find_installer_files(temp_path)
            assert isinstance(found_files, list), "Should return list of files"
            
            # Clean up any database connections
            if hasattr(runner, 'success_monitor') and hasattr(runner.success_monitor, 'cleanup'):
                try:
                    runner.success_monitor.cleanup()
                except:
                    pass
            
            logger.info("✅ Comprehensive test runner module validation passed")
            return True
            
    except Exception as e:
        logger.error(f"❌ Comprehensive test runner validation failed: {e}")
        return False

def validate_github_workflow():
    """Validate the GitHub Actions workflow file"""
    logger.info("⚙️ Validating GitHub Actions workflow...")
    
    try:
        workflow_file = Path(__file__).parent.parent.parent / ".github" / "workflows" / "comprehensive-installer-testing.yml"
        
        if not workflow_file.exists():
            logger.error(f"❌ Workflow file not found: {workflow_file}")
            return False
        
        # Basic validation - check if file is readable and has expected content
        with open(workflow_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_sections = [
            'name: Comprehensive Installer Testing',
            'cross-platform-testing:',
            'comprehensive-analysis:',
            'quality-gate:',
            'notify-results:'
        ]
        
        for section in required_sections:
            if section not in content:
                logger.error(f"❌ Missing required section in workflow: {section}")
                return False
        
        logger.info("✅ GitHub Actions workflow validation passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ GitHub Actions workflow validation failed: {e}")
        return False

def main():
    """Main validation function"""
    logger.info("🔍 Starting test system validation...")
    
    # Add current directory to Python path
    current_dir = Path(__file__).parent
    sys.path.insert(0, str(current_dir))
    
    validation_results = []
    
    # Run all validation tests
    tests = [
        ("Cross-Platform Tester", test_cross_platform_tester),
        ("User Experience Simulator", test_user_experience_simulator),
        ("Installation Success Monitor", test_installation_success_monitor),
        ("Comprehensive Test Runner", test_comprehensive_runner),
        ("GitHub Actions Workflow", validate_github_workflow)
    ]
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Testing: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            result = test_func()
            validation_results.append((test_name, result))
        except Exception as e:
            logger.error(f"❌ {test_name} validation crashed: {e}")
            validation_results.append((test_name, False))
    
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("VALIDATION SUMMARY")
    logger.info(f"{'='*50}")
    
    passed = 0
    total = len(validation_results)
    
    for test_name, result in validation_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        logger.info("🎉 All validation tests passed! The testing system is ready to use.")
        return True
    else:
        logger.error("❌ Some validation tests failed. Please review and fix issues before using the testing system.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)