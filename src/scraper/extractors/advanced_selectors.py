# src/scraper/extractors/advanced_selectors.py
"""
Advanced selector strategies including text-based, proximity-based, and AI-powered selection.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.remote.webdriver import WebDriver

try:
    import numpy as np
    from sentence_transformers import SentenceTransformer
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False


@dataclass
class ProximityContext:
    """Context for proximity-based selection"""
    reference_element: WebElement
    max_distance: int = 500  # pixels
    preferred_direction: Optional[str] = None  # 'above', 'below', 'left', 'right'
    same_container: bool = True


@dataclass
class TextMatchContext:
    """Context for text-based matching"""
    target_text: str
    fuzzy_match: bool = True
    min_similarity: float = 0.8
    case_sensitive: bool = False
    partial_match: bool = True


class AdvancedSelectors:
    """Advanced selection strategies for robust element finding"""
    
    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.logger = logging.getLogger(f'{__name__}.AdvancedSelectors')
        
        # Initialize AI model if available
        self.ai_model = None
        self.ai_available = AI_AVAILABLE
        if self.ai_available:
            try:
                self.ai_model = SentenceTransformer('all-MiniLM-L6-v2')
                self.logger.info("AI model loaded for semantic matching")
            except Exception as e:
                self.logger.warning(f"Failed to load AI model: {e}")
                self.ai_available = False
    
    def find_by_text_content(self, text: str, tag: str = "*", 
                           fuzzy: bool = True, min_similarity: float = 0.8) -> List[WebElement]:
        """
        Find elements by text content with fuzzy matching support
        
        Args:
            text: Text to search for
            tag: HTML tag to filter by
            fuzzy: Enable fuzzy matching
            min_similarity: Minimum similarity score for fuzzy matching
            
        Returns:
            List of matching elements
        """
        # Normalize search text
        search_text = text.strip().lower()
        
        # Use XPath for exact matching
        if not fuzzy:
            xpath = f"//{tag}[normalize-space(text())='{text}']"
            return self.driver.find_elements(By.XPATH, xpath)
        
        # Get all elements with text
        all_elements = self.driver.find_elements(By.XPATH, f"//{tag}[text()]")
        matches = []
        
        for element in all_elements:
            try:
                element_text = element.text.strip().lower()
                if not element_text:
                    continue
                
                # Calculate similarity
                similarity = self._calculate_text_similarity(search_text, element_text)
                
                if similarity >= min_similarity:
                    matches.append((element, similarity))
            except Exception as e:
                self.logger.debug(f"Error processing element: {e}")
                continue
        
        # Sort by similarity and return elements
        matches.sort(key=lambda x: x[1], reverse=True)
        return [match[0] for match in matches]
    
    def find_by_proximity(self, reference: WebElement, target_tag: str = "*",
                         max_distance: int = 300, direction: Optional[str] = None) -> List[WebElement]:
        """
        Find elements near a reference element
        
        Args:
            reference: Reference element
            target_tag: Tag of elements to find
            max_distance: Maximum distance in pixels
            direction: Preferred direction ('above', 'below', 'left', 'right')
            
        Returns:
            List of nearby elements sorted by distance
        """
        # Get reference position
        ref_location = reference.location
        ref_size = reference.size
        ref_center = {
            'x': ref_location['x'] + ref_size['width'] / 2,
            'y': ref_location['y'] + ref_size['height'] / 2
        }
        
        # Find all potential targets
        candidates = self.driver.find_elements(By.CSS_SELECTOR, target_tag)
        proximity_matches = []
        
        for candidate in candidates:
            if candidate == reference:
                continue
            
            try:
                # Get candidate position
                cand_location = candidate.location
                cand_size = candidate.size
                cand_center = {
                    'x': cand_location['x'] + cand_size['width'] / 2,
                    'y': cand_location['y'] + cand_size['height'] / 2
                }
                
                # Calculate distance
                distance = self._calculate_distance(ref_center, cand_center)
                
                if distance <= max_distance:
                    # Check direction if specified
                    if direction and not self._check_direction(ref_center, cand_center, direction):
                        continue
                    
                    proximity_matches.append((candidate, distance))
            except Exception as e:
                self.logger.debug(f"Error processing proximity candidate: {e}")
                continue
        
        # Sort by distance
        proximity_matches.sort(key=lambda x: x[1])
        return [match[0] for match in proximity_matches]
    
    def find_by_visual_pattern(self, pattern_description: str, 
                             container: Optional[WebElement] = None) -> List[WebElement]:
        """
        Find elements matching a visual pattern description
        
        Args:
            pattern_description: Natural language description of the pattern
            container: Container to search within
            
        Returns:
            List of matching elements
        """
        # Define pattern mappings
        patterns = {
            'button': {
                'tags': ['button', 'a', 'div', 'span'],
                'classes': ['btn', 'button', 'submit', 'action'],
                'attributes': {'role': 'button'}
            },
            'input_field': {
                'tags': ['input', 'textarea'],
                'types': ['text', 'email', 'tel', 'number', 'search']
            },
            'link': {
                'tags': ['a'],
                'attributes': {'href': True}
            },
            'image': {
                'tags': ['img'],
                'attributes': {'src': True}
            },
            'heading': {
                'tags': ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
            },
            'list': {
                'tags': ['ul', 'ol', 'dl']
            },
            'table': {
                'tags': ['table']
            },
            'form': {
                'tags': ['form']
            },
            'navigation': {
                'tags': ['nav', 'ul', 'div'],
                'classes': ['nav', 'menu', 'navigation'],
                'attributes': {'role': 'navigation'}
            }
        }
        
        # Parse pattern description
        pattern_key = None
        for key in patterns:
            if key in pattern_description.lower():
                pattern_key = key
                break
        
        if not pattern_key:
            self.logger.warning(f"Unknown pattern: {pattern_description}")
            return []
        
        pattern = patterns[pattern_key]
        search_root = container or self.driver
        matches = []
        
        # Search by tags
        for tag in pattern.get('tags', []):
            elements = search_root.find_elements(By.TAG_NAME, tag)
            
            for element in elements:
                # Check additional criteria
                if self._matches_pattern_criteria(element, pattern):
                    matches.append(element)
        
        return matches
    
    def find_by_semantic_similarity(self, description: str, 
                                  candidates: Optional[List[WebElement]] = None,
                                  min_similarity: float = 0.7) -> List[WebElement]:
        """
        Find elements by semantic similarity using AI
        
        Args:
            description: Natural language description
            candidates: List of candidate elements (all if None)
            min_similarity: Minimum similarity threshold
            
        Returns:
            List of semantically similar elements
        """
        if not self.ai_available or not self.ai_model:
            self.logger.warning("AI model not available for semantic matching")
            return []
        
        # Get candidates
        if candidates is None:
            candidates = self.driver.find_elements(By.XPATH, "//*[text()]")
        
        # Encode description
        desc_embedding = self.ai_model.encode(description)
        
        matches = []
        for element in candidates:
            try:
                # Get element context
                element_text = self._get_element_context(element)
                if not element_text:
                    continue
                
                # Calculate semantic similarity
                elem_embedding = self.ai_model.encode(element_text)
                similarity = self._cosine_similarity(desc_embedding, elem_embedding)
                
                if similarity >= min_similarity:
                    matches.append((element, similarity))
            except Exception as e:
                self.logger.debug(f"Error in semantic matching: {e}")
                continue
        
        # Sort by similarity
        matches.sort(key=lambda x: x[1], reverse=True)
        return [match[0] for match in matches]
    
    def find_related_elements(self, anchor_element: WebElement, 
                            relationship: str = "sibling") -> List[WebElement]:
        """
        Find elements related to an anchor element
        
        Args:
            anchor_element: Reference element
            relationship: Type of relationship ('sibling', 'parent', 'child', 'ancestor')
            
        Returns:
            List of related elements
        """
        try:
            if relationship == "sibling":
                # Find siblings
                parent = anchor_element.find_element(By.XPATH, "..")
                siblings = parent.find_elements(By.XPATH, "./*")
                return [s for s in siblings if s != anchor_element]
            
            elif relationship == "parent":
                return [anchor_element.find_element(By.XPATH, "..")]
            
            elif relationship == "child":
                return anchor_element.find_elements(By.XPATH, "./*")
            
            elif relationship == "ancestor":
                ancestors = []
                current = anchor_element
                while True:
                    try:
                        parent = current.find_element(By.XPATH, "..")
                        if parent.tag_name == "html":
                            break
                        ancestors.append(parent)
                        current = parent
                    except:
                        break
                return ancestors
            
            else:
                self.logger.warning(f"Unknown relationship type: {relationship}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error finding related elements: {e}")
            return []
    
    def find_by_composite_strategy(self, strategies: List[Dict[str, Any]]) -> List[WebElement]:
        """
        Find elements using multiple strategies combined
        
        Args:
            strategies: List of strategy configurations
            
        Returns:
            List of elements matching all strategies
        """
        results = None
        
        for strategy in strategies:
            strategy_type = strategy.get('type')
            
            if strategy_type == 'text':
                elements = self.find_by_text_content(
                    strategy.get('text', ''),
                    strategy.get('tag', '*'),
                    strategy.get('fuzzy', True),
                    strategy.get('min_similarity', 0.8)
                )
            
            elif strategy_type == 'proximity':
                ref_element = strategy.get('reference')
                if ref_element:
                    elements = self.find_by_proximity(
                        ref_element,
                        strategy.get('target_tag', '*'),
                        strategy.get('max_distance', 300),
                        strategy.get('direction')
                    )
                else:
                    elements = []
            
            elif strategy_type == 'pattern':
                elements = self.find_by_visual_pattern(
                    strategy.get('pattern', ''),
                    strategy.get('container')
                )
            
            elif strategy_type == 'css':
                elements = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    strategy.get('selector', '*')
                )
            
            else:
                self.logger.warning(f"Unknown strategy type: {strategy_type}")
                elements = []
            
            # Intersect results
            if results is None:
                results = set(elements)
            else:
                results = results.intersection(set(elements))
        
        return list(results) if results else []
    
    # Helper methods
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts"""
        # Simple character-based similarity
        if not text1 or not text2:
            return 0.0
        
        # Exact match
        if text1 == text2:
            return 1.0
        
        # Partial match
        if text1 in text2 or text2 in text1:
            shorter = min(len(text1), len(text2))
            longer = max(len(text1), len(text2))
            return shorter / longer
        
        # Levenshtein distance-based similarity
        distance = self._levenshtein_distance(text1, text2)
        max_len = max(len(text1), len(text2))
        return 1 - (distance / max_len)
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def _calculate_distance(self, point1: Dict[str, float], point2: Dict[str, float]) -> float:
        """Calculate Euclidean distance between two points"""
        dx = point1['x'] - point2['x']
        dy = point1['y'] - point2['y']
        return (dx ** 2 + dy ** 2) ** 0.5
    
    def _check_direction(self, ref_point: Dict[str, float], 
                        target_point: Dict[str, float], direction: str) -> bool:
        """Check if target is in specified direction from reference"""
        dx = target_point['x'] - ref_point['x']
        dy = target_point['y'] - ref_point['y']
        
        if direction == 'above':
            return dy < -10  # Some threshold
        elif direction == 'below':
            return dy > 10
        elif direction == 'left':
            return dx < -10
        elif direction == 'right':
            return dx > 10
        
        return True
    
    def _matches_pattern_criteria(self, element: WebElement, pattern: Dict[str, Any]) -> bool:
        """Check if element matches pattern criteria"""
        try:
            # Check element type
            if 'types' in pattern:
                element_type = element.get_attribute('type')
                if element_type not in pattern['types']:
                    return False
            
            # Check classes
            if 'classes' in pattern:
                element_classes = element.get_attribute('class') or ''
                if not any(cls in element_classes for cls in pattern['classes']):
                    return False
            
            # Check attributes
            if 'attributes' in pattern:
                for attr, expected in pattern['attributes'].items():
                    attr_value = element.get_attribute(attr)
                    if expected is True and not attr_value:
                        return False
                    elif expected is not True and attr_value != expected:
                        return False
            
            return True
            
        except Exception:
            return False
    
    def _get_element_context(self, element: WebElement) -> str:
        """Get text context around element"""
        try:
            # Get element text
            text_parts = [element.text]
            
            # Add attribute context
            for attr in ['title', 'alt', 'placeholder', 'aria-label']:
                attr_value = element.get_attribute(attr)
                if attr_value:
                    text_parts.append(attr_value)
            
            # Add nearby text (simplified)
            try:
                parent = element.find_element(By.XPATH, "..")
                parent_text = parent.text
                if parent_text and parent_text != element.text:
                    text_parts.append(parent_text)
            except:
                pass
            
            return ' '.join(text_parts)
            
        except Exception:
            return ""
    
    def _cosine_similarity(self, vec1, vec2) -> float:
        """Calculate cosine similarity between two vectors"""
        if self.ai_available:
            dot_product = np.dot(vec1, vec2)
            norm_a = np.linalg.norm(vec1)
            norm_b = np.linalg.norm(vec2)
            return dot_product / (norm_a * norm_b)
        return 0.0


