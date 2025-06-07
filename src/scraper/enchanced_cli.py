# src/scraper/enhanced_cli.py
"""
Enhanced Command-Line Interface with all new features integrated.
This can replace the existing cli.py to add the new functionality.
"""

import argparse
import logging
import sys
import os
from pathlib import Path
from typing import Any, List, Optional, Tuple
import json

from .core import InteractiveScraper
from .core.enhanced_template_scraper import EnhancedTemplateScraper
from .models import ExportFormat, ScrapingTemplate
from .utils.logging_config import setup_logging
from .utils.template_migration import TemplateMigrationManager
from .config import Config
from .cli import InteractiveCLI, _run_create_safe


def _run_apply_enhanced(args: argparse.Namespace = None):
    """Enhanced apply command with new features"""
    cli = InteractiveCLI()
    
    # Get arguments
    if args:
        template_path = args.template
        engine = args.engine
        headless = args.headless
        export_formats = [ExportFormat(fmt) for fmt in args.export]
        rate_limit = args.rate_limit
        auto_migrate = not args.no_migrate
        use_patterns = not args.no_patterns
    else:
        # Interactive mode
        templates = list(Config.TEMPLATES_DIR.glob("*.json"))
        if not templates:
            print("\n❌ No templates found.")
            return
        
        selected = cli.select_from_list(
            templates,
            "Select template:",
            display_func=lambda t: t.name
        )
        
        if not selected:
            return
        
        template_path = selected[0]
        
        # Get options
        engine_choice = cli.select_from_list(
            ['selenium', 'requests', 'playwright'],
            "Select scraping engine:",
            display_func=lambda x: f"{x} - {'JavaScript support' if x != 'requests' else 'Fast, no JS'}"
        )
        engine = engine_choice[0] if engine_choice else 'selenium'
        
        headless = not cli.get_user_confirmation("Show browser window?", default=False)
        
        # Rate limiting
        rate_limit_choice = cli.select_from_list(
            ['respectful_bot', 'conservative', 'moderate', 'aggressive', 'none'],
            "Select rate limiting preset:",
            display_func=lambda x: x.replace('_', ' ').title()
        )
        rate_limit = rate_limit_choice[0] if rate_limit_choice else 'respectful_bot'
        
        # Features
        auto_migrate = cli.get_user_confirmation("Auto-migrate template if needed?", default=True)
        use_patterns = cli.get_user_confirmation("Enable pattern-based extraction?", default=True)
        
        # Export formats
        format_options = list(ExportFormat)
        selected_formats = cli.select_from_list(
            format_options,
            "Select export format(s):",
            display_func=lambda f: f.value.upper(),
            allow_multiple=True
        )
        export_formats = selected_formats if selected_formats else [ExportFormat.JSON]
    
    # Check Playwright installation
    if engine == 'playwright':
        try:
            import playwright
        except ImportError:
            print("\n❌ Playwright not installed. Install with:")
            print("   pip install playwright")
            print("   playwright install")
            return
    
    # Apply template with enhanced scraper
    print(f"\n🚀 Applying template with enhanced features:")
    print(f"   Template: {template_path.name}")
    print(f"   Engine: {engine}")
    print(f"   Rate limiting: {rate_limit}")
    print(f"   Pattern extraction: {'✅' if use_patterns else '❌'}")
    print(f"   Auto-migration: {'✅' if auto_migrate else '❌'}")
    
    scraper = None
    try:
        # Create enhanced scraper
        scraper = EnhancedTemplateScraper(
            engine=engine,
            headless=headless,
            rate_limit_preset=rate_limit if rate_limit != 'none' else None
        )
        
        # Apply template
        result = scraper.apply_template(
            str(template_path),
            export_formats=export_formats,
            auto_migrate=auto_migrate
        )
        
        # Display results
        print("\n" + "="*50)
        print("📊 Scraping Results")
        print("="*50)
        print(f"  Duration: {result.end_time}")
        print(f"  Total Items: {result.total_items}")
        print(f"  Success Rate: {result.success_rate():.1f}%")
        
        # Show rate limiting stats
        if rate_limit != 'none':
            stats = scraper.get_scraping_stats()
            if stats['rate_limiting']:
                print("\n⏱️  Rate Limiting Statistics:")
                for domain, domain_stats in stats['rate_limiting'].items():
                    print(f"  {domain}: {domain_stats['total_requests']} requests")
        
        print(f"\n✅ Data exported to: {Config.OUTPUT_DIR}")
        
    except Exception as e:
        logging.error(f"Failed to apply template: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
    finally:
        if scraper:
            scraper.close()


def _run_migrate(args: argparse.Namespace = None):
    """Run template migration command"""
    manager = TemplateMigrationManager()
    
    if args and hasattr(args, 'template'):
        # Migrate specific template
        template_path = Path(args.template)
        if not template_path.exists():
            print(f"❌ Template not found: {template_path}")
            return
        
        try:
            if manager.migrate_file(template_path):
                print(f"✅ Successfully migrated {template_path.name}")
            else:
                print(f"ℹ️  {template_path.name} is already up to date")
        except Exception as e:
            print(f"❌ Migration failed: {e}")
    else:
        # Migrate all templates
        print("🔄 Migrating all templates...")
        results = manager.migrate_directory(Config.TEMPLATES_DIR)
        
        migrated = sum(1 for v in results.values() if v)
        print(f"\n✅ Migration complete:")
        print(f"  Migrated: {migrated}")
        print(f"  Already up-to-date: {len(results) - migrated}")


def _run_test_patterns(args: argparse.Namespace = None):
    """Test pattern extraction on text"""
    from .extractors.pattern_extractor import PatternExtractor
    
    cli = InteractiveCLI()
    extractor = PatternExtractor()
    
    if args and hasattr(args, 'text'):
        text = args.text
    else:
        print("\n📝 Enter or paste text to extract patterns from:")
        print("(Press Ctrl+D or Ctrl+Z when done)")
        
        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            pass
        
        text = '\n'.join(lines)
    
    if not text:
        print("❌ No text provided")
        return
    
    # Extract all patterns
    print("\n🔍 Extracting patterns...")
    print("="*50)
    
    pattern_types = [
        'email', 'phone', 'phone_international', 'date', 
        'price', 'address', 'zip_code', 'education', 
        'bar_admission', 'social_media'
    ]
    
    found_any = False
    for pattern_type in pattern_types:
        values = extractor.extract_all(text, pattern_type)
        if values:
            found_any = True
            print(f"\n{pattern_type.upper().replace('_', ' ')}:")
            for value in values:
                print(f"  • {value}")
    
    if not found_any:
        print("\n❌ No patterns found in the text")


def _run_analyze_site(args: argparse.Namespace = None):
    """Analyze a website for optimal scraping strategy"""
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from .extractors.advanced_selectors import AdvancedSelectors
    
    cli = InteractiveCLI()
    
    if args and hasattr(args, 'url'):
        url = args.url
    else:
        url = input("\n🌐 Enter URL to analyze: ").strip()
    
    if not url:
        print("❌ No URL provided")
        return
    
    print(f"\n🔍 Analyzing {url}...")
    
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)
    
    try:
        driver.get(url)
        advanced = AdvancedSelectors(driver)
        
        # Analyze page structure
        print("\n📊 Page Analysis:")
        
        # Check for dynamic content
        initial_height = driver.execute_script("return document.body.scrollHeight")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        import time
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        
        has_infinite_scroll = new_height > initial_height
        print(f"  • Infinite scroll detected: {'Yes' if has_infinite_scroll else 'No'}")
        
        # Look for load more buttons
        load_more_patterns = advanced.find_by_text_content(
            "load more", 
            tag="button",
            fuzzy=True,
            min_similarity=0.7
        )
        print(f"  • Load more buttons found: {len(load_more_patterns)}")
        
        # Check for JavaScript frameworks
        js_frameworks = {
            'React': "return !!window.React",
            'Angular': "return !!window.angular",
            'Vue': "return !!window.Vue"
        }
        
        detected_frameworks = []
        for framework, check in js_frameworks.items():
            if driver.execute_script(check):
                detected_frameworks.append(framework)
        
        print(f"  • JavaScript frameworks: {', '.join(detected_frameworks) if detected_frameworks else 'None detected'}")
        
        # Recommend engine
        print("\n💡 Recommendations:")
        if detected_frameworks or has_infinite_scroll:
            print("  • Engine: Playwright or Selenium (JavaScript rendering needed)")
        else:
            print("  • Engine: Requests (faster, no JavaScript needed)")
        
        if has_infinite_scroll:
            print("  • Load strategy: Scroll")
        elif load_more_patterns:
            print("  • Load strategy: Button click")
        
        # Pattern detection potential
        body_text = driver.find_element(By.TAG_NAME, "body").text
        from .extractors.pattern_extractor import PatternExtractor
        extractor = PatternExtractor()
        
        pattern_counts = {}
        for pattern_type in ['email', 'phone', 'date', 'price']:
            count = len(extractor.extract_all(body_text, pattern_type))
            if count > 0:
                pattern_counts[pattern_type] = count
        
        if pattern_counts:
            print("\n🎯 Pattern extraction potential:")
            for pattern_type, count in pattern_counts.items():
                print(f"  • {pattern_type}: {count} found")
        
    finally:
        driver.quit()


