"""
INPI Service
Search Brazilian patent database
"""
import httpx
from typing import List, Dict


async def search_inpi(medicine_name: str) -> List[Dict]:
    """
    Search INPI database
    
    Args:
        medicine_name: Medicine/molecule name
        
    Returns:
        List of BR patents
    """
    results = []
    
    try:
        # Call existing INPI crawler on Railway
        url = f"https://crawler3-production.up.railway.app/api/data/inpi/patents?medicine={medicine_name}"
        
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                patents = data.get('data', [])
                
                for p in patents:
                    if p.get('processNumber') and p.get('title', '').startswith('BR'):
                        results.append({
                            'publication_number': p['title'].replace(' ', '-'),
                            'title': p.get('applicant', ''),
                            'filing_date': p.get('depositDate', ''),
                            'link': f"https://busca.inpi.gov.br/pePI/servlet/PatenteServletController?Action=detail&CodPedido={p['title']}",
                            'source': 'inpi'
                        })
                        
                print(f"  ✅ INPI: {len(results)} BR patents")
                
    except Exception as e:
        print(f"  ⚠ INPI error: {str(e)[:100]}")
        
    return results
