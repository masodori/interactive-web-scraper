# src/scraper/unified_cli.py
"""
Unified Command-Line Interface for Interactive Web Scraper
Consolidates all functionality into a single, comprehensive CLI
"""

import argparse
import logging
import sys
import os
import time
import json
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from urllib.parse import urlparse

# Import core functionality
from .core.enhanced_template_scraper import EnhancedTemplateScraper
from .core.unified_interactive_scraper import UnifiedInteractiveScraper
from .models import ExportFormat, ScrapingTemplate, ScrapingType, SiteInfo, TemplateRules, LoadStrategyConfig
from .utils.logging_config import setup_logging
from .utils.user_experience import UserExperience, ValidationHelper
from .utils.rate_limiter import RATE_LIMIT_PRESETS
from .extractors.pattern_extractor import PatternExtractor
from .config import Config

# Colors for output
from colorama import Fore, Style, init
init(autoreset=True)


class UnifiedCLI:
    """
    Unified CLI that consolidates all interactive web scraper functionality
    """
    
    def __init__(self):
        self.ux = UserExperience()
        self.validator = ValidationHelper()
        self.config = Config
        self.pattern_extractor = PatternExtractor()
        self.first_time_user = self._check_first_time_user()
        
        # Initialize unified scraper as None - will be created when needed
        self.interactive_scraper = None
        self.current_engine = None
        
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
                    self._create_template_flow()
                elif choice == '2':
                    self._apply_template_flow()
                elif choice == '3':
                    self._batch_process_flow()
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
        finally:
            self._cleanup()

    def _cleanup(self):
        """Clean up resources"""
        if self.interactive_scraper:
            try:
                self.interactive_scraper.close()
            except:
                pass

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

    def _create_template_flow(self):
        """Unified template creation flow"""
        self.ux.print_header("CREATE SCRAPING TEMPLATE", "Interactive template creation")
        
        try:
            # Step 1: Get URL
            url = self._get_valid_url()
            if not url:
                return
            
            # Step 2: Choose engine
            engine = self._select_engine()
            if not engine:
                return
            
            # Step 3: Initialize scraper
            if not self._initialize_scraper(engine):
                return
            
            # Step 4: Navigate to URL
            if not self._navigate_to_url(url):
                return
            
            # Step 5: Handle cookies
            self._handle_cookies()
            
            # Step 6: Get scraping type
            scraping_type = self._select_scraping_type()
            if not scraping_type:
                return
            
            # Step 7: Configure rate limiting
            rate_limiting = self._configure_rate_limiting()
            
            # Step 8: Create template using appropriate method
            if engine == 'selenium' and scraping_type == ScrapingType.LIST_DETAIL:
                # Use specialized Selenium template creator for list+detail
                from .core.selenium_template_creator import SeleniumTemplateCreator
                creator = SeleniumTemplateCreator(self.interactive_scraper)
                template = creator.create_list_detail_template(url)
            else:
                # Use standard template creation
                template = self.interactive_scraper.create_template_from_interaction(url, scraping_type)
                
            if not template:
                self.ux.print_error("Failed to create template")
                return
            
            # Step 9: Configure advanced features
            template_dict = template.to_dict()
            template_dict['rate_limiting'] = rate_limiting
            
            # Pattern extraction
            pattern_config = self._configure_pattern_extraction()
            if pattern_config:
                template_dict['extraction_patterns'] = pattern_config
            
            # Fallback strategies
            fallback_config = self._configure_fallback_strategies()
            template_dict['fallback_strategies'] = fallback_config
            
            # Step 10: Save template
            self._save_template(template_dict, engine)
            
        except Exception as e:
            self.ux.print_error(f"Failed to create template: {e}")
            logging.error(f"Template creation error: {e}", exc_info=True)

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
                self.ux.print_error(f"Invalid URL: {error}")
                if not self.ux.confirm_action("Try again?", default=True):
                    return None

    def _select_engine(self) -> Optional[str]:
        """Select scraping engine with detailed explanations"""
        print(f"\n{Fore.CYAN}Select Scraping Engine:{Style.RESET_ALL}")
        print("=" * 40)
        
        # Show engine comparison
        self._show_engine_comparison()
        
        engines = {
            "selenium": "Selenium - Reliable, full JavaScript support",
            "playwright": "Playwright - Modern, fast, full JavaScript",
            "requests": "Requests - Blazing fast, no JavaScript"
        }
        
        # Check Playwright availability
        try:
            import playwright
            playwright_available = True
        except ImportError:
            playwright_available = False
            engines["playwright"] += " (NOT INSTALLED)"
        
        choice = self._get_choice_input(
            "Choose engine",
            engines,
            default="selenium"
        )
        
        if choice == "playwright" and not playwright_available:
            self.ux.print_error("Playwright is not installed.")
            print("\nTo install Playwright:")
            print(f"  {Fore.YELLOW}pip install playwright{Style.RESET_ALL}")
            print(f"  {Fore.YELLOW}playwright install{Style.RESET_ALL}")
            return None
        
        return choice

    def _show_engine_comparison(self):
        """Show detailed engine comparison"""
        print(f"\n{Fore.CYAN}Engine Comparison:{Style.RESET_ALL}")
        print("-" * 50)
        
        engines = [
            {
                "name": "Selenium",
                "speed": "★★☆☆☆",
                "best_for": "Complex sites with heavy JavaScript",
                "pros": ["Full JavaScript support", "Interactive element selection", "Handles dynamic content", "Most compatible"],
                "cons": ["Slower performance", "Higher resource usage"]
            },
            {
                "name": "Playwright", 
                "speed": "★★★★☆",
                "best_for": "Modern web apps, SPAs",
                "pros": ["Modern & fast", "Full JavaScript support", "Interactive selection", "Better performance than Selenium"],
                "cons": ["Requires separate installation", "Newer, less documentation"]
            },
            {
                "name": "Requests",
                "speed": "★★★★★", 
                "best_for": "Static HTML sites, APIs",
                "pros": ["Extremely fast", "Low resource usage", "No browser needed"],
                "cons": ["No JavaScript support", "Manual selector input only", "Can't handle dynamic content"]
            }
        ]
        
        for engine in engines:
            print(f"\n{Fore.YELLOW}{engine['name']}{Style.RESET_ALL}")
            print(f"Speed: {engine['speed']}")
            print(f"Best for: {engine['best_for']}")
            print("Pros:")
            for pro in engine['pros']:
                print(f"  ✓ {pro}")
            print("Cons:")
            for con in engine['cons']:
                print(f"  ✗ {con}")
            print("-" * 50)

    def _initialize_scraper(self, engine: str) -> bool:
        """Initialize the unified scraper for the selected engine"""
        try:
            self.ux.animate_loading(f"Initializing {engine} engine", 1.5)
            
            # Create unified interactive scraper
            self.interactive_scraper = UnifiedInteractiveScraper(engine=engine, headless=False)
            
            # Initialize the engine
            if not self.interactive_scraper.initialize():
                self.ux.print_error(f"Failed to initialize {engine} engine")
                return False
            
            self.current_engine = engine
            self.ux.print_success(f"{engine.title()} engine initialized successfully!")
            self._show_engine_tips(engine)
            return True
            
        except Exception as e:
            self.ux.print_error(f"Failed to initialize {engine} engine: {e}")
            return False

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
                "Best for static HTML sites",
                "Cannot handle JavaScript or dynamic content",
                "You'll need to provide CSS selectors manually"
            ]
        }
        
        print(f"\n{Fore.CYAN}💡 Tips for {engine}:{Style.RESET_ALL}")
        for tip in tips.get(engine, []):
            print(f"  • {tip}")

    def _navigate_to_url(self, url: str) -> bool:
        """Navigate to the target URL"""
        print(f"\n{Fore.CYAN}🌐 Navigating to {url}...{Style.RESET_ALL}")
        
        try:
            self.current_url = url  # Store for later use
            success = self.interactive_scraper.navigate_to(url)
            
            if success:
                self.ux.print_success("Page loaded successfully!")
                return True
            else:
                self.ux.print_error("Failed to load page")
                return False
                
        except Exception as e:
            self.ux.print_error(f"Navigation failed: {e}")
            return False

    def _handle_cookies(self):
        """Handle cookie consent banners"""
        if self.current_engine not in ['selenium', 'playwright']:
            return
        
        print(f"\n{Fore.CYAN}🍪 Checking for cookie banners...{Style.RESET_ALL}")
        
        cookie_selector = input("Enter custom cookie selector (or press Enter to auto-detect): ").strip()
        
        try:
            custom_selectors = [cookie_selector] if cookie_selector else None
            result = self.interactive_scraper.handle_cookies(custom_selectors)
            
            if result:
                self.ux.print_success("Cookie banner handled successfully")
            else:
                print("ℹ️  No cookie banner detected or handled")
                
        except Exception as e:
            logging.error(f"Cookie handling error: {e}")
            print("⚠️  Error handling cookies, continuing anyway...")

    def _select_scraping_type(self) -> Optional[ScrapingType]:
        """Select scraping type with better descriptions"""
        types = {
            "1": "List + Detail Pages - Extract from list, then follow links to detail pages",
            "2": "List Only - Extract data from list page only", 
            "3": "Single Page - Extract from current page only"
        }
        
        choice = self._get_choice_input(
            "📋 Select scraping type",
            types,
            default="1"
        )
        
        type_map = {
            "1": ScrapingType.LIST_DETAIL,
            "2": ScrapingType.LIST_ONLY,
            "3": ScrapingType.SINGLE_PAGE
        }
        
        return type_map.get(choice)

    def _configure_rate_limiting(self) -> Dict[str, Any]:
        """Configure rate limiting"""
        print(f"\n{Fore.CYAN}⏱️  Configure Rate Limiting:{Style.RESET_ALL}")
        print("=" * 40)
        
        presets = {
            "respectful_bot": "Respectful Bot - 0.2 req/sec, very slow but safe",
            "conservative": "Conservative - 0.5 req/sec, slow but respectful", 
            "moderate": "Moderate - 1 req/sec, balanced approach",
            "aggressive": "Aggressive - 5 req/sec, fast but may trigger blocks",
            "none": "No rate limiting - Maximum speed (not recommended)"
        }
        
        choice = self._get_choice_input(
            "Select rate limiting preset",
            presets,
            default="respectful_bot"
        )
        
        if choice == "none":
            return {"enabled": False}
        else:
            return {
                "enabled": True,
                "preset": choice
            }

    def _create_template_object(self, url: str, engine: str, scraping_type: ScrapingType) -> ScrapingTemplate:
        """Create the base template object"""
        site_info = SiteInfo(url=url)
        
        template = ScrapingTemplate(
            name="new_template",
            engine=engine,
            site_info=site_info,
            scraping_type=scraping_type,
            list_page_rules=(
                TemplateRules() if scraping_type != ScrapingType.SINGLE_PAGE else None
            ),
            detail_page_rules=TemplateRules(),
            version="2.1",
            created_at=datetime.now().isoformat()
        )
        
        return template

    def _configure_list_rules(self, template: ScrapingTemplate) -> bool:
        """Configure list page rules"""
        print(f"\n{Fore.CYAN}📋 List Page Configuration{Style.RESET_ALL}")
        print("=" * 40)
        
        rules = template.list_page_rules
        
        if self.current_engine in ['selenium', 'playwright']:
            return self._configure_list_rules_interactive(template)
        else:
            return self._configure_list_rules_manual(template)

    def _configure_list_rules_interactive(self, template: ScrapingTemplate) -> bool:
        """Configure list rules with interactive selection"""
        rules = template.list_page_rules
        
        # First, get the repeating item selector
        print("\n" + "="*50)
        print("🎯 STEP 1: Identify List Items")
        print("="*50)
        print("\nWe need to identify what represents each item in the list.")
        print("For example:")
        print("  • Attorney cards on a law firm directory")
        print("  • Product cards in an online store")
        print("  • Article items in a blog")
        
        print("\n" + Fore.YELLOW + "Options:" + Style.RESET_ALL)
        print("  1. Click to select (recommended) - Visual selection")
        print("  2. Enter CSS selector manually - If you know the selector")
        
        choice = input("\nChoose [1/2] (default: 1): ").strip() or "1"
        
        if choice == "2":
            # Manual entry
            print("\nCommon selectors:")
            print("  • .person-card")
            print("  • .attorney-item")
            print("  • article")
            print("  • li")
            print("  • .row")
            selector = input("\nEnter CSS selector: ").strip()
            if selector:
                rules.repeating_item_selector = selector
                self.ux.print_success(f"Using selector: {selector}")
            else:
                return False
        else:
            # Interactive selection
            print("\n" + Fore.CYAN + "Interactive Selection Mode" + Style.RESET_ALL)
            print("1. An overlay will appear on the page")
            print("2. Hover over items to see them highlighted in blue")
            print("3. Click on any item from the list")
            print("4. The tool will detect the pattern automatically")
            
            input("\n" + Fore.GREEN + "Press Enter when ready..." + Style.RESET_ALL)
            
            if not self._interactive_selector_detection(rules):
                return False
        
        # Configure fields within items
        print("\n" + "="*50)
        print("🔍 STEP 2: Select Fields to Extract")
        print("="*50)
        print("\nNow we need to select what data to extract from each item.")
        fields = self._configure_fields_interactive("list item")
        rules.fields = fields
        
        # Set profile link selector for list+detail
        if template.scraping_type == ScrapingType.LIST_DETAIL:
            print("\n" + "="*50)
            print("🔗 STEP 3: Detail Page Links")
            print("="*50)
            print("\nFor list+detail scraping, we need the link to each detail page.")
            print("This is typically an <a> tag within each list item.")
            
            link_selector = input("\nCSS selector for links (e.g., 'a', 'a.profile-link') [default: a]: ").strip() or "a"
            rules.profile_link_selector = link_selector
        
        # Configure load strategy
        print("\n" + "="*50)
        print("📄 STEP 4: Page Loading Strategy")
        print("="*50)
        load_strategy = self._configure_load_strategy()
        rules.load_strategy = LoadStrategyConfig(**load_strategy)
        
        return True

    def _interactive_selector_detection(self, rules: TemplateRules) -> bool:
        """Use interactive selection to detect repeating items"""
        print("\n🎯 IMPORTANT: Click on ONE INDIVIDUAL ITEM from the list")
        print("   Examples:")
        print("   • One person card (not the whole grid)")
        print("   • One product tile (not the container)")
        print("   • One article item (not the list)")
        print("\n⚠️  Make sure to click a specific item, not the container!")
        
        if not self.interactive_scraper.inject_interactive_selector("Click ONE item (e.g., one person card)"):
            self.ux.print_error("Failed to inject interactive selector")
            return False
        
        # Wait for selection
        selected_data = None
        for _ in range(30):  # 15 second timeout
            time.sleep(0.5)
            data = self.interactive_scraper.get_selected_element_data()
            if data:
                if data.get('done'):
                    break
                selected_data = data
                print(f"\n📍 Selected element: {data.get('selector', 'Unknown')}")
                selected_text = data.get('text', '')[:100]
                if selected_text:
                    print(f"   Text preview: '{selected_text}...'")
                break
        
        if not selected_data:
            self.ux.print_error("No element selected")
            return False
        
        # Process the selected selector
        item_selector = selected_data.get('selector', '')
        if item_selector:
            # Check if this looks like a container (common patterns)
            container_indicators = ['container', 'grid', 'list', 'wrapper', 'loading', 'results']
            might_be_container = any(indicator in item_selector.lower() for indicator in container_indicators)
            
            if might_be_container:
                print("\n⚠️  This might be a container, not an individual item!")
                print("   Selected:", item_selector)
                confirm = input("\nIs this correct? [y/N]: ").strip().lower()
                if confirm != 'y':
                    print("Please try again and select an individual item.")
                    return False
            
            # Try to generalize the selector
            parts = item_selector.split(' > ')
            if len(parts) > 1:
                container_selector = ' > '.join(parts[:-1])
                last_part = parts[-1]
                
                # Remove nth-of-type to make it match all items
                import re
                general_item_selector = re.sub(r':nth[-‐]of[-‐]type\(\d+\)', '', last_part)
                if not general_item_selector or general_item_selector.strip() == '':
                    general_item_selector = last_part.split(':')[0] if ':' in last_part else 'div'
                    print(f"\n⚠️  Selector seems too generic: '{general_item_selector}'")
                    
                # Always ask for confirmation/improvement
                print(f"\n📋 Generated repeating item selector: {general_item_selector}")
                print("   This will be used to find ALL similar items")
                better_selector = input("\nModify selector or press Enter to accept: ").strip()
                if better_selector:
                    general_item_selector = better_selector
                
                rules.container_selector = container_selector
                rules.repeating_item_selector = general_item_selector
                
                # Store the full selector for making relative selectors later
                self._last_item_selector = item_selector
                self._generalized_item_selector = general_item_selector
            else:
                rules.repeating_item_selector = item_selector
                self._last_item_selector = item_selector
                self._generalized_item_selector = item_selector
        
        print(f"\n✅ Configuration complete:")
        print(f"   Container: {getattr(rules, 'container_selector', None) or 'body'}")
        print(f"   Item selector: {rules.repeating_item_selector}")
        
        # Clean up selector overlay
        self._cleanup_interactive_selector()
        
        return True

    def _configure_fields_interactive(self, context: str) -> Dict[str, str]:
        """Configure fields using interactive selection"""
        fields = {}
        
        print(f"\n💡 Now click on elements WITHIN a single {context} to extract data")
        print("Click elements first, then I'll ask what to call them.")
        print("Click 'Done' when finished selecting fields.")
        
        # Provide site-specific hints if we detect certain URLs
        if hasattr(self, 'current_url') and self.current_url:
            if 'gibsondunn.com/people' in self.current_url:
                print("\n💡 For Gibson Dunn attorney cards, try clicking:")
                print("   • Attorney name")
                print("   • Title/position") 
                print("   • Office location")
                print("   • Practice areas")
                print("   • Email/phone if visible")
        
        print()
        
        field_count = 0
        while True:
            field_count += 1
            
            # Let user select an element
            if not self.interactive_scraper.inject_interactive_selector(f"Click field #{field_count} or Done"):
                break
            
            # Wait for selection
            field_data = None
            for _ in range(60):  # 30 second timeout
                time.sleep(0.5)
                data = self.interactive_scraper.get_selected_element_data()
                if data:
                    field_data = data
                    break
            
            if not field_data:
                print("⚠️  No selection made")
                break
                
            if field_data.get('done') or field_data == 'DONE_SELECTING':
                print("✅ Done selecting fields")
                break
            
            # Get the selector
            selector = field_data.get('selector', '')
            if not selector:
                continue
            
            # Make selector relative to the repeating item if possible
            original_selector = selector
            if hasattr(self, '_last_item_selector') and self._last_item_selector:
                # Try to make it relative to the actual clicked item
                relative_selector = self._make_selector_relative(selector, self._last_item_selector)
                
                # If we have a generalized selector, adjust for that too
                if hasattr(self, '_generalized_item_selector'):
                    # The relative selector should work from the generalized item
                    selector = relative_selector
                    print(f"📍 Selected element within item: {relative_selector}")
                else:
                    if relative_selector != selector:
                        selector = relative_selector
                        print(f"📍 Relative to item: {relative_selector}")
                    else:
                        print(f"📍 Selected: {selector}")
            else:
                print(f"📍 Selected: {selector}")
            
            # Show what was selected
            selected_text = field_data.get('text', '')[:50]
            if selected_text:
                print(f"   Text: '{selected_text}...'")
            
            # Ask what to call this field
            print("\nWhat is this field?")
            print("Common options: name, title, email, phone, location, department, bio")
            field_name = input("Field name (or press Enter to skip): ").strip()
            
            if field_name:
                fields[field_name] = selector
                print(f"✅ Saved as '{field_name}'")
            else:
                print("⚠️  Skipped this selection")
            
            print("-" * 40)
        
        # Clean up selector overlay
        self._cleanup_interactive_selector()
        
        if not fields:
            print("\n⚠️  No fields configured!")
        else:
            print(f"\n✅ Configured {len(fields)} fields:")
            for name, sel in fields.items():
                print(f"   • {name}: {sel}")
        
        return fields
    
    def _make_selector_relative(self, field_selector: str, item_selector: str) -> str:
        """Make a field selector relative to the repeating item selector"""
        # If the field selector already looks relative, return as-is
        if field_selector.startswith('.') or field_selector.startswith('#') or '>' not in field_selector:
            return field_selector
        
        # Split both selectors into parts
        field_parts = [p.strip() for p in field_selector.split('>')]
        item_parts = [p.strip() for p in item_selector.split('>')]
        
        # Find where they diverge
        common_length = 0
        for i in range(min(len(field_parts), len(item_parts))):
            if field_parts[i] == item_parts[i]:
                common_length = i + 1
            else:
                break
        
        # If the field is within the item, make it relative
        if common_length >= len(item_parts) - 1:
            # Get the parts after the item selector
            relative_parts = field_parts[common_length:]
            if relative_parts:
                return ' > '.join(relative_parts)
        
        # If we can't make it relative, try a simpler approach
        # Just get the last meaningful part
        last_part = field_parts[-1] if field_parts else field_selector
        
        # Clean up nth-of-type if it's there
        import re
        last_part = re.sub(r':nth-of-type\(\d+\)', '', last_part)
        
        return last_part.strip() or field_selector

    def _configure_list_rules_manual(self, template: ScrapingTemplate) -> bool:
        """Configure list rules manually for requests engine"""
        rules = template.list_page_rules
        
        print("\n📝 Manual Configuration (Requests Engine)")
        
        # Repeating item selector
        selector = input("Enter CSS selector for repeating items (e.g., '.person-card'): ").strip()
        if not selector:
            return False
        rules.repeating_item_selector = selector
        
        # Fields
        fields = {}
        print("\n📝 Define fields to extract from each item:")
        while True:
            field_name = input("Field name (or Enter to finish): ").strip()
            if not field_name:
                break
            
            field_selector = input(f"CSS selector for {field_name}: ").strip()
            if field_selector:
                fields[field_name] = field_selector
        
        rules.fields = fields
        
        # Profile link for list+detail
        if template.scraping_type == ScrapingType.LIST_DETAIL:
            link_selector = input("CSS selector for detail page link: ").strip()
            if link_selector:
                rules.profile_link_selector = link_selector
        
        # Load strategy
        load_strategy = self._configure_load_strategy()
        rules.load_strategy = LoadStrategyConfig(**load_strategy)
        
        return True

    def _configure_detail_rules(self, template: ScrapingTemplate) -> bool:
        """Configure detail page rules"""
        print(f"\n{Fore.CYAN}📄 Detail Page Configuration{Style.RESET_ALL}")
        print("=" * 40)
        
        rules = template.detail_page_rules
        
        # Navigate to detail page if needed
        if template.scraping_type == ScrapingType.LIST_DETAIL:
            print("\n📄 Please navigate to a detail/article page first")
            print("(You can click on any link from the list page)")
            
            if self.current_engine in ['selenium', 'playwright']:
                print("\n🧹 Cleaning up selector overlay to allow normal navigation...")
                self._cleanup_interactive_selector()
            
            input("Press Enter when you're on a detail page...")
        
        # Configure fields
        if self.current_engine in ['selenium', 'playwright']:
            fields = self._configure_fields_interactive("detail page")
        else:
            fields = self._configure_fields_manual("detail page")
        
        rules.fields = fields
        
        return True

    def _configure_fields_manual(self, context: str) -> Dict[str, str]:
        """Configure fields manually"""
        fields = {}
        print(f"\n📝 Define fields to extract from {context}:")
        
        while True:
            field_name = input("Field name (or Enter to finish): ").strip()
            if not field_name:
                break
            
            field_selector = input(f"CSS selector for {field_name}: ").strip()
            if field_selector:
                fields[field_name] = field_selector
        
        return fields

    def _configure_load_strategy(self) -> Dict[str, Any]:
        """Configure load strategy"""
        print(f"\n{Fore.CYAN}📄 Load Strategy Configuration:{Style.RESET_ALL}")
        
        strategies = {
            "auto": "Auto-detect (try to find load more buttons)",
            "button": "Click a specific button",
            "scroll": "Infinite scroll",
            "pagination": "Traditional pagination (next button)",
            "none": "No dynamic loading"
        }
        
        strategy_type = self._get_choice_input(
            "How does the site load more content?",
            strategies,
            default="auto"
        )
        
        config = {
            "type": strategy_type,
            "pause_time": 2.0,
            "consecutive_failure_limit": 3,
            "extended_wait_multiplier": 2.0
        }
        
        if strategy_type == "button":
            selector = input("Enter CSS selector for load more button: ").strip()
            if selector:
                config["button_selector"] = selector
        elif strategy_type == "pagination":
            selector = input("Enter CSS selector for next page button: ").strip()
            if selector:
                config["pagination_next_selector"] = selector
        
        return config

    def _configure_pattern_extraction(self) -> Optional[Dict[str, Any]]:
        """Configure pattern-based extraction"""
        print(f"\n{Fore.CYAN}🔍 Configure Pattern-Based Extraction:{Style.RESET_ALL}")
        print("=" * 40)
        print("Pattern extraction can automatically find common data types without selectors.")
        
        enable = self._get_choice_input(
            "Enable pattern-based extraction?",
            {"y": "Yes (Recommended)", "n": "No"},
            default="y"
        )
        
        if enable != "y":
            return None
        
        patterns = {}
        available_patterns = {
            "email": "Email addresses",
            "phone": "Phone numbers (US format)",
            "phone_international": "International phone numbers",
            "date": "Dates in various formats",
            "price": "Prices with currency symbols",
            "address": "Street addresses",
            "education": "Education credentials (JD, MBA, etc.)",
            "bar_admission": "Bar admissions and licenses"
        }
        
        print("\nSelect patterns to enable:")
        for pattern, description in available_patterns.items():
            enable = self._get_choice_input(
                f"  Enable {pattern} extraction ({description})?",
                {"y": "Yes", "n": "No"},
                default="y" if pattern in ["email", "phone", "education"] else "n"
            )
            
            if enable == "y":
                patterns[pattern] = {
                    "enabled": True,
                    "context_keywords": self.pattern_extractor.patterns[pattern].context_keywords
                }
        
        return patterns if patterns else None

    def _configure_fallback_strategies(self) -> Dict[str, Any]:
        """Configure fallback selector strategies"""
        print(f"\n{Fore.CYAN}🛡️  Configure Fallback Strategies:{Style.RESET_ALL}")
        print("=" * 40)
        print("Fallback strategies help find elements when primary selectors fail.")
        
        strategies = {
            "text_based_selection": "Find elements by their text content",
            "proximity_selection": "Find elements near labels",
            "pattern_matching_primary": "Use pattern extraction as primary method"
        }
        
        config = {}
        for strategy, description in strategies.items():
            enable = self._get_choice_input(
                f"Enable {description}?",
                {"y": "Yes", "n": "No"},
                default="y"
            )
            config[strategy] = (enable == "y")
        
        return config

    def _save_template(self, template_dict: Dict[str, Any], engine: str):
        """Save the template to file"""
        print(f"\n{Fore.CYAN}💾 Save Template{Style.RESET_ALL}")
        
        template_name = input("💾 Enter template name (letters, numbers, underscores only): ").strip()
        if not template_name:
            template_name = "my_template"
        
        # Clean template name
        template_name = template_name.replace(" ", "_").replace("-", "_")
        template_dict['name'] = f"{template_name}_{engine}"
        
        template_path = self.config.TEMPLATES_DIR / f"{template_dict['name']}.json"
        
        # Check if file exists
        if template_path.exists():
            overwrite = self._get_choice_input(
                f"Template '{template_name}' already exists. Overwrite?",
                {"y": "Yes", "n": "No"},
                default="n"
            )
            if overwrite != "y":
                new_name = input("Enter new template name: ").strip()
                if new_name:
                    template_dict['name'] = f"{new_name}_{engine}"
                    template_path = self.config.TEMPLATES_DIR / f"{template_dict['name']}.json"
        
        # Save template
        try:
            with open(template_path, 'w', encoding='utf-8') as f:
                json.dump(template_dict, f, indent=2, ensure_ascii=False)
            
            self.ux.print_success(f"Template saved successfully to: {template_path}")
            self._display_template_summary(template_dict)
            print(f"\n{Fore.GREEN}🎉 Template creation complete!{Style.RESET_ALL}")
            
        except Exception as e:
            logging.error(f"Failed to save template: {e}")
            self.ux.print_error(f"Failed to save template: {e}")

    def _display_template_summary(self, template: Dict[str, Any]):
        """Display comprehensive template summary"""
        print(f"\n{Fore.CYAN}📊 Template Summary:{Style.RESET_ALL}")
        print("=" * 40)
        print(f"  - Name: {template['name']}")
        print(f"  - Version: {template.get('version', '1.0')}")
        print(f"  - Engine: {template.get('engine', 'selenium')}")
        print(f"  - Type: {template['scraping_type']}")
        
        if template.get('list_page_rules'):
            rules = template['list_page_rules']
            print(f"  - List fields: {len(rules.get('fields', {}))}")
            print(f"  - Load strategy: {rules.get('load_strategy', {}).get('type', 'none')}")
        
        if template.get('detail_page_rules'):
            rules = template['detail_page_rules']
            print(f"  - Detail fields: {len(rules.get('fields', {}))}")
        
        if template.get('extraction_patterns'):
            print(f"  - Pattern extraction: {len(template['extraction_patterns'])} patterns enabled")
        
        if template.get('rate_limiting', {}).get('enabled'):
            print(f"  - Rate limiting: {template['rate_limiting']['preset']}")

    def _cleanup_interactive_selector(self):
        """Clean up interactive selector overlay"""
        if self.current_engine not in ['selenium', 'playwright']:
            return
        
        try:
            # Use the unified scraper's cleanup method
            self.interactive_scraper.cleanup_interactive_selector()
                
        except Exception as e:
            logging.error(f"Failed to cleanup interactive selector: {e}")

    def _apply_template_flow(self):
        """Apply existing template flow"""
        self.ux.print_header("APPLY TEMPLATE", "Run existing templates to extract data")
        
        # List available templates
        templates = self._list_templates()
        if not templates:
            self.ux.print_error("No templates found!")
            return
        
        # Select template
        print("Available Templates:\n")
        for i, template_info in enumerate(templates, 1):
            print(f"{i}. {template_info['file']}")
            print(f"   Engine: {template_info['engine']} | Type: {template_info['type']}")
            print(f"   Site: {template_info['url']}\n")
        
        try:
            choice = int(input("Select template number: ")) - 1
            if choice < 0 or choice >= len(templates):
                self.ux.print_error("Invalid template selection")
                return
                
            selected_template = templates[choice]
            
        except ValueError:
            self.ux.print_error("Invalid input")
            return
        
        # Select export formats
        export_formats = self._select_export_formats()
        
        # Run template
        self._run_template(selected_template['path'], export_formats)

    def _list_templates(self) -> List[Dict[str, Any]]:
        """List all available templates"""
        templates = []
        templates_dir = self.config.TEMPLATES_DIR
        
        if not templates_dir.exists():
            return templates
        
        for template_file in templates_dir.glob("*.json"):
            try:
                with open(template_file, 'r') as f:
                    template_data = json.load(f)
                
                templates.append({
                    'file': template_file.name,
                    'path': str(template_file),
                    'engine': template_data.get('engine', 'unknown'),
                    'type': template_data.get('scraping_type', 'unknown'),
                    'url': template_data.get('site_info', {}).get('url', 'unknown')
                })
                
            except Exception as e:
                logging.error(f"Error reading template {template_file}: {e}")
                continue
        
        return templates

    def _select_export_formats(self) -> List[ExportFormat]:
        """Select export formats"""
        formats = {
            "1": ("JSON", ExportFormat.JSON),
            "2": ("CSV", ExportFormat.CSV),
            "3": ("Excel", ExportFormat.EXCEL),
            "4": ("HTML", ExportFormat.HTML)
        }
        
        print("Select export format(s):")
        for key, (name, _) in formats.items():
            print(f"  {key}. {name}")
        
        choices = input("Enter format numbers (comma-separated): ").strip().split(',')
        
        selected_formats = []
        for choice in choices:
            choice = choice.strip()
            if choice in formats:
                selected_formats.append(formats[choice][1])
        
        return selected_formats if selected_formats else [ExportFormat.JSON]

    def _run_template(self, template_path: str, export_formats: List[ExportFormat]):
        """Run a template and export results"""
        try:
            self.ux.print_success("Loading template - Done!")
            
            # Create enhanced template scraper
            scraper = EnhancedTemplateScraper()
            
            # Apply template
            print("ℹ️  Applying template...")
            result = scraper.apply_template(template_path, export_formats)
            
            # Display results
            self._display_scraping_results(result)
            
            scraper.close()
            
        except Exception as e:
            self.ux.print_error(f"Error running template: {e}")
            logging.error(f"Template execution error: {e}", exc_info=True)

    def _display_scraping_results(self, result):
        """Display scraping results"""
        print(f"\n{Fore.CYAN}📊 SCRAPING RESULTS{Style.RESET_ALL}")
        print("=" * 60)
        
        print(f"Template: {result.template_name}")
        print(f"Duration: {result.end_time}")
        print(f"Total items: {result.total_items}")
        
        success_rate = (result.successful_items / result.total_items * 100) if result.total_items > 0 else 0
        print(f"Success rate: {success_rate:.1f}%")
        
        if result.errors:
            print(f"\nErrors encountered:")
            for error in result.errors[:5]:  # Show first 5 errors
                print(f"  • {error}")
        
        print(f"\n✅ Data exported to: {self.config.OUTPUT_DIR}")

    def _batch_process_flow(self):
        """Batch process multiple templates"""
        self.ux.print_header("BATCH PROCESS", "Run multiple templates")
        
        templates = self._list_templates()
        if not templates:
            self.ux.print_error("No templates found!")
            return
        
        print("Available templates:")
        for i, template_info in enumerate(templates, 1):
            print(f"  {i}. {template_info['file']}")
        
        selected_indices = input("\nEnter template numbers to run (comma-separated, or 'all'): ").strip()
        
        if selected_indices.lower() == 'all':
            selected_templates = templates
        else:
            try:
                indices = [int(x.strip()) - 1 for x in selected_indices.split(',')]
                selected_templates = [templates[i] for i in indices if 0 <= i < len(templates)]
            except ValueError:
                self.ux.print_error("Invalid input")
                return
        
        export_formats = self._select_export_formats()
        
        # Run each template
        for template_info in selected_templates:
            print(f"\n{Fore.YELLOW}Running: {template_info['file']}{Style.RESET_ALL}")
            self._run_template(template_info['path'], export_formats)

    def _view_templates(self):
        """View existing templates"""
        self.ux.print_header("VIEW TEMPLATES", "List all saved templates")
        
        templates = self._list_templates()
        if not templates:
            self.ux.print_error("No templates found!")
            return
        
        print(f"Found {len(templates)} template(s):\n")
        
        for template_info in templates:
            print(f"📋 {template_info['file']}")
            print(f"   Engine: {template_info['engine']}")
            print(f"   Type: {template_info['type']}")
            print(f"   URL: {template_info['url']}")
            print()

    def _show_tutorial(self):
        """Show interactive tutorial"""
        self.ux.show_interactive_tutorial()

    def _show_common_issues(self):
        """Show common issues and solutions"""
        self.ux.print_header("COMMON ISSUES & SOLUTIONS", "Troubleshooting help")
        
        issues = [
            {
                "issue": "Page not loading",
                "solutions": [
                    "Check internet connection",
                    "Try different browser engine",
                    "Disable headless mode to see what's happening",
                    "Check if site blocks automation"
                ]
            },
            {
                "issue": "Elements not found",
                "solutions": [
                    "Wait longer for page to load",
                    "Use more specific CSS selectors",
                    "Check if elements are in iframes",
                    "Try different selector strategies"
                ]
            },
            {
                "issue": "JavaScript not working",
                "solutions": [
                    "Use Selenium or Playwright instead of Requests",
                    "Wait for dynamic content to load",
                    "Check browser console for errors"
                ]
            }
        ]
        
        for issue_data in issues:
            print(f"\n{Fore.YELLOW}Issue: {issue_data['issue']}{Style.RESET_ALL}")
            print("Solutions:")
            for solution in issue_data['solutions']:
                print(f"  • {solution}")

    def _show_settings(self):
        """Show settings and configuration"""
        self.ux.print_header("SETTINGS & CONFIGURATION", "Adjust tool settings")
        
        print("Current Configuration:")
        print(f"  • Templates Directory: {self.config.TEMPLATES_DIR}")
        print(f"  • Output Directory: {self.config.OUTPUT_DIR}")
        print(f"  • Logs Directory: {self.config.LOGS_DIR}")
        print(f"  • Default Timeout: {self.config.DEFAULT_TIMEOUT}s")
        
        print("\nTo modify settings, edit the configuration files or environment variables.")

    def _get_choice_input(self, prompt: str, options: Dict[str, str], default: str = None) -> Optional[str]:
        """Get user choice from options"""
        print(f"\n{prompt}")
        for key, desc in options.items():
            print(f"  {key}: {desc}")
        
        if default:
            choice = input(f"Choose [{'/'.join(options.keys())}] (default: {default}): ").strip()
            return choice if choice else default
        else:
            choice = input(f"Choose [{'/'.join(options.keys())}]: ").strip()
            return choice if choice in options else None


def main():
    """Main entry point"""
    # Set up logging
    setup_logging()
    
    # Handle command line arguments
    parser = argparse.ArgumentParser(description="Interactive Web Scraper - Unified CLI")
    parser.add_argument("--version", action="version", version="2.1.0")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run the CLI
    cli = UnifiedCLI()
    cli.run()


if __name__ == "__main__":
    main()