def main():
    """Enhanced main entry point"""
    try:
        # Setup logging
        setup_logging()
        
        # Ensure directories exist
        Config.ensure_directories()
        
        # Create parser
        parser = argparse.ArgumentParser(
            description="Enhanced Interactive Web Scraper with advanced features",
            formatter_class=argparse.RawTextHelpFormatter
        )
        
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # Create command (unchanged)
        create_parser = subparsers.add_parser('create', help='Create a new scraping template')
        create_parser.set_defaults(func=_run_create_safe)
        
        # Apply command (enhanced)
        apply_parser = subparsers.add_parser('apply', help='Apply template with enhanced features')
        apply_parser.add_argument('template', type=Path, help='Template JSON file')
        apply_parser.add_argument('--engine', choices=['selenium', 'requests', 'playwright'], 
                                default='selenium', help='Scraping engine')
        apply_parser.add_argument('--headless', action='store_true', help='Run in headless mode')
        apply_parser.add_argument('--export', nargs='+', choices=[f.value for f in ExportFormat],
                                default=[ExportFormat.JSON.value], help='Export formats')
        apply_parser.add_argument('--rate-limit', choices=['respectful_bot', 'conservative', 
                                'moderate', 'aggressive', 'none'], default='respectful_bot',
                                help='Rate limiting preset')
        apply_parser.add_argument('--no-migrate', action='store_true', 
                                help='Disable automatic template migration')
        apply_parser.add_argument('--no-patterns', action='store_true',
                                help='Disable pattern-based extraction')
        apply_parser.set_defaults(func=_run_apply_enhanced)
        
        # Migrate command (new)
        migrate_parser = subparsers.add_parser('migrate', help='Migrate templates to latest version')
        migrate_parser.add_argument('template', type=Path, nargs='?', 
                                  help='Specific template to migrate (all if not specified)')
        migrate_parser.set_defaults(func=_run_migrate)
        
        # Test patterns command (new)
        patterns_parser = subparsers.add_parser('test-patterns', help='Test pattern extraction')
        patterns_parser.add_argument('--text', help='Text to extract from (interactive if not provided)')
        patterns_parser.set_defaults(func=_run_test_patterns)
        
        # Analyze command (new)
        analyze_parser = subparsers.add_parser('analyze', help='Analyze website for optimal strategy')
        analyze_parser.add_argument('url', nargs='?', help='URL to analyze')
        analyze_parser.set_defaults(func=_run_analyze_site)
        
        # Parse arguments
        args = parser.parse_args()
        
        if hasattr(args, 'func'):
            args.func(args)
        else:
            # No command - show enhanced interactive menu
            _run_enhanced_interactive_menu()
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Program interrupted by user.")
        return 130
    except Exception as e:
        logging.error(f"Critical error: {e}", exc_info=True)
        print(f"\n❌ Critical error: {e}")
        return 1
    
    return 0


