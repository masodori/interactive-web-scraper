# src/scraper/core/multi_engine_interactive_scraper.py
"""
Multi-engine version of EnhancedInteractiveScraper that properly supports
Selenium, Playwright, and Requests without re-selecting the engine.
"""

from .enhanced_interactive_scraper import EnhancedInteractiveScraper
from .multi_engine_scraper import MultiEngineScraper


class MultiEngineInteractiveScraper(EnhancedInteractiveScraper, MultiEngineScraper):
    """
    Enhanced interactive scraper with multi-engine support.
    Combines EnhancedInteractiveScraper functionality with MultiEngineScraper's
    multi-engine support.
    """
    
    def __init__(self, engine: str = "selenium", headless: bool = False):
        """
        Initialize with a specific engine.
        
        Args:
            engine: The engine to use ("selenium", "playwright", "requests")
            headless: Whether to run in headless mode
        """
        # Initialize MultiEngineScraper first to set up the driver
        MultiEngineScraper.__init__(self, engine=engine, headless=headless)
        
        # Then initialize the enhanced features
        self.pattern_extractor = self._v1_instance.pattern_extractor if hasattr(self, '_v1_instance') else None
        self.input_validator = self._v1_instance.input_validator if hasattr(self, '_v1_instance') else None
        self.prompt_formatter = self._v1_instance.prompt_formatter if hasattr(self, '_v1_instance') else None
        self._template_creation_attempts = 0
        self._max_creation_attempts = 3
        
        # Import the necessary modules for the parent class methods
        from ..extractors.pattern_extractor import PatternExtractor
        from ..utils.input_validators import InputValidator, PromptFormatter
        
        if not self.pattern_extractor:
            self.pattern_extractor = PatternExtractor()
        if not self.input_validator:
            self.input_validator = InputValidator()
        if not self.prompt_formatter:
            self.prompt_formatter = PromptFormatter()
    
    def _select_engine(self):
        """
        Override engine selection to return the already initialized engine.
        This prevents re-selection of engine during template creation.
        """
        # Just return the engine that was set during initialization
        return self.engine
    
    def _safe_navigate(self, url: str) -> bool:
        """Navigate to URL with engine-appropriate method."""
        if self.engine == "requests":
            # Requests doesn't navigate
            return True
        return self.navigate_to(url)
    
    def _handle_cookies(self):
        """Handle cookies if applicable."""
        if self.engine == "selenium" and self.cookie_handler:
            self.cookie_handler.handle_cookie_banners()
        # Playwright and Requests don't have cookie handler implemented yet