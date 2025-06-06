# src/scraper/extractors/requests_extractor.py
"""
Element extraction functionality for static HTML using BeautifulSoup.
"""

import logging
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag


class RequestExtractor:
    """Extract data from parsed BeautifulSoup content."""

    def __init__(self, soup: BeautifulSoup, base_url: str):
        """
        Initialize extractor with a BeautifulSoup object and a base URL.

        Args:
            soup: The BeautifulSoup object representing the parsed page.
            base_url: The original URL of the page for resolving relative links.
        """
        self.soup = soup
        self.base_url = base_url
        self.logger = logging.getLogger(f'{__name__}.RequestExtractor')

    def extract_text(self, selector: str, parent: Optional[Tag] = None,
                     multiple: bool = False) -> Optional[Union[str, List[str]]]:
        """Extract text from element(s) using a CSS selector."""
        search_context = parent or self.soup
        if not search_context:
            return [] if multiple else None
            
        try:
            if multiple:
                elements = search_context.select(selector)
                return [elem.get_text(strip=True) for elem in elements if elem.get_text(strip=True)]
            else:
                element = search_context.select_one(selector)
                return element.get_text(strip=True) if element else None
        except Exception as e:
            self.logger.warning(f"Error extracting text from {selector}: {e}")
            return [] if multiple else None

    def extract_attribute(self, selector: str, attribute: str,
                          parent: Optional[Tag] = None,
                          multiple: bool = False) -> Optional[Union[str, List[str]]]:
        """Extract an attribute value from element(s)."""
        search_context = parent or self.soup
        if not search_context:
            return [] if multiple else None

        try:
            if multiple:
                elements = search_context.select(selector)
                return [elem.get(attribute) for elem in elements if elem.get(attribute)]
            else:
                element = search_context.select_one(selector)
                return element.get(attribute) if element else None
        except Exception as e:
            self.logger.warning(f"Error extracting attribute '{attribute}' from {selector}: {e}")
            return [] if multiple else None

    def extract_link(self, selector: str, parent: Optional[Tag] = None,
                     absolute: bool = True) -> Optional[Dict[str, str]]:
        """Extract link (href and text) from an 'a' tag."""
        search_context = parent or self.soup
        if not search_context:
            return None
        
        try:
            # Find the link element itself
            link_element = search_context.select_one(selector)
            if not link_element:
                return None
            
            # If the selector points to something inside an 'a' tag, find the parent link
            if link_element.name != 'a':
                anchor = link_element.find_parent('a')
            else:
                anchor = link_element

            if not anchor or not anchor.has_attr('href'):
                return None

            href = anchor.get('href')
            if absolute and href:
                # Convert relative URL to absolute
                href = urljoin(self.base_url, href)

            return {
                "href": href,
                "text": link_element.get_text(strip=True),
                "title": anchor.get('title', '')
            }
        except Exception as e:
            self.logger.warning(f"Error extracting link from {selector}: {e}")
            return None