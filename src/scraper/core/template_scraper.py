# src/scraper/core/template_scraper.py
"""
Scraper that applies a JSON template to perform a structured scraping task,
handling various scraping modes and orchestrating handlers and exporters.
Now supports both 'selenium' and 'requests' engines.
"""

import logging
import time
import re
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    ElementNotInteractableException,
)

# Engine-specific imports
from .base_scraper import BaseScraper
from .requests_scraper import RequestScraper
from ..extractors.element_extractor import ElementExtractor
from ..extractors.requests_extractor import RequestExtractor
from ..extractors.table_extractor import TableExtractor

# Model imports - Config is imported from config module, not data_models
from ..models import (
    ScrapingTemplate,
    ScrapeResult,
    ScrapedItem,
    ExportFormat,
    ScrapingType
)
from ..config import Config  # This is the correct import location

# Handler imports
from ..handlers import LoadMoreHandler, PaginationHandler, CookieHandler
from ..exporters import JsonExporter, CsvExporter, ExcelExporter, HtmlExporter


class TemplateScraper:
    """
    Orchestrates a scraping job based on a JSON template, using either
    Selenium for dynamic sites or Requests for static sites.
    """

    def __init__(self, engine: str = 'selenium', headless: bool = True):
        """Initializes the TemplateScraper with a specific engine."""
        self.logger = logging.getLogger(f'{__name__}.TemplateScraper')
        self.config = Config()
        self.engine = engine
        self.headless = headless

        # Initialize exporters
        self.exporters = {
            ExportFormat.JSON: JsonExporter(),
            ExportFormat.CSV: CsvExporter(),
            ExportFormat.EXCEL: ExcelExporter(),
            ExportFormat.HTML: HtmlExporter(),
        }

        # Conditionally initialize the scraper and its components
        if self.engine == 'selenium':
            self.scraper = BaseScraper(headless=self.headless)
            self.extractor = ElementExtractor(self.scraper.driver)
            self.table_extractor = TableExtractor(self.scraper.driver)
            self.load_more_handler = LoadMoreHandler(self.scraper.driver, self.config)
            self.pagination_handler = PaginationHandler(self.scraper.driver, self.config)
            self.cookie_handler = self.scraper.cookie_handler
        elif self.engine == 'requests':
            self.scraper = RequestScraper(config=self.config)
            # Extractor will be initialized on a per-page basis for requests
            self.extractor = None
        else:
            raise ValueError(f"Unsupported engine: '{self.engine}'. Choose 'selenium' or 'requests'.")

        self.logger.info(f"TemplateScraper initialized with '{self.engine}' engine.")

    def close(self):
        """Safely closes the underlying scraper engine."""
        if self.scraper:
            self.scraper.close()

    def apply_template(
        self,
        template_path: str,
        export_formats: Optional[List[ExportFormat]] = None
    ) -> ScrapeResult:
        """
        Loads a template and executes the scraping and exporting process
        using the configured engine.
        """
        start_time = datetime.now()
        template = ScrapingTemplate.load(template_path)
        self.logger.info(f"Applying template: {template.name} with '{self.engine}' engine")

        items: List[ScrapedItem] = []
        errors: List[str] = []

        try:
            if self.engine == 'selenium':
                # Use Selenium-based scraping logic
                self.scraper.navigate_to(template.site_info.url)
                self.cookie_handler.accept_cookies()

                if template.scraping_type in (ScrapingType.LIST_ONLY, ScrapingType.LIST_DETAIL):
                    items = self._scrape_list_page_selenium(template)
                elif template.scraping_type == ScrapingType.SINGLE_PAGE:
                    items = self._scrape_single_page_selenium(template)

            elif self.engine == 'requests':
                # Use Requests-based scraping logic
                items = self._scrape_with_requests(template)

        except Exception as e:
            self.logger.error(f"A critical error occurred while applying template {template.name}: {e}", exc_info=True)
            errors.append(str(e))
        finally:
            self.close()

        result = ScrapeResult(
            template_name=template.name,
            start_time=start_time.isoformat(),
            end_time=datetime.now().isoformat(),
            total_items=len(items),
            items=items,
            errors=errors,
            successful_items=0,  # Will be recalculated in post_init
            failed_items=0      # Will be recalculated in post_init
        )

        if export_formats:
            self._export_results(result, export_formats)

        return result

    # --- Requests Engine Methods ---

    def _scrape_with_requests(self, template: ScrapingTemplate) -> List[ScrapedItem]:
        """High-level scraping orchestrator for the requests engine."""
        initial_soup = self.scraper.navigate_to(template.site_info.url)
        if not initial_soup:
            self.logger.error(f"Failed to fetch initial URL: {template.site_info.url}")
            return []

        if template.scraping_type == ScrapingType.SINGLE_PAGE:
            return self._scrape_single_page_requests(template, initial_soup)
        else: # LIST_ONLY or LIST_DETAIL
            return self._scrape_list_page_requests(template, initial_soup)

    def _scrape_list_page_requests(self, template: ScrapingTemplate, soup: BeautifulSoup) -> List[ScrapedItem]:
        """Scrapes a list page using Requests and BeautifulSoup."""
        list_rules = template.list_page_rules
        if not list_rules or not list_rules.repeating_item_selector:
            raise ValueError("Template for list scraping is missing 'repeating_item_selector'.")

        extractor = RequestExtractor(soup, self.scraper.current_url)
        item_elements = soup.select(list_rules.repeating_item_selector)
        self.logger.info(f"Found {len(item_elements)} items on the list page.")

        scraped_items = []
        for element in item_elements:
            item_data = {}
            for field_name, selector in list_rules.fields.items():
                value = extractor.extract_text(selector, parent=element)
                if value:
                    item_data[field_name] = value

            detail_url = None
            if template.scraping_type == ScrapingType.LIST_DETAIL and list_rules.profile_link_selector:
                link_data = extractor.extract_link(list_rules.profile_link_selector, parent=element)
                if link_data and link_data.get("href"):
                    detail_url = link_data["href"]

            if item_data or detail_url:
                scraped_items.append(ScrapedItem(
                    url=self.scraper.current_url,
                    timestamp=datetime.now().isoformat(),
                    data=item_data,
                    detail_url=detail_url
                ))

        if template.scraping_type == ScrapingType.LIST_DETAIL:
            self._scrape_detail_pages_parallel(scraped_items, template.detail_page_rules)

        return scraped_items

    def _scrape_detail_pages_parallel(self, items: List[ScrapedItem], detail_rules):
        """Scrapes detail pages in parallel using a thread pool."""
        if not detail_rules:
            return

        items_to_scrape = [item for item in items if item.detail_url]
        self.logger.info(f"Starting parallel scrape of {len(items_to_scrape)} detail pages.")

        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_item = {executor.submit(self._scrape_single_detail_page_requests, item, detail_rules): item for item in items_to_scrape}
            for future in as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    # The result of the future is the item itself, now updated
                    future.result()
                except Exception as exc:
                    self.logger.error(f"Detail page {item.detail_url} generated an exception: {exc}")
                    item.errors.append(str(exc))
        self.logger.info("Finished parallel scraping of detail pages.")


    def _scrape_single_detail_page_requests(self, item: ScrapedItem, detail_rules) -> ScrapedItem:
        """Scrapes a single detail page, designed to be called by the thread pool."""
        detail_soup = self.scraper.navigate_to(item.detail_url)
        if not detail_soup:
            item.errors.append(f"Failed to fetch detail URL: {item.detail_url}")
            return item

        extractor = RequestExtractor(detail_soup, item.detail_url)
        detail_data = {}
        for field_name, selector in detail_rules.fields.items():
            value = extractor.extract_text(selector)
            if value:
                detail_data[field_name] = value
        
        item.detail_data = detail_data
        return item


    def _scrape_single_page_requests(self, template: ScrapingTemplate, soup: BeautifulSoup) -> List[ScrapedItem]:
        """Handles single page scraping with the requests engine."""
        page_rules = template.detail_page_rules
        if not page_rules:
            raise ValueError("Template for single page scraping is missing 'detail_page_rules'.")
        
        extractor = RequestExtractor(soup, self.scraper.current_url)
        data = {}
        for field_name, selector in page_rules.fields.items():
            value = extractor.extract_text(selector)
            if value:
                data[field_name] = value

        item = ScrapedItem(
            url=self.scraper.current_url,
            timestamp=datetime.now().isoformat(),
            data=data
        )
        return [item]


    # --- Selenium Engine Methods ---

    def _scrape_list_page_selenium(self, template: ScrapingTemplate) -> List[ScrapedItem]:
        """Handles scraping for list_only and list_detail types with Selenium.
        
        This method has been optimized to extract items incrementally while the
        next set of results is loading. This reduces idle wait time when dealing
        with pagination or "load more" buttons.
        """

        list_rules = template.list_page_rules
        if not list_rules or not list_rules.repeating_item_selector:
            raise ValueError("Template for list scraping is missing 'repeating_item_selector'.")

        strategy = list_rules.load_strategy
        item_selector = list_rules.repeating_item_selector

        scraped_items: List[ScrapedItem] = []
        processed_count = 0

        def process_elements(elements: List[Any]):
            nonlocal processed_count
            for element in elements:
                try:
                    item_data = {}
                    for field_name, selector in list_rules.fields.items():
                        value = self.extractor.extract_text(selector, parent=element)
                        if value:
                            item_data[field_name] = value

                    detail_url = None
                    if template.scraping_type == ScrapingType.LIST_DETAIL and list_rules.profile_link_selector:
                        link_data = self.extractor.extract_link(list_rules.profile_link_selector, parent=element)
                        if link_data and link_data.get("href"):
                            detail_url = link_data["href"]

                    if item_data or detail_url:
                        scraped_items.append(ScrapedItem(
                            url=self.scraper.get_current_url(),
                            timestamp=datetime.now().isoformat(),
                            data=item_data,
                            detail_url=detail_url
                        ))
                except Exception as e:
                    self.logger.error(f"Error processing item {processed_count + 1}: {e}")
                    scraped_items.append(ScrapedItem(
                        url=self.scraper.get_current_url(),
                        timestamp=datetime.now().isoformat(),
                        data={},
                        errors=[str(e)]
                    ))
                processed_count += 1

        pause_time = strategy.pause_time

        while True:
            current_elements = self.scraper.driver.find_elements(By.CSS_SELECTOR, item_selector)
            new_elements = current_elements[processed_count:]
            if new_elements:
                process_elements(new_elements)

            # Determine if another page should be loaded
            if strategy.type == LoadStrategy.BUTTON and strategy.button_selector:
                try:
                    button = self.scraper.driver.find_element(By.CSS_SELECTOR, strategy.button_selector)
                    if not (button.is_displayed() and button.is_enabled()):
                        break
                    self.scraper.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", button)
                    time.sleep(0.5)
                    self.scraper.driver.execute_script("arguments[0].click();", button)
                    time.sleep(pause_time)
                    continue
                except (NoSuchElementException, StaleElementReferenceException, ElementNotInteractableException):
                    break

            elif strategy.type == LoadStrategy.PAGINATION and strategy.pagination_next_selector:
                try:
                    next_button = self.scraper.driver.find_element(By.CSS_SELECTOR, strategy.pagination_next_selector)
                    if not (next_button.is_displayed() and next_button.is_enabled()):
                        break
                    self.scraper.driver.execute_script("arguments[0].click();", next_button)
                    time.sleep(pause_time)
                    continue
                except (NoSuchElementException, StaleElementReferenceException):
                    break

            else:
                # For scrolling or no strategy, load once and exit
                if strategy.type in (LoadStrategy.SCROLL, LoadStrategy.AUTO):
                    self.load_more_handler.execute_loading(strategy, item_selector=item_selector)
                break

        # Process any items that loaded after the final click
        final_elements = self.scraper.driver.find_elements(By.CSS_SELECTOR, item_selector)
        if len(final_elements) > processed_count:
            process_elements(final_elements[processed_count:])

        if template.scraping_type == ScrapingType.LIST_DETAIL:
            self._scrape_detail_pages_selenium(scraped_items, template.detail_page_rules)

        return scraped_items

    def _scrape_detail_pages_selenium(self, items: List[ScrapedItem], detail_rules):
        """Scrapes detail pages sequentially using Selenium."""
        if not detail_rules:
            return
        
        original_url = self.scraper.get_current_url()
        for item in items:
            if not item.detail_url:
                continue
            try:
                if not self.scraper.navigate_to(item.detail_url):
                    item.errors.append("Failed to navigate to detail page")
                    continue
                time.sleep(1) # Simple wait for page load
                item.detail_data = self._extract_detail_data_smart(detail_rules)
            except Exception as e:
                self.logger.error(f"Error scraping detail page {item.detail_url}: {e}")
                item.errors.append(f"Detail page error: {str(e)}")
        
        try:
            self.scraper.navigate_to(original_url)
        except Exception:
            self.logger.warning("Could not return to original list page.")


    def _scrape_single_page_selenium(self, template: ScrapingTemplate) -> List[ScrapedItem]:
        """Handles scraping for single_page type with Selenium."""
        page_rules = template.detail_page_rules
        if not page_rules:
            raise ValueError("Template for single page scraping is missing 'detail_page_rules'.")

        data = {}
        for field_name, selector in page_rules.fields.items():
            data[field_name] = self.extractor.extract_text(selector)
        
        item = ScrapedItem(
            url=self.scraper.get_current_url(),
            timestamp=datetime.now().isoformat(),
            data=data
        )
        return [item]

    # --- Common Methods ---

    def _export_results(self, result: ScrapeResult, formats: List[ExportFormat]):
        """Exports the result object to the specified formats."""
        self.logger.info(f"Exporting results in formats: {[f.value for f in formats]}")
        for fmt in formats:
            exporter = self.exporters.get(fmt)
            if exporter:
                try:
                    path = exporter.export(result)
                    if path:
                        self.logger.info(f"Successfully exported to {path}")
                    else:
                        self.logger.error(f"Export to {fmt.value} failed.")
                except Exception as e:
                    self.logger.error(f"An error occurred during {fmt.value} export: {e}", exc_info=True)
            else:
                self.logger.warning(f"No exporter found for format: {fmt.value}")

    def _extract_detail_data_smart(self, detail_rules) -> Dict[str, Any]:
        """Smart extraction of detail data with multiple strategies (Selenium)."""
        # This method remains Selenium-specific as it uses the selenium extractor.
        detail_data = {}
        for field_name, selector in detail_rules.fields.items():
            try:
                value = self.extractor.extract_text(selector)
                if value:
                    detail_data[field_name] = value
                else:
                    self.logger.debug(f"No value found for {field_name}")
            except Exception as e:
                self.logger.debug(f"Error extracting {field_name}: {e}")
        return detail_data