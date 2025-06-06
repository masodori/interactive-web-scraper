# src/scraper/handlers/load_more_handler.py
"""
Enhanced handler for dynamic content loading with intelligent detection
of new items and automatic continuation.
"""

import time
import logging
from typing import Optional, Set, List

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

    def execute_loading(self, strategy: LoadStrategyConfig, item_selector: str = None):
        """
        Executes the content loading strategy with intelligent detection.

        Args:
            strategy: The configuration for the loading strategy.
            item_selector: CSS selector for items to count (for smart detection)
        """
        strategy_type = strategy.type
        self.logger.info(f"Executing load strategy: {strategy_type.value}")

        if strategy_type == strategy_type.SCROLL:
            count = self.handle_scroll_smart(strategy.max_scrolls, strategy.pause_time, item_selector)
            self.logger.info(f"Performed {count} scroll actions.")
        elif strategy_type == strategy_type.BUTTON and strategy.button_selector:
            count = self.handle_button_click_smart(
                strategy.button_selector,
                strategy.max_clicks,
                strategy.pause_time,
                item_selector
            )
            self.logger.info(f"Clicked 'load more' button {count} times.")
        elif strategy_type == strategy_type.AUTO:
            self.auto_detect_and_load_smart(item_selector)
        else:
            self.logger.debug("No active load strategy to execute.")

    def handle_scroll_smart(self, max_scrolls: int, pause_time: float, item_selector: str = None) -> int:
        """
        Handles infinite scrolling with smart detection of new content.

        Args:
            max_scrolls: Maximum number of times to scroll
            pause_time: Delay between scrolls
            item_selector: CSS selector to count items

        Returns:
            Number of scroll actions performed
        """
        scrolls_performed = 0
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        last_item_count = self._count_items(item_selector) if item_selector else 0
        no_new_items_count = 0

        for i in range(max_scrolls):
            # Scroll to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(pause_time)

            new_height = self.driver.execute_script("return document.body.scrollHeight")
            new_item_count = self._count_items(item_selector) if item_selector else 0
            scrolls_performed += 1

            # Check if we got new content
            if item_selector:
                if new_item_count > last_item_count:
                    self.logger.info(f"Scroll {scrolls_performed}: Found {new_item_count - last_item_count} new items (total: {new_item_count})")
                    last_item_count = new_item_count
                    no_new_items_count = 0
                else:
                    no_new_items_count += 1
                    if no_new_items_count >= 3:
                        self.logger.info(f"No new items found after 3 scrolls. Stopping at {new_item_count} items.")
                        break
            else:
                # Fallback to height check
                if new_height == last_height:
                    self.logger.info(f"Page height stable after {scrolls_performed} scrolls.")
                    break
                last_height = new_height
        
        return scrolls_performed

    def handle_button_click_smart(self, selector: str, max_clicks: int, pause_time: float, item_selector: str = None) -> int:
        """
        Repeatedly clicks 'load more' button with smart detection.

        Args:
            selector: CSS selector for the button
            max_clicks: Maximum number of times to click
            pause_time: Delay between clicks
            item_selector: CSS selector to count items

        Returns:
            Number of successful clicks
        """
        clicks = 0
        last_item_count = self._count_items(item_selector) if item_selector else 0
        no_new_items_count = 0
        
        self.logger.info(f"Starting with {last_item_count} items")

        for attempt in range(max_clicks):
            try:
                # Find the button
                button = self._find_load_more_button(selector)
                
                if not button:
                    self.logger.info("Load more button not found.")
                    break
                
                if not (button.is_displayed() and button.is_enabled()):
                    self.logger.info("Load more button not clickable.")
                    break
                
                # Click the button
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                time.sleep(0.5)
                self.driver.execute_script("arguments[0].click();", button)
                clicks += 1
                
                # Wait for content to load
                time.sleep(pause_time)
                
                # Check for new items
                new_item_count = self._count_items(item_selector) if item_selector else 0
                
                if item_selector:
                    if new_item_count > last_item_count:
                        items_loaded = new_item_count - last_item_count
                        self.logger.info(f"Click {clicks}: Loaded {items_loaded} new items (total: {new_item_count})")
                        last_item_count = new_item_count
                        no_new_items_count = 0
                    else:
                        no_new_items_count += 1
                        self.logger.warning(f"Click {clicks}: No new items loaded (still {new_item_count})")
                        
                        if no_new_items_count >= 3:
                            self.logger.info("No new items after 3 clicks. Assuming all content loaded.")
                            break
                
            except (NoSuchElementException, StaleElementReferenceException) as e:
                self.logger.info(f"Button error: {e}. Likely all content loaded.")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error clicking button: {e}")
                break
        
        self.logger.info(f"Completed with {clicks} clicks, loaded {self._count_items(item_selector)} total items")
        return clicks

    def auto_detect_and_load_smart(self, item_selector: str = None):
        """
        Automatically detects and uses the best loading strategy.
        """
        self.logger.info("Auto-detecting load strategy...")
        
        # First, try to find any load more buttons
        button_found = False
        
        for keyword in self.config.LOAD_MORE_KEYWORDS:
            try:
                xpath = f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword.lower()}')] | //a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword.lower()}')]"
                elements = self.driver.find_elements(By.XPATH, xpath)
                
                for button in elements:
                    if button.is_displayed() and button.is_enabled():
                        selector = self._get_stable_selector(button)
                        if selector:
                            self.logger.info(f"Found load more button: {button.text}")
                            self.handle_button_click_smart(
                                selector, 
                                self.config.LOAD_MORE_MAX_RETRIES * 5,  # More attempts for auto
                                self.config.LOAD_MORE_PAUSE_TIME,
                                item_selector
                            )
                            button_found = True
                            break
                
                if button_found:
                    break
                    
            except Exception as e:
                self.logger.debug(f"Error searching for button with keyword '{keyword}': {e}")
                continue
        
        if not button_found:
            # Try common button selectors
            common_selectors = [
                "button.wpgb-button",
                "button.load-more",
                "a.load-more",
                ".load-more-button",
                "[class*='load'][class*='more']"
            ]
            
            for selector in common_selectors:
                try:
                    button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if button.is_displayed() and button.is_enabled():
                        self.logger.info(f"Found button with selector: {selector}")
                        self.handle_button_click_smart(
                            selector,
                            self.config.LOAD_MORE_MAX_RETRIES * 5,
                            self.config.LOAD_MORE_PAUSE_TIME,
                            item_selector
                        )
                        button_found = True
                        break
                except:
                    continue
        
        if not button_found:
            # Fallback to scrolling
            self.logger.info("No load more button found, trying scroll strategy...")
            self.handle_scroll_smart(
                self.config.LOAD_MORE_MAX_RETRIES * 2,
                self.config.LOAD_MORE_PAUSE_TIME,
                item_selector
            )

    def _find_load_more_button(self, selector: str):
        """
        Finds the load more button with multiple strategies.
        """
        try:
            # Direct CSS selector
            return self.driver.find_element(By.CSS_SELECTOR, selector)
        except:
            try:
                # Try XPath if it looks like one
                if selector.startswith("//"):
                    return self.driver.find_element(By.XPATH, selector)
            except:
                pass
        
        # Try variations
        variations = [
            selector,
            f"{selector}:visible",
            f"{selector}:enabled",
            f"{selector}:not(:disabled)"
        ]
        
        for variant in variations:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, variant)
                for elem in elements:
                    if elem.is_displayed() and elem.is_enabled():
                        return elem
            except:
                continue
        
        return None

    def _count_items(self, selector: str) -> int:
        """
        Counts the number of items matching the selector.
        """
        if not selector:
            return 0
        
        try:
            return len(self.driver.find_elements(By.CSS_SELECTOR, selector))
        except Exception as e:
            self.logger.debug(f"Error counting items: {e}")
            return 0

    def _get_stable_selector(self, element) -> Optional[str]:
        """
        Generates a stable CSS selector for an element.
        """
        try:
            # Try ID first
            elem_id = element.get_attribute('id')
            if elem_id:
                return f"#{elem_id}"

            # Try unique class combination
            tag = element.tag_name.lower()
            classes = element.get_attribute('class')
            if classes:
                class_list = classes.strip().split()
                if class_list:
                    return f"{tag}.{'.'.join(class_list)}"
            
            # Try data attributes
            for attr in ['data-id', 'data-action', 'data-load-more']:
                value = element.get_attribute(attr)
                if value:
                    return f"{tag}[{attr}='{value}']"
            
            return None
        except:
            return None

    def wait_for_items_to_load(self, initial_count: int, selector: str, timeout: float = 10) -> bool:
        """
        Waits for new items to load after an action.
        
        Returns:
            True if new items loaded, False otherwise
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            current_count = self._count_items(selector)
            if current_count > initial_count:
                return True
            time.sleep(0.5)
        
        return False