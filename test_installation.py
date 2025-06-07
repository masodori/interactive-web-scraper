#!/usr/bin/env python3
"""
Simple test script to verify the installation works correctly.
"""

import sys
import importlib

def test_imports():
    """Test that all core modules can be imported"""
    print("Testing core imports...")
    
    try:
        # Test main package
        import scraper
        print("✅ Main package imported successfully")
        
        # Test core modules
        from scraper.core import BaseScraper, EnhancedInteractiveScraper
        print("✅ Core modules imported successfully")
        
        # Test models
        from scraper.models import ExportFormat, ScrapingTemplate
        print("✅ Models imported successfully")
        
        # Test config
        from scraper.config import Config
        print("✅ Config imported successfully")
        
        # Test improved CLI
        from scraper.improved_cli import main as improved_cli_main
        print("✅ Improved CLI imported successfully")
        
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_dependencies():
    """Test that all required dependencies are available"""
    print("\nTesting dependencies...")
    
    required_deps = [
        'selenium',
        'requests', 
        'bs4',  # beautifulsoup4
        'pandas',
        'colorama'
    ]
    
    optional_deps = [
        'playwright'
    ]
    
    for dep in required_deps:
        try:
            importlib.import_module(dep)
            print(f"✅ {dep} available")
        except ImportError:
            print(f"❌ {dep} not available (required)")
            return False
    
    for dep in optional_deps:
        try:
            importlib.import_module(dep)
            print(f"✅ {dep} available (optional)")
        except ImportError:
            print(f"⚠️  {dep} not available (optional)")
    
    return True

def test_cli_help():
    """Test that CLI help works"""
    print("\nTesting CLI functionality...")
    
    try:
        from scraper.improved_cli import main
        print("✅ CLI main function accessible")
        return True
    except Exception as e:
        print(f"❌ CLI test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Interactive Web Scraper v2.0 - Installation Test")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_dependencies,
        test_cli_help
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! Installation is working correctly.")
        print("\nTo get started:")
        print("  python -m scraper.improved_cli")
        return 0
    else:
        print("❌ Some tests failed. Please check dependencies.")
        return 1

if __name__ == "__main__":
    sys.exit(main())