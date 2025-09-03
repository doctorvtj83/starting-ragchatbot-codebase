#!/usr/bin/env python3
"""
Test runner for the RAG system backend tests.
Runs all tests and provides clear output about failures.
"""

import unittest
import sys
import os
from io import StringIO

def run_tests():
    """Run all tests and return results"""
    
    # Discover and run tests
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover('tests', pattern='test_*.py')
    
    # Create a test runner with detailed output
    stream = StringIO()
    test_runner = unittest.TextTestRunner(
        stream=stream, 
        verbosity=2,
        descriptions=True,
        failfast=False
    )
    
    print("=" * 70)
    print("RUNNING RAG SYSTEM BACKEND TESTS")
    print("=" * 70)
    
    # Run the tests
    result = test_runner.run(test_suite)
    
    # Get the output
    output = stream.getvalue()
    print(output)
    
    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped) if hasattr(result, 'skipped') else 0
    successful = total_tests - failures - errors - skipped
    
    print(f"Total tests run: {total_tests}")
    print(f"Successful: {successful}")
    print(f"Failures: {failures}")
    print(f"Errors: {errors}")
    print(f"Skipped: {skipped}")
    
    if result.failures:
        print("\nFAILURES:")
        print("-" * 50)
        for test, traceback in result.failures:
            print(f"FAILED: {test}")
            print(f"Traceback:\n{traceback}")
            print("-" * 50)
    
    if result.errors:
        print("\nERRORS:")
        print("-" * 50)
        for test, traceback in result.errors:
            print(f"ERROR: {test}")
            print(f"Traceback:\n{traceback}")
            print("-" * 50)
    
    # Return success status
    success = failures == 0 and errors == 0
    
    if success:
        print("\n🎉 ALL TESTS PASSED! 🎉")
        return 0
    else:
        print(f"\n❌ {failures + errors} tests failed or had errors")
        return 1

if __name__ == '__main__':
    # Change to backend directory if not already there
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(backend_dir)
    
    # Add backend to Python path
    sys.path.insert(0, backend_dir)
    
    exit_code = run_tests()
    sys.exit(exit_code)