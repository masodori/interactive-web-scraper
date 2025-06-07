# src/scraper/core/playwright_scraper.py
"""
Playwright-based scraper for JavaScript-heavy sites with better performance than Selenium.
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

try:
    from playwright.async_api import async_playwright, Page, Browser, Playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    
from ..config import Config
from ..handlers import CookieHandler


class PlaywrightScraper:
    """
    A scraper using Playwright for modern JavaScript rendering with better performance.
    Supports both headless and headed modes.
    """
    
    def __init__(self, headless: bool = True, browser_type: str = "chromium"):
        """
        Initialize Playwright scraper
        
        Args:
            headless: Run browser in headless mode
            browser_type: Browser to use (chromium, firefox, webkit)
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError(
                "Playwright is not installed. Install it with: pip install playwright && playwright install"
            )
        
        self.logger = logging.getLogger(f'{__name__}.PlaywrightScraper')
        self.config = Config
        self.headless = headless
        self.browser_type = browser_type
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.current_url: Optional[str] = None
        self._loop = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self._init_browser()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def _init_browser(self):
        """Initialize Playwright browser and page"""
        self.playwright = await async_playwright().start()
        
        # Select browser
        if self.browser_type == "firefox":
            browser_engine = self.playwright.firefox
        elif self.browser_type == "webkit":
            browser_engine = self.playwright.webkit
        else:
            browser_engine = self.playwright.chromium
        
        # Launch browser with options
        self.browser = await browser_engine.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        # Create context with viewport and user agent
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        
        # Create page
        self.page = await context.new_page()
        
        # Set default timeout
        self.page.set_default_timeout(self.config.DEFAULT_TIMEOUT * 1000)
        
        self.logger.info(f"Playwright browser initialized ({self.browser_type})")
    
    async def navigate_to(self, url: str, wait_until: str = "networkidle") -> bool:
        """
        Navigate to URL with Playwright
        
        Args:
            url: URL to navigate to
            wait_until: Wait condition (load, domcontentloaded, networkidle)
            
        Returns:
            True if successful
        """
        try:
            await self.page.goto(url, wait_until=wait_until)
            self.current_url = url
            self.logger.info(f"Navigated to {url}")
            return True
        except PlaywrightTimeout:
            self.logger.error(f"Timeout navigating to {url}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to navigate to {url}: {e}")
            return False
    
    async def wait_for_selector(self, selector: str, timeout: int = None) -> bool:
        """Wait for element to appear"""
        timeout = timeout or self.config.DEFAULT_TIMEOUT
        try:
            await self.page.wait_for_selector(selector, timeout=timeout * 1000)
            return True
        except PlaywrightTimeout:
            return False
    
    async def get_text(self, selector: str) -> Optional[str]:
        """Get text content of element"""
        try:
            element = await self.page.query_selector(selector)
            if element:
                return await element.text_content()
            return None
        except Exception as e:
            self.logger.debug(f"Error getting text from {selector}: {e}")
            return None
    
    async def get_texts(self, selector: str) -> List[str]:
        """Get text content of multiple elements"""
        try:
            elements = await self.page.query_selector_all(selector)
            texts = []
            for element in elements:
                text = await element.text_content()
                if text:
                    texts.append(text.strip())
            return texts
        except Exception as e:
            self.logger.debug(f"Error getting texts from {selector}: {e}")
            return []
    
    async def get_attribute(self, selector: str, attribute: str) -> Optional[str]:
        """Get attribute value of element"""
        try:
            element = await self.page.query_selector(selector)
            if element:
                return await element.get_attribute(attribute)
            return None
        except Exception as e:
            self.logger.debug(f"Error getting attribute from {selector}: {e}")
            return None
    
    async def click(self, selector: str, timeout: int = None) -> bool:
        """Click element"""
        timeout = timeout or self.config.DEFAULT_TIMEOUT
        try:
            await self.page.click(selector, timeout=timeout * 1000)
            return True
        except PlaywrightTimeout:
            self.logger.warning(f"Timeout clicking {selector}")
            return False
        except Exception as e:
            self.logger.warning(f"Error clicking {selector}: {e}")
            return False
    
    async def scroll_to_bottom(self, pause: float = 2.0) -> int:
        """
        Scroll to bottom of page
        
        Returns:
            Number of scrolls performed
        """
        scrolls = 0
        last_height = await self.page.evaluate("document.body.scrollHeight")
        
        while True:
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(pause)
            scrolls += 1
            
            new_height = await self.page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        
        return scrolls
    
    async def handle_cookies(self, selectors: List[str] = None) -> bool:
        """
        Handle cookie consent banners
        
        Args:
            selectors: Custom selectors to try
            
        Returns:
            True if cookies handled
        """
        default_selectors = [
            "button:has-text('Accept')",
            "button:has-text('Agree')",
            "button:has-text('OK')",
            "button:has-text('Got it')",
            "a:has-text('Accept')"
        ]
        
        selectors_to_try = (selectors or []) + default_selectors
        
        for selector in selectors_to_try:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    await element.click()
                    await asyncio.sleep(1)
                    self.logger.info(f"Clicked cookie button: {selector}")
                    return True
            except Exception:
                continue
        
        return False
    
    async def execute_script(self, script: str) -> Any:
        """Execute JavaScript in page context"""
        try:
            return await self.page.evaluate(script)
        except Exception as e:
            self.logger.error(f"Error executing script: {e}")
            return None
    
    async def take_screenshot(self, path: str = None) -> Optional[str]:
        """Take screenshot of current page"""
        if not path:
            path = str(self.config.OUTPUT_DIR / "screenshot.png")
        
        try:
            await self.page.screenshot(path=path, full_page=True)
            self.logger.info(f"Screenshot saved to {path}")
            return path
        except Exception as e:
            self.logger.error(f"Error taking screenshot: {e}")
            return None
    
    async def get_page_content(self) -> str:
        """Get full page HTML content"""
        return await self.page.content()
    
    async def wait_for_navigation(self, timeout: int = None) -> bool:
        """Wait for navigation to complete"""
        timeout = timeout or self.config.DEFAULT_TIMEOUT
        try:
            await self.page.wait_for_navigation(timeout=timeout * 1000)
            return True
        except PlaywrightTimeout:
            return False
    
    async def reload(self) -> bool:
        """Reload current page"""
        try:
            await self.page.reload()
            return True
        except Exception as e:
            self.logger.error(f"Error reloading page: {e}")
            return False
    
    async def go_back(self) -> bool:
        """Navigate back in history"""
        try:
            await self.page.go_back()
            return True
        except Exception:
            return False
    
    async def close(self):
        """Close browser and cleanup"""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        
        self.logger.info("Playwright browser closed")
    
    # Synchronous wrapper methods for compatibility
    def navigate_to_sync(self, url: str) -> bool:
        """Synchronous wrapper for navigate_to"""
        return asyncio.run(self.navigate_to(url))
    
    def get_text_sync(self, selector: str) -> Optional[str]:
        """Synchronous wrapper for get_text"""
        return asyncio.run(self.get_text(selector))
    
    def click_sync(self, selector: str) -> bool:
        """Synchronous wrapper for click"""
        return asyncio.run(self.click(selector))
    
    def close_sync(self):
        """Synchronous wrapper for close"""
        asyncio.run(self.close())


