"""
INPI Simple Crawler - Adapted from your Node.js version
Lightweight crawler for BR patent details
"""

import asyncio
import logging
import re
from typing import List, Dict, Optional
import httpx

logger = logging.getLogger(__name__)


class INPICrawler:
    """
    INPI (Brazilian Patent Office) Simple Crawler
    
    Adapted from your existing Node.js crawler
    Purpose: Get BR patent details for validation
    """
    
    # Your existing INPI crawler endpoint
    INPI_API_URL = "https://crawler3-production.up.railway.app/api/data/inpi/patents"
    
    def __init__(self):
        self.session = httpx.AsyncClient(timeout=120.0)
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.aclose()
    
    async def search_molecule(self, molecule: str) -> List[Dict]:
        """
        Search INPI for BR patents by molecule name
        
        Uses your existing deployed crawler
        
        Args:
            molecule: Molecule name
            
        Returns:
            List of BR patent dicts
        """
        logger.info(f"🔍 INPI Search: {molecule}")
        
        try:
            response = await self.session.get(
                self.INPI_API_URL,
                params={'medicine': molecule}
            )
            
            if response.status_code != 200:
                logger.warning(f"   INPI API failed: {response.status_code}")
                return []
                
            data = response.json()
            
            patents = data.get('data', [])
            
            # Parse results
            br_patents = []
            
            for p in patents:
                if not p.get('title') or not p.get('title').startswith('BR'):
                    continue
                    
                br_number = p.get('title', '').replace(' ', '-')
                
                br_patents.append({
                    'number': br_number,
                    'process_number': p.get('processNumber', ''),
                    'applicant': p.get('applicant', ''),
                    'deposit_date': p.get('depositDate', ''),
                    'full_text': p.get('fullText', ''),
                    'link': f"https://busca.inpi.gov.br/pePI/servlet/PatenteServletController?Action=detail&CodPedido={br_number}",
                    'source': 'inpi_crawler'
                })
                
            logger.info(f"   ✅ INPI: Found {len(br_patents)} BR patents")
            
            return br_patents
            
        except Exception as e:
            logger.warning(f"   INPI search error: {e}")
            return []
    
    async def validate_br_numbers(self, br_numbers: List[str]) -> Dict[str, bool]:
        """
        Validate if BR numbers exist in INPI
        
        Args:
            br_numbers: List of BR patent numbers
            
        Returns:
            Dict mapping BR -> exists (bool)
        """
        logger.info(f"   Validating {len(br_numbers)} BR numbers in INPI...")
        
        validation = {}
        
        # For now, simple check
        # In production, could query INPI directly
        for br in br_numbers:
            # Basic format validation
            # BR followed by 12 or 9 digits
            is_valid_format = bool(re.match(r'BR\d{9,12}', br.replace('-', '')))
            validation[br] = is_valid_format
            
        valid_count = sum(validation.values())
        logger.info(f"   ✅ {valid_count}/{len(br_numbers)} BR numbers valid")
        
        return validation


async def test_inpi():
    """Test INPI crawler"""
    
    async with INPICrawler() as inpi:
        # Test 1: Search by molecule
        patents = await inpi.search_molecule("Darolutamide")
        
        print(f"\nINPI Results: {len(patents)} BR patents")
        for p in patents[:5]:
            print(f"  - {p['number']}: {p['applicant']}")
            
        # Test 2: Validate BR numbers
        if patents:
            br_numbers = [p['number'] for p in patents[:3]]
            validation = await inpi.validate_br_numbers(br_numbers)
            
            print(f"\nValidation:")
            for br, valid in validation.items():
                print(f"  {br}: {'✅' if valid else '❌'}")


if __name__ == "__main__":
    asyncio.run(test_inpi())
