"""
Playwright Stealth Crawler
Layer 1: Most powerful anti-detection using CDP
"""
import asyncio
from typing import List, Dict, Any, Optional
from urllib.parse import quote, urlparse, parse_qs
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from app.utils.user_agents import get_desktop_user_agent
from app.utils.delays import page_load_delay, search_delay, gaussian_delay


class PlaywrightCrawler:
    """Playwright crawler with CDP stealth injection"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        
    async def __aenter__(self):
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
        
    async def start(self):
        """Start browser with stealth configuration"""
        self.playwright = await async_playwright().start()
        
        # Launch browser with stealth args
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-infobars',
                '--window-size=1920,1080'
            ]
        )
        
        # Create context with realistic settings
        user_agent = get_desktop_user_agent()
        
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=user_agent,
            locale='en-US',
            timezone_id='America/Sao_Paulo',
            geolocation={'latitude': -23.5505, 'longitude': -46.6333},
            permissions=['geolocation'],
            color_scheme='light',
            device_scale_factor=1
        )
        
        print(f"  🎭 Playwright started (UA: {user_agent[:50]}...)")
        
    async def stop(self):
        """Stop browser"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
            
    async def inject_stealth(self, page: Page):
        """
        Inject CDP stealth scripts to hide automation
        
        Critical techniques:
        1. Hide navigator.webdriver
        2. Add fake window.chrome object
        3. Add fake navigator.plugins
        4. Override permissions
        """
        await page.add_init_script("""
            // 1. Hide webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // 2. Add fake chrome object
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
            
            // 3. Add fake plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // 4. Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // 5. Add fake languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en', 'pt-BR']
            });
            
            // 6. Override hardware concurrency
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8
            });
            
            // 7. Override platform
            Object.defineProperty(navigator, 'platform', {
                get: () => 'Win32'
            });
        """)
        
    async def search_google(self, query: str) -> List[Dict[str, Any]]:
        """
        Search Google and extract results with multiple selector strategies
        
        Args:
            query: Search query
            
        Returns:
            List of search results with title, link, snippet
        """
        results = []
        page = None
        
        try:
            page = await self.context.new_page()
            await self.inject_stealth(page)
            
            # Navigate to Google
            search_url = f"https://www.google.com/search?q={quote(query)}&num=20"
            print(f"      → Navigating to: {search_url[:80]}...")
            
            await page.goto(search_url, wait_until='networkidle', timeout=30000)
            
            # Human-like delay
            await asyncio.sleep(gaussian_delay(2, 4))
            
            # DEBUG: Take screenshot
            screenshot_path = f"/tmp/google_search_{hash(query) % 10000}.png"
            try:
                await page.screenshot(path=screenshot_path)
                print(f"      → Screenshot saved: {screenshot_path}")
            except:
                pass
            
            # DEBUG: Check if CAPTCHA
            page_content = await page.content()
            if 'captcha' in page_content.lower() or 'unusual traffic' in page_content.lower():
                print(f"      ⚠ CAPTCHA detected!")
                return results
            
            # Strategy 1: Try modern Google selectors (2024+)
            print(f"      → Trying modern selectors...")
            result_elements = await page.query_selector_all('div[data-sokoban-container]')
            
            if not result_elements:
                # Strategy 2: Try classic div.g
                print(f"      → Trying classic div.g...")
                result_elements = await page.query_selector_all('div.g')
            
            if not result_elements:
                # Strategy 3: Try data-hveid containers
                print(f"      → Trying data-hveid containers...")
                result_elements = await page.query_selector_all('div[data-hveid]')
            
            if not result_elements:
                # Strategy 4: Try search result containers
                print(f"      → Trying generic search containers...")
                result_elements = await page.query_selector_all('div.MjjYud')
            
            print(f"      → Found {len(result_elements)} potential result containers")
            
            for i, elem in enumerate(result_elements[:20]):
                try:
                    # Extract title (multiple strategies)
                    title = ""
                    title_elem = await elem.query_selector('h3')
                    if title_elem:
                        title = await title_elem.inner_text()
                    
                    if not title:
                        # Try role=heading
                        title_elem = await elem.query_selector('[role="heading"]')
                        if title_elem:
                            title = await title_elem.inner_text()
                    
                    # Extract link (multiple strategies)
                    link = ""
                    link_elem = await elem.query_selector('a[href]')
                    if link_elem:
                        link = await link_elem.get_attribute('href')
                    
                    # Clean up link
                    if link and link.startswith('/url?q='):
                        # Google redirect link
                        from urllib.parse import urlparse, parse_qs
                        try:
                            parsed = urlparse(link)
                            link = parse_qs(parsed.query).get('q', [link])[0]
                        except:
                            pass
                    
                    # Extract snippet (multiple strategies)
                    snippet = ""
                    snippet_elem = await elem.query_selector('div[data-sncf]')
                    if not snippet_elem:
                        snippet_elem = await elem.query_selector('div.VwiC3b')
                    if not snippet_elem:
                        snippet_elem = await elem.query_selector('div.lEBKkf')
                    if not snippet_elem:
                        # Get all text from container
                        snippet = await elem.inner_text()
                    else:
                        snippet = await snippet_elem.inner_text()
                    
                    # Clean snippet (remove title to avoid duplication)
                    if title and snippet.startswith(title):
                        snippet = snippet[len(title):].strip()
                    
                    if title and link and link.startswith('http'):
                        results.append({
                            'title': title,
                            'link': link,
                            'snippet': snippet[:500]  # Limit snippet
                        })
                        print(f"      ✓ Result {i+1}: {title[:60]}...")
                        
                except Exception as e:
                    print(f"      ✗ Error extracting result {i+1}: {str(e)[:50]}")
                    continue
            
            print(f"    ✓ Found {len(results)} valid results for '{query[:50]}...'")
            
        except Exception as e:
            print(f"    ✗ Playwright error: {str(e)[:200]}")
            import traceback
            print(f"    ✗ Traceback: {traceback.format_exc()[:300]}")
        
        finally:
            if page:
                try:
                    await page.close()
                except:
                    pass
            
        return results
        
    async def search_google_patents(self, query: str) -> List[Dict[str, Any]]:
        """
        Search Google Patents specifically
        
        Args:
            query: Patent search query
            
        Returns:
            List of patent results
        """
        results = []
        
        try:
            page = await self.context.new_page()
            await self.inject_stealth(page)
            
            # Navigate to Google Patents
            search_url = f"https://patents.google.com/?q={query}&num=100"
            await page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
            
            # Wait for results to load
            await asyncio.sleep(gaussian_delay(3, 5))
            
            # Extract patent results
            result_elements = await page.query_selector_all('search-result-item')
            
            for elem in result_elements[:100]:
                try:
                    # Extract patent ID
                    id_elem = await elem.query_selector('span.patent-number')
                    patent_id = await id_elem.inner_text() if id_elem else ""
                    
                    # Extract title
                    title_elem = await elem.query_selector('a.patent-title')
                    title = await title_elem.inner_text() if title_elem else ""
                    
                    # Extract link
                    link = f"https://patents.google.com/patent/{patent_id}" if patent_id else ""
                    
                    if patent_id:
                        results.append({
                            'patent_id': patent_id,
                            'title': title,
                            'link': link
                        })
                except Exception as e:
                    continue
                    
            await page.close()
            print(f"    ✓ Found {len(results)} patents for '{query[:50]}...'")
            
        except Exception as e:
            print(f"    ✗ Playwright Google Patents error: {str(e)[:100]}")
            
        return results


async def test_crawler():
    """Test crawler"""
    async with PlaywrightCrawler() as crawler:
        results = await crawler.search_google("Darolutamide patent WO")
        for r in results[:3]:
            print(f"  - {r['title']}")


if __name__ == "__main__":
    asyncio.run(test_crawler())
