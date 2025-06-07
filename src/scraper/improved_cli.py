# src/scraper/improved_cli.py
"""
Improved Command-Line Interface with enhanced user experience.
"""

import argparse
import logging
import sys
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
import json

from .core.enhanced_template_scraper import EnhancedTemplateScraper
from .models import ExportFormat, ScrapingTemplate
from .utils.logging_config import setup_logging
from .utils.user_experience import UserExperience, ValidationHelper
from .config import Config
from colorama import Fore, Style


class ImprovedCLI:
    """Enhanced CLI with better user experience"""
    
    def __init__(self):
        self.ux = UserExperience()
        self.validator = ValidationHelper()
        self.config = Config
        self.first_time_user = self._check_first_time_user()
    
    def _check_first_time_user(self) -> bool:
        """Check if this is a first-time user"""
        config_file = Path.home() / '.interactive_scraper' / 'user_config.json'
        return not config_file.exists()
    
    def _save_user_preference(self, key: str, value: Any):
        """Save user preferences"""
        config_file = Path.home() / '.interactive_scraper' / 'user_config.json'
        config_file.parent.mkdir(exist_ok=True)
        
        config = {}
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
        
        config[key] = value
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def run(self):
        """Main entry point"""
        try:
            # Show welcome message for first-time users
            if self.first_time_user:
                self._show_welcome()
                self._save_user_preference('first_run_complete', True)
            
            while True:
                choice = self._show_main_menu()
                
                if choice == '1':
                    self._create_template()
                elif choice == '2':
                    self._apply_template()
                elif choice == '3':
                    self._batch_process()
                elif choice == '4':
                    self._view_templates()
                elif choice == '5':
                    self._show_tutorial()
                elif choice == '6':
                    self._show_common_issues()
                elif choice == '7':
                    self._show_settings()
                elif choice == '8':
                    if self.ux.confirm_action("Are you sure you want to exit?", default=True):
                        self.ux.print_success("Thank you for using Interactive Web Scraper! 👋")
                        break
                else:
                    self.ux.print_error("Invalid choice. Please try again.")
        
        except KeyboardInterrupt:
            print(f"\n\n{Fore.YELLOW}⚠️  Operation cancelled by user.{Style.RESET_ALL}")
            if self.ux.confirm_action("Exit the program?", default=True):
                print(f"\n{Fore.GREEN}👋 Goodbye!{Style.RESET_ALL}")
                sys.exit(0)
        except Exception as e:
            logging.error(f"Unexpected error: {e}", exc_info=True)
            self.ux.print_error(f"Unexpected error: {e}")
            self.ux.print_info("Check the log file for more details.")
    
    def _show_welcome(self):
        """Show welcome message for first-time users"""
        print("\n" + "=" * 70)
        print(f"{Fore.CYAN}{Style.BRIGHT}🎉 WELCOME TO INTERACTIVE WEB SCRAPER! 🎉{Style.RESET_ALL}")
        print("=" * 70)
        
        print("\nLooks like this is your first time using the tool!")
        print("Let me help you get started.\n")
        
        if self.ux.confirm_action("Would you like to see a quick tutorial?", default=True):
            self.ux.show_interactive_tutorial()
    
    def _show_main_menu(self) -> str:
        """Show enhanced main menu"""
        self.ux.print_header("INTERACTIVE WEB SCRAPER", "Extract data from any website", "🕷️")
        
        menu_items = [
            ("1", "🔧 Create a new scraping template", "Design a reusable template"),
            ("2", "📋 Apply an existing template", "Run a saved template"),
            ("3", "📦 Batch process templates", "Run multiple templates"),
            ("4", "📊 View existing templates", "List all saved templates"),
            ("5", "🎓 Interactive Tutorial", "Learn how to use the tool"),
            ("6", "🔧 Common Issues & Solutions", "Troubleshooting help"),
            ("7", "⚙️  Settings & Configuration", "Adjust tool settings"),
            ("8", "🚪 Exit", "Close the application")
        ]
        
        print("\nMain Menu:")
        for num, title, desc in menu_items:
            print(f"  {Fore.YELLOW}{num}{Style.RESET_ALL}. {title}")
            print(f"     {Fore.CYAN}{desc}{Style.RESET_ALL}")
        
        return input(f"\n{Fore.GREEN}Enter your choice (1-8): {Style.RESET_ALL}").strip()
    
    def _create_template(self):
        """Enhanced template creation workflow"""
        self.ux.print_header("CREATE SCRAPING TEMPLATE", "Step-by-step template creation")
        
        # Step 1: Get URL
        self.ux.print_step(1, 5, "Enter Target URL")
        url = self._get_valid_url()
        if not url:
            return
        
        # Step 2: Choose engine
        self.ux.print_step(2, 5, "Select Scraping Engine")
        self.ux.print_engine_comparison()
        
        engine = self._select_engine()
        if not engine:
            return
        
        # Create scraper with selected engine
        scraper = None
        try:
            self.ux.animate_loading(f"Initializing {engine} engine", 1.5)
            
            # Import the correct scraper based on engine
            if engine == 'selenium':
                from .core.enhanced_interactive_scraper import EnhancedInteractiveScraper
                scraper = EnhancedInteractiveScraper(headless=False)
            elif engine == 'playwright':
                # For now, use the same scraper but pass engine parameter
                from .core.enhanced_interactive_scraper import EnhancedInteractiveScraper
                scraper = EnhancedInteractiveScraper(headless=False)
                scraper.engine = 'playwright'
            else:  # requests
                from .core.enhanced_interactive_scraper import EnhancedInteractiveScraper
                scraper = EnhancedInteractiveScraper(headless=True)
                scraper.engine = 'requests'
            
            # Show engine-specific tips
            self._show_engine_tips(engine)
            
            # Let the enhanced scraper handle the rest of the template creation
            scraper.create_template()
            
        except ImportError as e:
            self.ux.print_error("Missing dependencies. Please install required packages.")
            if 'playwright' in str(e):
                print("\nTo install Playwright:")
                print(f"  {Fore.YELLOW}pip install playwright{Style.RESET_ALL}")
                print(f"  {Fore.YELLOW}playwright install{Style.RESET_ALL}")
        except Exception as e:
            self.ux.print_error(f"Failed to create template: {e}")
            self._suggest_recovery(e)
        finally:
            if scraper:
                scraper.close()
    
    def _get_valid_url(self) -> Optional[str]:
        """Get and validate URL with helpful feedback"""
        while True:
            url = input(f"\n{Fore.GREEN}Enter the URL to scrape: {Style.RESET_ALL}").strip()
            
            if not url:
                self.ux.print_error("URL cannot be empty")
                if not self.ux.confirm_action("Try again?", default=True):
                    return None
                continue
            
            # Validate URL
            is_valid, cleaned_url, error = self.validator.validate_url(url)
            
            if is_valid:
                self.ux.print_success(f"Valid URL: {cleaned_url}")
                return cleaned_url
            else:
                self.ux.print_error(error)
                self.ux.print_tip("Example: https://example.com/products")
                
                if not self.ux.confirm_action("Try again?", default=True):
                    return None
    
    def _select_engine(self) -> Optional[str]:
        """Enhanced engine selection with detailed help"""
        engines = {
            'selenium': 'Selenium - Reliable, full JavaScript support',
            'playwright': 'Playwright - Modern, fast, full JavaScript',
            'requests': 'Requests - Blazing fast, no JavaScript'
        }
        
        help_text = {
            'selenium': """
            Best for:
            • Most websites with JavaScript
            • Sites built with React, Vue, Angular
            • When you need maximum compatibility
            
            Limitations:
            • Slower than other options
            • Uses more memory
            """,
            'playwright': """
            Best for:
            • Modern web applications
            • When you need speed + JavaScript
            • Sites with complex interactions
            
            Limitations:
            • Requires separate installation
            • Newer technology (less tutorials)
            
            To install: pip install playwright && playwright install
            """,
            'requests': """
            Best for:
            • Simple HTML websites
            • Server-rendered content
            • When speed is critical
            • APIs returning HTML
            
            Limitations:
            • NO JavaScript support
            • Can't handle dynamic content
            • Manual selector entry only
            """
        }
        
        # Check Playwright availability
        try:
            import playwright
        except ImportError:
            engines['playwright'] += f" {Fore.RED}(NOT INSTALLED){Style.RESET_ALL}"
        
        choice = self.ux.get_choice_with_help(
            "Select scraping engine:",
            engines,
            help_text,
            default='selenium'
        )
        
        # Handle Playwright not installed
        if choice == 'playwright':
            try:
                import playwright
            except ImportError:
                self.ux.print_warning("Playwright is not installed!")
                print("\nTo install Playwright, run:")
                print(f"  {Fore.YELLOW}pip install playwright{Style.RESET_ALL}")
                print(f"  {Fore.YELLOW}playwright install{Style.RESET_ALL}")
                
                if self.ux.confirm_action("Choose a different engine?", default=True):
                    return self._select_engine()
                return None
        
        return choice
    
    def _show_engine_tips(self, engine: str):
        """Show engine-specific tips"""
        tips = {
            'selenium': [
                "The browser window will open (unless in headless mode)",
                "Wait for pages to fully load before selecting elements",
                "An overlay will appear for interactive selection"
            ],
            'playwright': [
                "Playwright is faster than Selenium",
                "Supports multiple browser types (Chromium, Firefox, WebKit)",
                "Great for modern single-page applications"
            ],
            'requests': [
                "You'll need to manually enter CSS selectors",
                "Open the site in your browser and use DevTools",
                "Right-click → Inspect → Copy selector"
            ]
        }
        
        if engine in tips:
            print(f"\n{Fore.CYAN}💡 Tips for {engine}:{Style.RESET_ALL}")
            for tip in tips[engine]:
                print(f"  • {tip}")
    
    def _apply_template(self):
        """Enhanced template application"""
        self.ux.print_header("APPLY TEMPLATE", "Run existing templates to extract data")
        
        # List available templates
        templates = list(self.config.TEMPLATES_DIR.glob("*.json"))
        if not templates:
            self.ux.print_warning("No templates found!")
            self.ux.print_tip("Create a template first using option 1")
            return
        
        # Show templates with details
        print("\nAvailable Templates:")
        for i, template_path in enumerate(templates, 1):
            try:
                with open(template_path, 'r') as f:
                    template_data = json.load(f)
                
                engine = template_data.get('engine', 'unknown')
                site = template_data.get('site_info', {}).get('url', 'unknown')
                scraping_type = template_data.get('scraping_type', 'unknown')
                
                print(f"\n{Fore.YELLOW}{i}{Style.RESET_ALL}. {template_path.name}")
                print(f"   Engine: {engine} | Type: {scraping_type}")
                print(f"   Site: {site}")
                
            except Exception:
                print(f"\n{Fore.YELLOW}{i}{Style.RESET_ALL}. {template_path.name}")
                print(f"   {Fore.RED}(Unable to read template details){Style.RESET_ALL}")
        
        # Select template
        try:
            choice = int(input(f"\n{Fore.GREEN}Select template number: {Style.RESET_ALL}"))
            if 1 <= choice <= len(templates):
                selected_template = templates[choice - 1]
            else:
                self.ux.print_error("Invalid selection")
                return
        except ValueError:
            self.ux.print_error("Please enter a number")
            return
        
        # Export format selection
        print("\nSelect export format(s):")
        formats = {
            '1': ('JSON', ExportFormat.JSON),
            '2': ('CSV', ExportFormat.CSV),
            '3': ('Excel', ExportFormat.XLSX),
            '4': ('HTML', ExportFormat.HTML)
        }
        
        for key, (name, _) in formats.items():
            print(f"  {Fore.YELLOW}{key}{Style.RESET_ALL}. {name}")
        
        format_input = input(f"\n{Fore.GREEN}Enter format numbers (comma-separated): {Style.RESET_ALL}")
        selected_formats = []
        
        for num in format_input.split(','):
            num = num.strip()
            if num in formats:
                selected_formats.append(formats[num][1])
        
        if not selected_formats:
            selected_formats = [ExportFormat.JSON]
            self.ux.print_info("No valid format selected, defaulting to JSON")
        
        # Apply template
        try:
            self.ux.animate_loading("Loading template", 1.0)
            
            # Load template to get engine
            with open(selected_template, 'r') as f:
                template_data = json.load(f)
            
            engine = template_data.get('engine', 'selenium')
            
            # Create scraper
            scraper = EnhancedTemplateScraper(
                engine=engine,
                headless=True,
                rate_limit_preset='respectful_bot'
            )
            
            self.ux.print_info(f"Applying template with {engine} engine...")
            
            # Apply template
            result = scraper.apply_template(
                str(selected_template),
                export_formats=selected_formats,
                auto_migrate=True
            )
            
            # Show results
            self._display_results(result)
            
        except Exception as e:
            self.ux.print_error(f"Failed to apply template: {e}")
            self._suggest_recovery(e)
        finally:
            if 'scraper' in locals():
                scraper.close()
    
    def _display_results(self, result):
        """Display scraping results"""
        print("\n" + "=" * 60)
        print(f"{Fore.CYAN}{Style.BRIGHT}📊 SCRAPING RESULTS{Style.RESET_ALL}")
        print("=" * 60)
        
        print(f"\nTemplate: {result.template_name}")
        print(f"Duration: {result.end_time}")
        print(f"Total items: {result.total_items}")
        print(f"Success rate: {result.success_rate():.1f}%")
        
        if result.errors:
            print(f"\n{Fore.YELLOW}Errors encountered:{Style.RESET_ALL}")
            for error in result.errors[:5]:  # Show first 5 errors
                print(f"  • {error}")
            
            if len(result.errors) > 5:
                print(f"  ... and {len(result.errors) - 5} more errors")
        
        print(f"\n{Fore.GREEN}✅ Data exported to: {self.config.OUTPUT_DIR}{Style.RESET_ALL}")
    
    def _suggest_recovery(self, error: Exception):
        """Suggest recovery actions based on error"""
        error_str = str(error).lower()
        
        print(f"\n{Fore.YELLOW}💡 Suggested actions:{Style.RESET_ALL}")
        
        if 'timeout' in error_str:
            print("• Increase timeout in settings")
            print("• Check your internet connection")
            print("• Try again with a different engine")
        elif 'selector' in error_str or 'element' in error_str:
            print("• Verify the website structure hasn't changed")
            print("• Try recreating the template")
            print("• Use more general selectors")
        elif 'permission' in error_str:
            print("• Check file/folder permissions")
            print("• Run as administrator (if needed)")
        elif 'connection' in error_str:
            print("• Check your internet connection")
            print("• Verify the website is accessible")
            print("• Check if you need to use a proxy")
        else:
            print("• Check the log file for detailed error information")
            print("• Try with a different engine")
            print("• Ensure all dependencies are installed")
    
    def _batch_process(self):
        """Batch process multiple templates"""
        self.ux.print_header("BATCH PROCESSING", "Run multiple templates at once")
        
        templates = list(self.config.TEMPLATES_DIR.glob("*.json"))
        if not templates:
            self.ux.print_warning("No templates found!")
            return
        
        # Let user select multiple templates
        print("\nAvailable Templates:")
        selected_templates = []
        
        for i, template_path in enumerate(templates, 1):
            print(f"{Fore.YELLOW}{i}{Style.RESET_ALL}. {template_path.name}")
        
        print(f"\n{Fore.CYAN}Enter template numbers to run (comma-separated):{Style.RESET_ALL}")
        print(f"Example: 1,3,5 or 'all' to run all templates")
        
        selection = input(f"{Fore.GREEN}Selection: {Style.RESET_ALL}").strip()
        
        if selection.lower() == 'all':
            selected_templates = templates
        else:
            try:
                indices = [int(x.strip()) - 1 for x in selection.split(',')]
                selected_templates = [templates[i] for i in indices if 0 <= i < len(templates)]
            except (ValueError, IndexError):
                self.ux.print_error("Invalid selection")
                return
        
        if not selected_templates:
            self.ux.print_warning("No templates selected")
            return
        
        # Export format selection
        formats = {
            'json': ExportFormat.JSON,
            'csv': ExportFormat.CSV,
            'xlsx': ExportFormat.XLSX,
            'html': ExportFormat.HTML
        }
        
        format_choice = self.ux.get_choice_with_help(
            "Select export format:",
            formats,
            default='json'
        )
        
        export_formats = [formats[format_choice]]
        
        # Process templates
        print(f"\n{Fore.CYAN}Processing {len(selected_templates)} templates...{Style.RESET_ALL}")
        
        results = []
        for i, template_path in enumerate(selected_templates, 1):
            print(f"\n[{i}/{len(selected_templates)}] Processing {template_path.name}...")
            
            try:
                # Load template to get engine
                with open(template_path, 'r') as f:
                    template_data = json.load(f)
                
                engine = template_data.get('engine', 'selenium')
                
                # Create scraper
                scraper = EnhancedTemplateScraper(
                    engine=engine,
                    headless=True,
                    rate_limit_preset='respectful_bot'
                )
                
                # Apply template
                result = scraper.apply_template(
                    str(template_path),
                    export_formats=export_formats,
                    auto_migrate=True
                )
                
                results.append((template_path.name, 'success', result))
                self.ux.print_success(f"Completed {template_path.name}")
                
            except Exception as e:
                results.append((template_path.name, 'failed', str(e)))
                self.ux.print_error(f"Failed {template_path.name}: {e}")
            finally:
                if 'scraper' in locals():
                    scraper.close()
        
        # Summary
        print("\n" + "=" * 60)
        print(f"{Fore.CYAN}{Style.BRIGHT}BATCH PROCESSING SUMMARY{Style.RESET_ALL}")
        print("=" * 60)
        
        successful = sum(1 for _, status, _ in results if status == 'success')
        failed = sum(1 for _, status, _ in results if status == 'failed')
        
        print(f"\nTotal templates: {len(results)}")
        print(f"{Fore.GREEN}Successful: {successful}{Style.RESET_ALL}")
        print(f"{Fore.RED}Failed: {failed}{Style.RESET_ALL}")
        
        if failed > 0:
            print(f"\n{Fore.YELLOW}Failed templates:{Style.RESET_ALL}")
            for name, status, error in results:
                if status == 'failed':
                    print(f"  • {name}: {error}")
    
    def _view_templates(self):
        """View and manage templates"""
        self.ux.print_header("TEMPLATE MANAGER", "View and manage your templates")
        
        templates = list(self.config.TEMPLATES_DIR.glob("*.json"))
        if not templates:
            self.ux.print_warning("No templates found!")
            return
        
        print(f"\nFound {len(templates)} template(s):\n")
        
        for template_path in templates:
            try:
                with open(template_path, 'r') as f:
                    template_data = json.load(f)
                
                print(f"{Fore.YELLOW}📄 {template_path.name}{Style.RESET_ALL}")
                print(f"   Engine: {template_data.get('engine', 'unknown')}")
                print(f"   Type: {template_data.get('scraping_type', 'unknown')}")
                print(f"   URL: {template_data.get('site_info', {}).get('url', 'unknown')}")
                print(f"   Created: {template_data.get('created_at', 'unknown')}")
                
                # Show field counts
                list_fields = len(template_data.get('list_page_rules', {}).get('fields', {}))
                detail_fields = len(template_data.get('detail_page_rules', {}).get('fields', {}))
                
                if list_fields > 0:
                    print(f"   List fields: {list_fields}")
                if detail_fields > 0:
                    print(f"   Detail fields: {detail_fields}")
                
                print()
                
            except Exception as e:
                print(f"{Fore.RED}   Error reading template: {e}{Style.RESET_ALL}\n")
    
    def _show_tutorial(self):
        """Show interactive tutorial"""
        self.ux.show_interactive_tutorial()
    
    def _show_common_issues(self):
        """Show common issues and solutions"""
        self.ux.show_common_issues()
        self.ux.print_selector_help()
    
    def _show_settings(self):
        """Show and manage settings"""
        self.ux.print_header("SETTINGS", "Configure application settings")
        
        print(f"\n{Fore.CYAN}📁 Directories:{Style.RESET_ALL}")
        print(f"  Templates: {self.config.TEMPLATES_DIR}")
        print(f"  Output: {self.config.OUTPUT_DIR}")
        print(f"  Logs: {self.config.LOGS_DIR}")
        
        print(f"\n{Fore.CYAN}⏱️  Timeouts:{Style.RESET_ALL}")
        print(f"  Default: {self.config.DEFAULT_TIMEOUT}s")
        print(f"  Page load: {self.config.PAGE_LOAD_TIMEOUT}s")
        
        print(f"\n{Fore.CYAN}🔧 Other Settings:{Style.RESET_ALL}")
        print(f"  Batch size: {self.config.BATCH_SIZE}")
        print(f"  Progress interval: {self.config.PROGRESS_LOG_INTERVAL}")
        
        print(f"\n{Fore.CYAN}🌐 Browser Settings:{Style.RESET_ALL}")
        print(f"  Headless mode: Enabled for template application")
        print(f"  User agent: Default browser agent")
        
        print(f"\n{Fore.CYAN}📊 Export Settings:{Style.RESET_ALL}")
        print(f"  Default format: JSON")
        print(f"  CSV delimiter: ,")
        print(f"  Excel styling: Enabled")
        
        # Tips
        print(f"\n{Fore.YELLOW}💡 Tips:{Style.RESET_ALL}")
        print("  • Templates are stored as JSON files")
        print("  • Output files include timestamps")
        print("  • Logs help debug scraping issues")
        print("  • Use headless=False for debugging")
    
    def _apply_template_direct(self, template_path: str, format_str: str):
        """Apply a template directly from command line"""
        try:
            # Validate template path
            template_file = Path(template_path)
            if not template_file.exists():
                # Try in templates directory
                template_file = self.config.TEMPLATES_DIR / template_path
                if not template_file.exists():
                    self.ux.print_error(f"Template not found: {template_path}")
                    return
            
            # Parse format
            try:
                export_format = ExportFormat.from_string(format_str)
            except ValueError:
                self.ux.print_error(f"Invalid format: {format_str}")
                print("Valid formats: json, csv, xlsx, html")
                return
            
            # Load template to get engine
            with open(template_file, 'r') as f:
                template_data = json.load(f)
            
            engine = template_data.get('engine', 'selenium')
            
            self.ux.print_info(f"Applying template: {template_file.name}")
            self.ux.print_info(f"Engine: {engine}")
            self.ux.print_info(f"Export format: {format_str}")
            
            # Create scraper and apply
            scraper = EnhancedTemplateScraper(
                engine=engine,
                headless=True,
                rate_limit_preset='respectful_bot'
            )
            
            result = scraper.apply_template(
                str(template_file),
                export_formats=[export_format],
                auto_migrate=True
            )
            
            # Show results
            self._display_results(result)
            
        except Exception as e:
            self.ux.print_error(f"Failed to apply template: {e}")
            self._suggest_recovery(e)
        finally:
            if 'scraper' in locals():
                scraper.close()