class FallbackSelector:
    """Manages fallback strategies for element selection"""
    
    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.advanced = AdvancedSelectors(driver)
        self.logger = logging.getLogger(f'{__name__}.FallbackSelector')
    
    def find_with_fallbacks(self, primary_selector: str, 
                          fallback_strategies: List[Dict[str, Any]]) -> Optional[WebElement]:
        """
        Try to find element with primary selector, then fallbacks
        
        Args:
            primary_selector: Primary CSS selector
            fallback_strategies: List of fallback strategies
            
        Returns:
            Found element or None
        """
        # Try primary selector
        try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, primary_selector)
            if elements:
                return elements[0]
        except Exception as e:
            self.logger.debug(f"Primary selector failed: {e}")
        
        # Try fallback strategies
        for strategy in fallback_strategies:
            try:
                strategy_type = strategy.get('type')
                
                if strategy_type == 'text':
                    elements = self.advanced.find_by_text_content(
                        strategy.get('text', ''),
                        strategy.get('tag', '*'),
                        strategy.get('fuzzy', True)
                    )
                    if elements:
                        return elements[0]
                
                elif strategy_type == 'xpath':
                    elements = self.driver.find_elements(
                        By.XPATH,
                        strategy.get('xpath', '')
                    )
                    if elements:
                        return elements[0]
                
                elif strategy_type == 'pattern':
                    elements = self.advanced.find_by_visual_pattern(
                        strategy.get('pattern', '')
                    )
                    if elements:
                        return elements[0]
                
            except Exception as e:
                self.logger.debug(f"Fallback strategy failed: {e}")
                continue
        
        return None