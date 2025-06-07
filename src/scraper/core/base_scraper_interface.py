# src/scraper/core/base_scraper_interface.py
"""
Base interface for scrapers to support multiple engines.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any


class BaseScraperInterface(ABC):
    """Abstract base class defining the interface for all scrapers."""
    
    @abstractmethod
    def navigate_to(self, url: str) -> bool:
        """Navigate to a URL."""
        pass
    
    @abstractmethod
    def execute_script(self, script: str) -> Any:
        """Execute JavaScript in the browser."""
        pass
    
    @abstractmethod
    def find_element(self, selector: str) -> Optional[Any]:
        """Find an element by CSS selector."""
        pass
    
    @abstractmethod
    def get_page_source(self) -> str:
        """Get the current page HTML."""
        pass
    
    @abstractmethod
    def close(self):
        """Close the browser/connection."""
        pass
    
    @abstractmethod
    def wait_for_element(self, selector: str, timeout: int = 10) -> bool:
        """Wait for an element to appear."""
        pass