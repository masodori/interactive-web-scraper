# src/scraper/handlers/load_more_handler.py
"""
Handles dynamic content loading mechanisms like infinite scroll and
"load more" buttons.
"""

import time
import logging
from typing import Optional

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

from ..config import Config
from ..models import LoadStrategyConfig


class LoadMoreHandler:
    """Manages strategies for loading dynamically added content."""

    def __init__(self, driver: WebDriver, config: Config):
        """
        Initializes the LoadMoreHandler.

        Args:
            driver: The Selenium WebDriver instance.
            config: The scraper's configuration object.
        """
        self.driver = driver
        self.config = config
        self.logger = logging.getLogger(f'{__name__}.LoadMoreHandler')

    def execute_loading(self, strategy: LoadStrategyConfig):
        """
        Executes the content loading strategy defined in the template.

        Args:
            strategy: The configuration for the loading strategy.
        """
        strategy_type = strategy.type

        self.logger.info(f"Executing load strategy: {strategy_type.value}")

        if strategy_type == strategy_type.SCROLL:
            count = self.handle_scroll(strategy.max_scrolls, strategy.pause_time)
            self.logger.info(f"Performed {count} scroll actions.")
        elif strategy_type == strategy_type.BUTTON and strategy.button_selector:
            count = self.handle_button_click(
                strategy.button_selector,
                strategy.max_clicks,
                strategy.pause_time
            )
            self.logger.info(f"Clicked 'load more' button {count} times.")
        elif strategy_type == strategy_type.AUTO:
            self.auto_detect_and_load()
        else:
            self.logger.debug("No active load strategy to execute.")

    def handle_scroll(self, max_scrolls: int, pause_time: float) -> int:
        """
        Handles infinite scrolling to load more content.

        Args:
            max_scrolls: The maximum number of times to scroll.
            pause_time: The delay between scrolls.

        Returns:
            The number of scroll actions performed.
        """
        scrolls_performed = 0
        last_height = self.driver.execute_script("return document.body.scrollHeight")

        for i in range(max_scrolls):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(pause_time)

            new_height = self.driver.execute_script("return document.body.scrollHeight")
            scrolls_performed += 1

            if new_height == last_height:
                self.logger.info(f"Scrolling stopped after {scrolls_performed} scrolls; page height is stable.")
                break
            last_height = new_height
        
        return scrolls_performed

    def handle_button_click(self, selector: str, max_clicks: int, pause_time: float) -> int:
        """
        Repeatedly clicks a 'load more' button.

        Args:
            selector: The CSS selector for the button.
            max_clicks: The maximum number of times to click.
            pause_time: The delay between clicks.

        Returns:
            The number of successful clicks.
        """
        clicks = 0
        for _ in range(max_clicks):
            try:
                button = self.driver.find_element(By.CSS_SELECTOR, selector)
                if button.is_displayed() and button.is_enabled():
                    self.driver.execute_script("arguments[0].click();", button)
                    clicks += 1
                    time.sleep(pause_time)
                else:
                    self.logger.info("'Load more' button is no longer visible or enabled.")
                    break
            except (NoSuchElementException, StaleElementReferenceException):
                self.logger.info("'Load more' button not found, stopping.")
                break
            except Exception as e:
                self.logger.warning(f"Error clicking 'load more' button: {e}")
                break
        return clicks

    def auto_detect_and_load(self):
        """
        Attempts to automatically find and click a 'load more' button,
        falling back to scrolling if no button is found.
        """
        self.logger.info("Auto-detecting load strategy...")
        
        # Try to find a 'load more' button by keywords
        for keyword in self.config.LOAD_MORE_KEYWORDS:
            try:
                # Case-insensitive XPath
                xpath = f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword.lower()}')] | //a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword.lower()}')]"
                
                elements = self.driver.find_elements(By.XPATH, xpath)
                for button in elements:
                    if button.is_displayed() and button.is_enabled():
                        self.logger.info(f"Auto-detected 'load more' button with text: '{button.text}'")
                        # We need a stable selector to click repeatedly
                        selector = self._get_stable_selector(button)
                        if selector:
                            self.handle_button_click(selector, self.config.LOAD_MORE_MAX_RETRIES, self.config.LOAD_MORE_PAUSE_TIME)
                            return # Strategy executed, exit
            except Exception:
                continue

        # Fallback to scrolling
        self.logger.info("No 'load more' button found, falling back to scrolling.")
        self.handle_scroll(self.config.LOAD_MORE_MAX_RETRIES, self.config.LOAD_MORE_PAUSE_TIME)
        
    def _get_stable_selector(self, element) -> Optional[str]:
        """
        Generates a reasonably stable CSS selector for a given element.
        Tries ID, then unique class combination.
        """
        # Try ID first
        elem_id = element.get_attribute('id')
        if elem_id:
            return f"#{elem_id}"

        # Try tag + class combination
        tag = element.tag_name.lower()
        classes = element.get_attribute('class')
        if classes:
            class_list = classes.strip().split()
            if class_list:
                return f"{tag}.{'.'.join(class_list)}"
        
        return None