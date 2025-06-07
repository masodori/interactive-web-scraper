#!/usr/bin/env python3
"""
Test script to verify Playwright interactive selection works properly.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from scraper.core.multi_engine_interactive_scraper import MultiEngineInteractiveScraper


def test_playwright_interactive():
    """Test Playwright with interactive selection."""
    print("=" * 50)
    print("🧪 Testing Playwright Interactive Selection")
    print("=" * 50)
    
    # Create scraper with Playwright
    print("\n📋 Creating Playwright scraper...")
    scraper = MultiEngineInteractiveScraper(engine="playwright", headless=True)
    
    # Verify engine is set correctly
    print(f"✅ Engine: {scraper.engine}")
    
    # Test navigation
    print("\n🌐 Navigating to example.com...")
    success = scraper.navigate_to("https://example.com")
    print(f"✅ Navigation: {'Success' if success else 'Failed'}")
    
    # Test engine selection override
    print("\n🔧 Testing _select_engine() override...")
    selected_engine = scraper._select_engine()
    print(f"✅ Selected engine: {selected_engine}")
    
    if selected_engine != "playwright":
        print("❌ ERROR: Engine override not working!")
        print(f"   Expected: playwright")
        print(f"   Got: {selected_engine}")
    else:
        print("✅ Engine override working correctly!")
    
    # Clean up
    scraper.close()
    print("\n✨ Test complete!")


if __name__ == "__main__":
    test_playwright_interactive()