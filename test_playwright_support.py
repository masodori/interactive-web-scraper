#!/usr/bin/env python3
"""
Test script to verify Playwright support in the interactive scraper.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from scraper.core.enhanced_interactive_scraper_v2 import EnhancedInteractiveScraperV2
from scraper.core.playwright_sync_wrapper import PLAYWRIGHT_AVAILABLE


def test_playwright_wrapper():
    """Test basic Playwright wrapper functionality."""
    print("=" * 50)
    print("🧪 Testing Playwright Support")
    print("=" * 50)
    
    # Check if Playwright is installed
    if not PLAYWRIGHT_AVAILABLE:
        print("❌ Playwright is not installed.")
        print("   Install with: pip install playwright && playwright install")
        return False
    
    print("✅ Playwright is installed")
    
    # Test creating scraper with Playwright
    try:
        print("\n📋 Creating Playwright-based scraper...")
        scraper = EnhancedInteractiveScraperV2(engine="playwright", headless=True)
        print("✅ Scraper created successfully")
        
        # Test navigation
        print("\n🌐 Testing navigation...")
        success = scraper.navigate_to("https://example.com")
        if success:
            print("✅ Navigation successful")
        else:
            print("❌ Navigation failed")
            return False
        
        # Test JavaScript execution
        print("\n🔧 Testing JavaScript execution...")
        title = scraper.execute_script("return document.title")
        print(f"✅ Page title: {title}")
        
        # Test interactive selector injection
        print("\n🎯 Testing interactive selector injection...")
        if scraper.inject_interactive_selector("Test selection"):
            print("✅ Interactive selector injected successfully")
            
            # Check if overlay exists
            overlay_exists = scraper.execute_script(
                "return !!document.getElementById('scrapeOverlay')"
            )
            if overlay_exists:
                print("✅ Overlay created successfully")
            else:
                print("❌ Overlay not found")
        else:
            print("❌ Failed to inject interactive selector")
        
        # Clean up
        scraper.close()
        print("\n✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False


def compare_engines():
    """Compare Selenium vs Playwright for interactive selection."""
    print("\n" + "=" * 50)
    print("🔄 Comparing Selenium vs Playwright")
    print("=" * 50)
    
    test_url = "https://example.com"
    
    # Test Selenium
    print("\n1️⃣ Testing Selenium...")
    try:
        selenium_scraper = EnhancedInteractiveScraperV2(engine="selenium", headless=True)
        selenium_scraper.navigate_to(test_url)
        selenium_success = selenium_scraper.inject_interactive_selector("Selenium test")
        selenium_scraper.close()
        print(f"   Result: {'✅ Success' if selenium_success else '❌ Failed'}")
    except Exception as e:
        print(f"   Result: ❌ Error - {e}")
        selenium_success = False
    
    # Test Playwright
    print("\n2️⃣ Testing Playwright...")
    if PLAYWRIGHT_AVAILABLE:
        try:
            playwright_scraper = EnhancedInteractiveScraperV2(engine="playwright", headless=True)
            playwright_scraper.navigate_to(test_url)
            playwright_success = playwright_scraper.inject_interactive_selector("Playwright test")
            playwright_scraper.close()
            print(f"   Result: {'✅ Success' if playwright_success else '❌ Failed'}")
        except Exception as e:
            print(f"   Result: ❌ Error - {e}")
            playwright_success = False
    else:
        print("   Result: ⚠️  Not installed")
        playwright_success = False
    
    # Summary
    print("\n📊 Summary:")
    print(f"   Selenium: {'✅ Working' if selenium_success else '❌ Not working'}")
    print(f"   Playwright: {'✅ Working' if playwright_success else '❌ Not working'}")


if __name__ == "__main__":
    # Run tests
    if test_playwright_wrapper():
        compare_engines()
    
    print("\n✨ Testing complete!")