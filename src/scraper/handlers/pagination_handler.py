# src/scraper/handlers/pagination_handler.py
"""
Handles classic pagination by repeatedly clicking a 'next page' element.
"""

import time
import logging

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

from ..config import Config


class PaginationHandler:
    """Manages navigating through paginated content."""

    def __init__(self, driver: WebDriver, config: Config):
        """
        Initializes the PaginationHandler.

        Args:
            driver: The Selenium WebDriver instance.
            config: The scraper's configuration object.
        """
        self.driver = driver
        self.config = config
        self.logger = logging.getLogger(f'{__name__}.PaginationHandler')

    def navigate_pages(self, next_button_selector: str, max_pages: int = 100) -> int:
        """
        Navigates through pages by clicking the 'next' button.

        Args:
            next_button_selector: The CSS selector for the 'next page' button.
            max_pages: A safeguard to prevent infinite loops.

        Returns:
            The total number of pages navigated (including the first).
        """
        pages_navigated = 1
        for _ in range(max_pages - 1):
            try:
                next_button = self.driver.find_element(By.CSS_SELECTOR, next_button_selector)

                if not (next_button.is_displayed() and next_button.is_enabled()):
                    self.logger.info("Next button is not interactable. Ending pagination.")
                    break

                # Use JavaScript click for reliability
                self.driver.execute_script("arguments[0].click();", next_button)
                pages_navigated += 1
                self.logger.debug(f"Navigated to page {pages_navigated}")

                # Wait for the next page to load
                time.sleep(self.config.LOAD_MORE_PAUSE_TIME)

            except (NoSuchElementException, StaleElementReferenceException):
                self.logger.info("No more 'next' buttons found. Pagination complete.")
                break
            except Exception as e:
                self.logger.error(f"An error occurred during pagination: {e}")
                break
        
        self.logger.info(f"Navigated through a total of {pages_navigated} pages.")
        return pages_navigated