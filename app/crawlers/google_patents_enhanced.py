"""
Google Patents Enhanced Crawler - V7
Advanced crawler with family member extraction
"""
import asyncio
import random
import re
from typing import List, Dict, Set, Optional
from playwright.async_api import async_playwright, Page
import logging

logger = logging.getLogger(__name__)


class GooglePatentsEnhancedCrawler:
    """
    Enhanced Google Patents crawler with family extraction
    
    Features:
    - Multi-strategy WO search
    - Family member extraction (BR patents)
    - Anti-detection (stealth mode)
    - Intelligent retry with exponential backoff
    """
    
    USER_AGENTS = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]
    
    def __init__(self):
        self.browser = None
        self.context = None
        self.base_url = "https://patents.google.com"
        
    async def __aenter__(self):
        await self.initialize()
        return self
        
    async def __aexit__(self, *args):
        await self.cleanup()
        
    async def initialize(self):
        """Initialize browser with stealth"""
        playwright = await async_playwright().start()
        
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox'
            ]
        )
        
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=random.choice(self.USER_AGENTS),
            locale='en-US'
        )
        
        logger.info("✅ Google Patents Enhanced crawler initialized")
        
    async def cleanup(self):
        """Cleanup browser"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
            
    async def _add_stealth(self, page: Page):
        """Add anti-detection"""
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            window.chrome = {runtime: {}};
        """)
        
    async def search_wo_numbers(
        self,
        molecule_name: str,
        dev_codes: List[str] = None,
        cas_number: str = None,
        years: List[str] = None
    ) -> Set[str]:
        """
        Multi-strategy WO number search
        
        Strategies:
        1. Molecule name + WO + year
        2. Dev codes + WO
        3. CAS number + WO
        4. Molecule + assignee
        """
        wo_numbers = set()
        
        if years is None:
            years = ['2011', '2016', '2017', '2018', '2019', '2020', 
                    '2021', '2022', '2023', '2024']
        
        # Strategy 1: Molecule + WO + year
        for year in years:
            query = f"{molecule_name} WO{year}"
            wo_set = await self._search_query(query)
            wo_numbers.update(wo_set)
            await asyncio.sleep(random.uniform(2, 4))
        
        # Strategy 2: Dev codes
        if dev_codes:
            for dev_code in dev_codes[:5]:
                query = f"{dev_code} WO"
                wo_set = await self._search_query(query)
                wo_numbers.update(wo_set)
                await asyncio.sleep(random.uniform(2, 4))
        
        # Strategy 3: CAS number
        if cas_number:
            query = f"{cas_number} WO"
            wo_set = await self._search_query(query)
            wo_numbers.update(wo_set)
            await asyncio.sleep(random.uniform(2, 4))
        
        # Strategy 4: Molecule + companies
        companies = ['Bayer', 'Orion', 'Novartis']
        for company in companies:
            query = f"{molecule_name} {company} WO"
            wo_set = await self._search_query(query)
            wo_numbers.update(wo_set)
            await asyncio.sleep(random.uniform(2, 4))
        
        return wo_numbers
    
    async def _search_query(self, query: str) -> Set[str]:
        """Execute search query and extract WO numbers"""
        wo_numbers = set()
        
        try:
            page = await self.context.new_page()
            await self._add_stealth(page)
            
            # Go to Google Patents
            search_url = f"{self.base_url}/?q={query.replace(' ', '+')}&oq={query.replace(' ', '+')}"
            
            await page.goto(search_url, wait_until='networkidle', timeout=60000)
            await asyncio.sleep(random.uniform(2, 3))
            
            # Extract WO numbers from search results
            content = await page.content()
            
            # Pattern: WO followed by year and number
            # WO2016162604, WO/2016/162604, WO 2016/162604
            wo_pattern = r'WO\s*[-/]?\s*(\d{4})\s*[-/]?\s*(\d{6})'
            matches = re.findall(wo_pattern, content, re.IGNORECASE)
            
            for year, num in matches:
                wo_num = f"WO{year}{num}"
                wo_numbers.add(wo_num)
            
            # Also try simpler pattern for search result titles
            result_links = await page.query_selector_all('a[href*="/patent/WO"]')
            for link in result_links:
                href = await link.get_attribute('href')
                if href:
                    # Extract WO number from URL
                    wo_match = re.search(r'WO(\d{4})(\d{6})', href)
                    if wo_match:
                        wo_num = f"WO{wo_match.group(1)}{wo_match.group(2)}"
                        wo_numbers.add(wo_num)
            
            await page.close()
            
        except Exception as e:
            logger.warning(f"      Error in search query '{query}': {e}")
        
        return wo_numbers
    
    async def get_br_patents_from_wo(self, wo_number: str) -> List[str]:
        """
        Extract BR patents from WO family
        
        Goes to patent page and extracts "Worldwide applications" section
        """
        br_patents = []
        
        try:
            logger.info(f"   Getting BR family for {wo_number}")
            
            page = await self.context.new_page()
            await self._add_stealth(page)
            
            # Format: WO2016162604 -> /patent/WO2016162604
            patent_url = f"{self.base_url}/patent/{wo_number}"
            
            await page.goto(patent_url, wait_until='networkidle', timeout=60000)
            await asyncio.sleep(random.uniform(2, 3))
            
            # Get page content
            content = await page.content()
            
            # Look for BR patents in content
            # Patterns: BR112017021636, BR 112017021636, BR-112017021636
            br_pattern = r'BR\s*[-/]?\s*(\d{12}|\d{9})'
            br_matches = re.findall(br_pattern, content, re.IGNORECASE)
            
            for match in br_matches:
                # Clean BR number
                br_num = f"BR{match.replace('-', '').replace('/', '').replace(' ', '')}"
                if br_num not in br_patents:
                    br_patents.append(br_num)
                    logger.info(f"      Found BR: {br_num}")
            
            # Try to click "Worldwide applications" if present
            try:
                # Look for expandable section
                worldwide_button = await page.query_selector('text="Worldwide applications"')
                if worldwide_button:
                    await worldwide_button.click()
                    await asyncio.sleep(random.uniform(1, 2))
                    
                    # Get updated content
                    content = await page.content()
                    br_matches = re.findall(br_pattern, content, re.IGNORECASE)
                    
                    for match in br_matches:
                        br_num = f"BR{match.replace('-', '').replace('/', '').replace(' ', '')}"
                        if br_num not in br_patents:
                            br_patents.append(br_num)
                            logger.info(f"      Found BR: {br_num}")
            except:
                pass
            
            await page.close()
            await asyncio.sleep(random.uniform(1, 2))
            
        except Exception as e:
            logger.warning(f"      Error getting BR patents: {e}")
        
        return br_patents
    
    async def comprehensive_search_and_extract(
        self,
        molecule_name: str,
        dev_codes: List[str] = None,
        cas_number: str = None
    ) -> Dict:
        """
        Comprehensive search: find WO numbers and extract BR families
        """
        # Step 1: Find WO numbers
        logger.info(f"\n📡 Searching WO numbers for {molecule_name}...")
        wo_numbers = await self.search_wo_numbers(
            molecule_name,
            dev_codes,
            cas_number
        )
        
        logger.info(f"   Found {len(wo_numbers)} WO numbers")
        
        # Step 2: Extract BR patents from each WO
        logger.info(f"\n🔍 Extracting BR patents from WO families...")
        br_mapping = {}
        all_br_patents = []
        
        for i, wo_num in enumerate(list(wo_numbers)[:30], 1):  # Limit to 30
            logger.info(f"   [{i}/{min(len(wo_numbers), 30)}] Processing {wo_num}")
            
            br_list = await self.get_br_patents_from_wo(wo_num)
            
            if br_list:
                br_mapping[wo_num] = br_list
                all_br_patents.extend(br_list)
            
            # Delay between requests
            await asyncio.sleep(random.uniform(3, 5))
        
        # Deduplicate BR patents
        unique_br = list(set(all_br_patents))
        
        return {
            'wo_numbers': list(wo_numbers),
            'br_mapping': br_mapping,
            'all_br_patents': unique_br,
            'total_wo_found': len(wo_numbers),
            'total_br_found': len(unique_br),
            'conversion_rate': len(br_mapping) / len(wo_numbers) if wo_numbers else 0
        }


# Test function
async def test_google_patents_enhanced():
    """Test enhanced Google Patents crawler"""
    async with GooglePatentsEnhancedCrawler() as crawler:
        results = await crawler.comprehensive_search_and_extract(
            molecule_name="Darolutamide",
            dev_codes=["ODM-201", "BAY-1841788"],
            cas_number="1297538-32-9"
        )
        
        print("\n" + "="*80)
        print("GOOGLE PATENTS ENHANCED SEARCH RESULTS")
        print("="*80)
        print(f"\nWO Numbers Found: {results['total_wo_found']}")
        print(f"BR Patents Found: {results['total_br_found']}")
        print(f"Conversion Rate: {results['conversion_rate']*100:.1f}%")
        
        print(f"\nWO → BR Mapping:")
        for wo, br_list in list(results['br_mapping'].items())[:10]:
            print(f"  {wo} → {', '.join(br_list)}")
        
        print(f"\nAll BR Patents:")
        for br in results['all_br_patents']:
            print(f"  - {br}")


if __name__ == "__main__":
    asyncio.run(test_google_patents_enhanced())
