"""
WIPO Patentscope Crawler - FIXED VERSION
Cross-validates EPO results and finds additional WO patents
"""

import asyncio
import logging
import random
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Page, Browser

logger = logging.getLogger(__name__)


class WIPOCrawler:
    """
    WIPO Patentscope crawler with applicant filtering
    
    Purpose: Cross-validate EPO results and find additional WO
    """
    
    SEARCH_URL = "https://patentscope.wipo.int/search/en/search.jsf"
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.playwright = None
        
    async def __aenter__(self):
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()
    
    async def initialize(self):
        """Initialize Playwright browser"""
        logger.info("✅ WIPO Patentscope crawler initialized")
        
        self.playwright = await async_playwright().start()
        
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled'
            ]
        )
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def search_by_applicant(
        self,
        molecule: str,
        applicants: List[str],
        max_per_applicant: int = 20
    ) -> Dict:
        """
        Search WIPO by molecule + applicant
        
        Args:
            molecule: Molecule name
            applicants: List of applicant companies
            max_per_applicant: Max results per applicant
            
        Returns:
            {
                'wo_numbers': [...],
                'statistics': {...}
            }
        """
        logger.info(f"🔍 WIPO Search: {molecule} by applicants")
        
        results = {
            'wo_numbers': set(),
            'statistics': {
                'queries': 0,
                'total_found': 0,
                'by_applicant': {},
                'errors': 0
            }
        }
        
        for applicant in applicants:
            logger.info(f"   Searching: {applicant}")
            
            try:
                wo_list = await self._search_single_applicant(molecule, applicant, max_per_applicant)
                
                results['wo_numbers'].update(wo_list)
                results['statistics']['queries'] += 1
                results['statistics']['by_applicant'][applicant] = len(wo_list)
                results['statistics']['total_found'] += len(wo_list)
                
                logger.info(f"      Found {len(wo_list)} WO from {applicant}")
                
                # Delay between queries
                await asyncio.sleep(random.uniform(2, 4))
                
            except Exception as e:
                logger.warning(f"      Error searching {applicant}: {e}")
                results['statistics']['errors'] += 1
                
        results['wo_numbers'] = sorted(list(results['wo_numbers']))
        
        logger.info(f"   ✅ WIPO Total: {len(results['wo_numbers'])} WO")
        
        return results
    
    async def _search_single_applicant(
        self,
        molecule: str,
        applicant: str,
        max_results: int
    ) -> List[str]:
        """Execute single WIPO search"""
        
        context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        
        page = await context.new_page()
        
        # Stealth
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)
        
        try:
            # Build advanced query
            # EN = English title/abstract
            # PA = Applicant
            query = f'(EN:"{molecule}") AND PA:"{applicant}"'
            
            search_url = f"{self.WIPO_SEARCH_URL}?query={query}"
            
            # Navigate - FIXED: proper timeout syntax
            await page.goto(search_url, wait_until='networkidle', timeout=90000)
            
            # Wait for results
            await page.wait_for_selector('.result-list, .no-results', timeout=10000)
            
            # Extract WO numbers
            wo_numbers = await page.evaluate("""
                () => {
                    const results = [];
                    const links = document.querySelectorAll('a[href*="WO"]');
                    
                    links.forEach(link => {
                        const text = link.textContent || '';
                        const match = text.match(/WO[\\s-]?(\\d{4})[\\s\\/]?(\\d{6})/);
                        if (match) {
                            const wo = 'WO' + match[1] + match[2];
                            if (!results.includes(wo)) {
                                results.push(wo);
                            }
                        }
                    });
                    
                    return results;
                }
            """)
            
            return wo_numbers[:max_results]
            
        finally:
            await page.close()
            await context.close()


async def test_wipo():
    """Test WIPO crawler"""
    
    async with WIPOCrawler() as wipo:
        results = await wipo.search_by_applicant(
            molecule="Darolutamide",
            applicants=["Bayer", "Orion"],
            max_per_applicant=10
        )
        
        print(f"\nWIPO Results:")
        print(f"  WO Found: {len(results['wo_numbers'])}")
        print(f"  Statistics: {results['statistics']}")
        
        for wo in results['wo_numbers'][:10]:
            print(f"    - {wo}")


if __name__ == "__main__":
    asyncio.run(test_wipo())
