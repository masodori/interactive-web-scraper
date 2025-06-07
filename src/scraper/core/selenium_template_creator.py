"""
Selenium-specific template creator with proper list->detail page flow
"""

import time
import logging
from typing import Dict, List, Optional, Any
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from ..models import ScrapingTemplate, ScrapingType, TemplateRules, SiteInfo
from ..config import Config


class SeleniumTemplateCreator:
    """Handles template creation for Selenium with proper flow"""
    
    def __init__(self, scraper):
        self.scraper = scraper  # UnifiedInteractiveScraper instance
        self.logger = logging.getLogger(__name__)
        self.config = Config()
        
    def create_list_detail_template(self, url: str) -> Optional[ScrapingTemplate]:
        """Create a list+detail template with proper flow"""
        
        # Step 1: Configure list page
        print("\n" + "="*60)
        print("📋 STEP 1: Configure List Page")
        print("="*60)
        
        list_rules = TemplateRules()
        
        # Get repeating item selector
        if not self._configure_repeating_item(list_rules):
            return None
            
        # Get fields within each item
        print("\n💡 Now select fields WITHIN a single list item")
        list_fields = self._configure_fields("list item")
        list_rules.fields = list_fields
        
        # Get link selector for detail pages
        print("\n🔗 Select the link to detail pages")
        link_selector = self._get_link_selector()
        if not link_selector:
            print("❌ No link selector provided")
            return None
        list_rules.profile_link_selector = link_selector
        
        # Step 2: Navigate to a detail page
        print("\n" + "="*60)
        print("📄 STEP 2: Configure Detail Page")
        print("="*60)
        
        # Get first link and navigate
        if not self._navigate_to_first_detail_page(list_rules):
            return None
            
        # Configure detail page
        detail_rules = TemplateRules()
        
        # Check if detail page also has repeating items
        print("\n❓ Does the detail page have repeating items?")
        print("   (e.g., list of publications, cases, education)")
        has_repeating = input("Has repeating items? [y/N]: ").strip().lower() == 'y'
        
        if has_repeating:
            if not self._configure_repeating_item(detail_rules):
                return None
        
        # Get fields for detail page
        print("\n💡 Select fields to extract from detail page")
        detail_fields = self._configure_fields("detail page")
        detail_rules.fields = detail_fields
        
        # Create template
        template = ScrapingTemplate(
            name="new_template",
            engine="selenium",
            site_info=SiteInfo(url=url),
            scraping_type=ScrapingType.LIST_DETAIL,
            list_page_rules=list_rules,
            detail_page_rules=detail_rules,
            version="2.1"
        )
        
        return template
        
    def _configure_repeating_item(self, rules: TemplateRules) -> bool:
        """Configure repeating item selector with validation"""
        
        print("\n🎯 Click on ONE individual item (not the container)")
        print("Examples: one attorney card, one product, one article")
        
        # Clear any previous selection
        self._clear_selection()
        
        # Inject selector
        if not self.scraper.inject_interactive_selector("Click ONE item"):
            return False
            
        # Wait for selection
        selector = self._wait_for_selection()
        if not selector:
            return False
            
        # Validate and improve the selector
        validated_selector = self._validate_and_improve_selector(selector)
        if not validated_selector:
            print("\n❌ Invalid selection. Please try again.")
            return self._configure_repeating_item(rules)
            
        rules.repeating_item_selector = validated_selector
        print(f"✅ Using selector: {validated_selector}")
        
        self.scraper.cleanup_interactive_selector()
        return True
        
    def _configure_fields(self, context: str) -> Dict[str, str]:
        """Configure fields with click-first approach"""
        fields = {}
        
        print(f"Click elements first, then name them.")
        print("Click 'Done' when finished.\n")
        
        field_count = 0
        while True:
            field_count += 1
            
            # Clear previous selection
            self._clear_selection()
            
            # Inject selector
            if not self.scraper.inject_interactive_selector(f"Select field #{field_count} or Done"):
                break
                
            # Wait for selection
            data = self._wait_for_selection(return_data=True)
            if not data:
                break
                
            if data.get('done'):
                print("✅ Done selecting fields")
                break
                
            selector = data.get('selector', '')
            text = data.get('text', '')[:50]
            
            if selector:
                print(f"\n📍 Selected: {selector}")
                if text:
                    print(f"   Text: '{text}...'")
                    
                # Ask what to call it
                print("\nWhat is this field?")
                print("Common: name, title, email, phone, office, department, bio")
                field_name = input("Field name: ").strip()
                
                if field_name:
                    # Make selector relative if possible
                    if hasattr(self, '_current_item_selector'):
                        selector = self._make_relative(selector, self._current_item_selector)
                    
                    fields[field_name] = selector
                    print(f"✅ Saved as '{field_name}'")
                    
            self.scraper.cleanup_interactive_selector()
            print("-" * 40)
            
        return fields
        
    def _get_link_selector(self) -> Optional[str]:
        """Get selector for detail page links"""
        
        print("Click on the link that goes to detail pages")
        print("(Usually the person's name or 'View Profile' link)")
        
        self._clear_selection()
        
        if not self.scraper.inject_interactive_selector("Click detail page link"):
            return None
            
        selector = self._wait_for_selection()
        if selector:
            # Make the link selector relative to the item
            if hasattr(self, '_current_item_selector'):
                relative_selector = self._make_relative(selector, self._current_item_selector)
                print(f"✅ Link selector (relative): {relative_selector}")
                selector = relative_selector
            else:
                # Clean up nth-of-type from the selector
                selector = self._process_item_selector(selector)
                print(f"✅ Link selector: {selector}")
            
        self.scraper.cleanup_interactive_selector()
        return selector
        
    def _navigate_to_first_detail_page(self, list_rules: TemplateRules) -> bool:
        """Navigate to the first detail page"""
        
        print("\n🔄 Navigating to first detail page...")
        
        try:
            # Find all items
            items = self.scraper.scraper.driver.find_elements(
                By.CSS_SELECTOR, 
                list_rules.repeating_item_selector
            )
            
            if not items:
                print("❌ No items found with selector")
                return False
                
            print(f"📊 Found {len(items)} items")
            
            # Try to find a link in the first few items
            for i, item in enumerate(items[:3]):  # Check first 3 items
                try:
                    # First try the profile link selector
                    if list_rules.profile_link_selector:
                        try:
                            link = item.find_element(
                                By.CSS_SELECTOR, 
                                list_rules.profile_link_selector
                            )
                        except:
                            # Try simpler selector within item
                            link = item.find_element(By.CSS_SELECTOR, "a")
                    else:
                        # No specific selector, find first link
                        link = item.find_element(By.CSS_SELECTOR, "a")
                    
                    url = link.get_attribute('href')
                    
                    if url and not url.endswith('#'):
                        print(f"📍 Found detail URL in item {i+1}: {url}")
                        
                        # Navigate
                        self.scraper.navigate_to(url)
                        time.sleep(3)  # Give more time to load
                        
                        # Verify we're on a different page
                        new_url = self.scraper.scraper.driver.current_url
                        if new_url != self.scraper.current_url:
                            print("✅ Successfully navigated to detail page")
                            return True
                        
                except NoSuchElementException:
                    continue
                    
            print("❌ Could not find valid links in items")
                
        except Exception as e:
            self.logger.error(f"Navigation error: {e}")
            
        # Fallback - manual navigation
        print("\n⚠️  Automatic navigation failed")
        print("This might be due to JavaScript-heavy navigation or dynamic loading.")
        input("Please manually click on any person/item to go to their detail page, then press Enter...")
        return True
        
    def _clear_selection(self):
        """Clear any previous selection"""
        try:
            self.scraper.scraper.driver.execute_script("""
                const input = document.getElementById('selected_element_data');
                if (input) {
                    input.value = '';
                }
            """)
        except:
            pass
            
    def _wait_for_selection(self, return_data: bool = False, timeout: int = 30):
        """Wait for user to select an element"""
        
        for _ in range(timeout * 2):  # Check every 0.5s
            time.sleep(0.5)
            data = self.scraper.get_selected_element_data()
            
            if data:
                if return_data:
                    return data
                else:
                    return data.get('selector', '')
                    
        print("⏱️  Selection timeout")
        return None
        
    def _looks_like_container(self, selector: str) -> bool:
        """Check if selector looks like a container"""
        container_hints = [
            'container', 'wrapper', 'grid', 'list', 
            'results', 'items', 'collection', 'loading',
            'people', 'attorneys', 'professionals', 'team',
            'wpgb-template', 'wp-grid-builder'  # WordPress Grid Builder
        ]
        selector_lower = selector.lower()
        return any(hint in selector_lower for hint in container_hints)
        
    def _process_item_selector(self, selector: str) -> str:
        """Process item selector to make it general"""
        import re
        
        # Remove nth-of-type
        processed = re.sub(r':nth-of-type\(\d+\)', '', selector)
        
        # Store for relative selectors
        self._current_item_selector = selector
        
        return processed or selector
        
    def _make_relative(self, field_selector: str, item_selector: str) -> str:
        """Make field selector relative to item"""
        
        # Split into parts
        field_parts = field_selector.split(' > ')
        item_parts = item_selector.split(' > ')
        
        # Find common prefix
        common = 0
        for i in range(min(len(field_parts), len(item_parts))):
            if field_parts[i].strip() == item_parts[i].strip():
                common = i + 1
            else:
                break
                
        # Return relative part
        if common > 0:
            relative_parts = field_parts[common:]
            if relative_parts:
                return ' > '.join(relative_parts)
                
        # Fallback to last part
        return field_parts[-1] if field_parts else field_selector
        
    def _validate_and_improve_selector(self, selector: str) -> Optional[str]:
        """Validate selector and try to improve it"""
        
        try:
            # Count matching elements
            elements = self.scraper.scraper.driver.find_elements(By.CSS_SELECTOR, selector)
            count = len(elements)
            
            print(f"\n🔍 Found {count} matching elements")
            
            # If only one element, it might be a container
            if count == 1:
                # Check if it's a container
                if self._looks_like_container(selector):
                    print("⚠️  This appears to be a container!")
                    
                    # Try to find repeating items within
                    improved = self._find_repeating_items_in_container(selector)
                    if improved:
                        return improved
                    
                    # Ask user
                    print(f"   Selected: {selector}")
                    confirm = input("\nContinue with this selector? [y/N]: ").strip().lower()
                    if confirm != 'y':
                        return None
                        
                # Process for single valid item
                return self._process_item_selector(selector)
                
            elif count > 1:
                # Multiple matches - good!
                print("✅ Multiple items found - looks good!")
                
                # Show sample of what was found
                if count > 3:
                    print(f"   Showing first 3 of {count} items:")
                    for i in range(min(3, count)):
                        text = elements[i].text.strip()[:50]
                        if text:
                            print(f"   {i+1}. {text}...")
                            
                return self._process_item_selector(selector)
                
            else:
                print("❌ No elements found with this selector")
                return None
                
        except Exception as e:
            self.logger.error(f"Selector validation error: {e}")
            return None
            
    def _find_repeating_items_in_container(self, container_selector: str) -> Optional[str]:
        """Try to find repeating items within a container"""
        
        print("\n🔍 Analyzing container for repeating items...")
        
        # Special handling for known patterns
        if 'people.loading' in container_selector or 'wpgb-' in container_selector:
            print("💡 Detected dynamic content container")
            print("   Waiting for content to load...")
            time.sleep(2)  # Give dynamic content time to load
            
            # For Gibson Dunn, the actual items are often articles within the container
            # Try removing the .loading class which might be temporary
            if '.loading' in container_selector:
                container_selector = container_selector.replace('.loading', '')
                print(f"   Adjusted selector: {container_selector}")
            
        try:
            container = self.scraper.scraper.driver.find_element(By.CSS_SELECTOR, container_selector)
            
            # Common patterns for repeating items (ordered by likelihood)
            item_patterns = [
                # WordPress Grid Builder patterns (Gibson Dunn uses this)
                'article.wpgb-card', 'div.wpgb-card', '.wpgb-item',
                # Gibson Dunn specific
                'article.attorney', 'div.attorney', 'div.person', 
                'article[class*="attorney"]', 'div[class*="attorney"]',
                # Generic patterns
                'article', 'li', '.item', '.card', '.person', '.attorney',
                '.result', '.entry', '.profile', 'div[class*="item"]',
                'div[class*="card"]', 'div[class*="person"]'
            ]
            
            for pattern in item_patterns:
                try:
                    items = container.find_elements(By.CSS_SELECTOR, pattern)
                    if len(items) > 1:
                        # Found multiple items!
                        full_selector = f"{container_selector} > {pattern}"
                        
                        # Verify with full page
                        all_items = self.scraper.scraper.driver.find_elements(
                            By.CSS_SELECTOR, full_selector
                        )
                        
                        if len(all_items) > 1:
                            print(f"✅ Found {len(all_items)} repeating items: {pattern}")
                            
                            # Show sample
                            for i in range(min(3, len(all_items))):
                                text = all_items[i].text.strip()[:50]
                                if text:
                                    print(f"   {i+1}. {text}...")
                                    
                            use_this = input(f"\nUse '{full_selector}'? [Y/n]: ").strip().lower()
                            if use_this != 'n':
                                return full_selector
                                
                except Exception:
                    continue
                    
            # Try direct children if no patterns work
            children = container.find_elements(By.XPATH, "./*")
            if len(children) > 1:
                # Check if children have same tag
                tags = {}
                for child in children:
                    tag = child.tag_name
                    tags[tag] = tags.get(tag, 0) + 1
                    
                # Find most common tag with multiple instances
                for tag, count in sorted(tags.items(), key=lambda x: x[1], reverse=True):
                    if count > 1:
                        full_selector = f"{container_selector} > {tag}"
                        print(f"✅ Found {count} repeating <{tag}> elements")
                        
                        # Show sample
                        sample_items = self.scraper.scraper.driver.find_elements(
                            By.CSS_SELECTOR, full_selector
                        )[:3]
                        for i, item in enumerate(sample_items):
                            text = item.text.strip()[:50]
                            if text:
                                print(f"   {i+1}. {text}...")
                        
                        use_this = input(f"\nUse '{full_selector}'? [Y/n]: ").strip().lower()
                        if use_this != 'n':
                            return full_selector
                            
            # Last resort - look for any repeated structures
            print("\n🔍 Searching for repeated structures...")
            
            # Try to find elements with same class pattern
            all_elements = container.find_elements(By.XPATH, ".//*")
            class_counts = {}
            for elem in all_elements:
                classes = elem.get_attribute('class')
                if classes:
                    # Look for meaningful classes
                    for cls in classes.split():
                        if cls and not cls.isdigit() and len(cls) > 2:
                            class_counts[cls] = class_counts.get(cls, 0) + 1
                            
            # Find classes that appear multiple times
            for cls, count in sorted(class_counts.items(), key=lambda x: x[1], reverse=True):
                if count > 1 and cls not in ['wp-block', 'has-text', 'is-style']:
                    selector = f"{container_selector} .{cls}"
                    print(f"💡 Found {count} elements with class '{cls}'")
                    
                    use_this = input(f"Try selector '{selector}'? [Y/n]: ").strip().lower()
                    if use_this != 'n':
                        return selector
                            
        except Exception as e:
            self.logger.error(f"Container analysis error: {e}")
            
        return None