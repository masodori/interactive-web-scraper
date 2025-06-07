# src/scraper/core/enhanced_template_scraper.py
"""
Enhanced template scraper that integrates all improvements:
- Pattern-based extraction
- Playwright engine support
- Rate limiting
- Template migration
- Advanced selector strategies
"""

import logging
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor

from ..models import (
    ScrapingTemplate,
    ScrapeResult,
    ScrapedItem,
    ExportFormat,
    ScrapingType
)
from ..config import Config
from ..utils.rate_limiter import DomainRateLimiter, RATE_LIMIT_PRESETS
from ..utils.template_migration import TemplateMigrationManager
from ..extractors.enhanced_element_extractor import EnhancedElementExtractor
from ..extractors.pattern_extractor import PatternExtractor

# Import engine-specific components
from .base_scraper import BaseScraper
from .requests_scraper import RequestScraper
from .playwright_scraper import PlaywrightScraper, PlaywrightExtractor
from .template_scraper import TemplateScraper

# Import exporters
from ..exporters import JsonExporter, CsvExporter, ExcelExporter, HtmlExporter


class EnhancedTemplateScraper(TemplateScraper):
    """Enhanced template scraper with all new features"""
    
    def __init__(self, engine: str = 'selenium', headless: bool = True, 
                 rate_limit_preset: str = 'respectful_bot'):
        """
        Initialize enhanced scraper
        
        Args:
            engine: Scraping engine ('selenium', 'requests', 'playwright')
            headless: Run browser in headless mode
            rate_limit_preset: Rate limiting preset name
        """
        # For playwright, initialize manually to bypass parent's engine validation
        if engine == 'playwright':
            self.logger = logging.getLogger(f'{__name__}.EnhancedTemplateScraper')
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
        else:
            # Initialize base class for selenium/requests
            super().__init__(engine, headless)
        
        # Initialize rate limiter
        rate_config = RATE_LIMIT_PRESETS.get(rate_limit_preset)
        self.rate_limiter = DomainRateLimiter(rate_config)
        
        # Initialize pattern extractor
        self.pattern_extractor = PatternExtractor()
        
        # Initialize migration manager
        self.migration_manager = TemplateMigrationManager()
        
        # Override extractors with enhanced versions
        if self.engine == 'selenium':
            self.extractor = EnhancedElementExtractor(self.scraper.driver)
        elif self.engine == 'playwright':
            self._init_playwright()
        
        self.logger.info(f"Enhanced scraper initialized with {engine} engine")
    
    def _init_playwright(self):
        """Initialize Playwright components"""
        try:
            self.playwright_scraper = PlaywrightScraper(
                headless=self.headless,
                browser_type='chromium'
            )
            # Run async initialization
            asyncio.run(self.playwright_scraper._init_browser())
            self.playwright_extractor = PlaywrightExtractor(self.playwright_scraper.page)
            self.logger.info("Playwright engine initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize Playwright: {e}")
            raise
    
    def apply_template(self, template_path: str, 
                      export_formats: Optional[List[ExportFormat]] = None,
                      auto_migrate: bool = True) -> ScrapeResult:
        """
        Apply template with automatic migration and enhancements
        
        Args:
            template_path: Path to template file
            export_formats: Export formats
            auto_migrate: Automatically migrate old templates
            
        Returns:
            Scraping results
        """
        # Load and potentially migrate template
        template = ScrapingTemplate.load(template_path)
        
        if auto_migrate and self.migration_manager.needs_migration(template.to_dict()):
            self.logger.info("Migrating template to latest version")
            template_dict = self.migration_manager.migrate_template(template.to_dict())
            template = ScrapingTemplate.from_dict(template_dict)
            
            # Save migrated template
            template.save(template_path)
        
        # Check if template engine matches scraper engine
        template_engine = getattr(template, 'engine', 'selenium')
        if template_engine != self.engine:
            self.logger.warning(f"Template engine ({template_engine}) doesn't match scraper engine ({self.engine})")
            # Respect the template's engine choice by reinitializing if needed
            if template_engine in ['selenium', 'requests', 'playwright']:
                self.__init__(engine=template_engine, headless=self.headless, rate_limit_preset='respectful_bot')
        
        # Check rate limit configuration
        template_dict = template.to_dict()
        if template_dict.get('rate_limiting', {}).get('enabled'):
            preset = template_dict['rate_limiting'].get('preset', 'respectful_bot')
            if preset in RATE_LIMIT_PRESETS:
                self.rate_limiter.default_config = RATE_LIMIT_PRESETS[preset]
        
        # Apply template based on engine
        if self.engine == 'playwright':
            return self._apply_template_playwright(template, export_formats)
        else:
            # For both selenium and requests engines, use parent's apply_template
            # which already handles the engine-specific logic
            return super().apply_template(template_path, export_formats)
    
    def _apply_template_playwright(self, template: ScrapingTemplate,
                                 export_formats: Optional[List[ExportFormat]] = None) -> ScrapeResult:
        """Apply template using Playwright engine"""
        start_time = datetime.now()
        items: List[ScrapedItem] = []
        errors: List[str] = []
        
        async def scrape_async():
            try:
                # Navigate to URL
                await self.playwright_scraper.navigate_to(template.site_info.url)
                
                # Handle cookies
                await self.playwright_scraper.handle_cookies()
                
                # Scrape based on type
                if template.scraping_type == ScrapingType.SINGLE_PAGE:
                    items.extend(await self._scrape_single_page_playwright(template))
                else:
                    items.extend(await self._scrape_list_page_playwright(template))
                    
            except Exception as e:
                self.logger.error(f"Playwright scraping error: {e}")
                errors.append(str(e))
        
        # Run async scraping
        asyncio.run(scrape_async())
        
        # Create result
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
    
    async def _scrape_single_page_playwright(self, template: ScrapingTemplate) -> List[ScrapedItem]:
        """Scrape single page with Playwright"""
        page_rules = template.detail_page_rules
        if not page_rules:
            return []
        
        data = {}
        
        # Extract using selectors
        for field_name, selector in page_rules.fields.items():
            value = await self.playwright_scraper.get_text(selector)
            if value:
                data[field_name] = value
        
        # Apply pattern extraction if enabled
        if hasattr(page_rules, 'extraction_patterns'):
            page_content = await self.playwright_scraper.get_page_content()
            for field_name, pattern_config in page_rules.extraction_patterns.items():
                if field_name not in data or not data[field_name]:
                    value = self.pattern_extractor.extract(
                        page_content,
                        field_name,
                        context=' '.join(pattern_config.get('context_keywords', []))
                    )
                    if value:
                        data[field_name] = value
        
        return [ScrapedItem(
            url=self.playwright_scraper.current_url,
            timestamp=datetime.now().isoformat(),
            data=data
        )]
    
    async def _scrape_list_page_playwright(self, template: ScrapingTemplate) -> List[ScrapedItem]:
        """Scrape list page with Playwright"""
        list_rules = template.list_page_rules
        if not list_rules:
            return []
        
        items = []
        
        # Get all list items
        item_selector = list_rules.repeating_item_selector
        item_elements = await self.playwright_scraper.page.query_selector_all(item_selector)
        
        for element in item_elements:
            item_data = {}
            
            # Extract fields
            for field_name, selector in list_rules.fields.items():
                try:
                    field_element = await element.query_selector(selector)
                    if field_element:
                        value = await field_element.text_content()
                        if value:
                            item_data[field_name] = value.strip()
                except Exception as e:
                    self.logger.debug(f"Error extracting {field_name}: {e}")
            
            # Get detail URL if needed
            detail_url = None
            if template.scraping_type == ScrapingType.LIST_DETAIL and list_rules.profile_link_selector:
                try:
                    link_element = await element.query_selector(list_rules.profile_link_selector)
                    if link_element:
                        detail_url = await link_element.get_attribute('href')
                except Exception:
                    pass
            
            if item_data or detail_url:
                items.append(ScrapedItem(
                    url=self.playwright_scraper.current_url,
                    timestamp=datetime.now().isoformat(),
                    data=item_data,
                    detail_url=detail_url
                ))
        
        # Handle detail pages if needed
        if template.scraping_type == ScrapingType.LIST_DETAIL:
            await self._scrape_detail_pages_playwright(items, template.detail_page_rules)
        
        return items
    
    async def _scrape_detail_pages_playwright(self, items: List[ScrapedItem], detail_rules):
        """Scrape detail pages with Playwright"""
        for item in items:
            if not item.detail_url:
                continue
            
            try:
                # Apply rate limiting
                self.rate_limiter.acquire(item.detail_url)
                
                # Navigate to detail page
                await self.playwright_scraper.navigate_to(item.detail_url)
                
                # Extract data
                detail_data = {}
                for field_name, selector in detail_rules.fields.items():
                    value = await self.playwright_scraper.get_text(selector)
                    if value:
                        detail_data[field_name] = value
                
                # Apply pattern extraction
                if hasattr(detail_rules, 'extraction_patterns'):
                    page_content = await self.playwright_scraper.get_page_content()
                    for field_name, pattern_config in detail_rules.extraction_patterns.items():
                        if field_name not in detail_data:
                            value = self.pattern_extractor.extract(
                                page_content,
                                field_name
                            )
                            if value:
                                detail_data[field_name] = value
                
                item.detail_data = detail_data
                
            except Exception as e:
                self.logger.error(f"Error scraping detail page {item.detail_url}: {e}")
                item.errors.append(str(e))
    
    def _extract_detail_data_smart(self, detail_rules) -> Dict[str, Any]:
        """
        Override parent method to use enhanced extraction
        """
        if self.engine != 'selenium':
            return super()._extract_detail_data_smart(detail_rules)
        
        detail_data = {}
        
        # Use enhanced extractor for Selenium
        if isinstance(self.extractor, EnhancedElementExtractor):
            # Check if template has pattern configurations
            patterns = {}
            if hasattr(detail_rules, 'extraction_patterns'):
                patterns = {
                    field: config.get('pattern', field)
                    for field, config in detail_rules.extraction_patterns.items()
                }
            
            # Extract with patterns
            detail_data = self.extractor.extract_with_patterns(
                detail_rules.fields,
                patterns
            )
            
            # Try advanced strategies for missing fields
            if hasattr(detail_rules, 'advanced_selectors'):
                config = detail_rules.advanced_selectors
                
                for field_name, selector in detail_rules.fields.items():
                    if field_name not in detail_data:
                        # Try text-based selection
                        if config.get('use_text_content', {}).get(field_name):
                            text_to_find = config['use_text_content'][field_name]
                            value = self.extractor.find_and_extract_by_label(
                                text_to_find
                            )
                            if value:
                                detail_data[field_name] = value
                        
                        # Try proximity-based selection
                        elif config.get('use_proximity', {}).get(field_name):
                            prox_config = config['use_proximity'][field_name]
                            # Implementation depends on specific configuration
                            pass
        else:
            # Fallback to parent implementation
            detail_data = super()._extract_detail_data_smart(detail_rules)
        
        return detail_data
    
    def close(self):
        """Clean up resources"""
        if hasattr(self, 'playwright_scraper'):
            asyncio.run(self.playwright_scraper.close())
        
        super().close()
    
    def get_scraping_stats(self) -> Dict[str, Any]:
        """Get scraping statistics including rate limiting"""
        stats = {
            'engine': self.engine,
            'rate_limiting': self.rate_limiter.get_stats()
        }
        
        return stats