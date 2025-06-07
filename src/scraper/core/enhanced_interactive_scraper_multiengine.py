# src/scraper/core/enhanced_interactive_scraper_multiengine.py
"""
Enhanced Interactive Scraper with true multi-engine support.
This version properly supports Selenium, Playwright, and Requests engines.
"""

import time
from typing import Optional, Dict, Any
from urllib.parse import urlparse
from datetime import datetime

from .multi_engine_scraper import MultiEngineScraper
from ..models import (
    ScrapingTemplate,
    SiteInfo,
    ScrapingType,
    TemplateRules,
    LoadStrategyConfig,
)
from ..utils.input_validators import InputValidator, PromptFormatter
from ..extractors.pattern_extractor import PatternExtractor


class EnhancedInteractiveScraperMultiEngine(MultiEngineScraper):
    """Enhanced interactive scraper with proper multi-engine support"""

    def __init__(self, engine: str = "selenium", headless: bool = False):
        """
        Initialize enhanced scraper with specified engine.
        
        Args:
            engine: The engine to use ("selenium", "playwright", "requests")
            headless: Whether to run in headless mode
        """
        super().__init__(engine=engine, headless=headless)
        self.pattern_extractor = PatternExtractor()
        self.input_validator = InputValidator()
        self.prompt_formatter = PromptFormatter()
        self._template_creation_attempts = 0
        self._max_creation_attempts = 3

    def create_template(self):
        """Create template with proper engine support"""
        self._template_creation_attempts += 1

        if self._template_creation_attempts > self._max_creation_attempts:
            print(f"❌ Maximum template creation attempts ({self._max_creation_attempts}) exceeded.")
            return

        print("\n" + "=" * 50)
        print(f"🔧 Interactive Template Creation ({self.engine.title()} Engine)")
        print("=" * 50)

        try:
            # Get URL
            url = input("\n🌐 Enter URL to scrape: ").strip()
            if not url:
                print("❌ No URL provided")
                return

            # Navigate to URL (for browser engines)
            if self.engine in ["selenium", "playwright"]:
                print(f"\n🌐 Navigating to {url} with {self.engine}...")
                if not self.navigate_to(url):
                    print("❌ Failed to navigate to URL")
                    return
                print("✅ Page loaded successfully!")

                # Handle cookies (only for Selenium)
                if self.engine == "selenium" and self.cookie_handler:
                    print("\n🍪 Checking for cookie banners...")
                    self.cookie_handler.handle_cookie_banners()

            elif self.engine == "requests":
                print("\n⚠️  Requests engine selected - manual configuration required")
                print("   No JavaScript support or interactive selection available")

            # Get scraping type
            print("\n📋 Select scraping type")
            print("  1: List + Detail Pages - Extract from list, then follow links")
            print("  2: List Only - Extract data from list page only")
            print("  3: Single Page - Extract from current page only")
            
            type_choice = input("Choose [1/2/3] (default: 1): ").strip() or "1"
            scraping_type_map = {
                "1": ScrapingType.LIST_DETAIL,
                "2": ScrapingType.LIST_ONLY,
                "3": ScrapingType.SINGLE_PAGE
            }
            scraping_type = scraping_type_map.get(type_choice, ScrapingType.LIST_DETAIL)

            # Create template
            template = ScrapingTemplate(
                name="new_template",
                engine=self.engine,
                site_info=SiteInfo(url=url),
                scraping_type=scraping_type,
                list_page_rules=(
                    TemplateRules() if scraping_type != ScrapingType.SINGLE_PAGE else None
                ),
                detail_page_rules=TemplateRules(),
                version="2.1",
                created_at=datetime.now().isoformat(),
            )

            # Define rules based on engine
            if self.engine in ["selenium", "playwright"]:
                print(f"\n✨ Using {self.engine} for interactive element selection")
                
                # Define list rules if needed
                if scraping_type in (ScrapingType.LIST_DETAIL, ScrapingType.LIST_ONLY):
                    if not self._define_list_rules_interactive(template):
                        return

                # Define detail rules if needed
                if scraping_type in (ScrapingType.LIST_DETAIL, ScrapingType.SINGLE_PAGE):
                    if not self._define_detail_rules_interactive(template):
                        return
                        
            else:  # requests engine
                print("\n📝 Manual Configuration Required")
                print("Since you're using the requests engine, you'll need to manually specify selectors.")
                
                if scraping_type in (ScrapingType.LIST_DETAIL, ScrapingType.LIST_ONLY):
                    self._define_list_rules_manual(template)

                if scraping_type in (ScrapingType.LIST_DETAIL, ScrapingType.SINGLE_PAGE):
                    self._define_detail_rules_manual(template)

            # Save template
            import json
            from pathlib import Path
            
            template_name = input("\n💾 Enter template name (default: my_template): ").strip()
            if not template_name:
                template_name = "my_template"
                
            template_dict = template.to_dict()
            template_dict["name"] = f"{template_name}_{self.engine}"
            
            template_path = self.config.TEMPLATES_DIR / f"{template_dict['name']}.json"
            
            with open(template_path, "w", encoding="utf-8") as f:
                json.dump(template_dict, f, indent=2)

            print(f"\n✅ Template saved to: {template_path}")
            print("🎉 Template creation complete!")

        except Exception as e:
            self.logger.error(f"Template creation failed: {e}", exc_info=True)
            print(f"\n❌ Template creation failed: {e}")

    def _define_list_rules_interactive(self, template: ScrapingTemplate) -> bool:
        """Define list rules with interactive element selection"""
        rules = template.list_page_rules
        if not rules:
            return False
            
        print("\n🎯 Interactive List Item Selection")
        print("=" * 40)
        
        # First, select the list container
        print("\n1️⃣ Click on any item in the list (this helps identify the container)")
        
        if not self.inject_interactive_selector("Click on any list item"):
            print("❌ Failed to inject interactive selector")
            print("Falling back to manual configuration...")
            self._define_list_rules_manual(template)
            return True
            
        # Wait for user to select an element
        selected_data = None
        while True:
            time.sleep(0.5)
            data = self.get_selected_element_data()
            if data:
                if data.get('done'):
                    break
                selected_data = data
                print(f"✅ Selected: {data.get('selector', 'Unknown')}")
                break
        
        if not selected_data:
            print("❌ No element selected")
            self._define_list_rules_manual(template)
            return True
            
        # Extract container selector
        item_selector = selected_data.get('selector', '')
        if item_selector:
            # Try to generalize the selector to find the container
            parts = item_selector.split(' > ')
            if len(parts) > 1:
                # Remove the last part to get potential container
                container_selector = ' > '.join(parts[:-1])
                rules.container_selector = container_selector
                rules.item_selector = parts[-1]
            else:
                rules.item_selector = item_selector
                
        print(f"\n📦 Container: {rules.container_selector or 'body'}")
        print(f"📋 Item selector: {rules.item_selector}")
        
        # Now select fields within items
        print("\n2️⃣ Now we'll select fields within the list items")
        print("Click on different fields you want to extract (title, link, etc.)")
        
        fields = {}
        field_names = ["title", "link", "description", "date", "price", "custom"]
        
        for field_name in field_names:
            print(f"\n🔍 Select the {field_name} field (or click 'Done Selecting' to skip)")
            
            if not self.inject_interactive_selector(f"Select {field_name} field"):
                break
                
            # Wait for selection
            field_data = None
            while True:
                time.sleep(0.5)
                data = self.get_selected_element_data()
                if data:
                    if data.get('done'):
                        break
                    field_data = data
                    break
                    
            if field_data and not field_data.get('done'):
                selector = field_data.get('selector', '')
                if selector:
                    # Make selector relative to item if possible
                    if item_selector and selector.startswith(item_selector):
                        relative_selector = selector[len(item_selector):].strip()
                        if relative_selector.startswith(' > '):
                            relative_selector = relative_selector[3:]
                        fields[field_name] = relative_selector
                    else:
                        fields[field_name] = selector
                        
                    print(f"✅ {field_name}: {fields[field_name]}")
                    
                    # If it's a link field, also set link selector
                    if field_name == "link" and selector.endswith('a'):
                        rules.link_selector = fields[field_name]
            
            # Ask if user wants to add more fields
            if field_data and field_data.get('done'):
                break
                
        rules.fields = fields
        
        print("\n✅ List rules configured successfully!")
        return True

    def _define_detail_rules_interactive(self, template: ScrapingTemplate) -> bool:
        """Define detail rules with interactive element selection"""
        rules = template.detail_page_rules
        if not rules:
            return False
            
        print("\n🎯 Interactive Detail Page Selection")
        print("=" * 40)
        
        # Navigate to a detail page if needed
        if template.scraping_type == ScrapingType.LIST_DETAIL:
            print("\n📄 Please navigate to a detail/article page first")
            print("(You can click on any link from the list page)")
            input("Press Enter when you're on a detail page...")
            
        print("\n🔍 Now select the fields you want to extract from this page")
        
        fields = {}
        common_fields = ["title", "content", "author", "date", "category", "tags", "image"]
        
        for field_name in common_fields:
            print(f"\n📌 Select the {field_name} (or click 'Done Selecting' to skip)")
            
            if not self.inject_interactive_selector(f"Select {field_name}"):
                break
                
            # Wait for selection
            field_data = None
            while True:
                time.sleep(0.5)
                data = self.get_selected_element_data()
                if data:
                    if data.get('done'):
                        break
                    field_data = data
                    break
                    
            if field_data and not field_data.get('done'):
                selector = field_data.get('selector', '')
                if selector:
                    fields[field_name] = selector
                    print(f"✅ {field_name}: {selector}")
                    
            # Ask if done
            if field_data and field_data.get('done'):
                break
                
        # Allow custom fields
        while True:
            custom_name = input("\n💡 Add custom field name (or press Enter to finish): ").strip()
            if not custom_name:
                break
                
            print(f"\n📌 Select the {custom_name} element")
            
            if not self.inject_interactive_selector(f"Select {custom_name}"):
                break
                
            # Wait for selection
            custom_data = None
            while True:
                time.sleep(0.5)
                data = self.get_selected_element_data()
                if data:
                    custom_data = data
                    break
                    
            if custom_data and not custom_data.get('done'):
                selector = custom_data.get('selector', '')
                if selector:
                    fields[custom_name] = selector
                    print(f"✅ {custom_name}: {selector}")
                    
        rules.fields = fields
        
        print("\n✅ Detail page rules configured successfully!")
        print(f"📊 Total fields selected: {len(fields)}")
        
        return True

    def _define_list_rules_manual(self, template: ScrapingTemplate):
        """Manual configuration for list rules"""
        rules = template.list_page_rules
        if not rules:
            return
            
        print("\n📋 List Page Manual Configuration")
        print("=" * 40)
        
        # Container selector
        container = input("Enter CSS selector for the list container (or press Enter for 'body'): ").strip()
        rules.container_selector = container if container else "body"
        
        # Item selector
        item = input("Enter CSS selector for repeating items (e.g., 'div.item'): ").strip()
        if not item:
            print("❌ Item selector is required")
            return
        rules.item_selector = item
        
        # Fields
        print("\n📝 Define fields to extract from each item")
        fields = {}
        
        while True:
            field_name = input("\nField name (or press Enter to finish): ").strip()
            if not field_name:
                break
                
            field_selector = input(f"CSS selector for {field_name}: ").strip()
            if field_selector:
                fields[field_name] = field_selector
                
        rules.fields = fields
        
        # Link selector for list-detail
        if template.scraping_type == ScrapingType.LIST_DETAIL:
            link_selector = input("\nCSS selector for detail page links: ").strip()
            if link_selector:
                rules.link_selector = link_selector

    def _define_detail_rules_manual(self, template: ScrapingTemplate):
        """Manual configuration for detail rules"""
        rules = template.detail_page_rules
        if not rules:
            return
            
        print("\n📄 Detail Page Manual Configuration")
        print("=" * 40)
        
        print("📝 Define fields to extract from detail pages")
        fields = {}
        
        while True:
            field_name = input("\nField name (or press Enter to finish): ").strip()
            if not field_name:
                break
                
            field_selector = input(f"CSS selector for {field_name}: ").strip()
            if field_selector:
                fields[field_name] = field_selector
                
        rules.fields = fields