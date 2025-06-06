# src/scraper/extractors/table_extractor.py
"""
Specialized extractor for parsing HTML tables and converting them into a
structured format (list of dictionaries).
"""

import logging
from typing import List, Dict, Optional, Any

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException


class TableExtractor:
    """Extracts and parses data from HTML tables."""

    def __init__(self, driver: WebDriver):
        """
        Initializes the TableExtractor.

        Args:
            driver: The Selenium WebDriver instance.
        """
        self.driver = driver
        self.logger = logging.getLogger(f'{__name__}.TableExtractor')

    def extract_table(self, selector: str) -> Optional[List[Dict[str, Any]]]:
        """
        Finds a table by its selector and extracts its data.

        The method first tries to find headers in `<thead>`. If not found, it
        assumes the first `<tr>` contains the headers. It then iterates over
        the rows in `<tbody>` (or all `<tr>` elements if no `<tbody>` exists)
        and maps cell data to the corresponding header.

        Args:
            selector: The CSS selector for the table element.

        Returns:
            A list of dictionaries, where each dictionary represents a row.
            Returns None if the table cannot be found.
        """
        self.logger.debug(f"Attempting to extract table with selector: {selector}")
        try:
            table_element = self.driver.find_element(By.CSS_SELECTOR, selector)
            
            # 1. Extract Headers
            headers = []
            # First, try to find headers in a <thead> tag
            header_elements = table_element.find_elements(By.CSS_SELECTOR, "thead th, thead td")
            if not header_elements:
                # If no <thead>, assume the first row contains headers
                header_elements = table_element.find_elements(By.CSS_SELECTOR, "tr:first-child th, tr:first-child td")
            
            headers = [h.text.strip() for h in header_elements]
            if not headers:
                self.logger.warning(f"No headers found for table: {selector}. Cannot extract structured data.")
                return None

            # 2. Extract Rows
            rows_data = []
            # Prefer rows from <tbody>
            row_elements = table_element.find_elements(By.CSS_SELECTOR, "tbody tr")
            if not row_elements:
                # If no <tbody>, get all rows and skip the header row
                row_elements = table_element.find_elements(By.CSS_SELECTOR, "tr")[1:]

            for row in row_elements:
                cells = row.find_elements(By.CSS_SELECTOR, "td, th")
                # Ensure the number of cells matches the number of headers
                if len(cells) == len(headers):
                    row_data = {headers[i]: cells[i].text.strip() for i in range(len(headers))}
                    rows_data.append(row_data)
                else:
                    self.logger.debug(f"Skipping row with mismatched cell count. Expected {len(headers)}, found {len(cells)}.")

            self.logger.info(f"Successfully extracted {len(rows_data)} rows from table: {selector}")
            return rows_data

        except NoSuchElementException:
            self.logger.warning(f"Table not found with selector: {selector}")
            return None
        except Exception as e:
            self.logger.error(f"An unexpected error occurred while extracting table {selector}: {e}")
            return None