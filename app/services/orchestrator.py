"""
Multi-Layer Search Orchestrator
Coordinates 3 fallback layers: Playwright → Selenium → HTTP
"""
import asyncio
import httpx
from typing import List, Dict, Any
from app.services.playwright_crawler import PlaywrightCrawler
from app.services.selenium_crawler import SeleniumCrawler
from app.utils.delays import retry_with_backoff


class SearchOrchestrator:
    """Orchestrates multi-layer search with automatic fallback"""
    
    def __init__(self):
        self.playwright_crawler = None
        self.selenium_crawler = None
        
    async def search_with_fallback(self, query: str) -> Dict[str, Any]:
        """
        Search with automatic fallback through 3 layers
        
        Layers:
        1. Playwright (most powerful, CDP stealth)
        2. Selenium (fallback, webdriver stealth)
        3. HTTP requests (last resort, basic)
        
        Args:
            query: Search query
            
        Returns:
            Dict with results and metadata
        """
        results = []
        layer_used = None
        error_log = []
        
        # Layer 1: Playwright (async)
        try:
            print(f"  🎭 Layer 1: Playwright...")
            if not self.playwright_crawler:
                self.playwright_crawler = PlaywrightCrawler()
                await self.playwright_crawler.start()
                
            results = await self.playwright_crawler.search_google(query)
            
            if results:
                layer_used = "playwright"
                print(f"    ✅ Playwright SUCCESS: {len(results)} results")
                return {
                    'results': results,
                    'layer': layer_used,
                    'success': True,
                    'errors': []
                }
        except Exception as e:
            error_log.append(f"Playwright failed: {str(e)[:100]}")
            print(f"    ❌ Playwright failed: {str(e)[:100]}")
            
        # Layer 2: Selenium (sync)
        try:
            print(f"  🔧 Layer 2: Selenium...")
            if not self.selenium_crawler:
                self.selenium_crawler = SeleniumCrawler()
                self.selenium_crawler.start()
                
            results = self.selenium_crawler.search_google(query)
            
            if results:
                layer_used = "selenium"
                print(f"    ✅ Selenium SUCCESS: {len(results)} results")
                return {
                    'results': results,
                    'layer': layer_used,
                    'success': True,
                    'errors': error_log
                }
        except Exception as e:
            error_log.append(f"Selenium failed: {str(e)[:100]}")
            print(f"    ❌ Selenium failed: {str(e)[:100]}")
            
        # Layer 3: HTTP (last resort)
        try:
            print(f"  🌐 Layer 3: HTTP...")
            results = await self._http_search(query)
            
            if results:
                layer_used = "http"
                print(f"    ✅ HTTP SUCCESS: {len(results)} results")
                return {
                    'results': results,
                    'layer': layer_used,
                    'success': True,
                    'errors': error_log
                }
        except Exception as e:
            error_log.append(f"HTTP failed: {str(e)[:100]}")
            print(f"    ❌ HTTP failed: {str(e)[:100]}")
            
        # All layers failed
        print(f"  ❌ ALL LAYERS FAILED")
        return {
            'results': [],
            'layer': None,
            'success': False,
            'errors': error_log
        }
        
    async def _http_search(self, query: str) -> List[Dict[str, Any]]:
        """
        Basic HTTP search (fallback layer 3)
        
        Note: This is likely to be blocked by Google,
        but included as last resort fallback
        """
        results = []
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            url = f"https://www.google.com/search?q={query}&num=20"
            response = await client.get(url, headers=headers)
            
            if response.status_code == 200:
                # Very basic parsing (just for fallback)
                html = response.text
                
                # Extract WO numbers via regex
                import re
                wo_pattern = r'WO[\s-]?(\d{4})[\s\/]?(\d{6})'
                matches = re.findall(wo_pattern, html)
                
                for year, num in matches:
                    wo_number = f"WO{year}{num}"
                    results.append({
                        'title': wo_number,
                        'link': f"https://patents.google.com/patent/{wo_number}",
                        'snippet': ''
                    })
                    
        return results
        
    async def cleanup(self):
        """Cleanup resources"""
        if self.playwright_crawler:
            await self.playwright_crawler.stop()
        if self.selenium_crawler:
            self.selenium_crawler.stop()


async def test_orchestrator():
    """Test orchestrator"""
    orchestrator = SearchOrchestrator()
    
    result = await orchestrator.search_with_fallback("Darolutamide patent WO2016")
    
    print(f"\n✅ SUCCESS!")
    print(f"Layer used: {result['layer']}")
    print(f"Results: {len(result['results'])}")
    
    if result['results']:
        print(f"\nFirst 3 results:")
        for r in result['results'][:3]:
            print(f"  - {r['title']}")
            
    await orchestrator.cleanup()


if __name__ == "__main__":
    asyncio.run(test_orchestrator())
