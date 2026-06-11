import unittest
import sys
import os

if __name__ == "__main__":
    # Ensure we are in the project root
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(project_root)

    # Discover and run tests in the 'tests' folder
    loader = unittest.TestLoader()
    suite = loader.discover('tests', pattern='test_*.py')

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        try:
            print("\n✅ All Tests Passed! The system is stable.")
        except UnicodeEncodeError:
            print("\n[OK] All Tests Passed! The system is stable.")
        sys.exit(0)
    else:
        try:
            print("\n❌ Some tests failed. Please review the errors above.")
        except UnicodeEncodeError:
            print("\n[ERROR] Some tests failed. Please review the errors above.")
        sys.exit(1)