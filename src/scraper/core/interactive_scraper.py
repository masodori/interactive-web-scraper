# src/scraper/core/interactive_scraper.py
"""
Enhanced Interactive Scraper with comprehensive error handling for user prompts
and interactions.
"""

import time
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urlparse

from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, InvalidArgumentException, NoSuchElementException

from .base_scraper import BaseScraper
from ..models import ScrapingTemplate, SiteInfo, ScrapingType, TemplateRules, LoadStrategy, LoadStrategyConfig
from ..utils.selectors import normalize_selector, generalize_selector, make_relative_selector


class InteractiveScraper(BaseScraper):
    """Enhanced interactive scraper with robust error handling."""

    def __init__(self):
        """Initializes the InteractiveScraper in non-headless mode."""
        super().__init__(headless=False)
        self._last_js_data_read = None
        self._current_url = None
        self._template_creation_attempts = 0
        self._max_creation_attempts = 3

    def _validate_url(self, url: str) -> Tuple[bool, str]:
        """
        Validate URL format and accessibility.

        Args:
            url: URL string to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if URL is empty
        if not url or not url.strip():
            return False, "URL cannot be empty"

        # Add protocol if missing
        if not url.startswith(('http://', 'https://', 'file://')):
            url = 'https://' + url

        # Parse URL
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False, "Invalid URL format. Please include the domain (e.g., example.com)"
        except Exception:
            return False, "Unable to parse URL"

        # Check common URL mistakes
        if ' ' in url:
            return False, "URL contains spaces. Please check the URL"

        if not '.' in parsed.netloc or parsed.netloc.endswith('.'):
            return False, "Invalid domain name"

        return True, url

    def _get_user_input_with_validation(
        self,
        prompt: str,
        default: str = "",
        validator: Optional[callable] = None,
        error_message: str = "Invalid input. Please try again.",
        max_attempts: int = 3,
        allow_empty: bool = True
    ) -> Optional[str]:
        """
        Get user input with validation and error handling.

        Args:
            prompt: Prompt message
            default: Default value if empty input
            validator: Optional validation function
            error_message: Error message for invalid input
            max_attempts: Maximum number of attempts
            allow_empty: Whether to allow empty input

        Returns:
            Validated input or None if max attempts exceeded
        """
        attempts = 0
        while attempts < max_attempts:
            try:
                response = input(f"\n{prompt}").strip()

                # Handle empty input
                if not response:
                    if allow_empty:
                        return default
                    else:
                        print("❌ Input cannot be empty.")
                        attempts += 1
                        continue

                # Apply validator if provided
                if validator:
                    is_valid, validated_value = validator(response)
                    if is_valid:
                        return validated_value
                    else:
                        print(f"❌ {validated_value}")  # validated_value contains error message
                        attempts += 1
                        continue

                return response

            except KeyboardInterrupt:
                print("\n\n⚠️  Operation cancelled by user.")
                return None
            except EOFError:
                print("\n❌ Input stream ended unexpectedly.")
                return None
            except Exception as e:
                self.logger.error(f"Unexpected error during input: {e}")
                print(f"❌ An error occurred: {e}")
                attempts += 1

        print(f"\n❌ Maximum attempts ({max_attempts}) exceeded.")
        return None

    def _get_choice_input(
        self,
        prompt: str,
        choices: Dict[str, Any],
        default: str = None,
        max_attempts: int = 3
    ) -> Optional[str]:
        """
        Get user choice from a list of options with validation.

        Args:
            prompt: Prompt message
            choices: Dictionary of valid choices
            default: Default choice
            max_attempts: Maximum attempts

        Returns:
            Selected choice or None
        """
        def validate_choice(response):
            if response in choices:
                return True, response
            # Check if it's a number and corresponds to a choice
            try:
                choice_num = int(response)
                choice_list = list(choices.keys())
                if 1 <= choice_num <= len(choice_list):
                    return True, choice_list[choice_num - 1]
            except ValueError:
                pass

            valid_options = ", ".join(choices.keys())
            return False, f"Invalid choice. Please enter one of: {valid_options}"

        # Build prompt with choices
        full_prompt = f"{prompt}\n"
        for i, (key, description) in enumerate(choices.items(), 1):
            full_prompt += f"{i}. {description}\n"

        if default:
            full_prompt += f"\nEnter choice [{default}]: "
        else:
            full_prompt += f"\nEnter choice: "

        return self._get_user_input_with_validation(
            full_prompt,
            default=default,
            validator=validate_choice,
            error_message="Invalid choice",
            max_attempts=max_attempts,
            allow_empty=bool(default)
        )

    def _safe_navigate(self, url: str, max_retries: int = 3) -> bool:
        """
        Safely navigate to URL with error handling.

        Args:
            url: URL to navigate to
            max_retries: Maximum retry attempts

        Returns:
            True if successful, False otherwise
        """
        for attempt in range(max_retries):
            try:
                if self.navigate_to(url):
                    self._current_url = url
                    return True
                else:
                    print(f"⚠️  Failed to load {url} (attempt {attempt + 1}/{max_retries})")
                    time.sleep(2)
            except InvalidArgumentException:
                print(f"❌ Invalid URL: {url}")
                return False
            except WebDriverException as e:
                print(f"❌ Browser error: {e}")
                if attempt < max_retries - 1:
                    print("🔄 Retrying...")
                    time.sleep(2)
                else:
                    return False
            except Exception as e:
                self.logger.error(f"Unexpected navigation error: {e}")
                print(f"❌ Unexpected error: {e}")
                return False

        return False

    def _inject_interactive_js_with_retry(self, context_message: str = "", max_retries: int = 3) -> bool:
        """
        Inject JavaScript with retry logic.

        Args:
            context_message: Message to display in overlay
            max_retries: Maximum retry attempts

        Returns:
            True if successful
        """
        for attempt in range(max_retries):
            try:
                if self._inject_interactive_js(context_message):
                    return True
                else:
                    if attempt < max_retries - 1:
                        print(f"⚠️  Failed to inject selection tool (attempt {attempt + 1}/{max_retries})")
                        time.sleep(1)
            except Exception as e:
                self.logger.error(f"Error injecting JS: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)

        print("❌ Failed to initialize selection tool. Please try again.")
        return False

    def _collect_fields_with_recovery(
        self,
        rules: TemplateRules,
        is_relative_to: Optional[str] = None,
        max_fields: int = 50
    ) -> bool:
        """
        Collect fields with error recovery and limits.

        Args:
            rules: Template rules to populate
            is_relative_to: Container selector for relative selectors
            max_fields: Maximum number of fields to collect

        Returns:
            True if at least one field was collected
        """
        if not self._inject_interactive_js_with_retry("Click on data fields. Click 'Done Selecting' when finished."):
            return False

        fields_collected = 0
        consecutive_errors = 0
        max_consecutive_errors = 3

        while fields_collected < max_fields:
            try:
                selection = self._get_user_selection()

                if not selection:
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        print("⚠️  No response from selection tool. Ending field collection.")
                        break
                    time.sleep(1)
                    continue

                consecutive_errors = 0  # Reset error counter

                if selection.get("type") == "done":
                    break

                if selection.get("type") != "element_selected":
                    continue

                raw_selector = selection.get('selector', '')
                text_content = selection.get('text', '')[:50]

                if not raw_selector:
                    print("⚠️  Invalid selection. Please try again.")
                    continue

                # Get field name with validation
                field_name = self._get_user_input_with_validation(
                    f"Enter field name for '{text_content}...' (or 'skip' to skip): ",
                    validator=lambda x: (True, x) if x and x.lower() != 'skip' else (False, "Skipping field"),
                    allow_empty=False,
                    max_attempts=3
                )

                if not field_name or field_name.lower() == 'skip':
                    continue

                # Sanitize field name
                field_name = field_name.strip().replace(' ', '_').replace('-', '_')

                # Check for duplicate field names
                if field_name in rules.fields:
                    overwrite = self._get_choice_input(
                        f"Field '{field_name}' already exists. Overwrite?",
                        {"y": "Yes", "n": "No"},
                        default="n"
                    )
                    if overwrite != 'y':
                        continue

                # Make selector relative if needed
                try:
                    if is_relative_to:
                        selector = make_relative_selector(raw_selector, is_relative_to)
                    else:
                        selector = raw_selector

                    rules.fields[field_name] = selector
                    fields_collected += 1
                    print(f"✅ Added field '{field_name}' ({fields_collected} total)")

                except Exception as e:
                    self.logger.error(f"Error processing selector: {e}")
                    print(f"⚠️  Error processing selector. Skipping field.")

            except KeyboardInterrupt:
                print("\n⚠️  Field collection interrupted.")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error in field collection: {e}")
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    print("❌ Too many errors. Ending field collection.")
                    break

        if fields_collected == 0:
            print("\n⚠️  No fields were collected.")
            retry = self._get_choice_input(
                "Would you like to try again?",
                {"y": "Yes", "n": "No"},
                default="y"
            )
            if retry == 'y':
                return self._collect_fields_with_recovery(rules, is_relative_to, max_fields)

        return fields_collected > 0

    def create_template(self):
        """Enhanced template creation with comprehensive error handling."""
        self._template_creation_attempts += 1

        if self._template_creation_attempts > self._max_creation_attempts:
            print(f"❌ Maximum template creation attempts ({self._max_creation_attempts}) exceeded.")
            return

        print("\n" + "="*50)
        print("🔧 Interactive Template Creation")
        print("="*50)

        try:
            # Step 1: Get and validate URL
            url = None
            while not url:
                url_input = self._get_user_input_with_validation(
                    "Enter the target URL (or 'quit' to exit): ",
                    default="https://www.gibsondunn.com/people/",
                    allow_empty=True
                )

                if not url_input or url_input.lower() == 'quit':
                    print("👋 Exiting template creation.")
                    return

                is_valid, result = self._validate_url(url_input)
                if is_valid:
                    url = result
                else:
                    print(f"❌ {result}")
                    url = None

            # Step 2: Navigate to URL
            print(f"\n🌐 Navigating to {url}...")
            if not self._safe_navigate(url):
                retry = self._get_choice_input(
                    "Failed to navigate to URL. Would you like to try a different URL?",
                    {"y": "Yes", "n": "No"},
                    default="y"
                )
                if retry == 'y':
                    return self.create_template()
                else:
                    return

            print("✅ Page loaded successfully!")

            # Step 3: Handle cookies
            print("\n🍪 Checking for cookie banners...")
            cookie_selector = self._get_user_input_with_validation(
                "Enter custom cookie selector (or press Enter to auto-detect): ",
                allow_empty=True
            )

            try:
                if self.cookie_handler.accept_cookies([cookie_selector] if cookie_selector else None):
                    print("✅ Cookie banner handled")
                else:
                    print("ℹ️  No cookie banner detected or handled")
            except Exception as e:
                self.logger.error(f"Cookie handling error: {e}")
                print("⚠️  Error handling cookies, continuing anyway...")

            # Step 4: Create site info
            site_info = SiteInfo(url=url, cookie_css=cookie_selector or None)

            # Step 5: Get scraping type
            scraping_type_choice = self._get_choice_input(
                "\n📋 Select scraping type:",
                {
                    "1": "List + Detail (scrape list page and detail pages)",
                    "2": "List Only (scrape list page only)",
                    "3": "Single Page (scrape current page only)"
                },
                default="1"
            )

            if not scraping_type_choice:
                print("❌ No scraping type selected.")
                return

            scraping_type_map = {
                "1": ScrapingType.LIST_DETAIL,
                "2": ScrapingType.LIST_ONLY,
                "3": ScrapingType.SINGLE_PAGE
            }
            scraping_type = scraping_type_map.get(scraping_type_choice, ScrapingType.LIST_DETAIL)

            # Step 6: Create template
            template = ScrapingTemplate(
                name="new_template",
                site_info=site_info,
                scraping_type=scraping_type,
                list_page_rules=TemplateRules() if scraping_type != ScrapingType.SINGLE_PAGE else None,
                detail_page_rules=TemplateRules()
            )

            # Step 7: Define rules based on type
            try:
                if scraping_type in (ScrapingType.LIST_DETAIL, ScrapingType.LIST_ONLY):
                    if not self._define_list_rules_safe(template):
                        print("⚠️  Failed to define list rules completely.")
                        save_anyway = self._get_choice_input(
                            "Save template anyway?",
                            {"y": "Yes", "n": "No"},
                            default="n"
                        )
                        if save_anyway != 'y':
                            return

                if scraping_type in (ScrapingType.LIST_DETAIL, ScrapingType.SINGLE_PAGE):
                    if not self._define_detail_rules_safe(template):
                        print("⚠️  Failed to define detail rules completely.")
                        save_anyway = self._get_choice_input(
                            "Save template anyway?",
                            {"y": "Yes", "n": "No"},
                            default="n"
                        )
                        if save_anyway != 'y':
                            return

            except Exception as e:
                self.logger.error(f"Error defining rules: {e}")
                print(f"❌ Error during rule definition: {e}")
                return

            # Step 8: Save template
            template_name = self._get_user_input_with_validation(
                "\n💾 Enter template name (letters, numbers, underscores only): ",
                default="my_template",
                validator=lambda x: (True, x.replace(' ', '_').replace('-', '_')) if x.replace(' ', '_').replace('-', '_').replace('_', '').isalnum() else (False, "Name must contain only letters, numbers, and underscores"),
                allow_empty=True
            )

            if not template_name:
                template_name = "my_template"

            template.name = template_name
            template_path = self.config.TEMPLATES_DIR / f"{template_name}.json"

            # Check if file exists
            if template_path.exists():
                overwrite = self._get_choice_input(
                    f"Template '{template_name}' already exists. Overwrite?",
                    {"y": "Yes", "n": "No"},
                    default="n"
                )
                if overwrite != 'y':
                    new_name = self._get_user_input_with_validation(
                        "Enter new template name: ",
                        validator=lambda x: (True, x.replace(' ', '_').replace('-', '_')) if x else (False, "Name cannot be empty"),
                        allow_empty=False
                    )
                    if new_name:
                        template_name = new_name
                        template.name = template_name
                        template_path = self.config.TEMPLATES_DIR / f"{template_name}.json"

            # Save template
            try:
                template.save(template_path)
                print(f"\n✅ Template saved successfully to: {template_path}")
                print(f"\n📊 Template Summary:")
                print(f"  - Name: {template.name}")
                print(f"  - Type: {scraping_type.value}")
                if template.list_page_rules:
                    print(f"  - List fields: {len(template.list_page_rules.fields)}")
                if template.detail_page_rules:
                    print(f"  - Detail fields: {len(template.detail_page_rules.fields)}")
                print("\n🎉 Template creation complete!")

            except Exception as e:
                self.logger.error(f"Failed to save template: {e}")
                print(f"❌ Failed to save template: {e}")

        except KeyboardInterrupt:
            print("\n\n⚠️  Template creation cancelled by user.")
        except Exception as e:
            self.logger.error(f"Unexpected error in template creation: {e}")
            print(f"\n❌ Unexpected error: {e}")
            retry = self._get_choice_input(
                "Would you like to try again?",
                {"y": "Yes", "n": "No"},
                default="y"
            )
            if retry == 'y':
                return self.create_template()

    def _define_list_rules_safe(self, template: ScrapingTemplate) -> bool:
        """Safely define list rules with error handling."""
        rules = template.list_page_rules
        if not rules:
            return False

        print("\n" + "="*40)
        print("📋 List Page Configuration")
        print("="*40)

        # Step 1: Select repeating item
        print("\n🎯 Step 1: Select a repeating item container")
        print("Click on ONE complete item (e.g., a person card, product card, etc.)")
        print("This helps identify all similar items on the page.")

        if not self._inject_interactive_js_with_retry("Click on ONE complete repeating item"):
            return False

        selection = None
        attempts = 0
        max_attempts = 3

        while attempts < max_attempts:
            try:
                selection = self._get_user_selection()
                if selection and selection.get('type') == 'element_selected':
                    break
                elif selection and selection.get('type') == 'done':
                    print("⚠️  No item selected. Please select an item first.")
                    attempts += 1
                else:
                    time.sleep(1)
            except Exception as e:
                self.logger.error(f"Error getting selection: {e}")
                attempts += 1

        if not selection or selection.get('type') != 'element_selected':
            print("❌ Failed to get item selection.")
            return False

        try:
            selector = generalize_selector(selection['selector'])
            rules.repeating_item_selector = selector

            # Validate selector
            items_found = len(self.driver.find_elements(By.CSS_SELECTOR, selector))
            print(f"✅ Repeating item selector set: {selector}")
            print(f"ℹ️  Found {items_found} matching items on the page")

            if items_found == 0:
                print("⚠️  Warning: No items found with this selector!")
            elif items_found == 1:
                print("⚠️  Warning: Only 1 item found. This might not be the right selector.")

        except Exception as e:
            self.logger.error(f"Error setting repeating item selector: {e}")
            print("❌ Failed to set repeating item selector.")
            return False

        # Step 2: Select fields within item
        print("\n🎯 Step 2: Select data fields WITHIN one item")
        print("Click on each piece of data you want to extract (name, price, etc.)")
        print("Click 'Done Selecting' when finished.")

        if not self._collect_fields_with_recovery(rules, is_relative_to=rules.repeating_item_selector):
            return False

        # Step 3: Select detail link (if needed)
        if template.scraping_type == ScrapingType.LIST_DETAIL:
            print("\n🎯 Step 3: Select the link to detail page")
            print("Click on the link that leads to the detail/profile page")

            if not self._inject_interactive_js_with_retry("Click the link to the detail page"):
                return False

            link_selection = None
            attempts = 0

            while attempts < max_attempts:
                try:
                    link_selection = self._get_user_selection()
                    if link_selection and link_selection.get('type') == 'element_selected':
                        break
                    elif link_selection and link_selection.get('type') == 'done':
                        print("⚠️  No link selected.")
                        skip = self._get_choice_input(
                            "Skip detail page link?",
                            {"y": "Yes", "n": "No"},
                            default="n"
                        )
                        if skip == 'y':
                            return True
                        attempts += 1
                    else:
                        time.sleep(1)
                except Exception as e:
                    self.logger.error(f"Error getting link selection: {e}")
                    attempts += 1

            if link_selection and link_selection.get('type') == 'element_selected':
                try:
                    link_selector = make_relative_selector(
                        link_selection['selector'],
                        rules.repeating_item_selector
                    )
                    rules.profile_link_selector = link_selector
                    print(f"✅ Detail link selector set")
                except Exception as e:
                    self.logger.error(f"Error setting link selector: {e}")
                    print("⚠️  Failed to set detail link selector")

        return True

    def _define_detail_rules_safe(self, template: ScrapingTemplate) -> bool:
        """Safely define detail rules with error handling."""
        if not template.detail_page_rules:
            return False

        print("\n" + "="*40)
        print("📄 Detail Page Configuration")
        print("="*40)

        # Navigate to detail page if list+detail
        if template.scraping_type == ScrapingType.LIST_DETAIL and template.list_page_rules:
            print("\n🔍 Navigating to a sample detail page...")

            try:
                # Try to find and navigate to first detail page
                first_item = self.driver.find_element(
                    By.CSS_SELECTOR,
                    template.list_page_rules.repeating_item_selector
                )

                if template.list_page_rules.profile_link_selector:
                    link_element = first_item.find_element(
                        By.CSS_SELECTOR,
                        template.list_page_rules.profile_link_selector
                    )

                    # Walk up the DOM to find the actual <a> tag
                    anchor_element = link_element
                    while anchor_element.tag_name.lower() != 'a' and anchor_element.tag_name.lower() != 'body':
                        anchor_element = anchor_element.find_element(By.XPATH, '..')

                    detail_url = None
                    if anchor_element.tag_name.lower() == 'a':
                        detail_url = anchor_element.get_attribute('href')

                    if detail_url:
                        print(f"🌐 Navigating to: {detail_url}")
                        if not self._safe_navigate(detail_url):
                            print("❌ Failed to navigate to detail page")
                            manual = self._get_choice_input(
                                "Manually navigate to a detail page?",
                                {"y": "Yes", "n": "No"},
                                default="y"
                            )
                            if manual != 'y':
                                return False
                            else:
                                input("\n⏸️  Navigate to a detail page and press Enter when ready...")
                        else:
                            print("✅ Navigated to detail page")
                    else:
                        print("⚠️  No detail URL found")
                        return False

            except Exception as e:
                self.logger.error(f"Error navigating to detail page: {e}")
                print(f"⚠️  Could not automatically navigate to detail page: {e}")
                manual = self._get_choice_input(
                    "Manually navigate to a detail page?",
                    {"y": "Yes", "n": "No"},
                    default="y"
                )
                if manual == 'y':
                    input("\n⏸️  Navigate to a detail page and press Enter when ready...")
                else:
                    return False

        # Collect fields on detail page
        print("\n🎯 Select data fields on this page")
        print("Click on each piece of data you want to extract")

        return self._collect_fields_with_recovery(template.detail_page_rules)