def _run_enhanced_interactive_menu():
    """Enhanced interactive menu with new features"""
    cli = InteractiveCLI()
    
    while True:
        try:
            print("\n" + "="*50)
            print("🕷️  Enhanced Web Scraper v2.0")
            print("="*50)
            print("\n📋 Main Menu:")
            print("1. 🔧 Create scraping template")
            print("2. 🚀 Apply template (enhanced)")
            print("3. 🔄 Migrate templates")
            print("4. 🔍 Test pattern extraction")
            print("5. 📊 Analyze website")
            print("6. 📚 View documentation")
            print("7. ⚙️  Settings")
            print("8. 🚪 Exit")
            
            choice = input("\nSelect option (1-8): ").strip()
            
            if choice == '1':
                _run_create_safe()
            elif choice == '2':
                _run_apply_enhanced()
            elif choice == '3':
                _run_migrate()
            elif choice == '4':
                _run_test_patterns()
            elif choice == '5':
                _run_analyze_site()
            elif choice == '6':
                _show_documentation()
            elif choice == '7':
                _show_settings()
            elif choice == '8':
                if cli.get_user_confirmation("Exit the program?"):
                    print("\n👋 Goodbye!")
                    break
            else:
                print("❌ Invalid choice")
                
        except KeyboardInterrupt:
            print("\n\n⚠️  Operation cancelled.")
            if cli.get_user_confirmation("Exit the program?"):
                break


