#!/usr/bin/env python
"""
migrate_templates.py - Migrate scraper templates to the latest version
"""

import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from src.scraper.utils.template_migration import TemplateMigrationManager
from src.scraper.config import Config


def display_migration_info(template_path: Path, current_version: str, target_version: str):
    """Display information about a template migration"""
    print(f"\n📄 Template: {template_path.name}")
    print(f"   Current version: {current_version}")
    print(f"   Target version: {target_version}")
    
    # Show what will be added/changed
    if current_version == "1.0" and target_version >= "2.0":
        print("\n   Changes to be applied:")
        print("   ✓ Add engine selection support")
        print("   ✓ Add pattern-based extraction")
        print("   ✓ Update load strategy configuration")
        print("   ✓ Remove deprecated max_scrolls and max_clicks")
    
    if current_version <= "2.0" and target_version >= "2.1":
        print("\n   Additional changes:")
        print("   ✓ Add rate limiting configuration")
        print("   ✓ Add fallback selector strategies")
        print("   ✓ Add advanced selector support")


def main():
    """Main migration function"""
    print("🔄 Template Migration Tool")
    print("=" * 50)
    
    # Initialize migration manager
    manager = TemplateMigrationManager()
    current_version = manager.get_current_version()
    
    print(f"\n📌 Latest template version: {current_version}")
    
    # Check for templates directory
    templates_dir = Config.TEMPLATES_DIR
    if not templates_dir.exists():
        print(f"\n❌ Templates directory not found: {templates_dir}")
        print("   Please ensure you're running this script from the project root.")
        return 1
    
    # Find all template files
    template_files = list(templates_dir.glob("*.json"))
    
    # Skip backup files
    template_files = [f for f in template_files if not f.name.endswith('.backup')]
    
    if not template_files:
        print("\n❌ No template files found.")
        return 0
    
    print(f"\n📁 Found {len(template_files)} template(s) in {templates_dir}")
    
    # Analyze templates
    needs_migration = []
    up_to_date = []
    errors = []
    
    for template_path in template_files:
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template = json.load(f)
            
            template_version = template.get('version', '1.0')
            
            if manager.needs_migration(template):
                needs_migration.append((template_path, template_version))
            else:
                up_to_date.append(template_path)
                
        except Exception as e:
            errors.append((template_path, str(e)))
    
    # Display analysis
    print("\n📊 Template Analysis:")
    print(f"   ✅ Up to date: {len(up_to_date)}")
    print(f"   🔄 Needs migration: {len(needs_migration)}")
    print(f"   ❌ Errors: {len(errors)}")
    
    if errors:
        print("\n⚠️  Templates with errors:")
        for path, error in errors:
            print(f"   - {path.name}: {error}")
    
    if not needs_migration:
        print("\n✅ All templates are up to date!")
        return 0
    
    # Show templates that need migration
    print("\n📋 Templates requiring migration:")
    for path, version in needs_migration:
        display_migration_info(path, version, current_version)
    
    # Ask for confirmation
    print("\n" + "=" * 50)
    response = input("\n🤔 Proceed with migration? (y/n) [y]: ").strip().lower()
    
    if response and response != 'y':
        print("\n❌ Migration cancelled.")
        return 0
    
    # Perform migrations
    print("\n🚀 Starting migration...")
    print("=" * 50)
    
    success_count = 0
    fail_count = 0
    
    for template_path, version in needs_migration:
        print(f"\n▶️  Migrating {template_path.name}...")
        
        try:
            # Create backup
            backup_path = template_path.with_suffix('.json.backup')
            if backup_path.exists():
                # Add timestamp to backup name
                import time
                timestamp = int(time.time())
                backup_path = template_path.with_name(f"{template_path.stem}.backup.{timestamp}.json")
            
            # Copy original to backup
            import shutil
            shutil.copy2(template_path, backup_path)
            print(f"   📋 Created backup: {backup_path.name}")
            
            # Perform migration
            if manager.migrate_file(template_path, create_backup=False):
                print(f"   ✅ Successfully migrated to version {current_version}")
                success_count += 1
            else:
                print(f"   ℹ️  Template already up to date")
                
        except Exception as e:
            print(f"   ❌ Migration failed: {e}")
            fail_count += 1
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Migration Summary:")
    print(f"   ✅ Successful: {success_count}")
    print(f"   ❌ Failed: {fail_count}")
    
    if success_count > 0:
        print("\n💡 Tips:")
        print("   - Backup files have been created with .backup extension")
        print("   - Test your migrated templates to ensure they work correctly")
        print("   - New features available:")
        print("     • Pattern-based extraction for emails, phones, etc.")
        print("     • Playwright engine for better JavaScript handling")
        print("     • Rate limiting to be respectful to websites")
        print("     • Advanced selector strategies for robust scraping")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())