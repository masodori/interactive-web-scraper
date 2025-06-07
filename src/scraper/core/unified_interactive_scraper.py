# src/scraper/core/unified_interactive_scraper.py
"""
Unified Interactive Scraper - Consolidates all interactive functionality
Supports Selenium, Playwright, and Requests engines with consistent interface
"""

import time
import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urlparse
from datetime import datetime

# Engine-specific imports with fallbacks
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import WebDriverException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# Core imports
from .base_scraper import BaseScraper
from .playwright_scraper import PlaywrightScraper
from .requests_scraper import RequestScraper
from ..models import (
    ScrapingTemplate, SiteInfo, ScrapingType, TemplateRules, 
    LoadStrategy, LoadStrategyConfig
)
from ..handlers.cookie_handler import CookieHandler
from ..extractors.pattern_extractor import PatternExtractor
from ..config import Config


class UnifiedInteractiveScraper:
    """
    Unified scraper that provides consistent interface across all engines
    Handles interactive element selection, template creation, and data extraction
    """
    
    def __init__(self, engine: str = 'selenium', headless: bool = False):
        """
        Initialize unified scraper
        
        Args:
            engine: Scraping engine ('selenium', 'playwright', 'requests')
            headless: Run browser in headless mode (for browser engines)
        """
        self.logger = logging.getLogger(f'{__name__}.UnifiedInteractiveScraper')
        self.config = Config()
        self.engine = engine
        self.headless = headless
        
        # Initialize components
        self.pattern_extractor = PatternExtractor()
        self.scraper = None
        self.cookie_handler = None
        
        # State tracking
        self.current_url = None
        self.is_initialized = False
        
        self.logger.info(f"Unified scraper created with {engine} engine")

    def initialize(self) -> bool:
        """Initialize the selected scraping engine"""
        try:
            if self.engine == 'selenium':
                return self._init_selenium()
            elif self.engine == 'playwright':
                return self._init_playwright()
            elif self.engine == 'requests':
                return self._init_requests()
            else:
                raise ValueError(f"Unsupported engine: {self.engine}")
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.engine} engine: {e}")
            return False

    def _init_selenium(self) -> bool:
        """Initialize Selenium engine"""
        if not SELENIUM_AVAILABLE:
            self.logger.error("Selenium is not available")
            return False
        
        try:
            chrome_options = ChromeOptions()
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            if self.headless:
                chrome_options.add_argument('--headless')
            
            self.scraper = BaseScraper(headless=self.headless, options=chrome_options)
            self.cookie_handler = CookieHandler(self.scraper.driver, self.config)
            
            self.is_initialized = True
            self.logger.info("Selenium engine initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Selenium initialization failed: {e}")
            return False

    def _init_playwright(self) -> bool:
        """Initialize Playwright engine"""
        if not PLAYWRIGHT_AVAILABLE:
            self.logger.error("Playwright is not available")
            return False
        
        try:
            self.scraper = PlaywrightScraper(headless=self.headless)
            # Initialize browser asynchronously
            asyncio.run(self.scraper._init_browser())
            
            self.is_initialized = True
            self.logger.info("Playwright engine initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Playwright initialization failed: {e}")
            return False

    def _init_requests(self) -> bool:
        """Initialize Requests engine"""
        try:
            self.scraper = RequestScraper(self.config)
            self.is_initialized = True
            self.logger.info("Requests engine initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Requests initialization failed: {e}")
            return False

    def navigate_to(self, url: str) -> bool:
        """Navigate to URL with engine-specific handling"""
        if not self.is_initialized:
            self.logger.error("Scraper not initialized")
            return False
        
        self.logger.info(f"Navigating to: {url}")
        
        try:
            if self.engine == 'selenium':
                success = self.scraper.navigate_to(url)
            elif self.engine == 'playwright':
                success = asyncio.run(self.scraper.navigate_to_smart(url))
            else:  # requests
                # For requests, validate and fetch the page
                if self._validate_url(url):
                    soup = self.scraper.navigate_to(url)
                    success = soup is not None
                else:
                    success = False
            
            if success:
                self.current_url = url
                self.logger.info("Navigation successful")
            else:
                self.logger.error("Navigation failed")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Navigation error: {e}")
            return False

    def _validate_url(self, url: str) -> bool:
        """Validate URL for requests engine"""
        try:
            parsed = urlparse(url)
            return bool(parsed.netloc and parsed.scheme)
        except:
            return False

    def handle_cookies(self, custom_selectors: Optional[List[str]] = None) -> bool:
        """Handle cookie consent banners"""
        if self.engine == 'requests':
            return True  # No cookies to handle
        
        try:
            if self.engine == 'selenium' and self.cookie_handler:
                result = self.cookie_handler.accept_cookies(custom_selectors)
                return bool(result)
            elif self.engine == 'playwright':
                result = asyncio.run(self.scraper.handle_cookies(custom_selectors))
                return bool(result)
            
        except Exception as e:
            self.logger.error(f"Cookie handling error: {e}")
        
        return False

    def inject_interactive_selector(self, context_message: str = "Select elements") -> bool:
        """Inject interactive selector for element selection"""
        if self.engine not in ['selenium', 'playwright']:
            self.logger.warning(f"Interactive selection not supported for {self.engine} engine")
            return False
        
        try:
            self.logger.info(f"Injecting interactive selector with message: '{context_message}'")
            if self.engine == 'selenium':
                result = self.scraper.inject_interactive_selector(context_message)
                if not result:
                    self.logger.error("Failed to inject interactive selector in BaseScraper")
                return result
            else:  # playwright
                # For Playwright, we'd need to implement similar functionality
                # For now, return False to indicate manual selection needed
                self.logger.warning("Interactive selection not yet implemented for Playwright")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to inject interactive selector: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False

    def get_selected_element_data(self) -> Optional[Dict[str, Any]]:
        """Get data from interactively selected element"""
        if self.engine not in ['selenium', 'playwright']:
            return None
        
        try:
            if self.engine == 'selenium':
                return self.scraper.get_selected_element_data()
            else:  # playwright
                # Implement for Playwright
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get selected element data: {e}")
            return None

    def cleanup_interactive_selector(self):
        """Clean up interactive selector overlay"""
        if self.engine not in ['selenium', 'playwright']:
            return
        
        try:
            cleanup_js = """
            // Remove the overlay
            const overlay = document.getElementById('scrapeOverlay');
            if (overlay) {
                overlay.remove();
            }
            
            // Remove any highlights
            document.querySelectorAll('[style*="outline"]').forEach(el => {
                el.style.outline = '';
            });
            
            // Remove hidden input
            const hiddenInput = document.getElementById('selected_element_data');
            if (hiddenInput) {
                hiddenInput.remove();
            }
            """
            
            if self.engine == 'selenium':
                self.scraper.driver.execute_script(cleanup_js)
            else:  # playwright
                asyncio.run(self.scraper.page.evaluate(cleanup_js))
                
            self.logger.info("Interactive selector cleaned up")
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup interactive selector: {e}")

    def extract_data(self, selector: str, attribute: str = 'text') -> Optional[str]:
        """Extract data from element using selector"""
        if not self.is_initialized:
            return None
        
        try:
            if self.engine == 'selenium':
                element = self.scraper.driver.find_element(By.CSS_SELECTOR, selector)
                if attribute == 'text':
                    return element.text
                else:
                    return element.get_attribute(attribute)
                    
            elif self.engine == 'playwright':
                if attribute == 'text':
                    return asyncio.run(self.scraper.get_text(selector))
                else:
                    return asyncio.run(self.scraper.get_attribute(selector, attribute))
                    
            else:  # requests
                # Use requests scraper
                return self.scraper.extract_text(selector)
                
        except Exception as e:
            self.logger.debug(f"Extraction failed for {selector}: {e}")
            return None

    def extract_multiple(self, selector: str) -> List[str]:
        """Extract data from multiple elements"""
        if not self.is_initialized:
            return []
        
        try:
            if self.engine == 'selenium':
                elements = self.scraper.driver.find_elements(By.CSS_SELECTOR, selector)
                return [elem.text for elem in elements]
                
            elif self.engine == 'playwright':
                return asyncio.run(self.scraper.get_texts(selector))
                
            else:  # requests
                return self.scraper.extract_multiple_texts(selector)
                
        except Exception as e:
            self.logger.debug(f"Multiple extraction failed for {selector}: {e}")
            return []

    def click_element(self, selector: str) -> bool:
        """Click an element"""
        if self.engine == 'requests':
            return False  # Cannot click with requests
        
        try:
            if self.engine == 'selenium':
                element = self.scraper.driver.find_element(By.CSS_SELECTOR, selector)
                element.click()
                return True
                
            elif self.engine == 'playwright':
                return asyncio.run(self.scraper.click(selector))
                
        except Exception as e:
            self.logger.error(f"Click failed for {selector}: {e}")
            return False

    def scroll_to_load_more(self, strategy: str = 'scroll', pause_time: float = 2.0) -> int:
        """Scroll to load more content"""
        if self.engine == 'requests':
            return 0  # Cannot scroll with requests
        
        try:
            if self.engine == 'selenium':
                # Implement scrolling for Selenium
                scrolls = 0
                last_height = self.scraper.driver.execute_script("return document.body.scrollHeight")
                
                while True:
                    self.scraper.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(pause_time)
                    scrolls += 1
                    
                    new_height = self.scraper.driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        break
                    last_height = new_height
                
                return scrolls
                
            elif self.engine == 'playwright':
                return asyncio.run(self.scraper.scroll_to_bottom(pause_time))
                
        except Exception as e:
            self.logger.error(f"Scroll failed: {e}")
            return 0

    def wait_for_element(self, selector: str, timeout: int = 10) -> bool:
        """Wait for element to appear"""
        if self.engine == 'requests':
            return True  # No waiting needed for requests
        
        try:
            if self.engine == 'selenium':
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                
                wait = WebDriverWait(self.scraper.driver, timeout)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                return True
                
            elif self.engine == 'playwright':
                return asyncio.run(self.scraper.wait_for_selector(selector, timeout))
                
        except Exception as e:
            self.logger.debug(f"Wait failed for {selector}: {e}")
            return False

    def get_page_source(self) -> str:
        """Get current page source"""
        if not self.is_initialized:
            return ""
        
        try:
            if self.engine == 'selenium':
                return self.scraper.driver.page_source
            elif self.engine == 'playwright':
                return asyncio.run(self.scraper.get_page_content())
            else:  # requests
                return self.scraper.get_page_source() if hasattr(self.scraper, 'get_page_source') else ""
                
        except Exception as e:
            self.logger.error(f"Failed to get page source: {e}")
            return ""

    def take_screenshot(self, path: Optional[str] = None) -> Optional[str]:
        """Take screenshot of current page"""
        if self.engine == 'requests':
            return None  # Cannot take screenshots with requests
        
        try:
            if not path:
                path = str(self.config.OUTPUT_DIR / f"screenshot_{int(time.time())}.png")
            
            if self.engine == 'selenium':
                self.scraper.driver.save_screenshot(path)
                return path
            elif self.engine == 'playwright':
                return asyncio.run(self.scraper.take_screenshot(path))
                
        except Exception as e:
            self.logger.error(f"Screenshot failed: {e}")
            return None

    def create_template_from_interaction(self, url: str, scraping_type: ScrapingType) -> Optional[ScrapingTemplate]:
        """Create a template using interactive element selection"""
        try:
            # Navigate to URL
            if not self.navigate_to(url):
                return None
            
            # Handle cookies
            self.handle_cookies()
            
            # Create base template
            site_info = SiteInfo(url=url)
            template = ScrapingTemplate(
                name="interactive_template",
                engine=self.engine,
                site_info=site_info,
                scraping_type=scraping_type,
                list_page_rules=TemplateRules() if scraping_type != ScrapingType.SINGLE_PAGE else None,
                detail_page_rules=TemplateRules(),
                version="2.1",
                created_at=datetime.now().isoformat()
            )
            
            # Configure rules based on scraping type
            if scraping_type in (ScrapingType.LIST_DETAIL, ScrapingType.LIST_ONLY):
                if not self._configure_list_rules_interactive(template):
                    return None
            
            if scraping_type in (ScrapingType.LIST_DETAIL, ScrapingType.SINGLE_PAGE):
                if not self._configure_detail_rules_interactive(template):
                    return None
            
            return template
            
        except Exception as e:
            self.logger.error(f"Template creation failed: {e}")
            return None

    def _configure_list_rules_interactive(self, template: ScrapingTemplate) -> bool:
        """Configure list rules using interactive selection"""
        if self.engine == 'requests':
            return self._configure_list_rules_manual(template)
        
        rules = template.list_page_rules
        
        # Get repeating item selector
        print("\n🎯 Identify Repeating Items")
        print("What selector represents each item in the list?")
        
        manual_selector = input("Enter CSS selector (or press Enter for interactive): ").strip()
        
        if manual_selector:
            rules.repeating_item_selector = manual_selector
        else:
            # Interactive selection
            if not self._detect_repeating_items(rules):
                return False
        
        # Configure fields
        fields = self._configure_fields_interactive("list item")
        rules.fields = fields
        
        # Set profile link for list+detail
        if template.scraping_type == ScrapingType.LIST_DETAIL:
            link_selector = input("CSS selector for detail page links: ").strip()
            if link_selector:
                rules.profile_link_selector = link_selector
        
        return True

    def _configure_detail_rules_interactive(self, template: ScrapingTemplate) -> bool:
        """Configure detail rules using interactive selection"""
        rules = template.detail_page_rules
        
        # Navigate to detail page if needed
        if template.scraping_type == ScrapingType.LIST_DETAIL:
            print("\n📄 Please navigate to a detail page")
            self.cleanup_interactive_selector()
            input("Press Enter when ready...")
        
        # Configure fields
        if self.engine == 'requests':
            fields = self._configure_fields_manual("detail page")
        else:
            fields = self._configure_fields_interactive("detail page")
        
        rules.fields = fields
        return True

    def _detect_repeating_items(self, rules: TemplateRules) -> bool:
        """Detect repeating items using interactive selection"""
        self.logger.info("Starting interactive detection of repeating items")
        print("Click on any item in the list...")
        
        if not self.inject_interactive_selector("Click on list item"):
            self.logger.error("Failed to inject interactive selector")
            print("❌ Failed to activate interactive selector")
            return False
        
        # Wait for selection
        for _ in range(30):
            time.sleep(0.5)
            data = self.get_selected_element_data()
            if data:
                selector = data.get('selector', '')
                if selector:
                    # Process selector to make it general
                    processed_selector = self._process_selector_for_repetition(selector)
                    rules.repeating_item_selector = processed_selector
                    print(f"✅ Using selector: {processed_selector}")
                    self.cleanup_interactive_selector()
                    return True
        
        return False

    def _process_selector_for_repetition(self, selector: str) -> str:
        """Process selector to make it work for all repeating items"""
        import re
        
        # Remove nth-of-type selectors
        processed = re.sub(r':nth[-‐]of[-‐]type\(\d+\)', '', selector)
        
        # If selector becomes empty or too generic, ask user
        if not processed.strip() or processed.strip() in ['div', 'span', '']:
            print(f"⚠️  Detected selector is too generic: {processed}")
            better = input("Enter a better selector (e.g., '.item-card'): ").strip()
            if better:
                return better
        
        return processed.strip() or 'div'

    def _configure_fields_interactive(self, context: str) -> Dict[str, str]:
        """Configure fields using interactive selection"""
        fields = {}
        
        if self.engine == 'requests':
            return self._configure_fields_manual(context)
        
        print(f"\nConfigure fields for {context}:")
        
        common_fields = ["title", "link", "description", "author", "date", "price"]
        
        for field_name in common_fields:
            print(f"\n🔍 Select {field_name} (or skip)")
            
            if self.inject_interactive_selector(f"Select {field_name}"):
                # Wait for selection
                for _ in range(30):
                    time.sleep(0.5)
                    data = self.get_selected_element_data()
                    if data:
                        if data.get('done'):
                            break
                        selector = data.get('selector', '')
                        if selector:
                            fields[field_name] = selector
                            print(f"✅ {field_name}: {selector}")
                        break
                
                if data and data.get('done'):
                    break
        
        # Custom fields
        while True:
            custom_name = input("\nAdd custom field (or Enter to finish): ").strip()
            if not custom_name:
                break
            
            if self.inject_interactive_selector(f"Select {custom_name}"):
                for _ in range(30):
                    time.sleep(0.5)
                    data = self.get_selected_element_data()
                    if data:
                        selector = data.get('selector', '')
                        if selector:
                            fields[custom_name] = selector
                            print(f"✅ {custom_name}: {selector}")
                        break
        
        self.cleanup_interactive_selector()
        return fields

    def _configure_fields_manual(self, context: str) -> Dict[str, str]:
        """Configure fields manually for requests engine"""
        fields = {}
        print(f"\nManual field configuration for {context}:")
        
        while True:
            field_name = input("Field name (or Enter to finish): ").strip()
            if not field_name:
                break
            
            selector = input(f"CSS selector for {field_name}: ").strip()
            if selector:
                fields[field_name] = selector
        
        return fields

    def _configure_list_rules_manual(self, template: ScrapingTemplate) -> bool:
        """Configure list rules manually"""
        rules = template.list_page_rules
        
        # Repeating item selector
        selector = input("CSS selector for repeating items: ").strip()
        if not selector:
            return False
        rules.repeating_item_selector = selector
        
        # Fields
        fields = self._configure_fields_manual("list item")
        rules.fields = fields
        
        # Profile link
        if template.scraping_type == ScrapingType.LIST_DETAIL:
            link_selector = input("CSS selector for detail links: ").strip()
            if link_selector:
                rules.profile_link_selector = link_selector
        
        return True

    def close(self):
        """Clean up and close scraper"""
        try:
            if self.scraper:
                if self.engine == 'selenium':
                    self.scraper.driver.quit()
                elif self.engine == 'playwright':
                    try:
                        # Try to get the existing event loop
                        loop = asyncio.get_event_loop()
                        if loop.is_closed():
                            # If the loop is closed, create a new one
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                        loop.run_until_complete(self.scraper.close())
                    except RuntimeError as e:
                        # Event loop is closed, try synchronous cleanup
                        if "Event loop is closed" in str(e):
                            self.logger.warning("Event loop closed, attempting direct cleanup")
                            # Just log the error since we can't do async cleanup
                        else:
                            raise
                # Requests scraper doesn't need closing
                
            self.is_initialized = False
            self.logger.info("Scraper closed successfully")
            
        except Exception as e:
            self.logger.error(f"Error closing scraper: {e}")

    def __enter__(self):
        """Context manager entry"""
        if self.initialize():
            return self
        else:
            raise RuntimeError("Failed to initialize scraper")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

    def get_capabilities(self) -> Dict[str, bool]:
        """Get capabilities of current engine"""
        if self.engine == 'selenium':
            return {
                'javascript': True,
                'interactive_selection': True,
                'screenshots': True,
                'cookies': True,
                'scrolling': True,
                'clicking': True
            }
        elif self.engine == 'playwright':
            return {
                'javascript': True,
                'interactive_selection': False,  # Not fully implemented yet
                'screenshots': True,
                'cookies': True,
                'scrolling': True,
                'clicking': True
            }
        else:  # requests
            return {
                'javascript': False,
                'interactive_selection': False,
                'screenshots': False,
                'cookies': False,
                'scrolling': False,
                'clicking': False
            }

    def get_engine_info(self) -> Dict[str, Any]:
        """Get information about current engine"""
        return {
            'engine': self.engine,
            'headless': self.headless,
            'initialized': self.is_initialized,
            'current_url': self.current_url,
            'capabilities': self.get_capabilities()
        }