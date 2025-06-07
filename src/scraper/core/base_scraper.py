# src/scraper/core/base_scraper.py
"""
Base scraper class with fundamental web interaction methods, driver management,
and context manager support.
"""

import logging
import time
from typing import Optional, Any

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
    ElementClickInterceptedException,
    ElementNotInteractableException
)
from webdriver_manager.chrome import ChromeDriverManager

from ..config import Config
from ..handlers import CookieHandler
from ..utils.retry import retry_on_exception


class BaseScraper:
    """
    Base class for web scrapers, handling driver initialization,
    navigation, and basic page interactions.
    """

    def __init__(self, headless: bool = True, options: Optional[webdriver.ChromeOptions] = None):
        """
        Initializes the scraper and the Selenium WebDriver.

        Args:
            headless: Whether to run the browser in headless mode.
            options: Custom Chrome options to use.
        """
        self.logger = logging.getLogger(f'{__name__}.BaseScraper')
        self.config = Config
        self.driver = self._init_driver(headless, options)
        self.wait = WebDriverWait(self.driver, self.config.DEFAULT_TIMEOUT)
        self.cookie_handler = CookieHandler(self.driver, self.config)

    def _init_driver(self, headless: bool, options: Optional[webdriver.ChromeOptions]) -> webdriver.Chrome:
        """
        Initializes the Chrome WebDriver with robust options.

        Args:
            headless: If True, runs Chrome in headless mode.
            options: Pre-configured ChromeOptions object.

        Returns:
            An instance of the Chrome WebDriver.
        """
        if options is None:
            options = webdriver.ChromeOptions()
            chrome_options_list = self.config.get_chrome_options(headless)
            for opt in chrome_options_list:
                options.add_argument(opt)
            
            # Add experimental options to hide automation indicators
            experimental_options = self.config.CHROME_OPTIONS.get('experimental', {})
            for key, value in experimental_options.items():
                options.add_experimental_option(key, value)

        service = Service(ChromeDriverManager().install())
        try:
            driver = webdriver.Chrome(service=service, options=options)
            if not headless:
                driver.maximize_window()
            self.logger.info("WebDriver initialized successfully.")
            return driver
        except WebDriverException as e:
            self.logger.error(f"Failed to initialize WebDriver: {e}")
            raise

    @retry_on_exception()
    def navigate_to(self, url: str) -> bool:
        """
        Navigates to the specified URL with retry logic.

        Args:
            url: The URL to navigate to.

        Returns:
            True if navigation is successful, False otherwise.
        """
        try:
            self.driver.get(url)
            self.logger.info(f"Navigated to {url}")
            return True
        except WebDriverException as e:
            self.logger.error(f"Failed to navigate to {url}: {e}")
            return False

    def get_current_url(self) -> str:
        """Returns the current URL of the browser."""
        return self.driver.current_url

    def get_page_title(self) -> str:
        """Returns the title of the current page."""
        return self.driver.title

    def wait_for_element(self, by: Any, value: str, timeout: int = None) -> Optional[WebElement]:
        """
        Waits for a single element to be present on the page.

        Args:
            by: The Selenium locator strategy (e.g., By.CSS_SELECTOR).
            value: The selector value.
            timeout: The maximum time to wait.

        Returns:
            The WebElement if found, otherwise None.
        """
        timeout = timeout or self.config.DEFAULT_TIMEOUT
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            self.logger.debug(f"Element not found with locator ('{by}', '{value}') after {timeout}s.")
            return None

    def safe_click(self, element: WebElement) -> bool:
        """
        Attempts to click an element, with fallbacks for interception.

        Args:
            element: The WebElement to click.

        Returns:
            True if the click was successful, False otherwise.
        """
        try:
            # First, try a standard click
            element.click()
            return True
        except (ElementClickInterceptedException, ElementNotInteractableException):
            self.logger.debug("Standard click failed, trying JavaScript click.")
            try:
                # Fallback to JavaScript click
                self.driver.execute_script("arguments[0].click();", element)
                return True
            except WebDriverException as e:
                self.logger.warning(f"JavaScript click also failed for element: {e}")
                return False
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during click: {e}")
            return False
            
    def take_screenshot(self, filename: str) -> Optional[str]:
        """
        Takes a screenshot and saves it to the output directory.

        Args:
            filename: The name for the screenshot file.

        Returns:
            The full path to the saved screenshot, or None on failure.
        """
        self.config.ensure_directories()
        filepath = self.config.OUTPUT_DIR / filename
        try:
            self.driver.save_screenshot(str(filepath))
            self.logger.info(f"Screenshot saved to {filepath}")
            return str(filepath)
        except WebDriverException as e:
            self.logger.error(f"Failed to take screenshot: {e}")
            return None

    def inject_interactive_selector(self, context_message: str = "Select elements") -> bool:
        """
        Injects the interactive selector JavaScript into the page.
        
        Args:
            context_message: Message to display in the overlay
            
        Returns:
            True if injection successful, False otherwise
        """
        try:
            # Load the JavaScript file
            js_path = self.config.get_js_asset_path(self.config.INTERACTIVE_JS_FILENAME)
            with open(js_path, 'r', encoding='utf-8') as f:
                js_content = f.read()
            
            # Set context message
            self.driver.execute_script(f"window.scraperContextMessage = '{context_message}';")
            
            # Inject the JavaScript
            self.driver.execute_script(js_content)
            
            self.logger.info("Interactive selector JavaScript injected successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to inject interactive selector: {e}")
            return False
    
    def get_selected_element_data(self) -> Optional[dict]:
        """
        Retrieves the selected element data from the hidden input.
        
        Returns:
            Dictionary with selector and text, or None if no selection
        """
        try:
            value = self.driver.execute_script(
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
        """Safely quits the WebDriver."""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("WebDriver closed successfully.")
            except WebDriverException as e:
                self.logger.warning(f"Error while closing WebDriver: {e}")
            finally:
                self.driver = None

    def __enter__(self):
        """Enter the context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager, ensuring the driver is closed."""
        self.close()