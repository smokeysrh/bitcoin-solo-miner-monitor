#!/usr/bin/env python3
"""
Test Runner

This script runs all tests for the Bitcoin Solo Miner Monitoring App.
"""

import unittest
import argparse
import sys
import os
import logging
from typing import List, Optional

# Add parent directory to path to allow importing from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


def discover_tests(test_path: str, pattern: str = 'test_*.py') -> unittest.TestSuite:
    """
    Discover tests in the specified path.
    
    Args:
        test_path (str): Path to search for tests
        pattern (str, optional): Pattern to match test files. Defaults to 'test_*.py'.
        
    Returns:
        unittest.TestSuite: Test suite containing discovered tests
    """
    return unittest.defaultTestLoader.discover(test_path, pattern=pattern)


def run_tests(test_suite: unittest.TestSuite, verbosity: int = 2) -> unittest.TestResult:
    """
    Run the specified test suite.
    
    Args:
        test_suite (unittest.TestSuite): Test suite to run
        verbosity (int, optional): Verbosity level. Defaults to 2.
        
    Returns:
        unittest.TestResult: Test results
    """
    runner = unittest.TextTestRunner(verbosity=verbosity)
    return runner.run(test_suite)


def main():
    """
    Main entry point.
    """
    parser = argparse.ArgumentParser(description="Run tests for Bitcoin Solo Miner Monitoring App")
    parser.add_argument("--path", type=str, default="src/tests", help="Path to search for tests")
    parser.add_argument("--pattern", type=str, default="test_*.py", help="Pattern to match test files")
    parser.add_argument("--verbosity", type=int, default=2, help="Verbosity level (1-3)")
    parser.add_argument("--specific", type=str, help="Run a specific test module (e.g., miners.test_bitaxe_miner)")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run specific test if specified
    if args.specific:
        specific_module = args.specific.replace('/', '.').replace('\\', '.')
        if specific_module.endswith('.py'):
            specific_module = specific_module[:-3]
        
        print(f"Running specific test module: {specific_module}")
        test_suite = unittest.defaultTestLoader.loadTestsFromName(specific_module)
    else:
        # Discover and run all tests
        print(f"Discovering tests in {args.path} with pattern {args.pattern}")
        test_suite = discover_tests(args.path, args.pattern)
    
    # Run tests
    result = run_tests(test_suite, args.verbosity)
    
    # Print summary
    print("\n=== Test Summary ===")
    print(f"Ran {result.testsRun} tests")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    # Exit with non-zero code if any tests failed
    if result.failures or result.errors:
        sys.exit(1)


if __name__ == "__main__":
    main()