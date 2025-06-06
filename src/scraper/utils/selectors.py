# src/scraper/utils/selectors.py
"""
CSS selector manipulation and generation utilities.
"""

import re
from typing import Optional, List, Tuple


def normalize_selector(selector: str) -> str:
    """
    Normalize Unicode characters and clean up CSS selector.
    
    Args:
        selector: Raw CSS selector
        
    Returns:
        Normalized selector
    """
    if not selector:
        return selector
    
    # Unicode dash replacements
    replacements = {
        '\u2010': '-',  # Hyphen
        '\u2011': '-',  # Non-breaking hyphen
        '\u2012': '-',  # Figure dash
        '\u2013': '-',  # En dash
        '\u2014': '-',  # Em dash
        '\u2015': '-',  # Horizontal bar
        '\u2212': '-',  # Minus sign
    }
    
    for old, new in replacements.items():
        selector = selector.replace(old, new)
    
    # Remove extra whitespace
    selector = ' '.join(selector.split())
    
    return selector


def generalize_selector(selector: str) -> str:
    """
    Remove specific indices and nth-of-type from selector to make it more general.
    
    Args:
        selector: CSS selector
        
    Returns:
        Generalized selector
    """
    if not selector:
        return selector
    
    selector = normalize_selector(selector)
    
    # Remove :nth-of-type(...) patterns
    selector = re.sub(r':nth-of-type\(\s*\d+\s*\)', '', selector)
    
    # Remove :nth-child(...) patterns
    selector = re.sub(r':nth-child\(\s*\d+\s*\)', '', selector)
    
    # Remove numeric indices in brackets
    selector = re.sub(r'\[\s*\d+\s*\]', '', selector)
    
    # Remove :first-child, :last-child, etc.
    selector = re.sub(r':(first|last|only)-child', '', selector)
    selector = re.sub(r':(first|last|only)-of-type', '', selector)
    
    # Collapse multiple spaces
    return ' '.join(selector.split())


def make_relative_selector(absolute_selector: str, container_selector: str) -> str:
    """
    Convert absolute selector to relative selector within container.
    
    Args:
        absolute_selector: Full CSS selector from document root
        container_selector: Container CSS selector
        
    Returns:
        Relative selector within container
    """
    abs_sel = normalize_selector(absolute_selector)
    cont_sel = generalize_selector(container_selector)
    
    # Split selectors by child combinator
    abs_parts = [part.strip() for part in abs_sel.split('>')]
    cont_parts = [part.strip() for part in cont_sel.split('>')]
    
    # Find where container ends in absolute selector
    for i in range(len(abs_parts)):
        # Build partial selector up to current position
        partial = ' > '.join(abs_parts[:i+1])
        partial_generalized = generalize_selector(partial)
        
        if partial_generalized == cont_sel:
            # Found container endpoint, return remaining parts
            if i + 1 < len(abs_parts):
                return ' > '.join(abs_parts[i+1:])
            else:
                return ""
    
    # If container not found in path, try descendant selector
    # Remove container prefix if absolute selector starts with it
    if abs_sel.startswith(cont_sel):
        relative = abs_sel[len(cont_sel):].strip()
        # Remove leading > if present
        if relative.startswith('>'):
            relative = relative[1:].strip()
        return relative
    
    # Fallback: return original selector
    return abs_sel


def split_selector(selector: str) -> List[str]:
    """
    Split compound selector into individual parts.
    
    Args:
        selector: CSS selector
        
    Returns:
        List of selector parts
    """
    # Handle different combinators
    parts = []
    current = ""
    in_brackets = False
    
    for char in selector:
        if char == '[':
            in_brackets = True
            current += char
        elif char == ']':
            in_brackets = False
            current += char
        elif char in ' >+~' and not in_brackets:
            if current:
                parts.append(current)
            if char != ' ':
                parts.append(char)
            current = ""
        else:
            current += char
    
    if current:
        parts.append(current)
    
    return [p for p in parts if p.strip()]


def validate_selector(driver, selector: str) -> Tuple[bool, int]:
    """
    Validate CSS selector and return match count.
    
    Args:
        driver: Selenium WebDriver
        selector: CSS selector to validate
        
    Returns:
        Tuple of (is_valid, match_count)
    """
    try:
        from selenium.webdriver.common.by import By
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
        return True, len(elements)
    except Exception:
        return False, 0


