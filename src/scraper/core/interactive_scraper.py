# src/scraper/core/interactive_scraper.py
"""
Interactive scraper for backward compatibility.
This module provides the InteractiveScraper class which is now
implemented as EnhancedInteractiveScraper.
"""

from .enhanced_interactive_scraper import EnhancedInteractiveScraper


class InteractiveScraper(EnhancedInteractiveScraper):
    """
    Interactive scraper for creating templates through user interaction.
    
    This class maintains backward compatibility by inheriting from
    EnhancedInteractiveScraper which includes all the original functionality
    plus additional features.
    """
    pass