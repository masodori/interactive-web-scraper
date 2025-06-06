#!/usr/bin/env python
"""
Template validator and optimizer for the Interactive Web Scraper.
Validates templates and suggests improvements.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import InvalidSelectorException


class TemplateValidator:
    """Validate and optimize scraping templates."""
    
    def __init__(self, headless: bool = True):
        """Initialize validator with optional browser for testing."""
        self.driver = None
        self.headless = headless
        self.issues = []
        self.suggestions = []
    
    def __enter__(self):
        """Context manager entry."""
        if not self.headless:
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            self.driver = webdriver.Chrome(options=options)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.driver:
            self.driver.quit()
    
    def validate_template(self, template_path: Path) -> Tuple[bool, List[str], List[str]]:
        """
        Validate a template file.
        
        Returns:
            Tuple of (is_valid, issues, suggestions)
        """
        self.issues = []
        self.suggestions = []
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template = json.load(f)
        except Exception as e:
            self.issues.append(f"Failed to load template: {e}")
            return False, self.issues, self.suggestions
        
        # Validate structure
        self._validate_structure(template)
        
        # Validate selectors
        self._validate_selectors(template)
        
        # Check for common issues
        self._check_common_issues(template)
        
        # Generate suggestions
        self._generate_suggestions(template)
        
        is_valid = len(self.issues) == 0
        return is_valid, self.issues, self.suggestions
    
    def _validate_structure(self, template: Dict[str, Any]):
        """Validate template structure."""
        required_fields = ['name', 'site_info', 'scraping_type']
        
        for field in required_fields:
            if field not in template:
                self.issues.append(f"Missing required field: {field}")
        
        # Validate site_info
        if 'site_info' in template:
            if 'url' not in template['site_info']:
                self.issues.append("Missing URL in site_info")
        
        # Validate scraping type
        if 'scraping_type' in template:
            valid_types = ['single_page', 'list_only', 'list_detail']
            if template['scraping_type'] not in valid_types:
                self.issues.append(f"Invalid scraping_type: {template['scraping_type']}")
    
    def _validate_selectors(self, template: Dict[str, Any]):
        """Validate all CSS selectors in template."""
        # List page selectors
        if 'list_page_rules' in template and template['list_page_rules']:
            rules = template['list_page_rules']
            
            # Validate fields
            if 'fields' in rules:
                for field_name, selector in rules['fields'].items():
                    self._validate_selector(selector, f"list_page.{field_name}")
            
            # Validate other selectors
            if 'repeating_item_selector' in rules:
                self._validate_selector(rules['repeating_item_selector'], 'repeating_item_selector')
            
            if 'profile_link_selector' in rules:
                self._validate_selector(rules['profile_link_selector'], 'profile_link_selector')
        
        # Detail page selectors
        if 'detail_page_rules' in template and template['detail_page_rules']:
            rules = template['detail_page_rules']
            
            if 'fields' in rules:
                for field_name, selector in rules['fields'].items():
                    self._validate_selector(selector, f"detail_page.{field_name}")
    
    def _validate_selector(self, selector: str, field_name: str):
        """Validate a single CSS selector."""
        if not selector:
            return
        
        # Check for trailing >
        if selector.strip().endswith('>'):
            self.issues.append(f"{field_name}: Selector ends with '>' (incomplete child combinator)")
        
        # Check for invalid characters
        invalid_chars = ['<', '{', '}', '\\']
        for char in invalid_chars:
            if char in selector:
                self.issues.append(f"{field_name}: Contains invalid character '{char}'")
        
        # Check for balanced brackets
        if selector.count('[') != selector.count(']'):
            self.issues.append(f"{field_name}: Unbalanced square brackets")
        
        if selector.count('(') != selector.count(')'):
            self.issues.append(f"{field_name}: Unbalanced parentheses")
        
        # Test with Selenium if driver available
        if self.driver:
            try:
                self.driver.find_elements(By.CSS_SELECTOR, selector)
            except InvalidSelectorException as e:
                self.issues.append(f"{field_name}: Invalid selector - {str(e)}")
    
    def _check_common_issues(self, template: Dict[str, Any]):
        """Check for common template issues."""
        # Check for overly complex selectors
        if 'detail_page_rules' in template and template['detail_page_rules']:
            rules = template['detail_page_rules']
            if 'fields' in rules:
                for field_name, selector in rules['fields'].items():
                    if selector and len(selector) > 150:
                        self.issues.append(f"detail_page.{field_name}: Overly complex selector (length: {len(selector)})")
                    
                    # Check for too many nth-of-type
                    nth_count = selector.count('nth-of-type') if selector else 0
                    if nth_count > 3:
                        self.issues.append(f"detail_page.{field_name}: Too many nth-of-type selectors ({nth_count})")
        
        # Check for missing detail page fields
        if template.get('scraping_type') == 'list_detail':
            detail_rules = template.get('detail_page_rules', {})
            if not detail_rules.get('fields'):
                self.issues.append("List+Detail template has no detail page fields defined")
    
    def _generate_suggestions(self, template: Dict[str, Any]):
        """Generate improvement suggestions."""
        # Suggest simpler selectors
        if 'detail_page_rules' in template and template['detail_page_rules']:
            rules = template['detail_page_rules']
            if 'fields' in rules:
                for field_name, selector in rules['fields'].items():
                    if selector and len(selector) > 100:
                        self.suggestions.append(
                            f"{field_name}: Consider using simpler selectors like "
                            f"'.{field_name.lower()}' or '[class*=\"{field_name.lower()}\"]'"
                        )
        
        # Suggest pattern-based extraction
        detail_fields = template.get('detail_page_rules', {}).get('fields', {})
        pattern_fields = ['Email', 'PhoneNumber', 'Education1', 'Education2', 'Creds']
        
        for field in pattern_fields:
            if field in detail_fields and not detail_fields[field]:
                self.suggestions.append(
                    f"{field}: Consider using pattern-based extraction as primary method"
                )
        
        # Suggest load strategy
        list_rules = template.get('list_page_rules', {})
        load_strategy = list_rules.get('load_strategy', {})
        if load_strategy.get('type') == 'auto':
            self.suggestions.append(
                "Consider specifying exact button selector for load_strategy if known"
            )


def validate_all_templates():
    """Validate all templates in the templates directory."""
    templates_dir = Path("templates")
    
    if not templates_dir.exists():
        print("❌ Templates directory not found!")
        return
    
    template_files = list(templates_dir.glob("*.json"))
    
    if not template_files:
        print("❌ No template files found!")
        return
    
    print(f"🔍 Validating {len(template_files)} template(s)...\n")
    
    all_valid = True
    
    with TemplateValidator(headless=True) as validator:
        for template_path in template_files:
            print(f"\n📄 Validating: {template_path.name}")
            print("-" * 50)
            
            is_valid, issues, suggestions = validator.validate_template(template_path)
            
            if is_valid:
                print("✅ Template is valid!")
            else:
                print("❌ Template has issues:")
                all_valid = False
                for issue in issues:
                    print(f"   • {issue}")
            
            if suggestions:
                print("\n💡 Suggestions:")
                for suggestion in suggestions:
                    print(f"   • {suggestion}")
    
    print("\n" + "="*50)
    if all_valid:
        print("✅ All templates are valid!")
    else:
        print("❌ Some templates have issues. Please fix them.")
        print("\n🔧 Run fix_template_selectors.py to automatically fix selector issues")


def create_template_report(output_file: str = "template_report.txt"):
    """Create a detailed report of all templates."""
    templates_dir = Path("templates")
    template_files = list(templates_dir.glob("*.json"))
    
    with open(output_file, 'w', encoding='utf-8') as report:
        report.write("Template Analysis Report\n")
        report.write("="*50 + "\n\n")
        
        for template_path in template_files:
            with open(template_path, 'r', encoding='utf-8') as f:
                template = json.load(f)
            
            report.write(f"Template: {template['name']}\n")
            report.write(f"URL: {template['site_info']['url']}\n")
            report.write(f"Type: {template['scraping_type']}\n")
            
            # Count fields
            list_fields = len(template.get('list_page_rules', {}).get('fields', {}))
            detail_fields = len(template.get('detail_page_rules', {}).get('fields', {}))
            
            report.write(f"List fields: {list_fields}\n")
            report.write(f"Detail fields: {detail_fields}\n")
            report.write("\n")
    
    print(f"📊 Report generated: {output_file}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "report":
        create_template_report()
    else:
        validate_all_templates()