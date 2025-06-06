# src/scraper/extractors/metadata_extractor.py
"""
Specialized extractor for pulling metadata from a webpage's <head> section,
including the title and meta tags.
"""

import logging
from typing import Dict, Any

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By


class MetadataExtractor:
    """Extracts metadata from the current page."""

    def __init__(self, driver: WebDriver):
        """
        Initializes the MetadataExtractor.

        Args:
            driver: The Selenium WebDriver instance.
        """
        self.driver = driver
        self.logger = logging.getLogger(f'{__name__}.MetadataExtractor')

    def extract_all_metadata(self) -> Dict[str, Any]:
        """
        Extracts key metadata from the page.

        Returns:
            A dictionary containing the page title and meta tag data.
        """
        self.logger.debug("Extracting page metadata.")
        metadata = {}

        # Extract page title
        try:
            metadata['title'] = self.driver.title
        except Exception as e:
            self.logger.warning(f"Could not extract page title: {e}")
            metadata['title'] = None

        # Extract meta tags
        try:
            meta_tags = self.driver.find_elements(By.CSS_SELECTOR, "meta[name], meta[property]")
            for tag in meta_tags:
                try:
                    name = tag.get_attribute("name") or tag.get_attribute("property")
                    content = tag.get_attribute("content")
                    if name and content:
                        # Sanitize key for easier use
                        meta_key = f"meta_{name.replace(':', '_').replace('.', '_')}"
                        metadata[meta_key] = content
                except Exception:
                    # Ignore individual broken meta tags
                    continue
        except Exception as e:
            self.logger.error(f"Could not extract meta tags: {e}")

        self.logger.info(f"Successfully extracted {len(metadata)} metadata fields.")
        return metadata