# src/scraper/handlers/cookie_handler.py
"""
Cookie consent handling functionality.
"""

import logging
import time
from typing import Optional, List, Union
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class CookieHandler:
    """Handle cookie consent popups and banners"""
    
    def __init__(self, driver, config):
        """
        Initialize cookie handler.
        
        Args:
            driver: Selenium WebDriver instance
            config: Configuration object
        """
        self.driver = driver
        self.config = config
        self.logger = logging.getLogger(f'{__name__}.CookieHandler')
        self.custom_selectors = []
    
    def add_custom_selector(self, selector: str, selector_type: str = "xpath"):
        """
        Add custom cookie selector.
        
        Args:
            selector: Selector string
            selector_type: Type of selector (xpath, css)
        """
        self.custom_selectors.append({
            'selector': selector,
            'type': selector_type
        })
        self.logger.debug(f"Added custom {selector_type} selector: {selector}")
    
    def accept_cookies(self, custom_selectors: Optional[List[str]] = None,
                      timeout: Optional[int] = None) -> Optional[str]:
        """
        Detect and accept cookie consent.
        
        Args:
            custom_selectors: List of custom selectors to try
            timeout: Custom timeout for cookie detection
            
        Returns:
            Selector that worked, or None if no cookies handled
        """
        timeout = timeout or self.config.COOKIE_ACCEPTANCE_TIMEOUT
        
        # Build list of selectors to try
        selectors_to_try = []
        
        # Add custom selectors first (highest priority)
        if custom_selectors:
            for selector in custom_selectors:
                selectors_to_try.append({
                    'selector': selector,
                    'type': 'xpath' if selector.startswith('//') else 'css'
                })
        
        # Add instance custom selectors
        selectors_to_try.extend(self.custom_selectors)
        
        # Add default XPath selectors
        for xpath in self.config.COOKIE_XPATHS:
            selectors_to_try.append({
                'selector': xpath,
                'type': 'xpath'
            })
        
        # Add default CSS selectors
        for css in self.config.COOKIE_CSS_SELECTORS:
            selectors_to_try.append({
                'selector': css,
                'type': 'css'
            })
        
        # Try each selector
        for selector_info in selectors_to_try:
            selector = selector_info['selector']
            selector_type = selector_info['type']
            
            if self._try_selector(selector, selector_type, timeout):
                self.logger.info(f"Cookie banner accepted using {selector_type}: {selector}")
                return selector
        
        self.logger.debug("No cookie banner found or accepted")
        return None
    
    def _try_selector(self, selector: str, selector_type: str, timeout: int) -> bool:
        """
        Try a single selector to find and click cookie button.
        
        Args:
            selector: Selector string
            selector_type: Type of selector (xpath, css)
            timeout: Timeout in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            by = By.XPATH if selector_type == 'xpath' else By.CSS_SELECTOR
            
            # Find all matching elements
            elements = self.driver.find_elements(by, selector)
            
            # Try each element
            for element in elements:
                if self._is_valid_cookie_button(element):
                    if self._click_element(element):
                        # Wait a bit for cookie banner to disappear
                        time.sleep(1)
                        return True
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Selector failed ({selector_type}): {selector} - {e}")
            return False
    
    def _is_valid_cookie_button(self, element) -> bool:
        """
        Check if element is a valid cookie button.
        
        Args:
            element: WebElement to check
            
        Returns:
            True if element appears to be a valid cookie button
        """
        try:
            # Check if element is displayed and enabled
            if not element.is_displayed() or not element.is_enabled():
                return False
            
            # Check element size (avoid tiny or hidden elements)
            size = element.size
            if size['width'] < 20 or size['height'] < 20:
                return False
            
            # Check if element is in viewport
            location = element.location
            viewport_height = self.driver.execute_script("return window.innerHeight")
            viewport_width = self.driver.execute_script("return window.innerWidth")
            
            if (location['y'] < -100 or location['y'] > viewport_height + 100 or
                location['x'] < -100 or location['x'] > viewport_width + 100):
                return False
            
            return True
            
        except Exception:
            return False
    
    def _click_element(self, element) -> bool:
        """
        Click element with multiple strategies.
        
        Args:
            element: WebElement to click
            
        Returns:
            True if click successful
        """
        try:
            # Try regular click
            element.click()
            return True
        except Exception:
            try:
                # Try JavaScript click
                self.driver.execute_script("arguments[0].click();", element)
                return True
            except Exception:
                try:
                    # Try scrolling into view first
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'});", 
                        element
                    )
                    time.sleep(0.5)
                    element.click()
                    return True
                except Exception as e:
                    self.logger.debug(f"Failed to click element: {e}")
                    return False
    
    def wait_for_cookie_popup(self, custom_xpath: Optional[str] = None, 
                            timeout: int = 10) -> Optional[bool]:
        """
        Wait for cookie popup and attempt to accept it.
        Legacy method for backward compatibility.
        
        Args:
            custom_xpath: Custom XPath selector
            timeout: Timeout in seconds
            
        Returns:
            True if cookies accepted, False if not found, None on error
        """
        custom_selectors = [custom_xpath] if custom_xpath else None
        result = self.accept_cookies(custom_selectors=custom_selectors, timeout=timeout)
        return result is not None
    
    def detect_cookie_banner(self) -> bool:
        """
        Check if a cookie banner is currently visible.
        
        Returns:
            True if cookie banner detected
        """
        # Common indicators of cookie banners
        keywords = [
            'cookie', 'gdpr', 'consent', 'privacy', 'accept',
            'agree', 'preferences', 'necessary', 'functional'
        ]
        
        # Check for common cookie banner containers
        common_selectors = [
            "[class*='cookie']", "[id*='cookie']",
            "[class*='consent']", "[id*='consent']",
            "[class*='gdpr']", "[id*='gdpr']",
            "[class*='privacy']", "[id*='privacy']",
            "[role='dialog']", "[role='alertdialog']"
        ]
        
        for selector in common_selectors:
            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            for element in elements:
                try:
                    if element.is_displayed():
                        text = element.text.lower()
                        if any(keyword in text for keyword in keywords):
                            self.logger.debug(f"Cookie banner detected: {selector}")
                            return True
                except Exception:
                    continue
        
        return False
    
    def handle_cookie_preferences(self, accept_all: bool = True) -> bool:
        """
        Handle cookie preference dialogs with options.
        
        Args:
            accept_all: Whether to accept all cookies or only necessary
            
        Returns:
            True if preferences handled successfully
        """
        # Try to find preference buttons
        if accept_all:
            # Look for "Accept All" type buttons
            selectors = [
                "//button[contains(., 'Accept All')]",
                "//button[contains(., 'Accept all')]",
                "//button[contains(., 'Allow All')]",
                "//button[contains(., 'Allow all')]",
                "//a[contains(., 'Accept All')]",
                "button.accept-all", "button#accept-all"
            ]
        else:
            # Look for "Necessary Only" type buttons
            selectors = [
                "//button[contains(., 'Necessary Only')]",
                "//button[contains(., 'Essential Only')]",
                "//button[contains(., 'Reject All')]",
                "//button[contains(., 'Decline')]",
                "button.necessary-only", "button.essential-only"
            ]
        
        for selector in selectors:
            selector_type = 'xpath' if selector.startswith('//') else 'css'
            if self._try_selector(selector, selector_type, timeout=5):
                self.logger.info(f"Cookie preferences set: {'Accept All' if accept_all else 'Necessary Only'}")
                return True
        
        # Fallback to regular accept
        return self.accept_cookies() is not None