class PlaywrightExtractor:
    """Data extraction utilities for Playwright"""
    
    def __init__(self, page: Page):
        self.page = page
        self.logger = logging.getLogger(f'{__name__}.PlaywrightExtractor')
    
    async def extract_table(self, selector: str) -> List[Dict[str, Any]]:
        """Extract table data"""
        try:
            # Get headers
            headers = await self.page.eval_on_selector_all(
                f"{selector} thead th, {selector} tr:first-child th, {selector} tr:first-child td",
                "elements => elements.map(e => e.textContent.trim())"
            )
            
            if not headers:
                return []
            
            # Get rows
            rows = await self.page.eval_on_selector_all(
                f"{selector} tbody tr, {selector} tr:not(:first-child)",
                """rows => rows.map(row => 
                    Array.from(row.querySelectorAll('td')).map(cell => cell.textContent.trim())
                )"""
            )
            
            # Convert to list of dicts
            result = []
            for row in rows:
                if len(row) == len(headers):
                    result.append(dict(zip(headers, row)))
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error extracting table: {e}")
            return []
    
    async def extract_links(self, container_selector: str, link_selector: str = "a[href]") -> List[Dict[str, str]]:
        """Extract all links within container"""
        try:
            return await self.page.eval_on_selector_all(
                f"{container_selector} {link_selector}",
                """links => links.map(link => ({
                    href: link.href,
                    text: link.textContent.trim(),
                    title: link.title || ''
                }))"""
            )
        except Exception as e:
            self.logger.error(f"Error extracting links: {e}")
            return []
    
    async def extract_structured_data(self, container_selector: str, field_map: Dict[str, str]) -> Dict[str, Any]:
        """Extract structured data using field mapping"""
        try:
            container = await self.page.query_selector(container_selector)
            if not container:
                return {}
            
            data = {}
            for field_name, selector in field_map.items():
                try:
                    element = await container.query_selector(selector)
                    if element:
                        data[field_name] = await element.text_content()
                except Exception:
                    data[field_name] = None
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error extracting structured data: {e}")
            return {}