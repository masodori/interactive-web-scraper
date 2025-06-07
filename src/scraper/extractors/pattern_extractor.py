# src/scraper/extractors/pattern_extractor.py
"""
Pattern-based extraction for common data types like emails, phones, addresses, etc.
"""

import re
import logging
from typing import Dict, List, Optional, Any, Pattern
from dataclasses import dataclass


@dataclass
class PatternConfig:
    """Configuration for a pattern-based extraction"""
    pattern: Pattern
    context_keywords: List[str]
    validation_func: Optional[callable] = None
    post_process_func: Optional[callable] = None


class PatternExtractor:
    """Extract data using regex patterns and contextual validation"""
    
    def __init__(self):
        self.logger = logging.getLogger(f'{__name__}.PatternExtractor')
        self.patterns = self._initialize_patterns()
    
    def _initialize_patterns(self) -> Dict[str, PatternConfig]:
        """Initialize common extraction patterns"""
        return {
            'email': PatternConfig(
                pattern=re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
                context_keywords=['email', 'contact', 'mail', '@'],
                validation_func=self._validate_email
            ),
            'phone': PatternConfig(
                pattern=re.compile(r'(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'),
                context_keywords=['phone', 'tel', 'call', 'mobile', 'cell', 'direct', 'office'],
                post_process_func=self._format_phone
            ),
            'phone_international': PatternConfig(
                pattern=re.compile(r'\+?[1-9]\d{0,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}'),
                context_keywords=['phone', 'tel', 'international'],
                validation_func=self._validate_international_phone
            ),
            'zip_code': PatternConfig(
                pattern=re.compile(r'\b\d{5}(?:-\d{4})?\b'),
                context_keywords=['zip', 'postal', 'code'],
                validation_func=lambda x: len(x.replace('-', '')) in [5, 9]
            ),
            'education': PatternConfig(
                pattern=re.compile(
                    r'(?:J\.?D\.?|LL\.?M\.?|B\.?A\.?|B\.?S\.?|M\.?A\.?|M\.?S\.?|Ph\.?D\.?|M\.?B\.?A\.?|'
                    r'JD|LLM|BA|BS|MA|MS|PhD|MBA)'
                    r'[^,\n]*?(?:,\s*(?:19|20)\d{2})?',
                    re.IGNORECASE
                ),
                context_keywords=['education', 'university', 'college', 'school', 'degree', 'graduated', 'alumni'],
                post_process_func=self._clean_education
            ),
            'bar_admission': PatternConfig(
                pattern=re.compile(
                    r'(?:Admitted to|Member of|Licensed in|Bar Admission[s]?)[^.]+?'
                    r'(?:Bar|Court|Practice)[^.]*\.?',
                    re.IGNORECASE
                ),
                context_keywords=['bar', 'admission', 'licensed', 'admitted', 'court', 'practice']
            ),
            'social_media': PatternConfig(
                pattern=re.compile(
                    r'(?:(?:https?://)?(?:www\.)?'
                    r'(?:linkedin\.com/in/|twitter\.com/|facebook\.com/)'
                    r'[A-Za-z0-9_.-]+)',
                    re.IGNORECASE
                ),
                context_keywords=['linkedin', 'twitter', 'facebook', 'social'],
                post_process_func=self._normalize_social_url
            ),
            'price': PatternConfig(
                pattern=re.compile(r'\$\s*\d+(?:,\d{3})*(?:\.\d{2})?'),
                context_keywords=['price', 'cost', 'fee', 'rate', '$'],
                post_process_func=self._parse_price
            ),
            'date': PatternConfig(
                pattern=re.compile(
                    r'\b(?:'
                    r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}|'
                    r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|'
                    r'\d{4}[-/]\d{1,2}[-/]\d{1,2}'
                    r')\b',
                    re.IGNORECASE
                ),
                context_keywords=['date', 'when', 'deadline', 'posted', 'updated'],
                post_process_func=self._normalize_date
            ),
            'address': PatternConfig(
                pattern=re.compile(
                    r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Plaza|Place|Pl)'
                    r'(?:[,\s]+(?:Suite|Ste|Floor|Fl)?[,\s]*\d*)?'
                    r'[,\s]+[A-Za-z\s]+[,\s]+[A-Z]{2}\s+\d{5}(?:-\d{4})?',
                    re.IGNORECASE
                ),
                context_keywords=['address', 'location', 'office', 'headquarters'],
                post_process_func=self._clean_address
            )
        }
    
    def extract(self, text: str, pattern_type: str, context: Optional[str] = None) -> Optional[Any]:
        """
        Extract data using specified pattern type
        
        Args:
            text: Text to extract from
            pattern_type: Type of pattern to use
            context: Additional context for validation
            
        Returns:
            Extracted value or None
        """
        if pattern_type not in self.patterns:
            self.logger.warning(f"Unknown pattern type: {pattern_type}")
            return None
        
        config = self.patterns[pattern_type]
        
        # Check context if provided
        if context and config.context_keywords:
            context_lower = context.lower()
            if not any(keyword in context_lower for keyword in config.context_keywords):
                self.logger.debug(f"Context doesn't match for {pattern_type}")
                return None
        
        # Find matches
        matches = config.pattern.findall(text)
        if not matches:
            return None
        
        # Get first match
        match = matches[0]
        if isinstance(match, tuple):
            match = ''.join(match)
        
        # Validate if function provided
        if config.validation_func and not config.validation_func(match):
            return None
        
        # Post-process if function provided
        if config.post_process_func:
            match = config.post_process_func(match)
        
        return match
    
    def extract_all(self, text: str, pattern_type: str, context: Optional[str] = None) -> List[Any]:
        """Extract all occurrences of a pattern"""
        if pattern_type not in self.patterns:
            return []
        
        config = self.patterns[pattern_type]
        
        # Check context
        if context and config.context_keywords:
            context_lower = context.lower()
            if not any(keyword in context_lower for keyword in config.context_keywords):
                return []
        
        matches = config.pattern.findall(text)
        results = []
        
        for match in matches:
            if isinstance(match, tuple):
                match = ''.join(match)
            
            if config.validation_func and not config.validation_func(match):
                continue
            
            if config.post_process_func:
                match = config.post_process_func(match)
            
            results.append(match)
        
        return results
    
    def extract_multiple_patterns(self, text: str, patterns: List[str]) -> Dict[str, Any]:
        """Extract multiple pattern types from text"""
        results = {}
        
        for pattern_type in patterns:
            value = self.extract(text, pattern_type)
            if value:
                results[pattern_type] = value
        
        return results
    
    def extract_with_context(self, text: str, pattern_type: str, window_size: int = 50) -> Optional[Dict[str, Any]]:
        """Extract pattern with surrounding context"""
        if pattern_type not in self.patterns:
            return None
        
        config = self.patterns[pattern_type]
        match = config.pattern.search(text)
        
        if not match:
            return None
        
        start, end = match.span()
        context_start = max(0, start - window_size)
        context_end = min(len(text), end + window_size)
        
        value = match.group()
        if config.validation_func and not config.validation_func(value):
            return None
        
        if config.post_process_func:
            value = config.post_process_func(value)
        
        return {
            'value': value,
            'context': text[context_start:context_end],
            'position': (start, end)
        }
    
    # Validation functions
    def _validate_email(self, email: str) -> bool:
        """Validate email format"""
        parts = email.split('@')
        if len(parts) != 2:
            return False
        
        local, domain = parts
        if not local or not domain:
            return False
        
        if '.' not in domain:
            return False
        
        # Basic checks
        if '..' in email or email.startswith('.') or email.endswith('.'):
            return False
        
        return True
    
    def _validate_international_phone(self, phone: str) -> bool:
        """Validate international phone number"""
        # Remove all non-digits
        digits = re.sub(r'\D', '', phone)
        
        # International numbers should have 10-15 digits
        return 10 <= len(digits) <= 15
    
    # Post-processing functions
    def _format_phone(self, phone: str) -> str:
        """Format phone number to standard format"""
        # Extract digits
        digits = re.sub(r'\D', '', phone)
        
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] == '1':
            return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
        else:
            return phone
    
    def _clean_education(self, education: str) -> str:
        """Clean education entry"""
        # Remove extra whitespace
        education = ' '.join(education.split())
        
        # Standardize degree abbreviations
        replacements = {
            'J.D.': 'JD',
            'LL.M.': 'LLM',
            'B.A.': 'BA',
            'B.S.': 'BS',
            'M.A.': 'MA',
            'M.S.': 'MS',
            'Ph.D.': 'PhD',
            'M.B.A.': 'MBA'
        }
        
        for old, new in replacements.items():
            education = education.replace(old, new)
        
        return education.strip()
    
    def _normalize_social_url(self, url: str) -> str:
        """Normalize social media URL"""
        if not url.startswith('http'):
            url = 'https://' + url
        
        # Remove trailing slashes
        return url.rstrip('/')
    
    def _parse_price(self, price: str) -> float:
        """Parse price string to float"""
        # Remove $ and commas
        price_clean = price.replace('$', '').replace(',', '').strip()
        
        try:
            return float(price_clean)
        except ValueError:
            return price
    
    def _normalize_date(self, date_str: str) -> str:
        """Normalize date format"""
        # This is a simple implementation
        # In production, use dateutil.parser
        return date_str.strip()
    
    def _clean_address(self, address: str) -> str:
        """Clean address formatting"""
        # Remove extra whitespace
        address = ' '.join(address.split())
        
        # Standardize abbreviations
        replacements = {
            ' Street': ' St',
            ' Avenue': ' Ave',
            ' Road': ' Rd',
            ' Boulevard': ' Blvd',
            ' Suite': ' Ste',
            ' Floor': ' Fl'
        }
        
        for old, new in replacements.items():
            address = address.replace(old, new)
        
        return address
    
    def add_custom_pattern(self, name: str, pattern: str, context_keywords: List[str] = None,
                          validation_func: callable = None, post_process_func: callable = None):
        """Add a custom pattern for extraction"""
        self.patterns[name] = PatternConfig(
            pattern=re.compile(pattern),
            context_keywords=context_keywords or [],
            validation_func=validation_func,
            post_process_func=post_process_func
        )
        
        self.logger.info(f"Added custom pattern: {name}")