# src/scraper/extractors/enhanced_element_extractor.py
"""
Enhanced element extractor that integrates pattern-based extraction,
advanced selectors, and fallback strategies.
"""

import logging
from typing import Dict, List, Optional, Any, Union
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

from .element_extractor import ElementExtractor
from .pattern_extractor import PatternExtractor
from .advanced_selectors import AdvancedSelectors, FallbackSelector
from ..utils.selectors import normalize_selector


class EnhancedElementExtractor(ElementExtractor):
    """Enhanced extractor with pattern matching and advanced selection strategies"""
    
    def __init__(self, driver):
        """Initialize enhanced extractor with all components"""
        super().__init__(driver)
        self.pattern_extractor = PatternExtractor()
        self.advanced_selectors = AdvancedSelectors(driver)
        self.fallback_selector = FallbackSelector(driver)
        self.logger = logging.getLogger(f'{__name__}.EnhancedElementExtractor')
    
    def extract_smart(self, field_name: str, selector: str = None, 
                     pattern_type: str = None, fallback_strategies: List[Dict] = None,
                     parent: Optional[WebElement] = None) -> Optional[Any]:
        """
        Smart extraction using multiple strategies
        
        Args:
            field_name: Name of field being extracted
            selector: CSS selector (optional)
            pattern_type: Pattern type for extraction (email, phone, etc.)
            fallback_strategies: List of fallback strategies
            parent: Parent element to search within
            
        Returns:
            Extracted value or None
        """
        value = None
        
        # Try CSS selector first
        if selector:
            value = self.extract_text(selector, parent)
        
        # Try pattern extraction if no value found
        if not value and pattern_type:
            # Get broader context for pattern matching
            context_element = parent or self.driver.find_element(By.TAG_NAME, "body")
            context_text = context_element.text
            
            # Use field name as context
            value = self.pattern_extractor.extract(
                context_text,
                pattern_type,
                context=field_name
            )
        
        # Try fallback strategies
        if not value and fallback_strategies:
            for strategy in fallback_strategies:
                element = self.fallback_selector.find_with_fallbacks(
                    selector or "",
                    [strategy]
                )
                if element:
                    value = element.text.strip()
                    if value:
                        break
        
        return value
    
    def extract_with_patterns(self, selectors: Dict[str, str], 
                            patterns: Dict[str, str] = None,
                            parent: Optional[WebElement] = None) -> Dict[str, Any]:
        """
        Extract multiple fields using selectors with pattern fallback
        
        Args:
            selectors: Dict of field_name -> selector
            patterns: Dict of field_name -> pattern_type
            parent: Parent element
            
        Returns:
            Dict of extracted values
        """
        results = {}
        patterns = patterns or {}
        
        for field_name, selector in selectors.items():
            # Determine pattern type
            pattern_type = patterns.get(field_name)
            if not pattern_type:
                # Auto-detect pattern type from field name
                pattern_type = self._guess_pattern_type(field_name)
            
            # Extract with smart strategy
            value = self.extract_smart(
                field_name,
                selector,
                pattern_type,
                parent=parent
            )
            
            if value:
                results[field_name] = value
        
        return results
    
    def extract_structured_data_enhanced(self, container_selector: str,
                                       field_map: Dict[str, str],
                                       use_patterns: bool = True,
                                       use_proximity: bool = True) -> Dict[str, Any]:
        """
        Enhanced structured data extraction with multiple strategies
        
        Args:
            container_selector: Container CSS selector
            field_map: Field name to selector mapping
            use_patterns: Enable pattern-based extraction
            use_proximity: Enable proximity-based extraction
            
        Returns:
            Extracted data dictionary
        """
        try:
            container = self.driver.find_element(By.CSS_SELECTOR, container_selector)
        except NoSuchElementException:
            self.logger.debug(f"Container not found: {container_selector}")
            return {}
        
        data = {}
        
        # First pass: Try direct selectors
        for field_name, selector in field_map.items():
            try:
                value = self.extract_text(selector, parent=container)
                if value:
                    data[field_name] = value
            except Exception as e:
                self.logger.debug(f"Failed to extract {field_name} with selector: {e}")
        
        # Second pass: Use patterns for missing fields
        if use_patterns:
            container_text = container.text
            pattern_types = {
                'email': ['email', 'contact', 'mail'],
                'phone': ['phone', 'tel', 'mobile', 'call'],
                'address': ['address', 'location', 'office'],
                'date': ['date', 'time', 'when', 'posted'],
                'price': ['price', 'cost', 'fee', 'rate']
            }
            
            for field_name in field_map:
                if field_name not in data:
                    # Guess pattern type
                    field_lower = field_name.lower()
                    for pattern_type, keywords in pattern_types.items():
                        if any(keyword in field_lower for keyword in keywords):
                            value = self.pattern_extractor.extract(
                                container_text,
                                pattern_type,
                                context=field_name
                            )
                            if value:
                                data[field_name] = value
                                break
        
        # Third pass: Use proximity for remaining fields
        if use_proximity:
            # Find labels and their associated values
            labels = container.find_elements(By.CSS_SELECTOR, "label, dt, th, .label, .field-label")
            
            for field_name in field_map:
                if field_name not in data:
                    # Look for label matching field name
                    for label in labels:
                        label_text = label.text.strip().lower()
                        if self._matches_field_name(field_name, label_text):
                            # Find nearby value
                            nearby_elements = self.advanced_selectors.find_by_proximity(
                                label,
                                target_tag="*",
                                max_distance=200,
                                direction="right"
                            )
                            
                            for element in nearby_elements:
                                value = element.text.strip()
                                if value and value != label_text:
                                    data[field_name] = value
                                    break
        
        return data
    
    def extract_table_smart(self, table_selector: str, 
                          column_patterns: Dict[str, str] = None) -> List[Dict[str, Any]]:
        """
        Extract table with pattern recognition for data cleaning
        
        Args:
            table_selector: Table CSS selector
            column_patterns: Column name to pattern type mapping
            
        Returns:
            List of row dictionaries
        """
        try:
            # Use parent's table extraction
            rows = super().extract_table(table_selector)
            if not rows or not column_patterns:
                return rows
            
            # Apply pattern extraction to specified columns
            cleaned_rows = []
            for row in rows:
                cleaned_row = row.copy()
                
                for column, pattern_type in column_patterns.items():
                    if column in row and row[column]:
                        # Extract pattern from cell value
                        extracted = self.pattern_extractor.extract(
                            str(row[column]),
                            pattern_type
                        )
                        if extracted:
                            cleaned_row[column] = extracted
                
                cleaned_rows.append(cleaned_row)
            
            return cleaned_rows
            
        except Exception as e:
            self.logger.error(f"Error in smart table extraction: {e}")
            return []
    
    def find_and_extract_by_label(self, label_text: str, 
                                value_selector: str = None,
                                max_distance: int = 300) -> Optional[str]:
        """
        Find a label and extract its associated value
        
        Args:
            label_text: Text of the label to find
            value_selector: Optional selector for value element
            max_distance: Maximum distance to look for value
            
        Returns:
            Extracted value or None
        """
        # Find label element
        label_elements = self.advanced_selectors.find_by_text_content(
            label_text,
            fuzzy=True,
            min_similarity=0.8
        )
        
        if not label_elements:
            return None
        
        label = label_elements[0]
        
        # If value selector provided, use it
        if value_selector:
            try:
                # Look for value element near label
                parent = label.find_element(By.XPATH, "..")
                value_element = parent.find_element(By.CSS_SELECTOR, value_selector)
                return value_element.text.strip()
            except:
                pass
        
        # Otherwise, use proximity search
        nearby_elements = self.advanced_selectors.find_by_proximity(
            label,
            max_distance=max_distance
        )
        
        # Find the most likely value element
        for element in nearby_elements:
            text = element.text.strip()
            # Skip if it's another label or empty
            if text and text.lower() != label_text.lower():
                # Check if it looks like a value (not another label)
                if not text.endswith(':') and len(text) < 200:
                    return text
        
        return None
    
    # Helper methods
    def _guess_pattern_type(self, field_name: str) -> Optional[str]:
        """Guess pattern type from field name"""
        field_lower = field_name.lower()
        
        patterns = {
            'email': ['email', 'mail', 'contact'],
            'phone': ['phone', 'tel', 'mobile', 'cell'],
            'date': ['date', 'posted', 'updated', 'created'],
            'price': ['price', 'cost', 'fee', 'amount'],
            'address': ['address', 'location', 'street'],
            'zip_code': ['zip', 'postal'],
            'education': ['education', 'degree', 'university', 'college'],
            'bar_admission': ['bar', 'admission', 'license']
        }
        
        for pattern_type, keywords in patterns.items():
            if any(keyword in field_lower for keyword in keywords):
                return pattern_type
        
        return None
    
    def _matches_field_name(self, field_name: str, label_text: str) -> bool:
        """Check if label text matches field name"""
        field_words = field_name.lower().replace('_', ' ').split()
        label_words = label_text.lower().split()
        
        # Check for any matching words
        return any(word in label_words for word in field_words)