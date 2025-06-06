#!/usr/bin/env python
"""
Script to fix invalid CSS selectors in template files and optimize them for reliability.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List


def fix_invalid_selectors(selector: str) -> str:
    """Fix common selector issues."""
    if not selector:
        return selector
    
    # Remove trailing > or spaces followed by >
    selector = re.sub(r'\s*>\s*$', '', selector)
    
    # Remove unnecessary nth-of-type(1) - it's redundant
    selector = re.sub(r':nth-of-type\(1\)', '', selector)
    
    # Normalize whitespace
    selector = ' '.join(selector.split())
    
    return selector


def simplify_selector(selector: str, field_name: str = "") -> str:
    """Simplify overly complex selectors based on field type."""
    # If selector is too long (likely too specific), try to simplify
    if len(selector) > 100:
        parts = selector.split(' > ')
        
        # For education fields, use simpler patterns
        if 'education' in field_name.lower() or 'creds' in field_name.lower():
            # Look for list items containing education
            for i, part in enumerate(parts):
                if 'ul' in part or 'ol' in part:
                    # Return from the list onward
                    return ' > '.join(parts[i:]) + ' li'
        
        # For bio fields, look for content areas
        if 'bio' in field_name.lower():
            for i, part in enumerate(parts):
                if any(cls in part for cls in ['.content', '.bio', '.description', '.text']):
                    return ' > '.join(parts[i:])
        
        # Generic simplification - take last 3-4 meaningful parts
        meaningful_parts = [p for p in parts if not re.match(r'^div:nth-of-type\(\d+\)$', p)]
        if len(meaningful_parts) > 4:
            return ' > '.join(meaningful_parts[-4:])
    
    return selector


def suggest_better_selectors(template: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    """Suggest more robust selectors based on common patterns."""
    suggestions = {
        "list_page": {},
        "detail_page": {}
    }
    
    # Common patterns for lawyer profile sites
    common_patterns = {
        # List page fields
        "Name": [
            ".lawyer-name", ".attorney-name", ".name", "h3.name", "h4.name",
            "[class*='name'] strong", ".profile-name", ".person-name"
        ],
        "Position": [
            ".title", ".position", ".role", ".designation",
            "[class*='title']", "[class*='position']", ".job-title"
        ],
        "Office": [
            ".office", ".location", ".office-location",
            "[class*='office']", "[class*='location']"
        ],
        "Email": [
            "a[href^='mailto:']", ".email a", ".contact-email",
            "[class*='email'] a", ".contact-details a[href^='mailto:']"
        ],
        
        # Detail page fields
        "Education1": [
            ".education li:nth-of-type(1)", ".bio-education li:first-child",
            "[class*='education'] ul li:first-child", ".credentials li:nth-of-type(1)"
        ],
        "Education2": [
            ".education li:nth-of-type(2)", ".bio-education li:nth-of-type(2)",
            "[class*='education'] ul li:nth-of-type(2)", ".credentials li:nth-of-type(2)"
        ],
        "PhoneNumber": [
            "a[href^='tel:']", ".phone", ".telephone",
            "[class*='phone']", ".contact-details a[href^='tel:']"
        ],
        "Creds": [
            ".bar-admissions", ".credentials", ".qualifications",
            "[class*='admission']", "[class*='credential']"
        ],
        "bio": [
            ".bio-content", ".biography", ".bio-text", ".lawyer-bio",
            "[class*='bio']:not(.bio-education)", ".overview"
        ]
    }
    
    # Check which patterns might work
    for field_name, patterns in common_patterns.items():
        suggestions["detail_page"][field_name] = patterns
    
    return suggestions


def fix_template_file(template_path: Path) -> bool:
    """Fix a single template file."""
    print(f"\n📄 Processing template: {template_path.name}")
    
    try:
        # Read template
        with open(template_path, 'r', encoding='utf-8') as f:
            template = json.load(f)
        
        modified = False
        
        # Fix list page rules
        if 'list_page_rules' in template and template['list_page_rules']:
            rules = template['list_page_rules']
            
            # Fix fields
            if 'fields' in rules:
                for field_name, selector in rules['fields'].items():
                    original = selector
                    fixed = fix_invalid_selectors(selector)
                    simplified = simplify_selector(fixed, field_name)
                    
                    if simplified != original:
                        rules['fields'][field_name] = simplified
                        print(f"  ✅ Fixed {field_name} selector")
                        print(f"     From: {original}")
                        print(f"     To:   {simplified}")
                        modified = True
            
            # Fix other selectors
            for key in ['repeating_item_selector', 'profile_link_selector']:
                if key in rules and rules[key]:
                    original = rules[key]
                    fixed = fix_invalid_selectors(rules[key])
                    if fixed != original:
                        rules[key] = fixed
                        print(f"  ✅ Fixed {key}")
                        modified = True
        
        # Fix detail page rules
        if 'detail_page_rules' in template and template['detail_page_rules']:
            rules = template['detail_page_rules']
            
            if 'fields' in rules:
                for field_name, selector in rules['fields'].items():
                    original = selector
                    fixed = fix_invalid_selectors(selector)
                    simplified = simplify_selector(fixed, field_name)
                    
                    if simplified != original:
                        rules['fields'][field_name] = simplified
                        print(f"  ✅ Fixed {field_name} selector")
                        print(f"     From: {original}")
                        print(f"     To:   {simplified}")
                        modified = True
        
        # Save if modified
        if modified:
            # Create backup
            backup_path = template_path.with_suffix('.json.backup')
            template_path.rename(backup_path)
            print(f"  💾 Created backup: {backup_path.name}")
            
            # Save fixed template
            with open(template_path, 'w', encoding='utf-8') as f:
                json.dump(template, f, indent=2, ensure_ascii=False)
            print(f"  ✅ Saved fixed template")
        else:
            print(f"  ℹ️  No invalid selectors found")
        
        # Show suggestions
        suggestions = suggest_better_selectors(template)
        if template.get('detail_page_rules', {}).get('fields'):
            print("\n  💡 Suggested alternative selectors for detail page:")
            for field, patterns in suggestions['detail_page'].items():
                if field in template['detail_page_rules']['fields']:
                    print(f"     {field}: {patterns[0]}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error processing template: {e}")
        return False


def add_fallback_selectors(template_path: Path):
    """Add fallback selectors to template for better reliability."""
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template = json.load(f)
        
        # Add a fallback_selectors section
        if 'detail_page_rules' in template:
            template['detail_page_rules']['fallback_selectors'] = {
                "education": [
                    ".education li",
                    ".bio-education li",
                    "[class*='education'] li",
                    ".credentials li",
                    ".qualifications li"
                ],
                "bar_admissions": [
                    ".bar-admissions",
                    ".admissions",
                    "[class*='admission']",
                    ".credentials:contains('Bar')",
                    ".qualifications:contains('admitted')"
                ],
                "phone": [
                    "a[href^='tel:']",
                    ".phone",
                    "[class*='phone']",
                    ".contact:contains('+')"
                ],
                "email": [
                    "a[href^='mailto:']",
                    ".email a",
                    "[class*='email'] a"
                ]
            }
            
            with open(template_path, 'w', encoding='utf-8') as f:
                json.dump(template, f, indent=2, ensure_ascii=False)
            
            print(f"  ✅ Added fallback selectors to template")
            
    except Exception as e:
        print(f"  ❌ Error adding fallback selectors: {e}")


def main():
    """Main function to fix all templates."""
    templates_dir = Path("templates")
    
    if not templates_dir.exists():
        print("❌ Templates directory not found!")
        print("Please run this script from the project root directory.")
        return
    
    template_files = list(templates_dir.glob("*.json"))
    
    if not template_files:
        print("❌ No template files found in templates directory.")
        return
    
    print(f"🔧 Found {len(template_files)} template file(s) to process\n")
    
    success_count = 0
    for template_path in template_files:
        if fix_template_file(template_path):
            success_count += 1
            
            # Optionally add fallback selectors
            add_fallback_selectors(template_path)
    
    print(f"\n✅ Successfully processed {success_count}/{len(template_files)} templates")
    
    # Additional recommendations
    print("\n📚 Additional Recommendations:")
    print("1. Use pattern-based extraction as primary method for detail pages")
    print("2. Keep selectors simple and semantic (use classes over complex paths)")
    print("3. Test with browser console: document.querySelector('your-selector')")
    print("4. Consider using data attributes for more reliable selection")


if __name__ == "__main__":
    main()