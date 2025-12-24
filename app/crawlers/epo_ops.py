"""
EPO OPS API Client - Official European Patent Office API
Free, fast, authoritative patent data with applicant filtering
"""

import httpx
import asyncio
import logging
from typing import List, Dict, Optional
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class EPOOPSClient:
    """
    EPO OPS (Open Patent Services) API Client
    
    Official API from European Patent Office
    - Free: 4GB/week quota
    - Fast: 1 request returns all family data
    - Authoritative: Official EPO data
    - Filter by: applicant, inventor, CPC, dates
    """
    
    BASE_URL = "https://ops.epo.org/3.2/rest-services"
    AUTH_URL = "https://ops.epo.org/3.2/auth/accesstoken"
    
    # EPO credentials (free tier, public)
    # Register at: https://developers.epo.org/
    CONSUMER_KEY = "ScPAZJnGHIw1CtGLLPBI3wD4DqYa"
    CONSUMER_SECRET = "WKVdH7pGjTqDoVDO3MRiOS8M9Nwa"
    
    def __init__(self):
        self.token = None
        self.token_expires = None
        self.session = httpx.AsyncClient(timeout=60.0)
        
    async def __aenter__(self):
        await self._ensure_token()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.aclose()
    
    async def _ensure_token(self):
        """Get or refresh OAuth token"""
        if self.token and self.token_expires and datetime.now() < self.token_expires:
            return
            
        logger.info("Getting EPO OPS access token...")
        
        auth = httpx.BasicAuth(self.CONSUMER_KEY, self.CONSUMER_SECRET)
        
        response = await self.session.post(
            self.AUTH_URL,
            auth=auth,
            data={"grant_type": "client_credentials"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code != 200:
            raise Exception(f"EPO auth failed: {response.status_code}")
            
        data = response.json()
        self.token = data["access_token"]
        # Token expires in 20 min, refresh after 15 min
        self.token_expires = datetime.now() + timedelta(minutes=15)
        
        logger.info("✅ EPO OPS token obtained")
    
    async def search_by_applicant(
        self, 
        molecule: str, 
        applicants: List[str],
        max_results: int = 50
    ) -> Dict:
        """
        Search patents by applicant and molecule
        
        Args:
            molecule: Molecule name (e.g., "Darolutamide")
            applicants: List of companies (e.g., ["Bayer", "Orion"])
            max_results: Max results per applicant
            
        Returns:
            {
                'wo_numbers': [...],
                'br_families': {...},
                'raw_patents': [...],
                'statistics': {...}
            }
        """
        await self._ensure_token()
        
        logger.info(f"🔍 EPO Search: {molecule} by {', '.join(applicants)}")
        
        all_results = {
            'wo_numbers': set(),
            'br_families': {},  # WO -> [BR numbers]
            'raw_patents': [],
            'statistics': {
                'queries': 0,
                'total_patents': 0,
                'wo_found': 0,
                'br_found': 0,
                'by_applicant': {}
            }
        }
        
        for applicant in applicants:
            logger.info(f"   Searching applicant: {applicant}")
            
            # Build EPO query
            # ta = title/abstract
            # pa = applicant
            query = f'ta="{molecule}" AND pa="{applicant}"'
            
            try:
                results = await self._search_biblio(query, max_results)
                all_results['statistics']['queries'] += 1
                all_results['statistics']['by_applicant'][applicant] = len(results)
                all_results['statistics']['total_patents'] += len(results)
                
                logger.info(f"      Found {len(results)} patents from {applicant}")
                
                for patent in results:
                    all_results['raw_patents'].append(patent)
                    
                    # Extract WO numbers
                    pub_number = patent.get('publication_number', '')
                    if pub_number.startswith('WO'):
                        all_results['wo_numbers'].add(pub_number)
                        all_results['statistics']['wo_found'] += 1
                        
            except Exception as e:
                logger.warning(f"      Error searching {applicant}: {e}")
                
        all_results['wo_numbers'] = sorted(list(all_results['wo_numbers']))
        
        logger.info(f"   ✅ Total: {len(all_results['wo_numbers'])} WO numbers")
        
        return all_results
    
    async def _search_biblio(self, query: str, max_results: int) -> List[Dict]:
        """Execute bibliographic search"""
        await self._ensure_token()
        
        url = f"{self.BASE_URL}/published-data/search/biblio"
        
        params = {
            'q': query,
            'Range': f'1-{max_results}'
        }
        
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Accept': 'application/json'
        }
        
        response = await self.session.get(url, params=params, headers=headers)
        
        if response.status_code != 200:
            raise Exception(f"EPO search failed: {response.status_code}")
            
        data = response.json()
        
        # Parse results
        patents = []
        
        try:
            search_result = data.get('ops:world-patent-data', {}).get('ops:biblio-search', {}).get('ops:search-result', {})
            
            pub_refs = search_result.get('ops:publication-reference', [])
            if not isinstance(pub_refs, list):
                pub_refs = [pub_refs]
                
            for ref in pub_refs:
                patent = self._parse_publication_reference(ref)
                if patent:
                    patents.append(patent)
                    
        except Exception as e:
            logger.warning(f"Error parsing EPO results: {e}")
            
        return patents
    
    def _parse_publication_reference(self, ref: Dict) -> Optional[Dict]:
        """Parse publication reference to extract patent info"""
        try:
            doc_id = ref.get('document-id', {})
            
            country = doc_id.get('country', {}).get('$', '')
            number = doc_id.get('doc-number', {}).get('$', '')
            kind = doc_id.get('kind', {}).get('$', '')
            date = doc_id.get('date', {}).get('$', '')
            
            if not country or not number:
                return None
                
            pub_number = f"{country}{number}{kind}" if kind else f"{country}{number}"
            
            return {
                'publication_number': pub_number,
                'country': country,
                'number': number,
                'kind': kind,
                'date': date
            }
            
        except Exception as e:
            logger.debug(f"Error parsing reference: {e}")
            return None
    
    async def get_inpadoc_family(self, wo_number: str) -> List[str]:
        """
        Get INPADOC family members (including BR) for a WO patent
        
        Args:
            wo_number: WO number (e.g., "WO2016162604")
            
        Returns:
            List of BR patent numbers
        """
        await self._ensure_token()
        
        logger.info(f"      Getting family for {wo_number}")
        
        # Clean WO number (remove spaces, normalize)
        wo_clean = wo_number.replace(' ', '').replace('-', '')
        
        url = f"{self.BASE_URL}/family/publication/docdb/{wo_clean}/biblio"
        
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Accept': 'application/json'
        }
        
        try:
            response = await self.session.get(url, headers=headers)
            
            if response.status_code != 200:
                logger.warning(f"         EPO family failed: {response.status_code}")
                return []
                
            data = response.json()
            
            # Parse family members
            br_patents = []
            
            try:
                family_members = data.get('ops:world-patent-data', {}).get('ops:patent-family', {}).get('ops:family-member', [])
                
                if not isinstance(family_members, list):
                    family_members = [family_members]
                    
                for member in family_members:
                    pub_ref = member.get('publication-reference', {}).get('document-id', {})
                    
                    country = pub_ref.get('country', {}).get('$', '')
                    number = pub_ref.get('doc-number', {}).get('$', '')
                    
                    if country == 'BR' and number:
                        br_number = f"BR{number}"
                        br_patents.append(br_number)
                        logger.info(f"         Found BR: {br_number}")
                        
            except Exception as e:
                logger.debug(f"Error parsing family: {e}")
                
            return br_patents
            
        except Exception as e:
            logger.warning(f"         Error getting family: {e}")
            return []
    
    async def batch_get_families(self, wo_numbers: List[str]) -> Dict[str, List[str]]:
        """
        Get BR families for multiple WO numbers
        
        Args:
            wo_numbers: List of WO numbers
            
        Returns:
            Dict mapping WO -> [BR numbers]
        """
        logger.info(f"   Getting BR families for {len(wo_numbers)} WO patents...")
        
        results = {}
        
        for i, wo in enumerate(wo_numbers, 1):
            logger.info(f"   [{i}/{len(wo_numbers)}] {wo}")
            
            br_patents = await self.get_inpadoc_family(wo)
            
            if br_patents:
                results[wo] = br_patents
                
            # Rate limiting: max 10 requests/second
            if i < len(wo_numbers):
                await asyncio.sleep(0.15)
                
        total_br = sum(len(v) for v in results.values())
        logger.info(f"   ✅ Found {total_br} BR patents from {len(results)} WO")
        
        return results


