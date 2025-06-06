# src/scraper/core/template_scraper.py
"""
Scraper that applies a JSON template to perform a structured scraping task,
handling various scraping modes and orchestrating handlers and exporters.
"""

import logging
import time
import re
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any

from selenium.webdriver.common.by import By

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
        """Handles scraping for list_only and list_detail types with smart loading."""
        list_rules = template.list_page_rules
        if not list_rules or not list_rules.repeating_item_selector:
            raise ValueError("Template for list scraping is missing 'repeating_item_selector'.")

        # Execute loading strategy with item selector for smart detection
        self.load_more_handler.execute_loading(
            list_rules.load_strategy,
            item_selector=list_rules.repeating_item_selector
        )

        # Get all items after loading
        item_elements = self.driver.find_elements(By.CSS_SELECTOR, list_rules.repeating_item_selector)
        self.logger.info(f"Found {len(item_elements)} total items after loading all content")
        
        scraped_items = []
        errors_count = 0
        
        for i, element in enumerate(item_elements):
            try:
                self.logger.debug(f"Scraping item {i+1}/{len(item_elements)}")
                item_data = {}
                
                # Extract fields with better error handling
                for field_name, selector in list_rules.fields.items():
                    try:
                        value = self.extractor.extract_text(selector, parent=element)
                        if value:
                            item_data[field_name] = value
                        else:
                            self.logger.debug(f"No value found for {field_name} in item {i+1}")
                    except Exception as e:
                        self.logger.debug(f"Error extracting {field_name} from item {i+1}: {e}")

                # Extract detail URL if needed
                detail_url = None
                if template.scraping_type == ScrapingType.LIST_DETAIL and list_rules.profile_link_selector:
                    try:
                        link_data = self.extractor.extract_link(list_rules.profile_link_selector, parent=element)
                        if link_data and link_data.get("href"):
                            detail_url = link_data["href"]
                        else:
                            self.logger.warning(f"No detail link found for item {i+1}")
                    except Exception as e:
                        self.logger.warning(f"Error extracting detail link for item {i+1}: {e}")

                # Only add item if we got some data
                if item_data or detail_url:
                    scraped_items.append(ScrapedItem(
                        url=self.get_current_url(),
                        timestamp=datetime.now().isoformat(),
                        data=item_data,
                        detail_url=detail_url
                    ))
                else:
                    errors_count += 1
                    self.logger.warning(f"No data extracted for item {i+1}")
                    
            except Exception as e:
                errors_count += 1
                self.logger.error(f"Error processing item {i+1}: {e}")
                
                # Add failed item with error
                scraped_items.append(ScrapedItem(
                    url=self.get_current_url(),
                    timestamp=datetime.now().isoformat(),
                    data={},
                    errors=[str(e)]
                ))
        
        self.logger.info(f"Successfully scraped {len(scraped_items) - errors_count}/{len(item_elements)} items")

        # Scrape detail pages if needed
        if template.scraping_type == ScrapingType.LIST_DETAIL:
            self._scrape_detail_pages(scraped_items, template.detail_page_rules)
            
        return scraped_items

    def _scrape_detail_pages(self, items: List[ScrapedItem], detail_rules):
        """Enhanced detail page scraping with better extraction."""
        if not detail_rules:
            return
        
        original_url = self.get_current_url()
        success_count = 0
        
        # Process in batches to avoid memory issues
        batch_size = 50
        
        for batch_start in range(0, len(items), batch_size):
            batch_end = min(batch_start + batch_size, len(items))
            batch_items = items[batch_start:batch_end]
            
            self.logger.info(f"Processing detail pages {batch_start+1}-{batch_end} of {len(items)}")
            
            for i, item in enumerate(batch_items, batch_start):
                if not item.detail_url:
                    continue

                try:
                    self.logger.debug(f"Scraping detail page {i+1}/{len(items)}: {item.detail_url}")
                    
                    # Navigate to detail page
                    if not self.navigate_to(item.detail_url):
                        item.errors.append("Failed to navigate to detail page")
                        continue
                    
                    # Wait for page to load
                    time.sleep(1)
                    
                    # Extract detail data with multiple strategies
                    detail_data = self._extract_detail_data_smart(detail_rules)
                    
                    if detail_data:
                        item.detail_data = detail_data
                        success_count += 1
                    else:
                        item.errors.append("No detail data extracted")
                        
                except Exception as e:
                    self.logger.error(f"Error scraping detail page {i+1}: {e}")
                    item.errors.append(f"Detail page error: {str(e)}")
            
            # Save progress periodically
            if batch_end % 100 == 0:
                self.logger.info(f"Progress: {batch_end}/{len(items)} detail pages processed")
        
        # Return to original page
        try:
            self.navigate_to(original_url)
        except:
            self.logger.warning("Could not return to original page")
        
        self.logger.info(f"Successfully scraped {success_count}/{len([i for i in items if i.detail_url])} detail pages")

    def _extract_detail_data_smart(self, detail_rules) -> Dict[str, Any]:
        """Smart extraction of detail data with multiple strategies."""
        detail_data = {}
        
        for field_name, selector in detail_rules.fields.items():
            try:
                # Strategy 1: Direct selector
                value = self.extractor.extract_text(selector)
                
                # Strategy 2: If no value, try broader search
                if not value:
                    # Try parent selectors
                    parent_selectors = [
                        selector.rsplit(' > ', 1)[0] if ' > ' in selector else selector,
                        selector.rsplit(' ', 1)[0] if ' ' in selector else selector,
                    ]
                    
                    for parent_sel in parent_selectors:
                        if parent_sel != selector:
                            value = self.extractor.extract_text(parent_sel)
                            if value:
                                break
                
                # Strategy 3: Try common variations
                if not value and ':nth-of-type' in selector:
                    # Remove nth-of-type and try again
                    base_selector = re.sub(r':nth-of-type\(\d+\)', '', selector)
                    values = self.extractor.extract_text(base_selector, multiple=True)
                    if values:
                        # Extract the index from original selector
                        match = re.search(r':nth-of-type\((\d+)\)', selector)
                        if match:
                            idx = int(match.group(1)) - 1
                            if 0 <= idx < len(values):
                                value = values[idx]
                
                # Strategy 4: Text pattern matching
                if not value and field_name.lower() in ['email', 'phone', 'education', 'bar', 'admission', 'creds', 'certs']:
                    value = self._extract_by_pattern(field_name)
                
                if value:
                    detail_data[field_name] = value
                    self.logger.debug(f"Extracted {field_name}: {value[:50]}...")
                else:
                    self.logger.debug(f"No value found for {field_name}")
                    
            except Exception as e:
                self.logger.debug(f"Error extracting {field_name}: {e}")
        
        return detail_data

    def _extract_by_pattern(self, field_type: str) -> Optional[str]:
        """Extract data by pattern matching when selectors fail."""
        try:
            # Get all text from common content areas
            content_selectors = [
                "main", "article", ".content", "#content", 
                ".bio", ".profile", ".details", "[role='main']",
                ".lawyer-bio", ".attorney-bio", ".people-bio"
            ]
            
            full_text = ""
            for sel in content_selectors:
                try:
                    elem = self.driver.find_element(By.CSS_SELECTOR, sel)
                    full_text = elem.text
                    if full_text:
                        break
                except:
                    continue
            
            if not full_text:
                return None
            
            # Pattern matching based on field type
            field_lower = field_type.lower()
            
            if field_lower == 'email':
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                match = re.search(email_pattern, full_text)
                return match.group(0) if match else None
                
            elif field_lower == 'phone':
                phone_pattern = r'(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'
                match = re.search(phone_pattern, full_text)
                return match.group(0) if match else None
                
            elif 'education' in field_lower or 'creds' in field_lower:
                # Look for university names and degrees
                edu_patterns = [
                    r'(?:University|College|School|Institute)[^,\n]*(?:,\s*\d{4})?',
                    r'(?:B\.A\.|B\.S\.|M\.A\.|M\.S\.|Ph\.D\.|J\.D\.|LL\.M\.|M\.B\.A\.)[^,\n]*'
                ]
                for pattern in edu_patterns:
                    matches = re.findall(pattern, full_text, re.IGNORECASE)
                    if matches:
                        # Return based on field name suffix
                        if '1' in field_type:
                            return matches[0] if matches else None
                        elif '2' in field_type:
                            return matches[1] if len(matches) > 1 else None
                        else:
                            return ' | '.join(matches[:2])
                            
            elif 'bar' in field_lower or 'admission' in field_lower or 'cert' in field_lower:
                # Look for bar admissions
                bar_pattern = r'(?:Bar|Admitted to practice|Licensed in|Court)[^,\n]*'
                matches = re.findall(bar_pattern, full_text, re.IGNORECASE)
                if matches:
                    return ' | '.join(matches[:3])  # Return first 3 matches
                    
        except Exception as e:
            self.logger.debug(f"Pattern extraction failed for {field_type}: {e}")
        
        return None

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

    # Enhanced detail page extraction methods for template_scraper.py

    def _extract_detail_data_smart(self, detail_rules) -> Dict[str, Any]:
        """Smart extraction of detail data with multiple strategies and fallbacks."""
        detail_data = {}
        
        # Get all text content for pattern matching fallback
        page_text = self._get_page_text_content()
        
        for field_name, selector in detail_rules.fields.items():
            value = None
            
            # Strategy 1: Try the original selector (after fixing)
            if selector and not selector.endswith('>'):
                value = self._try_selector_extraction(selector, field_name)
            
            # Strategy 2: Try common selectors for this field type
            if not value:
                value = self._try_common_selectors(field_name)
            
            # Strategy 3: Pattern matching in page text
            if not value:
                value = self._extract_by_pattern_enhanced(field_name, page_text)
            
            # Strategy 4: Try fallback selectors if defined
            if not value and hasattr(detail_rules, 'fallback_selectors'):
                fallback_list = detail_rules.fallback_selectors.get(
                    self._get_field_category(field_name), []
                )
                for fallback_sel in fallback_list:
                    value = self._try_selector_extraction(fallback_sel, field_name)
                    if value:
                        break
            
            if value:
                detail_data[field_name] = value
                self.logger.debug(f"✅ Extracted {field_name}: {value[:50]}...")
            else:
                self.logger.debug(f"❌ Could not extract {field_name}")
        
        return detail_data


    def _try_selector_extraction(self, selector: str, field_name: str) -> Optional[str]:
        """Try to extract using a selector with error handling."""
        try:
            # Clean selector first
            selector = selector.strip().rstrip('>')
            
            # For numbered fields (Education1, Education2), extract the number
            match = re.search(r'(\d+)$', field_name)
            if match:
                number = int(match.group(1))
                base_field = field_name[:-len(match.group(1))]
                
                # Try to get multiple elements and pick the nth one
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if len(elements) >= number:
                    return elements[number-1].text.strip()
            else:
                # Standard extraction
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                return element.text.strip()
        except Exception as e:
            self.logger.debug(f"Selector failed for {field_name}: {selector} - {e}")
            return None


    def _try_common_selectors(self, field_name: str) -> Optional[str]:
        """Try common selector patterns based on field name."""
        common_selectors = {
            'name': ['.lawyer-name', '.attorney-name', 'h1.name', '.profile-name'],
            'email': ['a[href^="mailto:"]', '.email a', '.contact-email a'],
            'phone': ['a[href^="tel:"]', '.phone', '.telephone', '.contact-phone'],
            'education': ['.education li', '.bio-education li', '.credentials li'],
            'bar': ['.bar-admissions', '.admissions', '.credentials'],
            'bio': ['.bio-content', '.biography', '.overview', '.bio-text'],
            'practice': ['.practice-areas', '.practices', '.expertise'],
            'office': ['.office', '.location', '.office-location']
        }
        
        # Determine field category
        field_lower = field_name.lower()
        for category, selectors in common_selectors.items():
            if category in field_lower:
                for selector in selectors:
                    try:
                        if 'education' in category and field_name[-1].isdigit():
                            # Handle numbered education fields
                            index = int(field_name[-1]) - 1
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            if len(elements) > index:
                                return elements[index].text.strip()
                        else:
                            element = self.driver.find_element(By.CSS_SELECTOR, selector)
                            return element.text.strip()
                    except:
                        continue
        
        return None


    def _get_page_text_content(self) -> str:
        """Get all text content from main content areas."""
        content_selectors = [
            'main', 'article', '.content', '#content', 
            '.main-content', '.page-content', '[role="main"]',
            '.lawyer-detail', '.attorney-detail', '.profile-detail'
        ]
        
        for selector in content_selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                return element.text
            except:
                continue
        
        # Fallback to body
        try:
            return self.driver.find_element(By.TAG_NAME, 'body').text
        except:
            return ""


    def _extract_by_pattern_enhanced(self, field_name: str, page_text: str) -> Optional[str]:
        """Enhanced pattern matching with better education and credentials extraction."""
        field_lower = field_name.lower()
        
        # Email pattern
        if 'email' in field_lower:
            pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            match = re.search(pattern, page_text)
            return match.group(0) if match else None
        
        # Phone pattern (more flexible)
        elif 'phone' in field_lower:
            patterns = [
                r'(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',
                r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
                r'(?:Tel|Phone|T|P):\s*([\d\s\-\.\(\)]+)'
            ]
            for pattern in patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    return match.group(0).strip()
        
        # Education extraction (improved)
        elif 'education' in field_lower:
            # Look for education section
            edu_section_pattern = r'(?:Education|Academic Background|Credentials)[:\s]*\n((?:.*\n){0,10})'
            section_match = re.search(edu_section_pattern, page_text, re.IGNORECASE)
            
            if section_match:
                edu_text = section_match.group(1)
            else:
                edu_text = page_text
            
            # Extract degree patterns
            degree_patterns = [
                r'((?:J\.D\.|JD|LL\.M\.|LLM|B\.A\.|BA|B\.S\.|BS|M\.A\.|MA|M\.S\.|MS|Ph\.D\.|PhD|M\.B\.A\.|MBA)[^,\n]*(?:,\s*\d{4})?)',
                r'([A-Z][a-z]+ (?:University|College|School|Institute)[^,\n]*(?:,\s*\d{4})?)',
                r'((?:Bachelor|Master|Doctor|Juris Doctor)[^,\n]*(?:,\s*\d{4})?)'
            ]
            
            all_matches = []
            for pattern in degree_patterns:
                matches = re.findall(pattern, edu_text, re.IGNORECASE)
                all_matches.extend(matches)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_matches = []
            for match in all_matches:
                if match not in seen:
                    seen.add(match)
                    unique_matches.append(match)
            
            # Return based on field number
            if field_name.endswith('1') and unique_matches:
                return unique_matches[0]
            elif field_name.endswith('2') and len(unique_matches) > 1:
                return unique_matches[1]
            elif unique_matches:
                return ' | '.join(unique_matches[:2])
        
        # Bar admissions / Credentials
        elif 'bar' in field_lower or 'cred' in field_lower or 'admission' in field_lower:
            # Look for bar admission section
            bar_patterns = [
                r'(?:Bar Admissions?|Admitted to (?:Practice|Bar)|Licensed)[:\s]*\n((?:.*\n){0,5})',
                r'((?:New York|California|Texas|Florida|Illinois)[^,\n]*(?:Bar|Court)[^,\n]*)',
                r'((?:U\.S\.|United States)[^,\n]*Court[^,\n]*)'
            ]
            
            admissions = []
            for pattern in bar_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                admissions.extend(matches)
            
            if admissions:
                # Clean and deduplicate
                cleaned = [a.strip() for a in admissions if len(a.strip()) > 5]
                return ' | '.join(cleaned[:5])  # Limit to 5 entries
        
        # Bio/Overview
        elif 'bio' in field_lower or 'overview' in field_lower:
            # Look for bio section
            bio_patterns = [
                r'(?:Biography|Overview|About)[:\s]*\n((?:.*\n){1,5})',
                r'^([A-Z][^.!?]*(?:[.!?]\s+[A-Z][^.!?]*){2,5})'  # First few sentences
            ]
            
            for pattern in bio_patterns:
                match = re.search(pattern, page_text, re.MULTILINE)
                if match:
                    bio_text = match.group(1).strip()
                    # Clean up and limit length
                    bio_text = re.sub(r'\s+', ' ', bio_text)
                    return bio_text[:500] + '...' if len(bio_text) > 500 else bio_text
        
        return None


    def _get_field_category(self, field_name: str) -> str:
        """Determine the category of a field for fallback selectors."""
        field_lower = field_name.lower()
        
        if any(term in field_lower for term in ['education', 'school', 'degree']):
            return 'education'
        elif any(term in field_lower for term in ['bar', 'admission', 'license', 'cred']):
            return 'bar_admissions'
        elif 'email' in field_lower:
            return 'email'
        elif 'phone' in field_lower or 'tel' in field_lower:
            return 'phone'
        elif 'bio' in field_lower or 'overview' in field_lower:
            return 'bio'
        
        return 'general'