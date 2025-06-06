# src/scraper/extractors/element_extractor.py
"""
Element extraction functionality for various HTML elements.
"""

import logging
from typing import Dict, List, Optional, Any, Union
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

from ..utils.selectors import normalize_selector


class ElementExtractor:
    """Extract data from various HTML elements"""
    
    def __init__(self, driver):
        """
        Initialize extractor with driver reference.
        
        Args:
            driver: Selenium WebDriver instance
        """
        self.driver = driver
        self.logger = logging.getLogger(f'{__name__}.ElementExtractor')
    
    def extract_text(self, selector: str, parent: Optional[Any] = None,
                    multiple: bool = False) -> Optional[Union[str, List[str]]]:
        """
        Extract text from element(s).
        
        Args:
            selector: CSS selector
            parent: Parent element to search within
            multiple: Whether to extract from multiple elements
            
        Returns:
            Text content or None
        """
        try:
            selector = normalize_selector(selector)
            search_context = parent or self.driver
            
            if multiple:
                elements = search_context.find_elements(By.CSS_SELECTOR, selector)
                return [elem.text.strip() for elem in elements if elem.text.strip()]
            else:
                element = search_context.find_element(By.CSS_SELECTOR, selector)
                return element.text.strip() if element.text else None
                
        except NoSuchElementException:
            self.logger.debug(f"Element not found: {selector}")
            return [] if multiple else None
        except Exception as e:
            self.logger.warning(f"Error extracting text from {selector}: {e}")
            return [] if multiple else None
    
    def extract_attribute(self, selector: str, attribute: str, 
                         parent: Optional[Any] = None,
                         multiple: bool = False) -> Optional[Union[str, List[str]]]:
        """
        Extract attribute value(s) from element(s).
        
        Args:
            selector: CSS selector
            attribute: Attribute name to extract
            parent: Parent element to search within
            multiple: Whether to extract from multiple elements
            
        Returns:
            Attribute value(s) or None
        """
        try:
            selector = normalize_selector(selector)
            search_context = parent or self.driver
            
            if multiple:
                elements = search_context.find_elements(By.CSS_SELECTOR, selector)
                return [elem.get_attribute(attribute) for elem in elements 
                       if elem.get_attribute(attribute)]
            else:
                element = search_context.find_element(By.CSS_SELECTOR, selector)
                return element.get_attribute(attribute)
                
        except NoSuchElementException:
            self.logger.debug(f"Element not found: {selector}")
            return [] if multiple else None
        except Exception as e:
            self.logger.warning(f"Error extracting attribute from {selector}: {e}")
            return [] if multiple else None
    
    def extract_link(self, selector: str, parent: Optional[Any] = None,
                    absolute: bool = True) -> Optional[Dict[str, str]]:
        """
        Extract link information.
        
        Args:
            selector: CSS selector
            parent: Parent element to search within
            absolute: Whether to return absolute URLs
            
        Returns:
            Dictionary with href, text, and title
        """
        try:
            selector = normalize_selector(selector)
            search_context = parent or self.driver
            element = search_context.find_element(By.CSS_SELECTOR, selector)
            
            href = element.get_attribute("href")
            if absolute and href and not href.startswith(('http://', 'https://', 'mailto:', 'tel:')):
                # Convert relative URLs to absolute
                from urllib.parse import urljoin
                base_url = self.driver.current_url
                href = urljoin(base_url, href)
            
            return {
                "href": href,
                "text": element.text.strip(),
                "title": element.get_attribute("title") or ""
            }
            
        except NoSuchElementException:
            self.logger.debug(f"Link not found: {selector}")
            return None
        except Exception as e:
            self.logger.warning(f"Error extracting link from {selector}: {e}")
            return None
    
    def extract_links(self, container_selector: str, 
                     link_selector: str = "a[href]") -> List[Dict[str, str]]:
        """
        Extract all links within a container.
        
        Args:
            container_selector: Container CSS selector
            link_selector: Link CSS selector within container
            
        Returns:
            List of link dictionaries
        """
        try:
            container = self.driver.find_element(By.CSS_SELECTOR, container_selector)
            links = container.find_elements(By.CSS_SELECTOR, link_selector)
            
            result = []
            for link in links:
                try:
                    href = link.get_attribute("href")
                    if href:
                        result.append({
                            "href": href,
                            "text": link.text.strip(),
                            "title": link.get_attribute("title") or ""
                        })
                except StaleElementReferenceException:
                    continue
                    
            return result
            
        except NoSuchElementException:
            self.logger.debug(f"Container not found: {container_selector}")
            return []
        except Exception as e:
            self.logger.warning(f"Error extracting links: {e}")
            return []
    
    def extract_image(self, selector: str, parent: Optional[Any] = None) -> Optional[Dict[str, str]]:
        """
        Extract image information.
        
        Args:
            selector: CSS selector
            parent: Parent element to search within
            
        Returns:
            Dictionary with src, alt, and title
        """
        try:
            selector = normalize_selector(selector)
            search_context = parent or self.driver
            element = search_context.find_element(By.CSS_SELECTOR, selector)
            
            return {
                "src": element.get_attribute("src"),
                "alt": element.get_attribute("alt") or "",
                "title": element.get_attribute("title") or "",
                "width": element.get_attribute("width") or "",
                "height": element.get_attribute("height") or ""
            }
            
        except NoSuchElementException:
            self.logger.debug(f"Image not found: {selector}")
            return None
        except Exception as e:
            self.logger.warning(f"Error extracting image from {selector}: {e}")
            return None
    
    def extract_images(self, container_selector: str) -> List[Dict[str, str]]:
        """
        Extract all images within a container.
        
        Args:
            container_selector: Container CSS selector
            
        Returns:
            List of image dictionaries
        """
        try:
            container = self.driver.find_element(By.CSS_SELECTOR, container_selector)
            images = container.find_elements(By.CSS_SELECTOR, "img")
            
            result = []
            for img in images:
                try:
                    src = img.get_attribute("src")
                    if src:
                        result.append({
                            "src": src,
                            "alt": img.get_attribute("alt") or "",
                            "title": img.get_attribute("title") or "",
                            "width": img.get_attribute("width") or "",
                            "height": img.get_attribute("height") or ""
                        })
                except StaleElementReferenceException:
                    continue
                    
            return result
            
        except NoSuchElementException:
            self.logger.debug(f"Container not found: {container_selector}")
            return []
        except Exception as e:
            self.logger.warning(f"Error extracting images: {e}")
            return []
    
    def extract_list(self, selector: str, item_selector: str = "li") -> Optional[List[str]]:
        """
        Extract list items as array of strings.
        
        Args:
            selector: List container CSS selector
            item_selector: Item CSS selector within list
            
        Returns:
            List of item texts
        """
        try:
            list_element = self.driver.find_element(By.CSS_SELECTOR, selector)
            items = list_element.find_elements(By.CSS_SELECTOR, item_selector)
            return [item.text.strip() for item in items if item.text.strip()]
            
        except NoSuchElementException:
            self.logger.debug(f"List not found: {selector}")
            return None
        except Exception as e:
            self.logger.warning(f"Error extracting list from {selector}: {e}")
            return None
    
    def extract_by_xpath(self, xpath: str, parent: Optional[Any] = None,
                        multiple: bool = False) -> Optional[Union[str, List[str]]]:
        """
        Extract text using XPath.
        
        Args:
            xpath: XPath expression
            parent: Parent element to search within
            multiple: Whether to extract from multiple elements
            
        Returns:
            Text content or None
        """
        try:
            search_context = parent or self.driver
            
            if multiple:
                elements = search_context.find_elements(By.XPATH, xpath)
                return [elem.text.strip() for elem in elements if elem.text.strip()]
            else:
                element = search_context.find_element(By.XPATH, xpath)
                return element.text.strip() if element.text else None
                
        except NoSuchElementException:
            self.logger.debug(f"Element not found by XPath: {xpath}")
            return [] if multiple else None
        except Exception as e:
            self.logger.warning(f"Error extracting by XPath {xpath}: {e}")
            return [] if multiple else None
    
    def extract_form_values(self, form_selector: str) -> Dict[str, Any]:
        """
        Extract all form field values.
        
        Args:
            form_selector: Form CSS selector
            
        Returns:
            Dictionary of field names and values
        """
        try:
            form = self.driver.find_element(By.CSS_SELECTOR, form_selector)
            values = {}
            
            # Input fields
            inputs = form.find_elements(By.CSS_SELECTOR, "input[name]")
            for inp in inputs:
                name = inp.get_attribute("name")
                inp_type = inp.get_attribute("type") or "text"
                
                if inp_type in ["text", "email", "tel", "number", "url", "search"]:
                    values[name] = inp.get_attribute("value") or ""
                elif inp_type == "checkbox":
                    values[name] = inp.is_selected()
                elif inp_type == "radio":
                    if inp.is_selected():
                        values[name] = inp.get_attribute("value")
            
            # Select fields
            selects = form.find_elements(By.CSS_SELECTOR, "select[name]")
            for select in selects:
                name = select.get_attribute("name")
                selected_option = select.find_element(By.CSS_SELECTOR, "option:checked")
                values[name] = selected_option.get_attribute("value") if selected_option else ""
            
            # Textarea fields
            textareas = form.find_elements(By.CSS_SELECTOR, "textarea[name]")
            for textarea in textareas:
                name = textarea.get_attribute("name")
                values[name] = textarea.get_attribute("value") or ""
            
            return values
            
        except NoSuchElementException:
            self.logger.debug(f"Form not found: {form_selector}")
            return {}
        except Exception as e:
            self.logger.warning(f"Error extracting form values: {e}")
            return {}
    
    def extract_structured_data(self, selector: str, 
                               field_map: Dict[str, str]) -> Dict[str, Any]:
        """
        Extract structured data using field mapping.
        
        Args:
            selector: Container CSS selector
            field_map: Dictionary mapping field names to selectors
            
        Returns:
            Dictionary of extracted data
        """
        try:
            container = self.driver.find_element(By.CSS_SELECTOR, selector)
            data = {}
            
            for field_name, field_selector in field_map.items():
                try:
                    # Try to extract text first
                    value = self.extract_text(field_selector, parent=container)
                    
                    # If no text, try to get href attribute for links
                    if not value and field_selector.endswith("a"):
                        link_data = self.extract_link(field_selector, parent=container)
                        value = link_data.get("href") if link_data else None
                    
                    data[field_name] = value
                    
                except Exception as e:
                    self.logger.debug(f"Failed to extract {field_name}: {e}")
                    data[field_name] = None
            
            return data
            
        except NoSuchElementException:
            self.logger.debug(f"Container not found: {selector}")
            return {}
        except Exception as e:
            self.logger.warning(f"Error extracting structured data: {e}")
            return {}