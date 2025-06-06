#!/usr/bin/env python
"""
Script to fix encoding issues in template files.
Run this to convert template files to proper UTF-8 encoding.
"""

import json
import sys
from pathlib import Path


def fix_template_encoding(template_path):
    """Fix encoding issues in a template file."""
    print(f"Fixing template: {template_path}")
    
    # Try different encodings
    encodings = ['utf-8', 'cp1252', 'latin-1', 'iso-8859-1']
    
    data = None
    used_encoding = None
    
    # Try to read with different encodings
    for encoding in encodings:
        try:
            with open(template_path, 'r', encoding=encoding) as f:
                data = json.load(f)
            used_encoding = encoding
            print(f"Successfully read with {encoding} encoding")
            break
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            print(f"Failed with {encoding}: {e}")
            continue
    
    if data is None:
        print("ERROR: Could not read template file with any encoding")
        return False
    
    # Normalize Unicode characters in selectors
    def normalize_selectors(obj):
        if isinstance(obj, dict):
            return {k: normalize_selectors(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [normalize_selectors(item) for item in obj]
        elif isinstance(obj, str):
            # Replace various dash characters with standard hyphen
            replacements = {
                '\u2010': '-',  # Hyphen
                '\u2011': '-',  # Non-breaking hyphen
                '\u2012': '-',  # Figure dash
                '\u2013': '-',  # En dash
                '\u2014': '-',  # Em dash
                '\u2015': '-',  # Horizontal bar
                '\u2212': '-',  # Minus sign
                '\u2019': "'",  # Right single quotation mark
                '\u201c': '"',  # Left double quotation mark
                '\u201d': '"',  # Right double quotation mark
            }
            for old, new in replacements.items():
                obj = obj.replace(old, new)
            return obj
        return obj
    
    # Normalize the data
    normalized_data = normalize_selectors(data)
    
    # Create backup
    backup_path = template_path.with_suffix('.json.bak')
    template_path.rename(backup_path)
    print(f"Created backup: {backup_path}")
    
    # Write with UTF-8 encoding
    try:
        with open(template_path, 'w', encoding='utf-8') as f:
            json.dump(normalized_data, f, indent=2, ensure_ascii=False)
        print(f"Successfully wrote normalized template to: {template_path}")
        return True
    except Exception as e:
        print(f"ERROR writing file: {e}")
        # Restore backup
        backup_path.rename(template_path)
        print("Restored original file from backup")
        return False


def main():
    """Main function to fix template files."""
    if len(sys.argv) > 1:
        # Fix specific file
        template_path = Path(sys.argv[1])
        if not template_path.exists():
            print(f"ERROR: File not found: {template_path}")
            sys.exit(1)
        success = fix_template_encoding(template_path)
        sys.exit(0 if success else 1)
    else:
        # Fix all templates in the templates directory
        templates_dir = Path("templates")
        if not templates_dir.exists():
            print("ERROR: templates directory not found")
            print("Please run this script from the project root directory")
            sys.exit(1)
        
        template_files = list(templates_dir.glob("*.json"))
        if not template_files:
            print("No template files found")
            sys.exit(0)
        
        print(f"Found {len(template_files)} template files")
        for template_path in template_files:
            print("\n" + "="*50)
            fix_template_encoding(template_path)
        
        print("\n" + "="*50)
        print("Done! All templates have been processed.")


if __name__ == "__main__":
    main()