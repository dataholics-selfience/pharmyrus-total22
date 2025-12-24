"""
WIPO Patentscope Crawler - V7 Enhanced
Advanced crawler for WIPO Patentscope with multiple search strategies
"""
import asyncio
import random
from typing import List, Dict, Optional, Set
from playwright.async_api import async_playwright, Page
import logging

logger = logging.getLogger(__name__)


class WIPOPatentscopeCrawler:
    """
    Advanced WIPO Patentscope crawler with multiple search strategies
    
    Strategies:
    1. Simple search (EN field - English names)
    2. Advanced search with operators (applicant + molecule)
    3. Dev code search
    4. CAS number search
    5. IPC classification search
    """
    
    USER_AGENTS = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    ]
    
    def __init__(self):
        self.browser = None
        self.context = None
        self.base_url = "https://patentscope.wipo.int"
        
    async def __aenter__(self):
        await self.initialize()
        return self
        
    async def __aexit__(self, *args):
        await self.cleanup()
        
    async def initialize(self):
        """Initialize browser with stealth settings"""
        playwright = await async_playwright().start()
        
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )
        
        # Create context with realistic settings
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=random.choice(self.USER_AGENTS),
            locale='en-US',
            timezone_id='America/New_York',
            permissions=['geolocation'],
            geolocation={'latitude': 40.7128, 'longitude': -74.0060},
            color_scheme='light',
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0'
            }
        )
        
        logger.info("✅ WIPO Patentscope crawler initialized")
        
    async def cleanup(self):
        """Cleanup browser resources"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
            
    async def _add_stealth_scripts(self, page: Page):
        """Add anti-detection scripts"""
        await page.add_init_script("""
            // Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            
            // Add chrome object
            window.chrome = {
                runtime: {}
            };
            
            // Mock permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
    async def search_by_molecule_and_applicant(
        self,
        molecule_name: str,
        applicants: List[str] = None
    ) -> Set[str]:
        """
        Search WIPO by molecule name and applicants
        
        Strategy: (EN:molecule_name AND PA:applicant)
        """
        wo_numbers = set()
        
        if applicants is None:
            applicants = ['Bayer', 'Orion', 'Pfizer', 'Novartis', 'Roche']
        
        for applicant in applicants:
            try:
                logger.info(f"   Searching WIPO: {molecule_name} + {applicant}")
                
                page = await self.context.new_page()
                await self._add_stealth_scripts(page)
                
                # Build advanced search query
                query = f'(EN:"{molecule_name}" OR ALLTXT:"{molecule_name}") AND PA:"{applicant}"'
                search_url = f"{self.base_url}/search/en/search.jsf"
                
                await page.goto(search_url, wait_until="networkidle", timeout=60000, timeout=60000)
                await asyncio.sleep(random.uniform(1, 2))
                
                # Enter query in search box
                await page.fill('input[name="simpleSearchQueryString"]', query)
                await asyncio.sleep(random.uniform(0.5, 1))
                
                # Click search
                await page.click('button[type="submit"]')
                await page.wait_for_load_state('networkidle')
                await asyncio.sleep(random.uniform(2, 3))
                
                # Extract WO numbers from results
                wo_links = await page.query_selector_all('a[href*="/en/detail.jsf?docId="]')
                
                for link in wo_links:
                    text = await link.text_content()
                    if text and text.startswith('WO'):
                        # Clean WO number
                        wo_num = text.strip().split()[0]  # Get WO2016162604
                        wo_numbers.add(wo_num)
                        logger.info(f"      Found: {wo_num}")
                
                await page.close()
                await asyncio.sleep(random.uniform(2, 4))
                
            except Exception as e:
                logger.warning(f"      Error searching {applicant}: {e}")
                continue
        
        return wo_numbers
    
    async def search_by_dev_code(self, dev_code: str) -> Set[str]:
        """
        Search WIPO by development code
        
        Strategy: ALLTXT:dev_code (searches all text fields)
        """
        wo_numbers = set()
        
        try:
            logger.info(f"   Searching WIPO by dev code: {dev_code}")
            
            page = await self.context.new_page()
            await self._add_stealth_scripts(page)
            
            # Simple search for dev code
            query = f'ALLTXT:"{dev_code}"'
            search_url = f"{self.base_url}/search/en/search.jsf"
            
            await page.goto(search_url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(random.uniform(1, 2))
            
            await page.fill('input[name="simpleSearchQueryString"]', query)
            await asyncio.sleep(random.uniform(0.5, 1))
            
            await page.click('button[type="submit"]')
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(random.uniform(2, 3))
            
            # Extract WO numbers
            wo_links = await page.query_selector_all('a[href*="/en/detail.jsf?docId="]')
            
            for link in wo_links:
                text = await link.text_content()
                if text and text.startswith('WO'):
                    wo_num = text.strip().split()[0]
                    wo_numbers.add(wo_num)
                    logger.info(f"      Found: {wo_num}")
            
            await page.close()
            await asyncio.sleep(random.uniform(2, 4))
            
        except Exception as e:
            logger.warning(f"      Error searching dev code: {e}")
        
        return wo_numbers
    
    async def search_by_cas(self, cas_number: str) -> Set[str]:
        """
        Search WIPO by CAS number
        
        Strategy: ALLTXT:cas_number
        """
        wo_numbers = set()
        
        try:
            logger.info(f"   Searching WIPO by CAS: {cas_number}")
            
            page = await self.context.new_page()
            await self._add_stealth_scripts(page)
            
            query = f'ALLTXT:"{cas_number}"'
            search_url = f"{self.base_url}/search/en/search.jsf"
            
            await page.goto(search_url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(random.uniform(1, 2))
            
            await page.fill('input[name="simpleSearchQueryString"]', query)
            await asyncio.sleep(random.uniform(0.5, 1))
            
            await page.click('button[type="submit"]')
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(random.uniform(2, 3))
            
            wo_links = await page.query_selector_all('a[href*="/en/detail.jsf?docId="]')
            
            for link in wo_links:
                text = await link.text_content()
                if text and text.startswith('WO'):
                    wo_num = text.strip().split()[0]
                    wo_numbers.add(wo_num)
                    logger.info(f"      Found: {wo_num}")
            
            await page.close()
            await asyncio.sleep(random.uniform(2, 4))
            
        except Exception as e:
            logger.warning(f"      Error searching CAS: {e}")
        
        return wo_numbers
    
    async def get_family_members(self, wo_number: str) -> Dict[str, List[str]]:
        """
        Get patent family members for a WO number
        
        Returns BR patents from the same family
        """
        family_members = {
            'br_patents': [],
            'us_patents': [],
            'ep_patents': [],
            'other': []
        }
        
        try:
            logger.info(f"   Getting family members for {wo_number}")
            
            page = await self.context.new_page()
            await self._add_stealth_scripts(page)
            
            # Go to patent detail page
            # WO2016162604 -> docId format
            doc_id = wo_number.replace('-', '')  # Remove hyphens
            detail_url = f"{self.base_url}/search/en/detail.jsf?docId={doc_id}"
            
            await page.goto(detail_url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(random.uniform(2, 3))
            
            # Look for "National Phase Entries" or "Patent Family" section
            # This varies by WIPO's UI, so we try multiple selectors
            
            # Try to find BR patents in the page
            page_content = await page.content()
            
            # Look for BR patent numbers (BR followed by numbers)
            import re
            br_pattern = r'BR\s*[-/]?\s*(\d{12}|\d{9})'
            br_matches = re.findall(br_pattern, page_content, re.IGNORECASE)
            
            for match in br_matches:
                br_num = f"BR{match.replace('-', '').replace('/', '')}"
                if br_num not in family_members['br_patents']:
                    family_members['br_patents'].append(br_num)
                    logger.info(f"      Found BR: {br_num}")
            
            await page.close()
            await asyncio.sleep(random.uniform(1, 2))
            
        except Exception as e:
            logger.warning(f"      Error getting family members: {e}")
        
        return family_members
    
    async def comprehensive_search(
        self,
        molecule_name: str,
        dev_codes: List[str] = None,
        cas_number: str = None,
        applicants: List[str] = None
    ) -> Dict:
        """
        Comprehensive multi-strategy search
        
        Returns:
        - wo_numbers: Set of WO numbers found
        - br_patents: Dict mapping WO -> BR patents
        - strategies_used: Which strategies found results
        """
        all_wo_numbers = set()
        br_mapping = {}
        strategies_used = []
        
        # Strategy 1: Molecule + Applicants
        if applicants:
            wo_set = await self.search_by_molecule_and_applicant(molecule_name, applicants)
            if wo_set:
                all_wo_numbers.update(wo_set)
                strategies_used.append(f"molecule+applicant ({len(wo_set)} found)")
        
        # Strategy 2: Dev codes
        if dev_codes:
            for dev_code in dev_codes[:5]:  # Limit to 5
                wo_set = await self.search_by_dev_code(dev_code)
                if wo_set:
                    all_wo_numbers.update(wo_set)
                    strategies_used.append(f"dev_code:{dev_code} ({len(wo_set)} found)")
        
        # Strategy 3: CAS number
        if cas_number:
            wo_set = await self.search_by_cas(cas_number)
            if wo_set:
                all_wo_numbers.update(wo_set)
                strategies_used.append(f"cas:{cas_number} ({len(wo_set)} found)")
        
        # For each WO, get BR family members
        logger.info(f"\n   Getting BR family members for {len(all_wo_numbers)} WO patents...")
        
        for wo_num in list(all_wo_numbers)[:20]:  # Limit to 20 to avoid too long
            family = await self.get_family_members(wo_num)
            if family['br_patents']:
                br_mapping[wo_num] = family['br_patents']
        
        return {
            'wo_numbers': list(all_wo_numbers),
            'br_mapping': br_mapping,
            'strategies_used': strategies_used,
            'total_wo_found': len(all_wo_numbers),
            'total_br_found': sum(len(v) for v in br_mapping.values())
        }


# Test function
async def test_wipo_crawler():
    """Test WIPO crawler with Darolutamide"""
    async with WIPOPatentscopeCrawler() as crawler:
        results = await crawler.comprehensive_search(
            molecule_name="Darolutamide",
            dev_codes=["ODM-201", "BAY-1841788"],
            cas_number="1297538-32-9",
            applicants=["Bayer", "Orion"]
        )
        
        print("\n" + "="*80)
        print("WIPO COMPREHENSIVE SEARCH RESULTS")
        print("="*80)
        print(f"\nWO Numbers Found: {results['total_wo_found']}")
        print(f"BR Patents Found: {results['total_br_found']}")
        print(f"\nStrategies Used:")
        for strategy in results['strategies_used']:
            print(f"  - {strategy}")
        
        print(f"\nWO → BR Mapping:")
        for wo, br_list in results['br_mapping'].items():
            print(f"  {wo} → {', '.join(br_list)}")


if __name__ == "__main__":
    asyncio.run(test_wipo_crawler())