def _show_documentation():
    """Show feature documentation"""
    print("\n" + "="*50)
    print("📚 Enhanced Features Documentation")
    print("="*50)
    
    features = {
        "Pattern-Based Extraction": """
    Automatically extract common data types using regex patterns:
    • Emails, phone numbers, addresses
    • Dates, prices, zip codes
    • Education credentials, bar admissions
    • Custom patterns can be added
        """,
        "Playwright Engine": """
    Alternative to Selenium with better performance:
    • Faster page loading and interaction
    • Better JavaScript handling
    • Built-in wait strategies
    • Supports Chromium, Firefox, and WebKit
        """,
        "Rate Limiting": """
    Respectful scraping with configurable limits:
    • Requests per second/minute/hour
    • Burst support for occasional speedups
    • Per-domain tracking
    • Multiple presets available
        """,
        "Template Migration": """
    Automatic updates for old templates:
    • Preserves existing configurations
    • Adds new feature support
    • Creates backups before migration
    • Version tracking
        """,
        "Advanced Selectors": """
    Fallback strategies for robust scraping:
    • Text-based element finding
    • Proximity-based selection
    • Visual pattern matching
    • AI-powered similarity matching (optional)
        """
    }
    
    for feature, description in features.items():
        print(f"\n🔸 {feature}:")
        print(description)
    
    input("\nPress Enter to continue...")


def _show_settings():
    """Show and modify settings"""
    print("\n" + "="*50)
    print("⚙️  Settings")
    print("="*50)
    
    print(f"\n📁 Directories:")
    print(f"  Templates: {Config.TEMPLATES_DIR}")
    print(f"  Output: {Config.OUTPUT_DIR}")
    print(f"  Logs: {Config.LOGS_DIR}")
    
    print(f"\n⏱️  Timeouts:")
    print(f"  Default: {Config.DEFAULT_TIMEOUT}s")
    print(f"  Page load: {Config.PAGE_LOAD_TIMEOUT}s")
    
    print(f"\n📦 Batch Processing:")
    print(f"  Batch size: {Config.BATCH_SIZE}")
    print(f"  Progress interval: {Config.PROGRESS_LOG_INTERVAL}")
    
    input("\nPress Enter to continue...")


if __name__ == '__main__':
    sys.exit(main())