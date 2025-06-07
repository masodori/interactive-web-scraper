# src/scraper/core/requests_scraper.py
"""
Core scraper that uses the `requests` library for fast, non-JavaScript scraping.
"""

import logging
from typing import Optional

import requests
from bs4 import BeautifulSoup

from ..config import Config


class RequestScraper:
    """
    A scraper that fetches static HTML using the requests library.
    It does not process JavaScript.
    """

    def __init__(self, config: Config):
        """Initializes the RequestScraper."""
        self.logger = logging.getLogger(f'{__name__}.RequestScraper')
        self.config = config
        self.session = requests.Session()
        # Use a common browser user-agent
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.current_url = None
        self.current_soup = None

    def navigate_to(self, url: str) -> Optional[BeautifulSoup]:
        """
        Fetches the content of a URL and parses it with BeautifulSoup.

        Args:
            url: The URL to fetch.

        Returns:
            A BeautifulSoup object if successful, otherwise None.
        """
        self.logger.info(f"Fetching URL with requests: {url}")
        try:
            response = self.session.get(url, timeout=self.config.DEFAULT_TIMEOUT)
            # Raise an exception for bad status codes (4xx or 5xx)
            response.raise_for_status()
            self.current_url = url
            # Use html.parser, but lxml is faster if installed
            self.current_soup = BeautifulSoup(response.text, 'html.parser')
            return self.current_soup
        except requests.RequestException as e:
            self.logger.error(f"Failed to fetch {url}: {e}")
            return None

    def extract_text(self, selector: str) -> Optional[str]:
        """Extract text from a single element"""
        if not self.current_soup:
            return None
        
        try:
            element = self.current_soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
            return None
        except Exception as e:
            self.logger.debug(f"Failed to extract text with selector {selector}: {e}")
            return None
    
    def extract_multiple_texts(self, selector: str) -> list:
        """Extract text from multiple elements"""
        if not self.current_soup:
            return []
        
        try:
            elements = self.current_soup.select(selector)
            return [elem.get_text(strip=True) for elem in elements]
        except Exception as e:
            self.logger.debug(f"Failed to extract multiple texts with selector {selector}: {e}")
            return []
    
    def get_page_source(self) -> str:
        """Get the current page source"""
        if self.current_soup:
            return str(self.current_soup)
        return ""
    
    def close(self):
        """Closes the requests session."""
        self.logger.info("Closing requests session.")
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()