def main():
    """Main entry point for improved CLI"""
    try:
        # Setup logging
        setup_logging()
        
        # Ensure directories exist
        Config.ensure_directories()
        
        # Check if running with arguments (command mode)
        if len(sys.argv) > 1:
            # Parse command-line arguments
            parser = argparse.ArgumentParser(
                description="Interactive Web Scraper - Enhanced Edition",
                formatter_class=argparse.RawTextHelpFormatter
            )
            
            parser.add_argument(
                '--version', '-v',
                action='store_true',
                help='Show version information'
            )
            
            parser.add_argument(
                '--tutorial', '-t',
                action='store_true',
                help='Show interactive tutorial'
            )
            
            parser.add_argument(
                '--apply', '-a',
                metavar='TEMPLATE',
                help='Apply a template directly (e.g., --apply my_template.json)'
            )
            
            parser.add_argument(
                '--format', '-f',
                metavar='FORMAT',
                default='json',
                help='Export format when using --apply (json, csv, xlsx, html)'
            )
            
            args = parser.parse_args()
            
            if args.version:
                print("Interactive Web Scraper v2.0 - Enhanced Edition")
                return 0
            
            if args.tutorial:
                ux = UserExperience()
                ux.show_interactive_tutorial()
                return 0
            
            if args.apply:
                # Direct template application
                cli = ImprovedCLI()
                cli._apply_template_direct(args.apply, args.format)
                return 0
        
        # Run interactive mode
        cli = ImprovedCLI()
        cli.run()
        
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}⚠️  Program interrupted by user.{Style.RESET_ALL}")
        return 130
    except Exception as e:
        logging.error(f"Critical error: {e}", exc_info=True)
        print(f"\n{Fore.RED}❌ Critical error: {e}{Style.RESET_ALL}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())