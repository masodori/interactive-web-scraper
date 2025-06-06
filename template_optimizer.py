#!/usr/bin/env python
"""
Template optimizer - Create optimized templates for lawyer profile sites.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


def create_optimized_template(
    name: str,
    url: str,
    site_type: str = "gibson_dunn"
) -> Dict[str, Any]:
    """Create an optimized template based on site type."""
    
    # Base template structure
    template = {
        "name": name,
        "version": "2.0",
        "created_at": datetime.now().isoformat(),
        "site_info": {
            "url": url,
            "cookie_xpath": None,
            "cookie_css": None,
            "headers": {},
            "wait_time": 0.0
        },
        "scraping_type": "list_detail",
        "optimization_settings": {
            "use_pattern_matching": True,
            "prefer_simple_selectors": True,
            "max_selector_length": 100,
            "fallback_to_patterns": True
        }
    }
    
    # Site-specific optimizations
    if site_type == "gibson_dunn":
        template["list_page_rules"] = {
            "fields": {
                "Name": "p.name strong, .lawyer-name, [class*='name'] strong",
                "Position": "p.title span:first-child, .position, .title",
                "Office": "p.title span:nth-child(2), .office, .location",
                "Email": "a[href^='mailto:'], .contact-details a[href^='mailto:']"
            },
            "repeating_item_selector": "div.wp-grid-builder > div, .lawyer-item, .attorney-card",
            "profile_link_selector": "a[href*='/lawyer/'], a[href*='/attorney/'], p.name a",
            "load_strategy": {
                "type": "button",
                "max_scrolls": 10,
                "max_clicks": 50,  # Increased for full loading
                "pause_time": 2.0,
                "button_selector": "button.wpgb-button, .load-more, button:contains('Load More')",
                "pagination_next_selector": None,
                "wait_for_element": ".lawyer-item"
            }
        }
        
        template["detail_page_rules"] = {
            "fields": {
                # Use multiple selectors with fallbacks
                "PhoneNumber": "a[href^='tel:'], .phone, [class*='phone'], .contact:contains('+')",
                "EmailAddress": "a[href^='mailto:'], .email a, [class*='email'] a",
                "Education": ".bio-education li, .education li, [class*='education'] li",
                "Credentials": ".bar-admissions, .credentials, [class*='admission'], [class*='credential']",
                "Bio": ".lawyer-bio, .bio-content, .overview, .biography",
                "PracticeAreas": ".practice-areas li, .practices li, [class*='practice'] li"
            },
            "repeating_item_selector": None,
            "profile_link_selector": None,
            "load_strategy": {
                "type": "none",
                "max_scrolls": 0,
                "max_clicks": 0,
                "pause_time": 1.0,
                "button_selector": None,
                "pagination_next_selector": None,
                "wait_for_element": None
            },
            # Pattern-based extraction as fallback
            "extraction_patterns": {
                "email": {
                    "pattern": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                    "context_keywords": ["email", "contact", "@"]
                },
                "phone": {
                    "pattern": r'(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',
                    "context_keywords": ["phone", "tel", "call", "mobile", "direct"]
                },
                "education": {
                    "pattern": r'(?:J\.D\.|JD|LL\.M\.|LLM|B\.A\.|BA|B\.S\.|BS|M\.A\.|MA|Ph\.D\.|PhD|M\.B\.A\.|MBA)[^,\n]*(?:,\s*\d{4})?',
                    "context_keywords": ["education", "university", "college", "degree", "graduated"]
                },
                "bar_admissions": {
                    "pattern": r'(?:Admitted to|Member of|Licensed in)[^.]+(?:Bar|Court)[^.]+\.',
                    "context_keywords": ["bar", "admission", "licensed", "admitted", "court"]
                }
            }
        }
    
    else:
        # Generic lawyer site template
        template["list_page_rules"] = {
            "fields": {
                "Name": ".name, h3.name, h4.name, [class*='name']",
                "Position": ".title, .position, [class*='title']",
                "Office": ".office, .location, [class*='location']",
                "Email": "a[href^='mailto:']"
            },
            "repeating_item_selector": ".lawyer-item, .attorney-item, .profile-card, article.person",
            "profile_link_selector": "a[href*='/lawyer/'], a[href*='/attorney/'], a[href*='/people/']",
            "load_strategy": {
                "type": "auto",
                "max_scrolls": 10,
                "max_clicks": 50,
                "pause_time": 2.0,
                "button_selector": None,
                "pagination_next_selector": None,
                "wait_for_element": None
            }
        }
        
        template["detail_page_rules"] = {
            "fields": {
                "PhoneNumber": "a[href^='tel:']",
                "EmailAddress": "a[href^='mailto:']",
                "Education": ".education li, [class*='education'] li",
                "Credentials": ".credentials, .bar-admissions",
                "Bio": ".bio, .biography, .overview"
            },
            "repeating_item_selector": None,
            "profile_link_selector": None,
            "load_strategy": {
                "type": "none",
                "max_scrolls": 0,
                "max_clicks": 0,
                "pause_time": 1.0,
                "button_selector": None,
                "pagination_next_selector": None,
                "wait_for_element": None
            }
        }
    
    # Add field mappings for standardized output
    template["field_mappings"] = {
        "Name": "name",
        "Position": "title",
        "Office": "office", 
        "Email": "email",
        "EmailAddress": "email",
        "PhoneNumber": "phone",
        "Education": "education",
        "Credentials": "credentials",
        "Bio": "biography",
        "PracticeAreas": "practice_areas"
    }
    
    return template


def optimize_existing_template(template_path: Path) -> Dict[str, Any]:
    """Optimize an existing template."""
    with open(template_path, 'r', encoding='utf-8') as f:
        template = json.load(f)
    
    # Add optimization settings
    template["optimization_settings"] = {
        "use_pattern_matching": True,
        "prefer_simple_selectors": True,
        "max_selector_length": 100,
        "fallback_to_patterns": True
    }
    
    # Simplify selectors
    if 'detail_page_rules' in template and template['detail_page_rules']:
        rules = template['detail_page_rules']
        
        # Add extraction patterns
        rules["extraction_patterns"] = {
            "email": {
                "pattern": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                "context_keywords": ["email", "contact"]
            },
            "phone": {
                "pattern": r'(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',
                "context_keywords": ["phone", "tel", "call"]
            },
            "education": {
                "pattern": r'(?:J\.D\.|JD|LL\.M\.|LLM|B\.A\.|BA|B\.S\.|BS|M\.A\.|MA|Ph\.D\.|PhD)[^,\n]*(?:,\s*\d{4})?',
                "context_keywords": ["education", "university", "degree"]
            }
        }
        
        # Improve load strategy
        if 'list_page_rules' in template:
            load_strategy = template['list_page_rules'].get('load_strategy', {})
            load_strategy['max_clicks'] = 50  # Ensure we get all items
            load_strategy['pause_time'] = 2.0  # Give time for content to load
    
    return template


def main():
    """Main function."""
    print("🚀 Template Optimizer")
    print("="*60)
    
    print("\nOptions:")
    print("1. Create new optimized template")
    print("2. Optimize existing template")
    print("3. Create template for Gibson Dunn")
    
    choice = input("\nSelect option (1-3): ").strip()
    
    if choice == "1":
        name = input("Template name: ").strip()
        url = input("Site URL: ").strip()
        
        template = create_optimized_template(name, url, "generic")
        
        output_path = Path("templates") / f"{name}.json"
        output_path.parent.mkdir(exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(template, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Created optimized template: {output_path}")
        
    elif choice == "2":
        template_name = input("Template file name (without .json): ").strip()
        template_path = Path("templates") / f"{template_name}.json"
        
        if template_path.exists():
            optimized = optimize_existing_template(template_path)
            
            # Save with _optimized suffix
            output_path = template_path.with_stem(f"{template_path.stem}_optimized")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(optimized, f, indent=2, ensure_ascii=False)
            
            print(f"\n✅ Created optimized version: {output_path}")
        else:
            print(f"\n❌ Template not found: {template_path}")
            
    elif choice == "3":
        # Create optimized Gibson Dunn template
        template = create_optimized_template(
            "gibson_dunn_optimized",
            "https://www.gibsondunn.com/people/",
            "gibson_dunn"
        )
        
        output_path = Path("templates") / "gibson_dunn_optimized.json"
        output_path.parent.mkdir(exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(template, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Created optimized Gibson Dunn template: {output_path}")
        print("\n📌 This template includes:")
        print("   • Multiple fallback selectors for each field")
        print("   • Pattern-based extraction as backup")
        print("   • Increased max_clicks to 50 for complete loading")
        print("   • Simplified selectors that are less likely to break")


if __name__ == "__main__":
    main()