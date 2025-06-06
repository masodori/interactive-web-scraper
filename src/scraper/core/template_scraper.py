# src/scraper/core/template_scraper.py
"""
Scraper that applies a JSON template to perform a structured scraping task,
handling various scraping modes and orchestrating handlers and exporters.
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from selenium.webdriver.common.by import By # <-- Import By

from .base_scraper import BaseScraper
from ..models import (
    ScrapingTemplate,
    ScrapeResult,
    ScrapedItem,
    ExportFormat,
    ScrapingType
)
from ..extractors import ElementExtractor, TableExtractor
from ..handlers import LoadMoreHandler, PaginationHandler
from ..exporters import JsonExporter, CsvExporter, ExcelExporter, HtmlExporter


class TemplateScraper(BaseScraper):
    """Orchestrates a scraping job based on a JSON template."""

    def __init__(self, headless: bool = True):
        """Initializes the TemplateScraper."""
        super().__init__(headless)
        self.extractor = ElementExtractor(self.driver)
        self.table_extractor = TableExtractor(self.driver)
        self.load_more_handler = LoadMoreHandler(self.driver, self.config)
        self.pagination_handler = PaginationHandler(self.driver, self.config)
        self.exporters = {
            ExportFormat.JSON: JsonExporter(),
            ExportFormat.CSV: CsvExporter(),
            ExportFormat.EXCEL: ExcelExporter(),
            ExportFormat.HTML: HtmlExporter(),
        }

    def apply_template(
        self,
        template_path: str,
        export_formats: Optional[List[ExportFormat]] = None
    ) -> ScrapeResult:
        """
        Loads a template and executes the scraping and exporting process.
        """
        start_time = datetime.now()
        template = ScrapingTemplate.load(template_path)
        self.logger.info(f"Applying template: {template.name}")

        items: List[ScrapedItem] = []
        errors: List[str] = []

        try:
            self.navigate_to(template.site_info.url)
            self.cookie_handler.accept_cookies()

            if template.scraping_type in (ScrapingType.LIST_ONLY, ScrapingType.LIST_DETAIL):
                items = self._scrape_list_page(template)
            elif template.scraping_type == ScrapingType.SINGLE_PAGE:
                items = self._scrape_single_page(template)
            else:
                raise ValueError(f"Unknown scraping type: {template.scraping_type}")

        except Exception as e:
            self.logger.error(f"A critical error occurred while applying template {template.name}: {e}", exc_info=True)
            errors.append(str(e))

        result = ScrapeResult(
            template_name=template.name,
            start_time=start_time.isoformat(),
            end_time=datetime.now().isoformat(),
            total_items=len(items),
            items=items,
            errors=errors,
            successful_items=0,
            failed_items=0
        )

        if export_formats:
            self._export_results(result, export_formats)

        return result

    def _scrape_list_page(self, template: ScrapingTemplate) -> List[ScrapedItem]:
        """Handles scraping for list_only and list_detail types."""
        list_rules = template.list_page_rules
        if not list_rules or not list_rules.repeating_item_selector:
            raise ValueError("Template for list scraping is missing 'repeating_item_selector'.")

        self.load_more_handler.execute_loading(list_rules.load_strategy)

        # CORRECTED LINE
        item_elements = self.driver.find_elements(By.CSS_SELECTOR, list_rules.repeating_item_selector)
        self.logger.info(f"Found {len(item_elements)} items matching selector '{list_rules.repeating_item_selector}'.")
        
        scraped_items = []
        for i, element in enumerate(item_elements):
            self.logger.debug(f"Scraping item {i+1}/{len(item_elements)}")
            item_data = {}
            for field_name, selector in list_rules.fields.items():
                item_data[field_name] = self.extractor.extract_text(selector, parent=element)

            detail_url = None
            if template.scraping_type == ScrapingType.LIST_DETAIL:
                link_data = self.extractor.extract_link(list_rules.profile_link_selector, parent=element)
                if link_data and link_data.get("href"):
                    detail_url = link_data["href"]
                else:
                    self.logger.warning(f"Could not find detail link for item {i+1}.")

            scraped_items.append(ScrapedItem(
                url=self.get_current_url(),
                timestamp=datetime.now().isoformat(),
                data=item_data,
                detail_url=detail_url
            ))

        if template.scraping_type == ScrapingType.LIST_DETAIL:
            self._scrape_detail_pages(scraped_items, template.detail_page_rules)
            
        return scraped_items

    def _scrape_detail_pages(self, items: List[ScrapedItem], detail_rules):
        """Iterates through items and scrapes their detail pages."""
        if not detail_rules:
            return
            
        original_url = self.get_current_url()
        for i, item in enumerate(items):
            if not item.detail_url:
                continue

            self.logger.debug(f"Scraping detail page {i+1}/{len(items)}: {item.detail_url}")
            self.navigate_to(item.detail_url)
            
            detail_data = {}
            for field_name, selector in detail_rules.fields.items():
                detail_data[field_name] = self.extractor.extract_text(selector)
            
            item.detail_data = detail_data
        
        self.navigate_to(original_url)

    def _scrape_single_page(self, template: ScrapingTemplate) -> List[ScrapedItem]:
        """Handles scraping for single_page type."""
        page_rules = template.detail_page_rules
        if not page_rules:
            raise ValueError("Template for single page scraping is missing 'detail_page_rules'.")

        data = {}
        for field_name, selector in page_rules.fields.items():
            data[field_name] = self.extractor.extract_text(selector)
        
        item = ScrapedItem(
            url=self.get_current_url(),
            timestamp=datetime.now().isoformat(),
            data=data
        )
        return [item]

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