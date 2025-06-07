"""
Interactive Web Scraper Package

A modular, extensible web scraping framework with cookie handling,
template-based scraping, and multiple export formats.
"""

__version__ = "2.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

# Import main classes for convenient access
from .core.base_scraper import BaseScraper
from .config.settings import Config
from .models.data_models import (
    ExportFormat,
    ScrapingType,
    LoadStrategy,
    ScrapedItem,
    ScrapeResult,
    ScrapingTemplate
)

# Import unified CLI
from .unified_cli import main as unified_cli_main

# Make key classes available at package level
__all__ = [
    'BaseScraper',
    'Config',
    'ExportFormat',
    'ScrapingType',
    'LoadStrategy',
    'ScrapedItem',
    'ScrapeResult',
    'ScrapingTemplate',
    'unified_cli_main'
]