def generate_unique_selector(element, driver) -> Optional[str]:
    """
    Generate unique CSS selector for element.
    
    Args:
        element: WebElement
        driver: Selenium WebDriver
        
    Returns:
        Unique CSS selector or None
    """
    try:
        # Try ID first
        elem_id = element.get_attribute('id')
        if elem_id:
            selector = f"#{elem_id}"
            valid, count = validate_selector(driver, selector)
            if valid and count == 1:
                return selector
        
        # Try unique class combination
        classes = element.get_attribute('class')
        if classes:
            class_list = classes.strip().split()
            tag = element.tag_name
            
            # Try each individual class
            for cls in class_list:
                selector = f"{tag}.{cls}"
                valid, count = validate_selector(driver, selector)
                if valid and count == 1:
                    return selector
            
            # Try combination of all classes
            if class_list:
                selector = f"{tag}.{'.'.join(class_list)}"
                valid, count = validate_selector(driver, selector)
                if valid and count == 1:
                    return selector
        
        # Try attributes
        for attr in ['name', 'data-id', 'data-testid', 'aria-label']:
            attr_value = element.get_attribute(attr)
            if attr_value:
                selector = f"{element.tag_name}[{attr}='{attr_value}']"
                valid, count = validate_selector(driver, selector)
                if valid and count == 1:
                    return selector
        
        # Build path selector
        path_parts = []
        current = element
        
        while current:
            tag = current.tag_name
            if tag == 'html':
                break
            
            # Get element position among siblings
            parent = current.find_element_by_xpath('..')
            siblings = parent.find_elements_by_tag_name(tag)
            
            if len(siblings) > 1:
                index = siblings.index(current) + 1
                path_parts.insert(0, f"{tag}:nth-of-type({index})")
            else:
                path_parts.insert(0, tag)
            
            current = parent if parent.tag_name != 'html' else None
        
        return ' > '.join(path_parts)
        
    except Exception:
        return None


def css_to_xpath(css_selector: str) -> str:
    """
    Convert CSS selector to XPath (basic conversion).
    
    Args:
        css_selector: CSS selector
        
    Returns:
        XPath expression
    """
    # This is a basic implementation
    # For complex selectors, consider using a proper CSS to XPath library
    
    xpath = css_selector
    
    # Convert ID selector
    xpath = re.sub(r'#([a-zA-Z][\w-]*)', r'[@id="\1"]', xpath)
    
    # Convert class selector
    xpath = re.sub(r'\.([a-zA-Z][\w-]*)', r'[contains(@class, "\1")]', xpath)
    
    # Convert attribute selectors
    xpath = re.sub(r'\[([a-zA-Z][\w-]*)\]', r'[@\1]', xpath)
    xpath = re.sub(r'\[([a-zA-Z][\w-]*)="([^"]+)"\]', r'[@\1="\2"]', xpath)
    xpath = re.sub(r'\[([a-zA-Z][\w-]*)=\'([^\']+)\'\]', r'[@\1="\2"]', xpath)
    
    # Convert descendant combinator
    xpath = xpath.replace(' ', '//')
    
    # Convert child combinator
    xpath = xpath.replace('>', '/')
    
    # Add // prefix if not present
    if not xpath.startswith('//'):
        xpath = '//' + xpath
    
    return xpath


def find_common_ancestor_selector(selectors: List[str]) -> Optional[str]:
    """
    Find common ancestor selector from list of selectors.
    
    Args:
        selectors: List of CSS selectors
        
    Returns:
        Common ancestor selector or None
    """
    if not selectors:
        return None
    
    if len(selectors) == 1:
        return selectors[0]
    
    # Split all selectors into parts
    all_parts = [split_selector(sel) for sel in selectors]
    
    # Find common prefix
    common_parts = []
    
    for i in range(min(len(parts) for parts in all_parts)):
        current_parts = [parts[i] for parts in all_parts]
        
        # Check if all parts at this position are the same
        if all(part == current_parts[0] for part in current_parts):
            common_parts.append(current_parts[0])
        else:
            break
    
    if common_parts:
        return ' '.join(common_parts)
    
    return None