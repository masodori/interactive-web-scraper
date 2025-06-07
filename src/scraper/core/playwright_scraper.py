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
        self.logger.info("🚀 Starting Playwright browser initialization...")
        
        self.playwright = await async_playwright().start()
        self.logger.info("✅ Playwright runtime started")
        
        # Select browser
        if self.browser_type == "firefox":
            browser_engine = self.playwright.firefox
            self.logger.info("🦊 Using Firefox browser engine")
        elif self.browser_type == "webkit":
            browser_engine = self.playwright.webkit
            self.logger.info("🍎 Using WebKit browser engine")
        else:
            browser_engine = self.playwright.chromium
            self.logger.info("🌐 Using Chromium browser engine")
        
        # Launch browser with options
        self.logger.info(f"🔧 Launching browser (headless: {self.headless})...")
        self.browser = await browser_engine.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        self.logger.info("✅ Browser launched successfully")
        
        # Create context with viewport and user agent
        self.logger.info("🖥️  Creating browser context with viewport 1920x1080...")
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            # Add network debugging
            extra_http_headers={'Accept-Language': 'en-US,en;q=0.9'}
        )
        self.logger.info("✅ Browser context created")
        
        # Enable request/response logging
        self.logger.info("🔧 Setting up network debugging...")
        context.on("request", lambda request: self.logger.debug(f"📤 Request: {request.method} {request.url}"))
        context.on("response", lambda response: self.logger.debug(f"📥 Response: {response.status} {response.url}"))
        context.on("requestfailed", lambda request: self.logger.warning(f"❌ Request failed: {request.url} - {request.failure}"))
        self.logger.info("✅ Network debugging enabled")
        
        # Create page
        self.logger.info("📄 Creating new page...")
        self.page = await context.new_page()
        self.logger.info("✅ New page created")
        
        # Set default timeout
        timeout_ms = self.config.DEFAULT_TIMEOUT * 1000
        self.page.set_default_timeout(timeout_ms)
        self.logger.info(f"⏱️  Default timeout set to {timeout_ms}ms")
        
        self.logger.info(f"🎉 Playwright browser fully initialized ({self.browser_type})")
    
    async def navigate_to(self, url: str, wait_until: str = "networkidle") -> bool:
        """
        Navigate to URL with Playwright with fallback strategies
        
        Args:
            url: URL to navigate to
            wait_until: Wait condition (load, domcontentloaded, networkidle)
            
        Returns:
            True if successful
        """
        self.logger.info(f"🌐 Navigating to: {url}")
        self.logger.info(f"⏳ Primary wait condition: {wait_until}")
        
        # Define fallback strategies in order of preference
        wait_strategies = [wait_until, "domcontentloaded", "load"]
        timeout_ms = 15000  # 15 seconds per attempt (more lenient)
        
        for i, strategy in enumerate(wait_strategies):
            try:
                if i > 0:
                    self.logger.warning(f"🔄 Trying fallback strategy #{i}: {strategy}")
                
                self.logger.info(f"⏱️  Attempting navigation with {strategy} (timeout: {timeout_ms/1000}s)")
                
                await self.page.goto(url, wait_until=strategy, timeout=timeout_ms)
                self.current_url = url
                
                # Get page title for confirmation
                title = await self.page.title()
                self.logger.info(f"✅ Successfully navigated to: {url}")
                self.logger.info(f"📄 Page title: {title}")
                self.logger.info(f"🎯 Wait strategy that worked: {strategy}")
                
                return True
                
            except PlaywrightTimeout:
                self.logger.warning(f"⏰ Timeout with {strategy} strategy (waited {timeout_ms/1000}s)")
                if i == len(wait_strategies) - 1:
                    self.logger.error(f"❌ All navigation strategies failed for {url}")
                    # Try one final attempt with no wait condition
                    try:
                        self.logger.info("🚨 Final attempt: navigation with no wait condition")
                        await self.page.goto(url, timeout=10000)
                        self.current_url = url
                        title = await self.page.title()
                        self.logger.info(f"✅ Final attempt succeeded: {title}")
                        return True
                    except:
                        self.logger.error("❌ Final navigation attempt also failed")
                        return False
                continue
                
            except Exception as e:
                self.logger.error(f"❌ Failed to navigate to {url} with {strategy}: {e}")
                if i == len(wait_strategies) - 1:
                    return False
                continue
        
        return False
    
    async def navigate_to_smart(self, url: str) -> bool:
        """
        Smart navigation that chooses the best wait condition based on the URL
        """
        self.logger.info(f"🧠 Smart navigation to: {url}")
        
        # Determine best wait condition based on common site patterns
        if any(domain in url.lower() for domain in ['linkedin', 'facebook', 'twitter', 'instagram']):
            wait_condition = "domcontentloaded"  # Social sites often have continuous loading
            self.logger.info("📱 Detected social media site - using domcontentloaded")
        elif any(pattern in url.lower() for pattern in ['spa', 'app', 'react', 'angular', 'vue']):
            wait_condition = "domcontentloaded"  # SPAs often have continuous network activity
            self.logger.info("⚛️  Detected SPA patterns - using domcontentloaded")
        elif any(pattern in url.lower() for pattern in ['shop', 'store', 'ecommerce', 'amazon']):
            wait_condition = "domcontentloaded"  # E-commerce sites often load additional content
            self.logger.info("🛒 Detected e-commerce site - using domcontentloaded")
        elif any(pattern in url.lower() for pattern in ['law', 'legal', 'firm', 'attorney', 'lawyer']):
            wait_condition = "load"  # Law firms often have complex loading - use basic load
            self.logger.info("⚖️  Detected law firm site - using basic load")
        elif any(pattern in url.lower() for pattern in ['wordpress', 'wp-', 'wix', 'squarespace']):
            wait_condition = "domcontentloaded"  # CMS sites often have dynamic loading
            self.logger.info("📝 Detected CMS site - using domcontentloaded")
        elif 'gibsondunn' in url.lower():
            wait_condition = "domcontentloaded"  # Use standard navigation for Gibson Dunn
            self.logger.info("🏢 Detected Gibson Dunn site - using domcontentloaded")
        else:
            wait_condition = "domcontentloaded"  # Changed default to be more reliable
            self.logger.info("🌐 Using safe default: domcontentloaded")
        
        return await self.navigate_to(url, wait_condition)
    
    async def navigate_to_fast(self, url: str) -> bool:
        """
        Ultra-fast navigation that doesn't wait for any conditions
        """
        self.logger.info(f"⚡ Ultra-fast navigation to: {url}")
        self.logger.info("🔧 Using 3-second timeout with 'commit' wait condition")
        
        try:
            # Add detailed pre-navigation logging
            self.logger.info("📡 Starting page.goto() call...")
            start_time = asyncio.get_event_loop().time()
            
            # Navigate with very aggressive timeout
            await self.page.goto(url, timeout=3000, wait_until="commit")
            
            end_time = asyncio.get_event_loop().time()
            elapsed = end_time - start_time
            self.logger.info(f"✅ page.goto() completed in {elapsed:.2f}s")
            
            self.current_url = url
            
            # Give it a moment to start loading
            self.logger.info("⏳ Waiting 1 second for initial content...")
            await asyncio.sleep(1)
            
            # Check if we can get basic page info
            try:
                self.logger.info("📄 Attempting to get page title...")
                title = await self.page.title()
                self.logger.info(f"⚡ Fast navigation successful: {title}")
                
                # Check if page has basic content
                self.logger.info("🔍 Checking for basic page content...")
                html = await self.page.content()
                if len(html) > 1000:
                    self.logger.info(f"📝 Page content looks good ({len(html)} chars)")
                else:
                    self.logger.warning(f"⚠️  Page content seems minimal ({len(html)} chars)")
                    
            except Exception as e:
                self.logger.warning(f"⚠️  Could not get page title: {e}")
                title = "Unknown"
                self.logger.info("⚡ Fast navigation completed (title unavailable)")
            
            return True
            
        except asyncio.TimeoutError:
            self.logger.error("❌ Fast navigation timed out after 3 seconds")
            return False
        except Exception as e:
            self.logger.error(f"❌ Fast navigation failed: {type(e).__name__}: {e}")
            return False
    
    async def navigate_to_minimal(self, url: str) -> bool:
        """
        Absolutely minimal navigation with maximum logging and diagnostics
        """
        self.logger.info(f"🚀 MINIMAL navigation to: {url}")
        
        # First, test basic connectivity
        self.logger.info("🔍 DIAGNOSTIC: Testing basic connectivity...")
        try:
            import socket
            import urllib.parse
            
            parsed = urllib.parse.urlparse(url)
            hostname = parsed.hostname
            port = parsed.port or (443 if parsed.scheme == 'https' else 80)
            
            self.logger.info(f"🌐 Testing connection to {hostname}:{port}")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((hostname, port))
            sock.close()
            
            if result == 0:
                self.logger.info("✅ Network connectivity confirmed")
            else:
                self.logger.error(f"❌ Cannot connect to {hostname}:{port} (error: {result})")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Connectivity test failed: {e}")
            return False
        
        # Try navigation with aggressive settings
        self.logger.info("🔧 Using 2-second timeout with NO wait condition")
        
        try:
            # Set a very short page timeout
            self.logger.info("⚙️  Setting page timeout to 2 seconds...")
            self.page.set_default_timeout(2000)
            
            # Try the most basic navigation possible
            self.logger.info("📡 Attempting page.goto() with no wait condition...")
            start_time = asyncio.get_event_loop().time()
            
            # Use asyncio.wait_for for additional timeout control
            await asyncio.wait_for(
                self.page.goto(url, timeout=2000),
                timeout=3.0  # Extra layer of timeout
            )
            
            end_time = asyncio.get_event_loop().time()
            elapsed = end_time - start_time
            self.logger.info(f"✅ Minimal navigation completed in {elapsed:.2f}s")
            
            self.current_url = url
            return True
            
        except asyncio.TimeoutError:
            self.logger.error("❌ Minimal navigation timed out (asyncio.wait_for)")
        except Exception as e:
            self.logger.error(f"❌ Minimal navigation failed: {type(e).__name__}: {e}")
            
        # Reset timeout
        try:
            self.page.set_default_timeout(10000)
        except:
            pass
            
        return False
    
    async def wait_for_selector(self, selector: str, timeout: int = None) -> bool:
        """Wait for element to appear"""
        timeout = timeout or self.config.DEFAULT_TIMEOUT
        self.logger.info(f"⏳ Waiting for selector: {selector} (timeout: {timeout}s)")
        
        try:
            await self.page.wait_for_selector(selector, timeout=timeout * 1000)
            self.logger.info(f"✅ Selector found: {selector}")
            return True
        except PlaywrightTimeout:
            self.logger.warning(f"⏰ Timeout waiting for selector: {selector}")
            return False
    
    async def get_text(self, selector: str) -> Optional[str]:
        """Get text content of element"""
        self.logger.debug(f"🔍 Getting text for selector: {selector}")
        
        try:
            element = await self.page.query_selector(selector)
            if element:
                text = await element.text_content()
                text_preview = text[:100] + "..." if len(text) > 100 else text
                self.logger.debug(f"✅ Text extracted: {text_preview}")
                return text
            else:
                self.logger.debug(f"❌ Element not found: {selector}")
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
        self.logger.info(f"👆 Clicking element: {selector}")
        
        try:
            await self.page.click(selector, timeout=timeout * 1000)
            self.logger.info(f"✅ Successfully clicked: {selector}")
            return True
        except PlaywrightTimeout:
            self.logger.warning(f"⏰ Timeout clicking {selector} (timeout: {timeout}s)")
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
        self.logger.info(f"📜 Starting infinite scroll (pause: {pause}s)")
        scrolls = 0
        last_height = await self.page.evaluate("document.body.scrollHeight")
        self.logger.info(f"📏 Initial page height: {last_height}px")
        
        while True:
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(pause)
            scrolls += 1
            
            new_height = await self.page.evaluate("document.body.scrollHeight")
            self.logger.debug(f"📜 Scroll #{scrolls}: {last_height}px → {new_height}px")
            
            if new_height == last_height:
                self.logger.info(f"✅ Reached bottom after {scrolls} scrolls")
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
        self.logger.info("🛑 Starting Playwright browser cleanup...")
        
        if self.page:
            self.logger.info("📄 Closing page...")
            await self.page.close()
            self.logger.info("✅ Page closed")
            
        if self.browser:
            self.logger.info("🌐 Closing browser...")
            await self.browser.close()
            self.logger.info("✅ Browser closed")
            
        if self.playwright:
            self.logger.info("🎭 Stopping Playwright runtime...")
            await self.playwright.stop()
            self.logger.info("✅ Playwright runtime stopped")
        
        self.logger.info("🎉 Playwright browser fully closed")
    
    # Synchronous wrapper methods for compatibility
    def navigate_to_sync(self, url: str) -> bool:
        """Synchronous wrapper for navigate_to"""
        self.logger.info(f"🔄 Running async navigate_to synchronously for: {url}")
        return asyncio.run(self.navigate_to(url))
    
    def get_text_sync(self, selector: str) -> Optional[str]:
        """Synchronous wrapper for get_text"""
        self.logger.debug(f"🔄 Running async get_text synchronously for: {selector}")
        return asyncio.run(self.get_text(selector))
    
    def click_sync(self, selector: str) -> bool:
        """Synchronous wrapper for click"""
        self.logger.info(f"🔄 Running async click synchronously for: {selector}")
        return asyncio.run(self.click(selector))
    
    def close_sync(self):
        """Synchronous wrapper for close"""
        self.logger.info("🔄 Running async close synchronously")
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