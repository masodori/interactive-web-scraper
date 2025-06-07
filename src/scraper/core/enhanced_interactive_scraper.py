# src/scraper/core/enhanced_interactive_scraper.py
"""
Enhanced Interactive Scraper with advanced features integrated into template creation.
"""

import json
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from datetime import datetime

from .base_scraper import BaseScraper
from ..models import (
    ScrapingTemplate,
    SiteInfo,
    ScrapingType,
    TemplateRules,
    # LoadStrategy,
    LoadStrategyConfig,
)
# from ..utils.selectors import (
#     normalize_selector,
#     generalize_selector,
#     make_relative_selector,
# )
from ..utils.input_validators import InputValidator, PromptFormatter
from ..extractors.pattern_extractor import PatternExtractor
# from ..extractors.advanced_selectors import AdvancedSelectors


class EnhancedInteractiveScraper(BaseScraper):
    """Enhanced interactive scraper with advanced features"""

    def __init__(self, headless: bool = False):
        """Initialize enhanced scraper"""
        super().__init__(headless=headless)
        self.pattern_extractor = PatternExtractor()
        self.input_validator = InputValidator()
        self.prompt_formatter = PromptFormatter()
        self._template_creation_attempts = 0
        self._max_creation_attempts = 3

    def create_template(self):
        """Enhanced template creation with all new features"""
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

            # Step 2: Select engine
            engine = self._select_engine()
            if not engine:
                return

            # For requests engine, we can't do interactive selection
            if engine == "requests":
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

            # Step 3: Navigate to URL (only for Selenium engine)
            if engine == "selenium":
                print(f"\n🌐 Navigating to {url}...")
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

                # Handle cookies
                print("\n🍪 Checking for cookie banners...")
                self._handle_cookies()

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
                engine=engine,
                site_info=site_info,
                scraping_type=scraping_type,
                list_page_rules=(
                    TemplateRules()
                    if scraping_type != ScrapingType.SINGLE_PAGE
                    else None
                ),
                detail_page_rules=TemplateRules(),
                version="2.1",  # Latest version
                created_at=datetime.now().isoformat(),
            )

            # Add advanced configurations
            template_dict = template.to_dict()
            template_dict["rate_limiting"] = rate_limiting

            # Step 8: Define rules based on type and engine
            if engine == "selenium":
                # Interactive selection for Selenium
                if scraping_type in (ScrapingType.LIST_DETAIL, ScrapingType.LIST_ONLY):
                    if not self._define_list_rules_enhanced(template):
                        return

                if scraping_type in (
                    ScrapingType.LIST_DETAIL,
                    ScrapingType.SINGLE_PAGE,
                ):
                    if not self._define_detail_rules_enhanced(template):
                        return
            else:
                # Manual configuration for non-Selenium engines
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

            template_dict["name"] = f"{template_name}_{engine}"
            template_path = self.config.TEMPLATES_DIR / f"{template_dict['name']}.json"

            # Check if file exists
            if template_path.exists():
                overwrite = self._get_choice_input(
                    f"Template '{template_name}' already exists. Overwrite?",
                    {"y": "Yes", "n": "No"},
                    default="n",
                )
                if overwrite != "y":
                    new_name = self._get_template_name("Enter new template name: ")
                    if new_name:
                        template_dict["name"] = f"{new_name}_{engine}"
                        template_path = (
                            self.config.TEMPLATES_DIR / f"{template_dict['name']}.json"
                        )

            # Save template
            try:
                with open(template_path, "w", encoding="utf-8") as f:
                    json.dump(template_dict, f, indent=2, ensure_ascii=False)

                print(f"\n✅ Template saved successfully to: {template_path}")
                self._display_template_summary(template_dict)
                print("\n🎉 Enhanced template creation complete!")

            except Exception as e:
                self.logger.error(f"Failed to save template: {e}")
                print(f"❌ Failed to save template: {e}")

        except KeyboardInterrupt:
            print("\n\n⚠️  Template creation cancelled by user.")
        except Exception as e:
            self.logger.error(f"Unexpected error in template creation: {e}")
            print(f"\n❌ Unexpected error: {e}")

    def _select_engine(self) -> Optional[str]:
        """Select scraping engine with detailed explanations"""
        print("\n⚙️  Select Scraping Engine:")
        print("=" * 40)

        engines = {
            "selenium": "Selenium (Default) - Full JavaScript support, interactive selection",
            "playwright": "Playwright - Faster JavaScript handling, modern browser automation",
            "requests": "Requests - Fast for static HTML, no JavaScript support",
        }

        # Check Playwright availability
        try:
            import playwright  # noqa: F401

            playwright_available = True
        except ImportError:
            playwright_available = False
            engines["playwright"] += " (NOT INSTALLED)"

        choice = self._get_choice_input("Select engine", engines, default="selenium")

        if choice == "playwright" and not playwright_available:
            print("\n❌ Playwright is not installed. Install with:")
            print("   pip install playwright")
            print("   playwright install")
            return self._select_engine()

        return choice

    def _configure_rate_limiting(self) -> Dict[str, Any]:
        """Configure rate limiting settings"""
        print("\n⏱️  Configure Rate Limiting:")
        print("=" * 40)

        presets = {
            "respectful_bot": "Respectful Bot - 0.2 req/sec, very slow but safe",
            "conservative": "Conservative - 0.5 req/sec, slow but respectful",
            "moderate": "Moderate - 1 req/sec, balanced approach",
            "aggressive": "Aggressive - 5 req/sec, fast but may trigger blocks",
            "none": "No rate limiting - Maximum speed (not recommended)",
        }

        choice = self._get_choice_input(
            "Select rate limiting preset", presets, default="respectful_bot"
        )

        if choice == "none":
            return {"enabled": False}

        return {"enabled": True, "preset": choice, "custom": None}

    def _configure_pattern_extraction(self) -> Optional[Dict[str, Any]]:
        """Configure pattern-based extraction"""
        print("\n🔍 Configure Pattern-Based Extraction:")
        print("=" * 40)
        print(
            "Pattern extraction can automatically find common data types without selectors."
        )

        use_patterns = self._get_choice_input(
            "Enable pattern-based extraction?",
            {"y": "Yes (Recommended)", "n": "No"},
            default="y",
        )

        if use_patterns != "y":
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
            "bar_admission": "Bar admissions and licenses",
        }

        print("\nSelect patterns to enable:")
        for pattern, description in available_patterns.items():
            enable = self._get_choice_input(
                f"  Enable {pattern} extraction ({description})?",
                {"y": "Yes", "n": "No"},
                default="y" if pattern in ["email", "phone", "education"] else "n",
            )

            if enable == "y":
                patterns[pattern] = {
                    "enabled": True,
                    "context_keywords": self.pattern_extractor.patterns[
                        pattern
                    ].context_keywords,
                }

        return patterns if patterns else None

    def _configure_fallback_strategies(self) -> Dict[str, Any]:
        """Configure fallback selector strategies"""
        print("\n🛡️  Configure Fallback Strategies:")
        print("=" * 40)
        print("Fallback strategies help find elements when primary selectors fail.")

        strategies = {
            "text_based_selection": "Find elements by their text content",
            "proximity_selection": "Find elements near labels",
            "pattern_matching_primary": "Use pattern extraction as primary method",
        }

        config = {}
        for strategy, description in strategies.items():
            enable = self._get_choice_input(
                f"Enable {description}?", {"y": "Yes", "n": "No"}, default="y"
            )
            config[strategy] = enable == "y"

        return config

    def _define_list_rules_enhanced(self, template: ScrapingTemplate) -> bool:
        """Enhanced list rules definition with advanced options"""
        rules = template.list_page_rules
        if not rules:
            return False

        print("\n" + "=" * 40)
        print("📋 List Page Configuration (Enhanced)")
        print("=" * 40)

        # First do the standard interactive selection
        if not self._define_list_rules_safe(template):
            return False

        # Then add enhanced options
        print("\n🚀 Advanced List Page Options:")

        # Configure load strategy
        print("\n📄 Load Strategy Configuration:")
        load_strategy = self._configure_load_strategy()
        rules.load_strategy = LoadStrategyConfig(**load_strategy)

        # Add text-based fallbacks for fields
        print("\n🔤 Text-Based Fallbacks:")
        print("Define text labels to search for if CSS selectors fail.")

        for field_name in rules.fields:
            label_text = self._get_user_input_with_validation(
                f"Label text for '{field_name}' field (or Enter to skip): ",
                allow_empty=True,
            )
            if label_text:
                if "advanced_selectors" not in template.list_page_rules.__dict__:
                    template.list_page_rules.__dict__["advanced_selectors"] = {
                        "use_text_content": {}
                    }
                template.list_page_rules.__dict__["advanced_selectors"][
                    "use_text_content"
                ][field_name] = label_text

        return True

    def _define_detail_rules_enhanced(self, template: ScrapingTemplate) -> bool:
        """Enhanced detail rules definition with pattern extraction"""
        # First do standard selection
        if not self._define_detail_rules_safe(template):
            return False

        rules = template.detail_page_rules

        print("\n🚀 Advanced Detail Page Options:")

        # Add text-based fallbacks
        print("\n🔤 Text-Based Fallbacks:")
        advanced_selectors = {"use_text_content": {}}

        for field_name in rules.fields:
            label_text = self._get_user_input_with_validation(
                f"Label text for '{field_name}' field (or Enter to skip): ",
                allow_empty=True,
            )
            if label_text:
                advanced_selectors["use_text_content"][field_name] = label_text

        if advanced_selectors["use_text_content"]:
            template.detail_page_rules.__dict__["advanced_selectors"] = (
                advanced_selectors
            )

        return True

    def _define_list_rules_manual(self, template: ScrapingTemplate):
        """Manual rule definition for non-Selenium engines"""
        rules = template.list_page_rules

        print("\n📋 List Page Manual Configuration")
        print("=" * 40)

        # Repeating item selector
        selector = self._get_user_input_with_validation(
            "Enter CSS selector for repeating items (e.g., 'div.lawyer-item'): ",
            allow_empty=False,
        )
        rules.repeating_item_selector = selector

        # Fields
        print("\n📝 Define fields to extract from each item:")
        while True:
            field_name = self._get_user_input_with_validation(
                "Field name (or Enter to finish): ", allow_empty=True
            )
            if not field_name:
                break

            selector = self._get_user_input_with_validation(
                f"CSS selector for {field_name}: ", allow_empty=False
            )
            rules.fields[field_name] = selector

        # Profile link for list+detail
        if template.scraping_type == ScrapingType.LIST_DETAIL:
            link_selector = self._get_user_input_with_validation(
                "CSS selector for detail page link: ", allow_empty=False
            )
            rules.profile_link_selector = link_selector

        # Load strategy
        load_strategy = self._configure_load_strategy()
        rules.load_strategy = LoadStrategyConfig(**load_strategy)

    def _define_detail_rules_manual(self, template: ScrapingTemplate):
        """Manual detail rule definition"""
        rules = template.detail_page_rules

        print("\n📄 Detail Page Manual Configuration")
        print("=" * 40)

        print("📝 Define fields to extract:")
        while True:
            field_name = self._get_user_input_with_validation(
                "Field name (or Enter to finish): ", allow_empty=True
            )
            if not field_name:
                break

            # Ask if they want to use pattern extraction for this field
            use_pattern = self._get_choice_input(
                f"Use pattern extraction for {field_name}?",
                {"y": "Yes", "n": "No, I'll provide a selector"},
                default=(
                    "y"
                    if field_name.lower() in ["email", "phone", "education"]
                    else "n"
                ),
            )

            if use_pattern == "n":
                selector = self._get_user_input_with_validation(
                    f"CSS selector for {field_name}: ", allow_empty=False
                )
                rules.fields[field_name] = selector
            else:
                # Leave selector empty to trigger pattern extraction
                rules.fields[field_name] = ""

    def _configure_load_strategy(self) -> Dict[str, Any]:
        """Configure how to load more content"""
        strategies = {
            "auto": "Auto-detect (try to find load more buttons)",
            "button": "Click a specific button",
            "scroll": "Infinite scroll",
            "pagination": "Traditional pagination (next button)",
            "none": "No dynamic loading",
        }

        strategy_type = self._get_choice_input(
            "How does the site load more content?", strategies, default="auto"
        )

        config = {
            "type": strategy_type,
            "pause_time": 2.0,
            "consecutive_failure_limit": 3,
            "extended_wait_multiplier": 2.0,
        }

        if strategy_type == "button":
            selector = self._get_user_input_with_validation(
                "Enter CSS selector for load more button: ", allow_empty=False
            )
            config["button_selector"] = selector
        elif strategy_type == "pagination":
            selector = self._get_user_input_with_validation(
                "Enter CSS selector for next page button: ", allow_empty=False
            )
            config["pagination_next_selector"] = selector

        return config

    def _display_template_summary(self, template: Dict[str, Any]):
        """Display comprehensive template summary"""
        print("\n📊 Template Summary:")
        print("=" * 40)
        print(f"  - Name: {template['name']}")
        print(f"  - Version: {template.get('version', '1.0')}")
        print(f"  - Engine: {template.get('engine', 'selenium')}")
        print(f"  - Type: {template['scraping_type']}")

        if template.get("list_page_rules"):
            rules = template["list_page_rules"]
            print(f"  - List fields: {len(rules.get('fields', {}))}")
            print(
                f"  - Load strategy: {rules.get('load_strategy', {}).get('type', 'none')}"
            )

        if template.get("detail_page_rules"):
            rules = template["detail_page_rules"]
            print(f"  - Detail fields: {len(rules.get('fields', {}))}")

            if rules.get("extraction_patterns"):
                print(
                    f"  - Pattern extraction: {len(rules['extraction_patterns'])} patterns enabled"
                )

        if template.get("rate_limiting", {}).get("enabled"):
            print(f"  - Rate limiting: {template['rate_limiting']['preset']}")

        if template.get("fallback_strategies"):
            enabled = sum(1 for v in template["fallback_strategies"].values() if v)
            print(f"  - Fallback strategies: {enabled} enabled")

        print("\n✨ Advanced Features:")
        features = []

        if template.get("engine") != "selenium":
            features.append("Alternative engine")
        if template.get("rate_limiting", {}).get("enabled"):
            features.append("Rate limiting")
        if template.get("detail_page_rules", {}).get("extraction_patterns"):
            features.append("Pattern extraction")
        if template.get("fallback_strategies"):
            features.append("Fallback strategies")
        if template.get("detail_page_rules", {}).get("advanced_selectors"):
            features.append("Advanced selectors")

        for feature in features:
            print(f"  ✓ {feature}")

    def _get_template_name(self, prompt: str = None) -> Optional[str]:
        """Get template name with validation"""
        if not prompt:
            prompt = "💾 Enter template name (letters, numbers, underscores only): "

        return self._get_user_input_with_validation(
            prompt,
            validator=lambda x: (
                (True, x.replace(" ", "_").replace("-", "_"))
                if x.replace(" ", "_").replace("-", "_").replace("_", "").isalnum()
                else (False, "Name must contain only letters, numbers, and underscores")
            ),
            allow_empty=True,
        )

    def _handle_cookies(self):
        """Enhanced cookie handling"""
        cookie_selector = self._get_user_input_with_validation(
            "Enter custom cookie selector (or press Enter to auto-detect): ",
            allow_empty=True,
        )

        try:
            result = self.cookie_handler.accept_cookies(
                [cookie_selector] if cookie_selector else None
            )
            if result:
                print(f"✅ Cookie banner handled using: {result}")
            else:
                print("ℹ️  No cookie banner detected or handled")
        except Exception as e:
            self.logger.error(f"Cookie handling error: {e}")
            print("⚠️  Error handling cookies, continuing anyway...")

    def _select_scraping_type(self) -> Optional[ScrapingType]:
        """Select scraping type with better descriptions"""
        types = {
            "1": "List + Detail Pages - Extract from list, then follow links to detail pages",
            "2": "List Only - Extract data from list page only",
            "3": "Single Page - Extract from current page only",
        }

        choice = self._get_choice_input("📋 Select scraping type", types, default="1")

        type_map = {
            "1": ScrapingType.LIST_DETAIL,
            "2": ScrapingType.LIST_ONLY,
            "3": ScrapingType.SINGLE_PAGE,
        }

        return type_map.get(choice)

    def _get_url_with_validation(self) -> Optional[str]:
        """Get URL with validation"""
        url = input("\n🌐 Enter URL to scrape: ").strip()
        if not url:
            print("❌ URL cannot be empty")
            return None

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            urlparse(url)
            return url
        except Exception as e:
            print(f"❌ Invalid URL: {e}")
            return None

    def _get_choice_input(
        self, prompt: str, choices: Dict[str, str], default: str = None
    ) -> Optional[str]:
        """Get choice input from user"""
        print(f"\n{prompt}")
        for key, desc in choices.items():
            print(f"  {key}: {desc}")

        choice = (
            input(
                f"Choose [{'/'.join(choices.keys())}]"
                f"{f' (default: {default})' if default else ''}: "
            )
            .strip()
            .lower()
        )

        if not choice and default:
            return default

        if choice in choices:
            return choice

        print("❌ Invalid choice")
        return None

    def _get_user_input_with_validation(
        self, prompt: str, validator=None, allow_empty: bool = False
    ) -> Optional[str]:
        """Get user input with optional validation"""
        value = input(prompt).strip()

        if not value and not allow_empty:
            print("❌ Value cannot be empty")
            return None

        if validator and value:
            valid, result = validator(value)
            if not valid:
                print(f"❌ {result}")
                return None
            return result

        return value

    def _safe_navigate(self, url: str) -> bool:
        """Safely navigate to URL"""
        try:
            return self.navigate_to(url)
        except Exception as e:
            self.logger.error(f"Navigation error: {e}")
            return False

    def _define_list_rules_safe(self, template: ScrapingTemplate) -> bool:
        """Define list rules with safe fallbacks"""
        # This is a placeholder - in a full implementation, this would handle
        # interactive element selection
        print("\n⚠️  Interactive selection requires additional implementation")
        print("Using manual configuration instead...")

        self._define_list_rules_manual(template)
        return True

    def _define_detail_rules_safe(self, template: ScrapingTemplate) -> bool:
        """Define detail rules with safe fallbacks"""
        # This is a placeholder - in a full implementation, this would handle
        # interactive element selection
        print("\n⚠️  Interactive selection requires additional implementation")
        print("Using manual configuration instead...")

        self._define_detail_rules_manual(template)
        return True
