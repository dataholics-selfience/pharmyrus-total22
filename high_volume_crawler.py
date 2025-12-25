"""
PHARMYRUS V17 - HIGH-VOLUME PARALLEL CRAWLER
- IP diferente garantido por consulta
- Paralelização inteligente
- Coleta real de WOs e BRs
"""
import asyncio
import httpx
import re
from typing import List, Dict, Set, Optional
from key_pool_manager import KeyPoolManager
from advanced_proxy_manager import AdvancedProxyManager


class HighVolumeCrawler:
    """
    Crawler de alto volume com:
    - IP garantido diferente por consulta
    - Paralelização (até 5 queries simultâneas)
    - Retry automático com proxy rotation
    - Coleta real de WOs e BRs
    """
    
    def __init__(self):
        self.key_pool = KeyPoolManager()
        self.proxy_manager = AdvancedProxyManager(
            quarantine_threshold=3,
            quarantine_duration=300  # 5 min
        )
        self.wo_pattern = re.compile(r'WO[\s/\-]?(\d{4})[\s/\-]?(\d{6})', re.IGNORECASE)
        self.br_pattern = re.compile(r'BR[\s/\-]?(\d{7,12})', re.IGNORECASE)
        
    async def initialize(self):
        """Initialize proxy pool"""
        print("\n🔧 Initializing HIGH-VOLUME crawler...")
        
        # Get proxies from all sources
        webshare = await self.key_pool.get_webshare_proxies()
        proxyscrape = await self.key_pool.get_proxyscrape_proxies()
        
        all_proxies = webshare + proxyscrape
        self.proxy_manager.add_proxies(all_proxies)
        
        print(f"✅ Crawler ready: {len(all_proxies)} proxies")
        
        self.key_pool.print_status()
    
    async def _fetch_with_rotation(self, url: str, max_retries: int = 3) -> Optional[str]:
        """
        Fetch URL with guaranteed proxy rotation
        - Each retry uses DIFFERENT proxy
        - Failed proxies go to quarantine
        """
        for attempt in range(max_retries):
            proxy = await self.proxy_manager.get_next_proxy()
            
            if not proxy:
                print(f"   ⚠️  No healthy proxies available")
                await asyncio.sleep(2)
                continue
            
            try:
                async with httpx.AsyncClient(
                    proxies={"http://": proxy, "https://": proxy},
                    timeout=20.0,
                    follow_redirects=True
                ) as client:
                    
                    print(f"   🌐 Using: {proxy[:40]}...")
                    
                    response = await client.get(url)
                    
                    if response.status_code == 200:
                        await self.proxy_manager.record_success(proxy)
                        return response.text
                    else:
                        await self.proxy_manager.record_failure(proxy)
                        
            except Exception as e:
                await self.proxy_manager.record_failure(proxy)
                print(f"   ❌ Proxy failed: {str(e)[:50]}")
                continue
        
        return None
    
    async def search_google_patents(self, query: str) -> Set[str]:
        """Search Google Patents for WO numbers"""
        wo_numbers = set()
        
        url = f"https://patents.google.com/?q={query}&num=20"
        
        print(f"\n🔍 Query: {query}")
        
        html = await self._fetch_with_rotation(url)
        
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
        
        html = await self._fetch_with_rotation(url)
        
        if html:
            # Extract BR numbers
            matches = self.br_pattern.findall(html)
            for br_num in matches:
                if 7 <= len(br_num) <= 12:  # Valid BR number
                    br_numbers.add(f"BR{br_num}")
            
            if br_numbers:
                print(f"   WO {wo_number}: {len(br_numbers)} BR patents")
        
        return br_numbers
    
    async def search_molecule_parallel(self, molecule: str, dev_codes: List[str] = None) -> Dict:
        """
        HIGH-VOLUME search with parallelization:
        - Multiple queries em paralelo (até 5 simultâneas)
        - IP diferente garantido por query
        - Coleta real de WOs e BRs
        """
        print(f"\n{'='*70}")
        print(f"🚀 HIGH-VOLUME SEARCH: {molecule}")
        print(f"{'='*70}\n")
        
        # Build queries
        queries = [
            f"{molecule} patent",
            f"{molecule} WO2011",
            f"{molecule} WO2016",
            f"{molecule} WO2018",
            f"{molecule} WO2020",
            f"{molecule} WO2021",
            f"{molecule} WO2023"
        ]
        
        if dev_codes:
            for code in dev_codes[:3]:
                queries.append(f"{code} patent WO")
        
        print(f"📊 Executing {len(queries)} queries in parallel (max 5 concurrent)...")
        
        # Execute queries in parallel with semaphore
        semaphore = asyncio.Semaphore(5)
        
        async def search_with_limit(query):
            async with semaphore:
                return await self.search_google_patents(query)
        
        # Run all queries
        results = await asyncio.gather(
            *[search_with_limit(q) for q in queries],
            return_exceptions=True
        )
        
        # Collect WO numbers
        all_wo_numbers = set()
        for result in results:
            if isinstance(result, set):
                all_wo_numbers.update(result)
        
        print(f"\n✅ Total WO numbers found: {len(all_wo_numbers)}")
        
        # Get BR numbers for each WO (also parallelized)
        print(f"\n📍 Extracting BR numbers from {len(all_wo_numbers)} WOs...")
        
        async def get_family_with_limit(wo):
            async with semaphore:
                return await self.get_wo_family(wo)
        
        br_results = await asyncio.gather(
            *[get_family_with_limit(wo) for wo in sorted(all_wo_numbers)],
            return_exceptions=True
        )
        
        # Collect BR numbers
        all_br_numbers = set()
        wo_details = []
        
        for wo, br_result in zip(sorted(all_wo_numbers), br_results):
            if isinstance(br_result, set):
                wo_details.append({
                    'wo_number': wo,
                    'br_numbers': list(br_result)
                })
                all_br_numbers.update(br_result)
        
        print(f"\n✅ Total BR numbers found: {len(all_br_numbers)}")
        
        # Print proxy status
        self.proxy_manager.print_status()
        
        return {
            'molecule': molecule,
            'wo_numbers': sorted(list(all_wo_numbers)),
            'br_numbers': sorted(list(all_br_numbers)),
            'wo_details': wo_details,
            'summary': {
                'total_wo': len(all_wo_numbers),
                'total_br': len(all_br_numbers),
                'queries_executed': len(queries),
                'parallel_execution': True
            },
            'proxy_stats': self.proxy_manager.get_status()
        }


# TEST
async def test_crawler():
    """Test high-volume crawler"""
    print("\n" + "="*70)
    print("TESTING HIGH-VOLUME CRAWLER")
    print("="*70)
    
    crawler = HighVolumeCrawler()
    
    # Initialize
    await crawler.initialize()
    
    # Test with darolutamide
    result = await crawler.search_molecule_parallel(
        molecule='darolutamide',
        dev_codes=['ODM-201']
    )
    
    print(f"\n{'='*70}")
    print("FINAL RESULTS:")
    print(f"{'='*70}")
    print(f"WO numbers: {result['summary']['total_wo']}")
    print(f"BR numbers: {result['summary']['total_br']}")
    
    if result['wo_numbers']:
        print(f"\nWO NUMBERS FOUND:")
        for wo in result['wo_numbers']:
            print(f"  ✅ {wo}")
    
    if result['br_numbers']:
        print(f"\nBR NUMBERS FOUND:")
        for br in result['br_numbers']:
            print(f"  ✅ {br}")
    
    return len(result['wo_numbers']) > 0


if __name__ == "__main__":
    success = asyncio.run(test_crawler())
    exit(0 if success else 1)
