# src/scraper/core/enhanced_interactive_scraper_v2.py
"""
Enhanced Interactive Scraper V2 with multi-engine support (Selenium, Playwright, Requests).
This version supports interactive element selection with both Selenium and Playwright.
"""

import json
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from datetime import datetime

from .multi_engine_scraper import MultiEngineScraper
from .enhanced_interactive_scraper import EnhancedInteractiveScraper as EnhancedInteractiveScraperV1
from ..models import (
    ScrapingTemplate,
    SiteInfo,
    ScrapingType,
    TemplateRules,
    LoadStrategyConfig,
)
from ..utils.input_validators import InputValidator, PromptFormatter
from ..extractors.pattern_extractor import PatternExtractor


class EnhancedInteractiveScraperV2(MultiEngineScraper):
    """Enhanced interactive scraper with multi-engine support"""

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
        
        # Copy all methods from V1 that don't need modification
        self._v1_instance = EnhancedInteractiveScraperV1.__new__(EnhancedInteractiveScraperV1)
        self._v1_instance.pattern_extractor = self.pattern_extractor
        self._v1_instance.input_validator = self.input_validator
        self._v1_instance.prompt_formatter = self.prompt_formatter
        self._v1_instance.config = self.config
        self._v1_instance.logger = self.logger

    def create_template(self):
        """Enhanced template creation with multi-engine support"""
        self._template_creation_attempts += 1

        if self._template_creation_attempts > self._max_creation_attempts:
            print(
                f"❌ Maximum template creation attempts ({self._max_creation_attempts}) exceeded."
            )
            return

        print("\n" + "=" * 50)
        print("🔧 Enhanced Interactive Template Creation v2.0")
        print("=" * 50)

        try:
            # Step 1: Get and validate URL
            url = self._get_url_with_validation()
            if not url:
                return

            # Step 2: Select engine (already set in __init__, but allow change)
            selected_engine = self._select_engine()
            if not selected_engine:
                return
                
            # If engine changed, reinitialize
            if selected_engine != self.engine:
                self.close()  # Close current driver
                self.__init__(engine=selected_engine, headless=self.headless)

            # For requests engine, we can't do interactive selection
            if self.engine == "requests":
                print(
                    "\n⚠️  Note: Requests engine doesn't support JavaScript or "
                    "interactive selection."
                )
                print(
                    "   It's best for static HTML sites. Consider using Selenium or "
                    "Playwright for dynamic sites."
                )

                continue_anyway = self._get_choice_input(
                    "Continue with requests engine?",
                    {
                        "y": "Yes (I understand the limitations)",
                        "n": "No (choose different engine)",
                    },
                    default="n",
                )

                if continue_anyway != "y":
                    return self.create_template()

            # Step 3: Navigate to URL (for browser engines)
            if self.engine in ["selenium", "playwright"]:
                print(f"\n🌐 Navigating to {url} with {self.engine}...")
                if not self._safe_navigate(url):
                    retry = self._get_choice_input(
                        "Failed to navigate to URL. Would you like to try a different URL?",
                        {"y": "Yes", "n": "No"},
                        default="y",
                    )
                    if retry == "y":
                        return self.create_template()
                    else:
                        return

                print("✅ Page loaded successfully!")

                # Handle cookies (only for Selenium - Playwright cookie handler not implemented yet)
                if self.engine == "selenium":
                    print("\n🍪 Checking for cookie banners...")
                    self._handle_cookies()

            # Continue with the rest of template creation...
            # (Using the same logic as V1 but with multi-engine support)
            
            # Step 4: Create site info
            site_info = SiteInfo(url=url)

            # Step 5: Get scraping type
            scraping_type = self._select_scraping_type()
            if not scraping_type:
                return

            # Step 6: Configure rate limiting
            rate_limiting = self._configure_rate_limiting()

            # Step 7: Create template
            template = ScrapingTemplate(
                name="new_template",
                engine=self.engine,  # Use actual engine
                site_info=site_info,
                scraping_type=scraping_type,
                list_page_rules=(
                    TemplateRules()
                    if scraping_type != ScrapingType.SINGLE_PAGE
                    else None
                ),
                detail_page_rules=TemplateRules(),
                version="2.1",
                created_at=datetime.now().isoformat(),
            )

            # Add advanced configurations
            template_dict = template.to_dict()
            template_dict["rate_limiting"] = rate_limiting

            # Step 8: Define rules based on type and engine
            if self.engine in ["selenium", "playwright"]:
                # Interactive selection for browser engines
                if scraping_type in (ScrapingType.LIST_DETAIL, ScrapingType.LIST_ONLY):
                    if not self._define_list_rules_safe(template):
                        return

                if scraping_type in (
                    ScrapingType.LIST_DETAIL,
                    ScrapingType.SINGLE_PAGE,
                ):
                    if not self._define_detail_rules_safe(template):
                        return
            else:
                # Manual configuration for non-browser engines
                print("\n📝 Manual Configuration Required")
                print(
                    "Since you're using the requests engine, you'll need to manually "
                    "specify selectors."
                )

                if scraping_type in (ScrapingType.LIST_DETAIL, ScrapingType.LIST_ONLY):
                    self._define_list_rules_manual(template)

                if scraping_type in (
                    ScrapingType.LIST_DETAIL,
                    ScrapingType.SINGLE_PAGE,
                ):
                    self._define_detail_rules_manual(template)

            # Step 9: Configure pattern extraction
            pattern_config = self._configure_pattern_extraction()
            if pattern_config:
                template_dict["detail_page_rules"][
                    "extraction_patterns"
                ] = pattern_config

            # Step 10: Configure fallback strategies
            fallback_config = self._configure_fallback_strategies()
            template_dict["fallback_strategies"] = fallback_config

            # Step 11: Save template
            template_name = self._get_template_name()
            if not template_name:
                template_name = "my_template"

            template_dict["name"] = f"{template_name}_{self.engine}"
            template_path = self.config.TEMPLATES_DIR / f"{template_dict['name']}.json"

            # Save template
            with open(template_path, "w", encoding="utf-8") as f:
                json.dump(template_dict, f, indent=2)

            print(f"\n✅ Template saved successfully to: {template_path}")
            print("\n🎉 Template creation complete!")

        except Exception as e:
            self.logger.error(f"Template creation failed: {e}", exc_info=True)
            print(f"\n❌ Template creation failed: {e}")

    # Delegate method calls to V1 instance for methods we don't override
    def __getattr__(self, name):
        """Delegate to V1 instance for non-overridden methods."""
        if hasattr(self._v1_instance, name):
            return getattr(self._v1_instance, name)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")