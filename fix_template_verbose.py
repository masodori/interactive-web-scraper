#!/usr/bin/env python
"""
Fix template selectors with verbose output and specific handling for complex selectors.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any
import sys


def fix_overly_complex_selectors(selector: str, field_name: str) -> str:
    """Fix overly complex selectors by simplifying them."""
    if not selector or len(selector) < 100:
        return selector
    
    # Remove trailing > if present
    selector = selector.strip().rstrip('>')
    
    # For Education and Credentials fields, use simpler patterns
    field_lower = field_name.lower()
    
    if 'education' in field_lower:
        # Try to find education-related classes in the complex selector
        if 'education' in selector.lower():
            # Extract the education-related part
            match = re.search(r'[\.#][\w-]*education[\w-]*', selector, re.IGNORECASE)
            if match:
                return match.group(0) + ' li'
        
        # Common education selectors
        return '.bio-education li, .education li, [class*="education"] li'
    
    elif 'credential' in field_lower or 'creds' in field_lower:
        # Try to find credential-related classes
        if any(term in selector.lower() for term in ['credential', 'admission', 'bar']):
            match = re.search(r'[\.#][\w-]*(credential|admission|bar)[\w-]*', selector, re.IGNORECASE)
            if match:
                return match.group(0)
        
        # Common credential selectors
        return '.credentials, .bar-admissions, [class*="credential"], [class*="admission"]'
    
    elif 'bio' in field_lower:
        return '.lawyer-bio, .bio-content, .biography, [class*="bio"]:not([class*="education"])'
    
    elif 'phone' in field_lower:
        return 'a[href^="tel:"], .phone, [class*="phone"]'
    
    elif 'email' in field_lower:
        return 'a[href^="mailto:"], .email a, [class*="email"] a'
    
    else:
        # Generic simplification - take the last meaningful part
        parts = selector.split(' > ')
        
        # Find the most specific part with a class or ID
        for part in reversed(parts):
            if '.' in part or '#' in part:
                return part
        
        # If no class/ID found, return the last part
        return parts[-1] if parts else selector


def process_template(template_path: Path) -> bool:
    """Process a single template file with verbose output."""
    print(f"\n🔧 Processing: {template_path.name}")
    print("="*60)
    
    try:
        # Read template
        with open(template_path, 'r', encoding='utf-8') as f:
            template = json.load(f)
            print(f"✅ Successfully loaded template")
    except Exception as e:
        print(f"❌ Failed to load template: {e}")
        return False
    
    modified = False
    fixes_made = []
    
    # Process detail page rules (where the complex selectors usually are)
    if 'detail_page_rules' in template and template['detail_page_rules']:
        rules = template['detail_page_rules']
        print(f"\n📋 Checking detail page rules...")
        
        if 'fields' in rules and rules['fields']:
            for field_name, selector in list(rules['fields'].items()):
                if selector:
                    original_length = len(selector)
                    
                    # Fix trailing >
                    if selector.strip().endswith('>'):
                        selector = selector.strip().rstrip('>')
                        fixes_made.append(f"Removed trailing '>' from {field_name}")
                        modified = True
                    
                    # Fix overly complex selectors
                    if original_length > 100:
                        new_selector = fix_overly_complex_selectors(selector, field_name)
                        if new_selector != selector:
                            fixes_made.append(
                                f"{field_name}: Simplified from {original_length} to {len(new_selector)} chars"
                            )
                            print(f"\n  🔄 {field_name}:")
                            print(f"     From: {selector[:60]}...")
                            print(f"     To:   {new_selector}")
                            rules['fields'][field_name] = new_selector
                            modified = True
                        else:
                            print(f"\n  ℹ️  {field_name}: Already optimized")
                    
                    # Remove empty selectors
                    if not selector.strip():
                        del rules['fields'][field_name]
                        fixes_made.append(f"Removed empty selector for {field_name}")
                        modified = True
    
    # Process list page rules
    if 'list_page_rules' in template and template['list_page_rules']:
        rules = template['list_page_rules']
        print(f"\n📋 Checking list page rules...")
        
        # Fix repeating item selector
        if 'repeating_item_selector' in rules and rules['repeating_item_selector']:
            selector = rules['repeating_item_selector']
            if selector.strip().endswith('>'):
                rules['repeating_item_selector'] = selector.strip().rstrip('>')
                fixes_made.append("Fixed repeating_item_selector")
                modified = True
    
    # Add fallback selectors for better extraction
    if modified and 'detail_page_rules' in template:
        print(f"\n📌 Adding fallback selectors...")
        template['detail_page_rules']['fallback_patterns'] = {
            "use_pattern_matching": True,
            "patterns": {
                "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                "phone": r'(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',
                "education": r'(?:J\.D\.|JD|LL\.M\.|LLM|B\.A\.|BA|B\.S\.|BS|M\.A\.|MA|Ph\.D\.|PhD)[^,\n]*(?:,\s*\d{4})?',
                "bar_admissions": r'(?:Bar Admissions?|Admitted to (?:Practice|Bar)|Licensed)[:\s]*[^.]+\.'
            }
        }
        fixes_made.append("Added pattern matching fallbacks")
    
    # Save if modified
    if modified:
        # Create backup
        backup_path = template_path.with_suffix('.json.backup')
        try:
            import shutil
            shutil.copy2(template_path, backup_path)
            print(f"\n💾 Created backup: {backup_path.name}")
        except Exception as e:
            print(f"\n⚠️  Could not create backup: {e}")
        
        # Save fixed template
        try:
            with open(template_path, 'w', encoding='utf-8') as f:
                json.dump(template, f, indent=2, ensure_ascii=False)
            print(f"✅ Saved fixed template")
            
            print(f"\n📝 Summary of fixes:")
            for fix in fixes_made:
                print(f"   • {fix}")
            
        except Exception as e:
            print(f"❌ Failed to save template: {e}")
            return False
    else:
        print(f"\n✅ No fixes needed - template is already optimized")
    
    # Show recommendations
    print(f"\n💡 Additional recommendations:")
    print(f"   • Use pattern matching as primary extraction method for detail pages")
    print(f"   • Test selectors in browser console before adding to template")
    print(f"   • Keep selectors as simple as possible")
    
    return True


def main():
    """Main function."""
    print("🔧 Template Selector Fixer")
    print("="*60)
    
    templates_dir = Path("templates")
    
    if not templates_dir.exists():
        print("❌ Templates directory not found!")
        print("   Please run from the project root directory")
        return 1
    
    # Check for specific template or process all
    if len(sys.argv) > 1:
        template_name = sys.argv[1]
        template_path = templates_dir / template_name
        if not template_path.exists():
            template_path = templates_dir / f"{template_name}.json"
        
        if template_path.exists():
            success = process_template(template_path)
            return 0 if success else 1
        else:
            print(f"❌ Template not found: {template_name}")
            return 1
    else:
        # Process all templates
        template_files = list(templates_dir.glob("*.json"))
        
        if not template_files:
            print("❌ No template files found!")
            return 1
        
        print(f"Found {len(template_files)} template(s)")
        
        success_count = 0
        for template_path in template_files:
            if process_template(template_path):
                success_count += 1
        
        print(f"\n{'='*60}")
        print(f"✅ Successfully processed {success_count}/{len(template_files)} templates")
        
        if success_count < len(template_files):
            return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())