async def test_epo_ops():
    """Test EPO OPS with Darolutamide"""
    
    async with EPOOPSClient() as epo:
        # Test 1: Search by applicant
        print("\n=== TEST 1: Search Darolutamide by Bayer/Orion ===")
        results = await epo.search_by_applicant(
            molecule="Darolutamide",
            applicants=["Bayer", "Orion"],
            max_results=20
        )
        
        print(f"\nWO Numbers Found: {len(results['wo_numbers'])}")
        for wo in results['wo_numbers'][:10]:
            print(f"  - {wo}")
            
        print(f"\nStatistics:")
        print(f"  Queries: {results['statistics']['queries']}")
        print(f"  Total Patents: {results['statistics']['total_patents']}")
        print(f"  WO Found: {results['statistics']['wo_found']}")
        print(f"  By Applicant: {results['statistics']['by_applicant']}")
        
        # Test 2: Get families
        if results['wo_numbers']:
            print(f"\n=== TEST 2: Get BR families for first 3 WO ===")
            wo_sample = results['wo_numbers'][:3]
            families = await epo.batch_get_families(wo_sample)
            
            print(f"\nBR Families Found: {len(families)}")
            for wo, br_list in families.items():
                print(f"\n  {wo} →")
                for br in br_list:
                    print(f"    - {br}")


if __name__ == "__main__":
    asyncio.run(test_epo_ops())
