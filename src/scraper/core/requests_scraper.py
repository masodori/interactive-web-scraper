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
            return BeautifulSoup(response.text, 'html.parser')
        except requests.RequestException as e:
            self.logger.error(f"Failed to fetch {url}: {e}")
            return None

    def close(self):
        """Closes the requests session."""
        self.logger.info("Closing requests session.")
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()