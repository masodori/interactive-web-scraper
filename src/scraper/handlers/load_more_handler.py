# src/scraper/handlers/load_more_handler.py
"""
Enhanced handler for dynamic content loading with intelligent detection
of new items and automatic continuation.
"""

import time
import logging
from typing import Optional

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException, 
    StaleElementReferenceException, 
    ElementNotInteractableException
)

from ..config import Config
from ..models import LoadStrategy, LoadStrategyConfig


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

    def execute_loading(self, strategy: LoadStrategyConfig, item_selector: str = None):
        """
        Executes the content loading strategy with intelligent detection.

        Args:
            strategy: The configuration for the loading strategy.
            item_selector: CSS selector for items to count for smart detection.
        """
        strategy_type = strategy.type
        self.logger.info(f"Executing load strategy: {strategy_type.value}")

        if not item_selector:
            self.logger.warning("No item_selector provided for smart loading. Strategy may not be effective.")

        if strategy_type == LoadStrategy.SCROLL:
            # This can also be enhanced with a similar smart detection logic
            count = self.handle_scroll_smart(pause_time=strategy.pause_time, item_selector=item_selector, consecutive_failure_limit=strategy.consecutive_failure_limit)
            self.logger.info(f"Performed {count} scroll actions.")
        elif strategy_type == LoadStrategy.BUTTON and strategy.button_selector:
            count = self.handle_button_click_smart(
                selector=strategy.button_selector,
                item_selector=item_selector,
                strategy_config=strategy
            )
            self.logger.info(f"Clicked 'load more' button {count} times.")
        elif strategy_type == LoadStrategy.AUTO:
            self.auto_detect_and_load_smart(item_selector, strategy)
        else:
            self.logger.debug("No active load strategy to execute.")

    def _is_button_still_active(self, selector: str) -> bool:
        """Checks if the 'load more' button still exists and is clickable."""
        try:
            button = self.driver.find_element(By.CSS_SELECTOR, selector)
            return button.is_displayed() and button.is_enabled()
        except (NoSuchElementException, StaleElementReferenceException):
            return False

    def handle_button_click_smart(
        self,
        selector: str,
        item_selector: str,
        strategy_config: LoadStrategyConfig
    ) -> int:
        """
        Repeatedly clicks a 'load more' button until no new items are loaded
        or the button disappears.

        Args:
            selector: CSS selector for the button.
            item_selector: CSS selector to count items to verify loading.
            strategy_config: The configuration for the loading strategy.

        Returns:
            Number of successful clicks.
        """
        clicks = 0
        consecutive_no_new_items = 0
        pause_time = strategy_config.pause_time
        
        while True:
            current_count = self._count_items(item_selector)
            self.logger.info(f"Currently {current_count} items. Checking for 'load more' button.")

            try:
                button = self.driver.find_element(By.CSS_SELECTOR, selector)
                if not (button.is_displayed() and button.is_enabled()):
                    self.logger.info("Load more button found but is not interactable. Stopping.")
                    break
                
                # Click the button and wait
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", button)
                time.sleep(0.5)  # Brief pause before click
                self.driver.execute_script("arguments[0].click();", button)
                clicks += 1
                self.logger.info(f"Clicked 'load more' button (Click #{clicks}). Waiting {pause_time}s for new items...")
                time.sleep(pause_time)
                
                new_count = self._count_items(item_selector)
                
                if new_count > current_count:
                    # Success: new items were loaded
                    consecutive_no_new_items = 0
                    self.logger.info(f"Success! Loaded {new_count - current_count} new items. Total: {new_count}.")
                else:
                    # Failure: no new items loaded
                    consecutive_no_new_items += 1
                    self.logger.warning(f"No new items detected after click #{clicks}. Consecutive failures: {consecutive_no_new_items}.")
                    
                    if consecutive_no_new_items >= strategy_config.consecutive_failure_limit:
                        self.logger.info(f"Reached consecutive failure limit of {strategy_config.consecutive_failure_limit}.")
                        
                        # Last check: is the button still active? If so, wait longer and try one more time.
                        if self._is_button_still_active(selector):
                            extended_wait = pause_time * strategy_config.extended_wait_multiplier
                            self.logger.warning(f"Button is still active. Waiting {extended_wait}s for a slow network...")
                            time.sleep(extended_wait)
                            
                            # If still no new items after extended wait, we're done
                            if self._count_items(item_selector) == new_count:
                                self.logger.info("No new items after extended wait. Stopping.")
                                break
                            else: # New items appeared, reset and continue
                                consecutive_no_new_items = 0

                        else:
                            self.logger.info("Button is no longer active. Assuming all content is loaded.")
                            break # Exit loop
            
            except (NoSuchElementException, StaleElementReferenceException):
                self.logger.info("Load more button no longer found. Assuming all content is loaded.")
                break
            except ElementNotInteractableException:
                self.logger.warning("Button not interactable. Assuming it's covered or disabled. Stopping.")
                break
            except Exception as e:
                self.logger.error(f"An unexpected error occurred during button click: {e}", exc_info=True)
                break
                
        self.logger.info(f"Loading finished. Total clicks: {clicks}, Final item count: {self._count_items(item_selector)}")
        return clicks

    def auto_detect_and_load_smart(self, item_selector: str, strategy: LoadStrategyConfig):
        """Automatically detects and uses the best loading strategy."""
        self.logger.info("Auto-detecting load strategy...")
        
        # Try to find any common load more buttons
        button_selectors_to_try = [
            "button.wpgb-button", "button.load-more", "a.load-more",
            ".load-more-button", "[class*='load'][class*='more']"
        ]
        
        # Add keywords search
        for keyword in self.config.LOAD_MORE_KEYWORDS:
             button_selectors_to_try.append(f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword.lower()}')]")
             button_selectors_to_try.append(f"//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword.lower()}')]")

        for selector in button_selectors_to_try:
            try:
                # Use a very short timeout to quickly check for existence
                self.driver.implicitly_wait(1)
                by = By.XPATH if selector.startswith("//") else By.CSS_SELECTOR
                button = self.driver.find_element(by, selector)
                
                if button.is_displayed() and button.is_enabled():
                    self.driver.implicitly_wait(self.config.IMPLICIT_WAIT) # Reset wait
                    self.logger.info(f"Found potential 'load more' button with selector: {selector}")
                    strategy.button_selector = selector
                    self.handle_button_click_smart(selector, item_selector, strategy)
                    return # Stop after finding one and running it
            except NoSuchElementException:
                continue # Selector not found, try next
            finally:
                self.driver.implicitly_wait(self.config.IMPLICIT_WAIT) # Always reset wait

        # Fallback to scrolling if no button is found
        self.logger.info("No active 'load more' button found, trying scroll strategy...")
        self.handle_scroll_smart(pause_time=strategy.pause_time, item_selector=item_selector, consecutive_failure_limit=strategy.consecutive_failure_limit)

    def _count_items(self, selector: str) -> int:
        """Counts the number of items matching the selector."""
        if not selector:
            return 0
        try:
            return len(self.driver.find_elements(By.CSS_SELECTOR, selector))
        except Exception as e:
            self.logger.debug(f"Error counting items with selector '{selector}': {e}")
            return 0

    def handle_scroll_smart(self, pause_time: float, item_selector: str, consecutive_failure_limit: int) -> int:
        """Handles infinite scrolling with smart detection of new content."""
        scrolls_performed = 0
        no_new_items_count = 0
        last_item_count = self._count_items(item_selector)

        while no_new_items_count < consecutive_failure_limit:
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            scrolls_performed += 1
            time.sleep(pause_time)

            new_height = self.driver.execute_script("return document.body.scrollHeight")
            new_item_count = self._count_items(item_selector)

            if new_item_count > last_item_count:
                self.logger.info(f"Scroll {scrolls_performed}: Found {new_item_count - last_item_count} new items (total: {new_item_count})")
                last_item_count = new_item_count
                no_new_items_count = 0
            # Also check if page height changed as a fallback
            elif new_height > last_height:
                self.logger.info(f"Scroll {scrolls_performed}: Page height changed. Continuing scroll.")
                no_new_items_count = 0
            else:
                no_new_items_count += 1
                self.logger.warning(f"No new items or height change after scroll #{scrolls_performed}. Consecutive failures: {no_new_items_count}")
        
        self.logger.info(f"Scrolling finished after {scrolls_performed} scrolls and {no_new_items_count} consecutive failures.")
        return scrolls_performed