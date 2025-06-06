# src/scraper/core/interactive_scraper.py
"""
Scraper that provides an interactive, point-and-click workflow for
creating new scraping templates directly in the browser.
"""

import time
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from selenium.webdriver.common.by import By  # <-- Import By

from .base_scraper import BaseScraper
from ..models import ScrapingTemplate, SiteInfo, ScrapingType, TemplateRules, LoadStrategy, LoadStrategyConfig
from ..utils.selectors import normalize_selector, generalize_selector, make_relative_selector


class InteractiveScraper(BaseScraper):
    """Guides a user through creating a scraping template interactively."""

    def __init__(self):
        """Initializes the InteractiveScraper in non-headless mode."""
        super().__init__(headless=False)
        self._last_js_data_read = None

    def _inject_interactive_js(self, context_message: str = ""):
        """Injects the interactive selector JavaScript into the current page."""
        js_path = self.config.get_js_asset_path()
        if not js_path.exists():
            self.logger.error(f"Interactive JS file not found at: {js_path}")
            print(f"\n ERROR: JavaScript asset not found. Please ensure '{self.config.INTERACTIVE_JS_FILENAME}' is in the assets/js directory.")
            return False
        
        with open(js_path, 'r', encoding='utf-8') as f:
            js_code = f.read()

        escaped_message = json.dumps(context_message)
        script = f"window.scraperContextMessage = {escaped_message};\n{js_code}"

        try:
            self.driver.execute_script(script)
            return True
        except Exception as e:
            self.logger.warning(f"Failed to inject interactive JS: {e}")
            return False

    def _get_user_selection(self) -> Optional[Dict[str, Any]]:
        """Waits for and retrieves a user's element selection from the browser."""
        while True:
            try:
                result = self.driver.execute_script(
                    "return document.getElementById('selected_element_data') ? document.getElementById('selected_element_data').value : null;"
                )
                if not result or result == 'null':
                    time.sleep(0.5)
                    continue

                if result == "DONE_SELECTING":
                    self.driver.execute_script("document.getElementById('selected_element_data').value = '';")
                    return {"type": "done"}

                if result != self._last_js_data_read:
                    self._last_js_data_read = result
                    return json.loads(result)
            except Exception:
                time.sleep(0.5)
                continue

    def _get_user_input(self, prompt: str, default: str = "") -> str:
        """Gets validated text input from the user."""
        response = input(f"\n{prompt}").strip()
        return response or default

    def create_template(self):
        """Main workflow for creating a new scraping template."""
        print("--- Interactive Template Creation ---")
        
        url = self._get_user_input("Enter the target URL:", "https://www.gibsondunn.com/people/")
        self.navigate_to(url)
        
        cookie_sel = self._get_user_input("Enter a custom cookie selector (or press Enter to auto-detect):")
        if self.cookie_handler.accept_cookies([cookie_sel] if cookie_sel else None):
            print("Cookie banner handled.")

        site_info = SiteInfo(url=url, cookie_css=cookie_sel or None)

        print("Select scraping type:\n1. List + Detail\n2. List Only\n3. Single Page")
        type_choice = self._get_user_input("Enter choice (1/2/3):", "1")
        scraping_type = {
            "1": ScrapingType.LIST_DETAIL, "2": ScrapingType.LIST_ONLY
        }.get(type_choice, ScrapingType.SINGLE_PAGE)

        template = ScrapingTemplate(
            name="new_template",
            site_info=site_info,
            scraping_type=scraping_type,
            list_page_rules=TemplateRules() if scraping_type != ScrapingType.SINGLE_PAGE else None,
            detail_page_rules=TemplateRules()
        )

        if scraping_type in (ScrapingType.LIST_DETAIL, ScrapingType.LIST_ONLY):
            self._define_list_rules(template)

        if scraping_type in (ScrapingType.LIST_DETAIL, ScrapingType.SINGLE_PAGE):
            self._define_detail_rules(template)

        template_name = self._get_user_input("Enter a name for this template:", "my_new_template").replace(" ", "_")
        template.name = template_name
        template_path = self.config.TEMPLATES_DIR / f"{template_name}.json"
        template.save(template_path)
        print(f"--- Template saved to {template_path} ---")

    def _define_list_rules(self, template: ScrapingTemplate):
        """Guides user to define rules for a list page."""
        rules = template.list_page_rules

        print("\n--- Step: Select a single repeating item (e.g., a product card) ---")
        self._inject_interactive_js("Click on ONE complete repeating item")
        selection = self._get_user_selection()
        if selection and selection.get('type') == 'element_selected':
            selector = generalize_selector(selection['selector'])
            rules.repeating_item_selector = selector
            print(f"Repeating item selector set to: {selector}")

        print("\n--- Step: Select data fields WITHIN one repeating item ---")
        self._collect_fields_interactive(rules, is_relative_to=rules.repeating_item_selector)
        
        if template.scraping_type == ScrapingType.LIST_DETAIL:
             print("\n--- Step: Select the link that leads to the detail page ---")
             self._inject_interactive_js("Click the link to the detail page inside one item")
             selection = self._get_user_selection()
             if selection and selection.get('type') == 'element_selected':
                link_selector = make_relative_selector(selection['selector'], rules.repeating_item_selector)
                rules.profile_link_selector = link_selector
                print(f"Profile link selector set to: {link_selector}")

    def _define_detail_rules(self, template: ScrapingTemplate):
        """Guides user to define rules for a detail page."""
        if template.scraping_type == ScrapingType.LIST_DETAIL:
            print("\n--- Navigating to a sample detail page for field selection ---")
            try:
                # CORRECTED LINE
                first_item = self.driver.find_element(By.CSS_SELECTOR, template.list_page_rules.repeating_item_selector)
                # CORRECTED LINE
                link_element = first_item.find_element(By.CSS_SELECTOR, template.list_page_rules.profile_link_selector)
                self.navigate_to(link_element.get_attribute('href'))
            except Exception as e:
                print(f"Could not automatically navigate to a detail page: {e}")
                return
        
        print("\n--- Step: Select data fields on the page ---")
        self._collect_fields_interactive(template.detail_page_rules)

    def _collect_fields_interactive(self, rules: TemplateRules, is_relative_to: Optional[str] = None):
        """Interactively collects field names and selectors from the user."""
        self._inject_interactive_js("Click on data fields to extract. Click 'Done Selecting' when finished.")
        while True:
            selection = self._get_user_selection()
            if not selection or selection.get("type") == "done":
                break
            
            raw_selector = selection['selector']
            text_content = selection['text']
            
            field_name = self._get_user_input(f"Enter field name for text '{text_content[:50]}...':")
            if not field_name:
                continue

            selector_to_save = make_relative_selector(raw_selector, is_relative_to) if is_relative_to else raw_selector
            rules.fields[field_name] = selector_to_save
            print(f"Saved field '{field_name}' with selector: {selector_to_save}")