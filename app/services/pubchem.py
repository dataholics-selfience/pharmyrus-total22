"""
PubChem Service
Extract molecular data and synonyms
"""
import httpx
from typing import Dict, List, Optional


async def get_pubchem_data(molecule_name: str) -> Dict:
    """
    Get PubChem data for molecule
    
    Args:
        molecule_name: Molecule name
        
    Returns:
        Dict with dev_codes, cas, synonyms
    """
    result = {
        'dev_codes': [],
        'cas': None,
        'all_synonyms': []
    }
    
    try:
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{molecule_name}/synonyms/JSON"
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                synonyms = data.get('InformationList', {}).get('Information', [{}])[0].get('Synonym', [])
                
                # Extract dev codes (pattern: AB-12345 or AB12345)
                import re
                dev_pattern = re.compile(r'^[A-Z]{2,5}[-\s]?\d{3,7}[A-Z]?$', re.IGNORECASE)
                
                for syn in synonyms:
                    if len(syn) < 3 or len(syn) > 40:
                        continue
                        
                    result['all_synonyms'].append(syn)
                    
                    # Check if dev code
                    if dev_pattern.match(syn) and 'CID' not in syn:
                        result['dev_codes'].append(syn)
                        
                    # Check if CAS number
                    if re.match(r'^\d{2,7}-\d{2}-\d$', syn):
                        result['cas'] = syn
                        
                result['all_synonyms'] = result['all_synonyms'][:100]  # Limit
                result['dev_codes'] = result['dev_codes'][:15]  # Limit
                
                print(f"  ✅ PubChem: {len(result['dev_codes'])} dev codes, CAS: {result['cas'] or 'N/A'}")
                
    except Exception as e:
        print(f"  ⚠ PubChem error: {str(e)[:100]}")
        
    return result
