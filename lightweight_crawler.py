"""
PHARMYRUS V16.1 - LIGHTWEIGHT CRAWLER
Sem Playwright - Apenas httpx + proxies para máxima compatibilidade
"""
import asyncio
import httpx
import re
from typing import List, Dict, Set, Optional
from key_pool_manager import KeyPoolManager


class LightweightCrawler:
    """
    Crawler leve com:
    - Pool de 14 API keys
    - 200+ proxies rotacionando
    - httpx async requests
    - Regex extraction
    """
    
    def __init__(self):
        self.key_pool = KeyPoolManager()
        self.wo_pattern = re.compile(r'WO[\s/\-]?(\d{4})[\s/\-]?(\d{6})', re.IGNORECASE)
        self.br_pattern = re.compile(r'BR[\s/\-]?(\d+)', re.IGNORECASE)
        self.proxies = []
        self.current_proxy_index = 0
        
    async def initialize(self):
        """Initialize proxy pool"""
        print("\n🔧 Initializing proxy pool...")
        
        # Get proxies from all sources
        webshare = await self.key_pool.get_webshare_proxies()
        proxyscrape = await self.key_pool.get_proxyscrape_proxies()
        
        self.proxies = webshare + proxyscrape
        
        print(f"✅ Proxy pool ready: {len(self.proxies)} proxies")
        
        self.key_pool.print_status()
    
    def _get_next_proxy(self) -> Optional[str]:
        """Get next proxy with round-robin"""
        if not self.proxies:
            return None
        
        proxy = self.proxies[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        
        return proxy
    
    async def _fetch_with_proxy(self, url: str, max_retries: int = 3) -> Optional[str]:
        """Fetch URL with proxy rotation"""
        for attempt in range(max_retries):
            proxy = self._get_next_proxy()
            
            try:
                async with httpx.AsyncClient(
                    proxies={"http://": proxy, "https://": proxy} if proxy else None,
                    timeout=30.0,
                    follow_redirects=True
                ) as client:
                    response = await client.get(url)
                    
                    if response.status_code == 200:
                        return response.text
                    
            except Exception as e:
                print(f"   ⚠️  Attempt {attempt+1} failed: {str(e)[:50]}")
                continue
        
        return None
    
    async def search_google_patents(self, query: str) -> Set[str]:
        """Search Google Patents for WO numbers"""
        wo_numbers = set()
        
        url = f"https://patents.google.com/?q={query}&num=20"
        
        print(f"   Searching: {query[:50]}...")
        
        html = await self._fetch_with_proxy(url)
        
        if html:
            # Extract WO numbers
            matches = self.wo_pattern.findall(html)
            for year, num in matches:
                wo = f"WO{year}{num}"
                wo_numbers.add(wo)
            
            print(f"   ✅ Found {len(wo_numbers)} WO numbers")
        else:
            print(f"   ⚠️  Failed to fetch")
        
        return wo_numbers
    
    async def get_wo_family(self, wo_number: str) -> Set[str]:
        """Get BR numbers from WO patent family"""
        br_numbers = set()
        
        url = f"https://patents.google.com/?q={wo_number}"
        
        html = await self._fetch_with_proxy(url)
        
        if html:
            # Extract BR numbers
            matches = self.br_pattern.findall(html)
            for br_num in matches:
                if len(br_num) >= 6:  # Valid BR number
                    br_numbers.add(f"BR{br_num}")
            
            if br_numbers:
                print(f"   WO {wo_number}: {len(br_numbers)} BR patents")
        
        return br_numbers
    
    async def search_molecule(self, molecule: str, dev_codes: List[str] = None) -> Dict:
        """
        Complete search for molecule:
        1. Search Google Patents for WO numbers
        2. For each WO, extract BR numbers
        """
        print(f"\n{'='*70}")
        print(f"🔬 SEARCHING: {molecule}")
        print(f"{'='*70}\n")
        
        all_wo_numbers = set()
        
        # Build queries
        queries = [
            f"{molecule} patent",
            f"{molecule} WO2011",
            f"{molecule} WO2016",
            f"{molecule} WO2018",
            f"{molecule} WO2020",
            f"{molecule} WO2021"
        ]
        
        if dev_codes:
            for code in dev_codes[:3]:
                queries.append(f"{code} patent")
        
        # Search for WO numbers
        print(f"📍 Searching {len(queries)} queries...")
        
        for query in queries:
            wo_numbers = await self.search_google_patents(query)
            all_wo_numbers.update(wo_numbers)
            
            await asyncio.sleep(1)  # Rate limit
        
        print(f"\n✅ Total WO numbers found: {len(all_wo_numbers)}")
        
        # Get BR numbers for each WO
        print(f"\n📍 Extracting BR numbers from {len(all_wo_numbers)} WOs...")
        
        all_br_numbers = set()
        wo_details = []
        
        for wo in sorted(all_wo_numbers):
            br_numbers = await self.get_wo_family(wo)
            
            wo_details.append({
                'wo_number': wo,
                'br_numbers': list(br_numbers)
            })
            
            if br_numbers:
                all_br_numbers.update(br_numbers)
            
            await asyncio.sleep(1)  # Rate limit
        
        print(f"\n✅ Total BR numbers found: {len(all_br_numbers)}")
        
        # Print status
        self.key_pool.print_status()
        
        return {
            'molecule': molecule,
            'wo_numbers': sorted(list(all_wo_numbers)),
            'br_numbers': sorted(list(all_br_numbers)),
            'wo_details': wo_details,
            'summary': {
                'total_wo': len(all_wo_numbers),
                'total_br': len(all_br_numbers),
                'queries_executed': len(queries)
            }
        }


# TEST
async def test_crawler():
    """Test lightweight crawler"""
    print("\n" + "="*70)
    print("TESTING LIGHTWEIGHT CRAWLER")
    print("="*70)
    
    crawler = LightweightCrawler()
    
    # Initialize
    await crawler.initialize()
    
    # Test with aspirin
    result = await crawler.search_molecule(
        molecule='aspirin',
        dev_codes=[]
    )
    
    print(f"\n{'='*70}")
    print("RESULTS:")
    print(f"{'='*70}")
    print(f"WO numbers: {result['summary']['total_wo']}")
    print(f"BR numbers: {result['summary']['total_br']}")
    
    if result['wo_numbers']:
        print(f"\nWO NUMBERS:")
        for wo in result['wo_numbers'][:5]:
            print(f"  ✅ {wo}")
    
    if result['br_numbers']:
        print(f"\nBR NUMBERS:")
        for br in result['br_numbers'][:5]:
            print(f"  ✅ {br}")
    
    return len(result['wo_numbers']) > 0


if __name__ == "__main__":
    success = asyncio.run(test_crawler())
    exit(0 if success else 1)
