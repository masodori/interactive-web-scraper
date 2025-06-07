# src/scraper/core/playwright_sync_wrapper.py
"""
Synchronous wrapper for Playwright to match Selenium's API.
This allows Playwright to be used with the existing interactive scraper infrastructure.
"""

import logging
import asyncio
from typing import Optional, Any, Dict
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright, Page, Browser, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

from ..config import Config
from ..handlers import CookieHandler


class PlaywrightSyncWrapper:
    """
    A synchronous wrapper around Playwright that mimics Selenium's WebDriver API.
    This allows the interactive scraper to work with Playwright without major refactoring.
    """
    
    def __init__(self, headless: bool = True, browser_type: str = "chromium"):
        """
        Initialize Playwright sync wrapper.
        
        Args:
            headless: Run browser in headless mode
            browser_type: Browser to use (chromium, firefox, webkit)
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError(
                "Playwright is not installed. Install it with: pip install playwright && playwright install"
            )
        
        self.logger = logging.getLogger(f'{__name__}.PlaywrightSyncWrapper')
        self.config = Config
        self.headless = headless
        self.browser_type = browser_type
        self.playwright = None
        self.browser = None
        self.page = None
        self.context = None
        
        self._init_browser()
        
    def _init_browser(self):
        """Initialize Playwright browser and page."""
        try:
            self.playwright = sync_playwright().start()
            
            # Launch browser
            launch_options = {
                'headless': self.headless,
                'args': ['--no-sandbox'] if self.headless else []
            }
            
            if self.browser_type == "chromium":
                self.browser = self.playwright.chromium.launch(**launch_options)
            elif self.browser_type == "firefox":
                self.browser = self.playwright.firefox.launch(**launch_options)
            elif self.browser_type == "webkit":
                self.browser = self.playwright.webkit.launch(**launch_options)
            else:
                raise ValueError(f"Unsupported browser type: {self.browser_type}")
            
            # Create context and page
            self.context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            self.page = self.context.new_page()
            
            # Set default timeout
            self.page.set_default_timeout(self.config.DEFAULT_TIMEOUT * 1000)  # Convert to ms
            
            self.logger.info(f"Playwright {self.browser_type} browser initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Playwright: {e}")
            raise
    
    # Selenium-compatible methods
    
    def get(self, url: str):
        """Navigate to URL (Selenium-compatible method)."""
        try:
            self.page.goto(url, wait_until='domcontentloaded')
            self.logger.info(f"Navigated to {url}")
        except Exception as e:
            self.logger.error(f"Failed to navigate to {url}: {e}")
            raise
    
    def execute_script(self, script: str, *args) -> Any:
        """Execute JavaScript (Selenium-compatible method)."""
        try:
            # Playwright expects expressions or functions, not statements with 'return'
            # Convert Selenium-style scripts to Playwright-compatible ones
            
            # Remove leading/trailing whitespace
            script = script.strip()
            
            # Handle different script patterns
            if script.startswith('return '):
                # Convert "return x" to just "x"
                expression = script[7:].strip()
                result = self.page.evaluate(expression)
            elif script.startswith('document.') or script.startswith('window.'):
                # Direct property access - evaluate as expression
                result = self.page.evaluate(script)
            elif '{' in script and '}' in script:
                # Multi-line script - wrap in function
                if not script.startswith('(') and not script.startswith('function'):
                    # Wrap in IIFE
                    wrapped = f"(() => {{ {script} }})()"
                    result = self.page.evaluate(wrapped)
                else:
                    result = self.page.evaluate(script)
            else:
                # Simple expression
                result = self.page.evaluate(script)
            
            return result
        except Exception as e:
            self.logger.error(f"Failed to execute script: {e}")
            raise
    
    def find_element(self, by: str, value: str):
        """Find element (Selenium-compatible method)."""
        try:
            if by == "css selector":
                return self.page.locator(value).first
            elif by == "xpath":
                return self.page.locator(f"xpath={value}").first
            elif by == "id":
                return self.page.locator(f"#{value}").first
            elif by == "class name":
                return self.page.locator(f".{value}").first
            elif by == "tag name":
                return self.page.locator(value).first
            else:
                raise ValueError(f"Unsupported locator type: {by}")
        except Exception as e:
            self.logger.error(f"Failed to find element: {e}")
            return None
    
    def find_elements(self, by: str, value: str):
        """Find elements (Selenium-compatible method)."""
        try:
            if by == "css selector":
                return self.page.locator(value).all()
            elif by == "xpath":
                return self.page.locator(f"xpath={value}").all()
            elif by == "id":
                return self.page.locator(f"#{value}").all()
            elif by == "class name":
                return self.page.locator(f".{value}").all()
            elif by == "tag name":
                return self.page.locator(value).all()
            else:
                raise ValueError(f"Unsupported locator type: {by}")
        except Exception as e:
            self.logger.error(f"Failed to find elements: {e}")
            return []
    
    def save_screenshot(self, path: str) -> bool:
        """Take screenshot (Selenium-compatible method)."""
        try:
            self.page.screenshot(path=path)
            return True
        except Exception as e:
            self.logger.error(f"Failed to take screenshot: {e}")
            return False
    
    @property
    def current_url(self) -> str:
        """Get current URL (Selenium-compatible property)."""
        return self.page.url
    
    @property
    def page_source(self) -> str:
        """Get page source (Selenium-compatible property)."""
        return self.page.content()
    
    def quit(self):
        """Close browser (Selenium-compatible method)."""
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            self.logger.info("Playwright browser closed successfully")
        except Exception as e:
            self.logger.warning(f"Error closing Playwright: {e}")
    
    def close(self):
        """Alias for quit() for compatibility."""
        self.quit()
    
    def maximize_window(self):
        """Maximize window (no-op for Playwright, viewport is set on context creation)."""
        pass
    
    # Additional helper methods for interactive selection
    
    def inject_javascript_file(self, file_path: str) -> bool:
        """Inject JavaScript from file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                js_content = f.read()
            self.page.evaluate(js_content)
            return True
        except Exception as e:
            self.logger.error(f"Failed to inject JavaScript file: {e}")
            return False
    
    def wait_for_selector(self, selector: str, timeout: Optional[int] = None) -> bool:
        """Wait for element to appear."""
        try:
            timeout_ms = (timeout or self.config.DEFAULT_TIMEOUT) * 1000
            self.page.wait_for_selector(selector, timeout=timeout_ms)
            return True
        except PlaywrightTimeout:
            return False
        except Exception as e:
            self.logger.error(f"Error waiting for selector: {e}")
            return False