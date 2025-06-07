# src/scraper/core/multi_engine_scraper.py
"""
Multi-engine scraper base class that supports Selenium, Playwright, and Requests.
"""

import logging
from typing import Optional, Any, Union
from abc import ABC

from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement

from .base_scraper import BaseScraper
from .playwright_sync_wrapper import PlaywrightSyncWrapper, PLAYWRIGHT_AVAILABLE
from ..config import Config


class MultiEngineScraper(BaseScraper):
    """
    Enhanced base scraper that supports multiple engines (Selenium, Playwright, Requests).
    Inherits from BaseScraper for backward compatibility but can use different drivers.
    """
    
    def __init__(self, engine: str = "selenium", headless: bool = True, 
                 options: Optional[webdriver.ChromeOptions] = None):
        """
        Initialize multi-engine scraper.
        
        Args:
            engine: The engine to use ("selenium", "playwright", "requests")
            headless: Whether to run in headless mode
            options: Chrome options (only for Selenium)
        """
        self.logger = logging.getLogger(f'{__name__}.MultiEngineScraper')
        self.config = Config
        self.engine = engine.lower()
        self.headless = headless
        
        # Initialize the appropriate driver
        if self.engine == "selenium":
            # Use parent class initialization for Selenium
            super().__init__(headless=headless, options=options)
        elif self.engine == "playwright":
            if not PLAYWRIGHT_AVAILABLE:
                raise ImportError(
                    "Playwright is not installed. Install with: "
                    "pip install playwright && playwright install"
                )
            # Initialize Playwright wrapper
            self.driver = PlaywrightSyncWrapper(headless=headless)
            self.wait = None  # Playwright has built-in waiting
            self.cookie_handler = None  # TODO: Implement for Playwright
        elif self.engine == "requests":
            # Requests doesn't need a driver
            self.driver = None
            self.wait = None
            self.cookie_handler = None
            self.logger.info("Requests engine initialized (no browser)")
        else:
            raise ValueError(f"Unsupported engine: {self.engine}")
    
    def navigate_to(self, url: str) -> bool:
        """Navigate to URL with engine-specific implementation."""
        if self.engine == "selenium":
            return super().navigate_to(url)
        elif self.engine == "playwright":
            try:
                self.driver.get(url)
                return True
            except Exception as e:
                self.logger.error(f"Failed to navigate with Playwright: {e}")
                return False
        elif self.engine == "requests":
            self.logger.warning("Requests engine doesn't support navigation")
            return False
    
    def execute_script(self, script: str, *args) -> Any:
        """Execute JavaScript with engine-specific implementation."""
        if self.engine == "selenium":
            return self.driver.execute_script(script, *args)
        elif self.engine == "playwright":
            return self.driver.execute_script(script, *args)
        elif self.engine == "requests":
            self.logger.warning("Requests engine doesn't support JavaScript execution")
            return None
    
    def inject_interactive_selector(self, context_message: str = "Select elements") -> bool:
        """
        Inject interactive selector with engine-specific implementation.
        
        Args:
            context_message: Message to display in the overlay
            
        Returns:
            True if successful, False otherwise
        """
        if self.engine == "requests":
            self.logger.warning("Requests engine doesn't support interactive selection")
            return False
        
        try:
            # Load the JavaScript file
            js_path = self.config.get_js_asset_path()
            with open(js_path, 'r', encoding='utf-8') as f:
                js_content = f.read()
            
            # Set context message
            self.execute_script(f"window.scraperContextMessage = '{context_message}';")
            
            # Inject the JavaScript
            self.execute_script(js_content)
            
            self.logger.info(f"Interactive selector injected successfully with {self.engine}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to inject interactive selector: {e}")
            return False
    
    def get_selected_element_data(self) -> Optional[dict]:
        """Get selected element data with engine-specific implementation."""
        if self.engine == "requests":
            return None
        
        try:
            value = self.execute_script(
                "return document.getElementById('selected_element_data') ? "
                "document.getElementById('selected_element_data').value : '';"
            )
            
            if value and value != '' and value != 'DONE_SELECTING':
                import json
                return json.loads(value)
            elif value == 'DONE_SELECTING':
                return {'done': True}
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get selected element data: {e}")
            return None
    
    def close(self):
        """Close the driver with engine-specific implementation."""
        if self.engine == "selenium":
            super().close()
        elif self.engine == "playwright":
            if self.driver:
                self.driver.close()
                self.driver = None
        # Requests doesn't need closing
    
    def take_screenshot(self, filename: str) -> Optional[str]:
        """Take screenshot with engine-specific implementation."""
        if self.engine == "selenium":
            return super().take_screenshot(filename)
        elif self.engine == "playwright":
            self.config.ensure_directories()
            filepath = self.config.OUTPUT_DIR / filename
            try:
                if self.driver.save_screenshot(str(filepath)):
                    self.logger.info(f"Screenshot saved to {filepath}")
                    return str(filepath)
            except Exception as e:
                self.logger.error(f"Failed to take screenshot: {e}")
            return None
        else:
            self.logger.warning(f"{self.engine} engine doesn't support screenshots")
            return None