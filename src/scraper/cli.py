# src/scraper/cli.py
"""
Enhanced Command-Line Interface with comprehensive error handling
for the Interactive Web Scraper.
"""

import argparse
import logging
import sys
import os
from pathlib import Path
from typing import Any, List, Optional, Tuple
import json

from .core import InteractiveScraper, TemplateScraper
from .models import ExportFormat, ScrapingTemplate
from .utils.logging_config import setup_logging
from .config import Config


class CLIError(Exception):
    """Custom exception for CLI errors"""
    pass


class InteractiveCLI:
    """Enhanced CLI with robust error handling"""
    
    def __init__(self):
        self.config = Config
        self.logger = logging.getLogger(__name__)
    
    def validate_template_file(self, template_path: Path) -> Tuple[bool, str]:
        """
        Validate template file exists and is valid JSON.
        
        Args:
            template_path: Path to template file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not template_path.exists():
            return False, f"Template file not found: {template_path}"
        
        if not template_path.is_file():
            return False, f"Template path is not a file: {template_path}"
        
        if template_path.suffix != '.json':
            return False, f"Template file must be a JSON file (got {template_path.suffix})"
        
        # Try to load and validate JSON
        try:
            with open(template_path, 'r') as f:
                data = json.load(f)
            
            # Basic validation of required fields
            required_fields = ['name', 'site_info', 'scraping_type']
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                return False, f"Template missing required fields: {', '.join(missing_fields)}"
            
            # Try to load as ScrapingTemplate
            template = ScrapingTemplate.from_dict(data)
            
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON in template file: {e}"
        except Exception as e:
            return False, f"Invalid template format: {e}"
        
        return True, ""
    
    def get_user_confirmation(
        self, 
        prompt: str, 
        default: bool = True,
        max_attempts: int = 3
    ) -> Optional[bool]:
        """
        Get yes/no confirmation from user with error handling.
        
        Args:
            prompt: Prompt message
            default: Default value if Enter pressed
            max_attempts: Maximum attempts
            
        Returns:
            True/False or None if failed
        """
        default_str = "Y/n" if default else "y/N"
        attempts = 0
        
        while attempts < max_attempts:
            try:
                response = input(f"\n{prompt} [{default_str}]: ").strip().lower()
                
                if not response:
                    return default
                
                if response in ['y', 'yes', '1', 'true']:
                    return True
                elif response in ['n', 'no', '0', 'false']:
                    return False
                else:
                    print("❌ Please enter 'y' for yes or 'n' for no.")
                    attempts += 1
                    
            except KeyboardInterrupt:
                print("\n⚠️  Operation cancelled.")
                return None
            except EOFError:
                return None
            except Exception as e:
                self.logger.error(f"Error getting confirmation: {e}")
                attempts += 1
        
        print(f"❌ Maximum attempts ({max_attempts}) exceeded.")
        return None
    
    def select_from_list(
        self,
        items: List[Any],
        prompt: str,
        display_func: callable = str,
        allow_multiple: bool = False,
        max_attempts: int = 3
    ) -> Optional[List[Any]]:
        """
        Select one or more items from a list with error handling.
        
        Args:
            items: List of items to choose from
            prompt: Prompt message
            display_func: Function to display items
            allow_multiple: Allow multiple selections
            max_attempts: Maximum attempts
            
        Returns:
            Selected item(s) or None
        """
        if not items:
            print("❌ No items to select from.")
            return None
        
        print(f"\n{prompt}")
        for i, item in enumerate(items, 1):
            print(f"  {i}) {display_func(item)}")
        
        if allow_multiple:
            print("\nEnter numbers separated by commas (e.g., 1,3,5)")
            print("Or enter 'all' to select all items")
        
        attempts = 0
        while attempts < max_attempts:
            try:
                if allow_multiple:
                    response = input("\nSelect items: ").strip()
                else:
                    response = input("\nSelect item: ").strip()
                
                if not response:
                    print("❌ No selection made.")
                    attempts += 1
                    continue
                
                if allow_multiple and response.lower() == 'all':
                    return items
                
                # Parse selection(s)
                if allow_multiple:
                    indices = []
                    for part in response.split(','):
                        try:
                            idx = int(part.strip()) - 1
                            if 0 <= idx < len(items):
                                indices.append(idx)
                            else:
                                print(f"❌ Invalid number: {part.strip()} (out of range)")
                                raise ValueError
                        except ValueError:
                            print(f"❌ Invalid input: {part.strip()}")
                            raise
                    
                    return [items[i] for i in indices]
                else:
                    idx = int(response) - 1
                    if 0 <= idx < len(items):
                        return [items[idx]]
                    else:
                        print(f"❌ Please enter a number between 1 and {len(items)}")
                        attempts += 1
                        
            except KeyboardInterrupt:
                print("\n⚠️  Selection cancelled.")
                return None
            except ValueError:
                print("❌ Please enter valid number(s).")
                attempts += 1
            except Exception as e:
                self.logger.error(f"Error in selection: {e}")
                attempts += 1
        
        print(f"❌ Maximum attempts ({max_attempts}) exceeded.")
        return None


def _run_create_safe(args: argparse.Namespace = None):
    """Safely run template creation with error handling."""
    cli = InteractiveCLI()
    
    try:
        print("\n🚀 Starting Interactive Template Creation")
        print("="*50)
        
        # Check if Chrome/Chromium is available
        try:
            from selenium import webdriver
            test_options = webdriver.ChromeOptions()
            test_options.add_argument('--headless')
            test_driver = webdriver.Chrome(options=test_options)
            test_driver.quit()
        except Exception as e:
            print("❌ Chrome/Chromium browser not found or not properly configured.")
            print("   Please ensure Chrome is installed and ChromeDriver is available.")
            print(f"   Error: {e}")
            return
        
        # Create interactive scraper
        scraper = None
        try:
            scraper = InteractiveScraper()
            scraper.create_template()
        except KeyboardInterrupt:
            print("\n⚠️  Template creation cancelled by user.")
        except Exception as e:
            logging.error(f"Failed to create template: {e}", exc_info=True)
            print(f"\n❌ Failed to create template: {e}")
            
            if cli.get_user_confirmation("View detailed error log?", default=False):
                print(f"\nCheck log file at: {Config.LOGS_DIR / 'scraper.log'}")
        finally:
            if scraper:
                try:
                    scraper.close()
                except:
                    pass
                    
    except Exception as e:
        logging.error(f"Critical error in template creation: {e}", exc_info=True)
        print(f"\n❌ Critical error: {e}")


def _run_apply_safe(args: argparse.Namespace = None):
    """Safely run template application with error handling."""
    cli = InteractiveCLI()
    
    # Get template path
    if args and hasattr(args, 'template'):
        template_path = args.template
        headless = args.headless if hasattr(args, 'headless') else True
        export_formats = [ExportFormat(fmt) for fmt in (args.export if hasattr(args, 'export') else ['json'])]
    else:
        # Interactive mode
        templates = list(Config.TEMPLATES_DIR.glob("*.json"))
        
        if not templates:
            print("\n❌ No templates found in the templates directory.")
            print(f"   Directory: {Config.TEMPLATES_DIR}")
            
            if cli.get_user_confirmation("Create a new template?"):
                _run_create_safe()
            return
        
        # Select template
        selected = cli.select_from_list(
            templates,
            "Available templates:",
            display_func=lambda t: f"{t.name} (modified: {t.stat().st_mtime})"
        )
        
        if not selected:
            return
        
        template_path = selected[0]
        
        # Get options
        headless = not cli.get_user_confirmation("Show browser window?", default=False)
        
        # Select export formats
        format_options = list(ExportFormat)
        selected_formats = cli.select_from_list(
            format_options,
            "Select export format(s):",
            display_func=lambda f: f.value.upper(),
            allow_multiple=True
        )
        
        export_formats = selected_formats if selected_formats else [ExportFormat.JSON]
    
    # Validate template
    is_valid, error_msg = cli.validate_template_file(template_path)
    if not is_valid:
        print(f"\n❌ Invalid template: {error_msg}")
        return
    
    print(f"\n📋 Applying template: {template_path.name}")
    print(f"🎯 Export formats: {[f.value for f in export_formats]}")
    print(f"👁️  Headless mode: {'Yes' if headless else 'No'}")
    
    # Apply template
    scraper = None
    try:
        scraper = TemplateScraper(headless=headless)
        result = scraper.apply_template(str(template_path), export_formats)
        
        # Display results
        print("\n" + "="*50)
        print("📊 Scraping Results")
        print("="*50)
        print(f"  Template:       {result.template_name}")
        print(f"  Duration:       {result.end_time}")
        print(f"  Total Items:    {result.total_items}")
        print(f"  Successful:     {result.successful_items} ✅")
        print(f"  Failed:         {result.failed_items} ❌")
        print(f"  Success Rate:   {result.success_rate():.1f}%")
        
        if result.errors:
            print(f"\n⚠️  General Errors ({len(result.errors)}):")
            for i, error in enumerate(result.errors[:5], 1):
                print(f"  {i}. {error}")
            if len(result.errors) > 5:
                print(f"  ... and {len(result.errors) - 5} more errors")
        
        print(f"\n✅ Data exported to: {Config.OUTPUT_DIR}")
        
        # Offer to view sample data
        if result.items and cli.get_user_confirmation("View sample data?", default=False):
            print("\n📄 Sample Data (first item):")
            first_item = result.items[0]
            print(json.dumps(first_item.to_dict(), indent=2))
            
    except KeyboardInterrupt:
        print("\n⚠️  Scraping cancelled by user.")
    except Exception as e:
        logging.error(f"Failed to apply template: {e}", exc_info=True)
        print(f"\n❌ Failed to apply template: {e}")
        
        if cli.get_user_confirmation("View detailed error log?", default=False):
            print(f"\nCheck log file at: {Config.LOGS_DIR / 'scraper.log'}")
    finally:
        if scraper:
            try:
                scraper.close()
            except:
                pass


def _run_batch_safe(args: argparse.Namespace = None):
    """Safely run batch processing with error handling."""
    cli = InteractiveCLI()
    
    templates_dir = args.templates_dir if args and hasattr(args, 'templates_dir') else Config.TEMPLATES_DIR
    headless = args.headless if args and hasattr(args, 'headless') else True
    
    if not templates_dir.exists():
        print(f"\n❌ Templates directory not found: {templates_dir}")
        return
    
    templates = list(templates_dir.glob("*.json"))
    
    if not templates:
        print(f"\n❌ No templates found in {templates_dir}")
        return
    
    # Validate all templates first
    valid_templates = []
    for template_path in templates:
        is_valid, error_msg = cli.validate_template_file(template_path)
        if is_valid:
            valid_templates.append(template_path)
        else:
            print(f"⚠️  Skipping invalid template {template_path.name}: {error_msg}")
    
    if not valid_templates:
        print("\n❌ No valid templates found.")
        return
    
    print(f"\n📋 Found {len(valid_templates)} valid template(s)")
    
    if not cli.get_user_confirmation(f"Process all {len(valid_templates)} templates?"):
        # Allow selecting specific templates
        selected = cli.select_from_list(
            valid_templates,
            "Select templates to process:",
            display_func=lambda t: t.name,
            allow_multiple=True
        )
        
        if not selected:
            return
        
        valid_templates = selected
    
    print(f"\n🚀 Starting batch process for {len(valid_templates)} template(s)...")
    print(f"👁️  Headless mode: {'Yes' if headless else 'No'}")
    
    results = []
    scraper = None
    
    try:
        scraper = TemplateScraper(headless=headless)
        
        for i, template_path in enumerate(valid_templates, 1):
            print(f"\n{'='*50}")
            print(f"📄 Processing template {i}/{len(valid_templates)}: {template_path.name}")
            print('='*50)
            
            try:
                result = scraper.apply_template(str(template_path), [ExportFormat.JSON])
                results.append({
                    'template': template_path.name,
                    'success': True,
                    'items': result.total_items,
                    'success_rate': result.success_rate()
                })
                print(f"✅ Completed: {result.total_items} items, {result.success_rate():.1f}% success rate")
                
            except Exception as e:
                logging.error(f"Failed to process {template_path.name}: {e}")
                results.append({
                    'template': template_path.name,
                    'success': False,
                    'error': str(e)
                })
                print(f"❌ Failed: {e}")
                
                if i < len(valid_templates):
                    if not cli.get_user_confirmation("Continue with remaining templates?"):
                        break
        
        # Display summary
        print("\n" + "="*50)
        print("📊 Batch Processing Summary")
        print("="*50)
        
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        
        print(f"  Total Templates:  {len(results)}")
        print(f"  Successful:       {successful} ✅")
        print(f"  Failed:           {failed} ❌")
        
        if successful > 0:
            total_items = sum(r.get('items', 0) for r in results if r['success'])
            avg_success_rate = sum(r.get('success_rate', 0) for r in results if r['success']) / successful
            
            print(f"  Total Items:      {total_items}")
            print(f"  Avg Success Rate: {avg_success_rate:.1f}%")
        
        if failed > 0:
            print("\n❌ Failed Templates:")
            for r in results:
                if not r['success']:
                    print(f"  - {r['template']}: {r.get('error', 'Unknown error')}")
                    
    except KeyboardInterrupt:
        print("\n⚠️  Batch processing cancelled by user.")
    except Exception as e:
        logging.error(f"Critical error in batch processing: {e}", exc_info=True)
        print(f"\n❌ Critical error: {e}")
    finally:
        if scraper:
            try:
                scraper.close()
            except:
                pass
    
    print(f"\n✅ Batch processing complete. Results saved to: {Config.OUTPUT_DIR}")


def _run_interactive_menu_safe():
    """Run interactive menu with comprehensive error handling."""
    cli = InteractiveCLI()
    
    while True:
        try:
            print("\n" + "="*50)
            print("🕷️  Interactive Web Scraper")
            print("="*50)
            print("\n1. 🔧 Create a new scraping template")
            print("2. 📋 Apply an existing template")
            print("3. 📦 Batch process templates")
            print("4. 📊 View existing templates")
            print("5. ⚙️  Configuration info")
            print("6. 🚪 Exit")
            
            choice = input("\nEnter your choice (1-6): ").strip()
            
            if choice == '1':
                _run_create_safe()
                
            elif choice == '2':
                _run_apply_safe()
                
            elif choice == '3':
                _run_batch_safe(None)
                
            elif choice == '4':
                # View templates
                templates = list(Config.TEMPLATES_DIR.glob("*.json"))
                if not templates:
                    print("\n❌ No templates found.")
                else:
                    print(f"\n📁 Templates directory: {Config.TEMPLATES_DIR}")
                    print(f"📋 Found {len(templates)} template(s):\n")
                    
                    for template_path in templates:
                        try:
                            with open(template_path, 'r') as f:
                                data = json.load(f)
                            
                            print(f"  • {template_path.name}")
                            print(f"    - URL: {data.get('site_info', {}).get('url', 'N/A')}")
                            print(f"    - Type: {data.get('scraping_type', 'N/A')}")
                            print(f"    - Created: {data.get('created_at', 'N/A')[:10]}")
                            
                        except Exception as e:
                            print(f"  • {template_path.name} (⚠️  Error reading template)")
                
                input("\nPress Enter to continue...")
                
            elif choice == '5':
                # Show configuration
                print("\n⚙️  Configuration Information")
                print("="*40)
                print(f"  Base Directory:     {Config.BASE_DIR}")
                print(f"  Templates:          {Config.TEMPLATES_DIR}")
                print(f"  Output:             {Config.OUTPUT_DIR}")
                print(f"  Logs:               {Config.LOGS_DIR}")
                print(f"  Default Timeout:    {Config.DEFAULT_TIMEOUT}s")
                print(f"  Batch Size:         {Config.BATCH_SIZE} items")
                print(f"  Chrome Headless:    Available")
                
                # Check directories
                print("\n📁 Directory Status:")
                for name, path in [
                    ("Templates", Config.TEMPLATES_DIR),
                    ("Output", Config.OUTPUT_DIR),
                    ("Logs", Config.LOGS_DIR),
                    ("Assets", Config.ASSETS_DIR)
                ]:
                    exists = "✅" if path.exists() else "❌"
                    print(f"  {name}: {exists}")
                
                input("\nPress Enter to continue...")
                
            elif choice == '6':
                if cli.get_user_confirmation("Are you sure you want to exit?"):
                    print("\n👋 Goodbye!")
                    break
                    
            else:
                print("\n❌ Invalid choice. Please enter a number between 1 and 6.")
                
        except KeyboardInterrupt:
            print("\n\n⚠️  Operation cancelled.")
            if cli.get_user_confirmation("Exit the program?"):
                print("\n👋 Goodbye!")
                break
        except Exception as e:
            logging.error(f"Error in menu: {e}", exc_info=True)
            print(f"\n❌ An error occurred: {e}")
            
            if cli.get_user_confirmation("Continue?", default=True):
                continue
            else:
                break


def main():
    """Enhanced main entry point with error handling."""
    try:
        # Setup logging
        setup_logging()
        
        # Ensure directories exist
        try:
            Config.ensure_directories()
        except Exception as e:
            print(f"❌ Failed to create required directories: {e}")
            print(f"   Please check permissions for: {Config.BASE_DIR}")
            return 1
        
        # Parse arguments or run interactive menu
        if len(sys.argv) == 1:
            _run_interactive_menu_safe()
        else:
            parser = argparse.ArgumentParser(
                description="Interactive Web Scraper - Create templates by clicking on web elements",
                formatter_class=argparse.RawTextHelpFormatter
            )
            
            subparsers = parser.add_subparsers(dest='command', help='Available commands')
            
            # Create command
            create_parser = subparsers.add_parser(
                'create', 
                help='Create a new scraping template interactively'
            )
            create_parser.set_defaults(func=_run_create_safe)
            
            # Apply command
            apply_parser = subparsers.add_parser(
                'apply', 
                help='Apply an existing template to scrape data'
            )
            apply_parser.add_argument(
                'template', 
                type=Path, 
                help='Path to the template JSON file'
            )
            apply_parser.add_argument(
                '--headless', 
                action='store_true', 
                help='Run browser in headless mode (no window)'
            )
            apply_parser.add_argument(
                '--export',
                nargs='+',
                choices=[f.value for f in ExportFormat],
                default=[ExportFormat.JSON.value],
                help='Export format(s) for scraped data (default: json)'
            )
            apply_parser.set_defaults(func=_run_apply_safe)
            
            # Batch command
            batch_parser = subparsers.add_parser(
                'batch', 
                help='Process multiple templates in batch'
            )
            batch_parser.add_argument(
                '--templates-dir',
                type=Path,
                default=Config.TEMPLATES_DIR,
                help=f'Directory containing templates (default: {Config.TEMPLATES_DIR})'
            )
            batch_parser.add_argument(
                '--headless', 
                action='store_true', 
                help='Run browser in headless mode'
            )
            batch_parser.set_defaults(func=_run_batch_safe)
            
            # Parse and execute
            args = parser.parse_args()
            
            if hasattr(args, 'func'):
                args.func(args)
            else:
                parser.print_help()
                
    except KeyboardInterrupt:
        print("\n\n⚠️  Program interrupted by user.")
        return 130  # Standard exit code for Ctrl+C
    except Exception as e:
        logging.error(f"Critical error in main: {e}", exc_info=True)
        print(f"\n❌ Critical error: {e}")
        print(f"   Check log file at: {Config.LOGS_DIR / 'scraper.log'}")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())