"""
Pharmyrus V13 - GOOGLE PATENTS DIRETO
======================================

INSIGHT DO USUÁRIO (estava certo o tempo todo!):
- Busca simples: "darolutamide wo site:patents.google.com"  
- Funciona, acha WOs facilmente
- Filtra por BR dentro do Google Patents
- SIMPLES E EFICAZ!

Por que V10/V11/V12 falharam?
- Dependiam de INPI Crawler (rate limiting, 500 errors)
- Overengineering com EPO API, Playwright, etc
- NÃO usavam Google Patents diretamente!

V13 - Estratégia do Usuário:
1. PubChem → Dev codes
2. SerpAPI Google Patents → WO numbers (DIRETO!)
3. Para cada WO → Buscar família BR via SerpAPI  
4. Skip INPI (não confiável)
"""

from fastapi import FastAPI
from typing import Dict, List, Any, Optional
import httpx
import asyncio
import re
from urllib.parse import quote
from datetime import datetime

app = FastAPI(title="Pharmyrus V13", version="13.0.0")

SERPAPI_KEY = "3f22448f4d43ce8259fa2f7f6385222323a67c4ce4e72fcc774b43d23812889d"

# ========================================
# PUBCHEM
# ========================================

async def get_pubchem_data(molecule: str) -> Dict[str, Any]:
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{quote(molecule)}/synonyms/JSON"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(url)
            data = resp.json()
            syns = data['InformationList']['Information'][0]['Synonym']
            
            dev_codes = [s for s in syns if re.match(r'^[A-Z]{2,5}[-\s]?\d{3,7}[A-Z]?$', s, re.I)][:10]
            cas = next((s for s in syns if re.match(r'^\d{2,7}-\d{2}-\d$', s)), None)
            
            return {'dev_codes': dev_codes, 'cas': cas}
        except:
            return {'dev_codes': [], 'cas': None}

# ========================================
# GOOGLE PATENTS - Estratégia do Usuário!
# ========================================

async def search_google_patents_wo(molecule: str, dev_codes: List[str]) -> List[str]:
    """
    EXATAMENTE a estratégia do usuário:
    - Query: "darolutamide wo site:patents.google.com"
    - Extrai WO numbers dos resultados
    """
    print(f"\n[2/4] Google Patents: WO Discovery (estratégia do usuário!)")
    
    queries = [
        f'{molecule} wo site:patents.google.com',
        f'{molecule} patent wo site:patents.google.com',
    ]
    
    # Add dev codes
    for dev in dev_codes[:3]:
        queries.append(f'{dev} wo site:patents.google.com')
    
    wo_numbers = set()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for query in queries[:5]:
            try:
                url = "https://serpapi.com/search.json"
                params = {
                    'engine': 'google',
                    'q': query,
                    'api_key': SERPAPI_KEY,
                    'num': 20
                }
                
                resp = await client.get(url, params=params)
                data = resp.json()
                
                results = data.get('organic_results', [])
                
                for r in results:
                    text = (r.get('title', '') + ' ' + 
                           r.get('snippet', '') + ' ' + 
                           r.get('link', ''))
                    
                    # Extrair WO numbers
                    matches = re.findall(r'WO[\s-]?(\d{4})[\s/-]?(\d{6})', text, re.I)
                    for year, num in matches:
                        wo = f'WO{year}{num}'
                        wo_numbers.add(wo)
                
                await asyncio.sleep(1.0)
                
            except Exception as e:
                print(f"    ✗ Query '{query[:40]}...': {type(e).__name__}")
    
    wo_list = sorted(list(wo_numbers))
    print(f"  → Found {len(wo_list)} WO numbers")
    for wo in wo_list[:10]:
        print(f"    • {wo}")
    
    return wo_list

# ========================================
# GOOGLE PATENTS - BR Family Search
# ========================================

async def get_br_from_wo(wo_number: str) -> List[Dict[str, Any]]:
    """
    Para cada WO, busca família BR
    Como usuário fez: clicar em BR no Google Patents
    """
    url = "https://serpapi.com/search.json"
    params = {
        'engine': 'google_patents',
        'q': wo_number,
        'api_key': SERPAPI_KEY
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params=params)
            data = resp.json()
            
            br_patents = []
            
            # Procurar BR na família de patentes
            worldwide = data.get('worldwide_applications', {})
            
            for year, apps in worldwide.items():
                if not isinstance(apps, list):
                    continue
                    
                for app in apps:
                    doc_id = app.get('document_id', '')
                    
                    if doc_id.startswith('BR'):
                        title = app.get('title', '')
                        link = app.get('link', f'https://patents.google.com/patent/{doc_id}')
                        
                        br_patents.append({
                            'br_number': doc_id,
                            'wo_origin': wo_number,
                            'title': title,
                            'link': link,
                            'source': 'google_patents_family'
                        })
            
            if br_patents:
                print(f"    ✓ {wo_number} → {len(br_patents)} BR")
            
            return br_patents
            
    except Exception as e:
        print(f"    ✗ {wo_number}: {type(e).__name__}")
        return []

async def search_br_patents(wo_numbers: List[str]) -> List[Dict[str, Any]]:
    """
    Para cada WO, busca BRs (como usuário fez manualmente)
    """
    print(f"\n[3/4] Google Patents: BR Family Search")
    
    all_br = []
    
    for wo in wo_numbers[:15]:  # Limitar a 15 WOs
        br_list = await get_br_from_wo(wo)
        all_br.extend(br_list)
        await asyncio.sleep(1.0)  # Delay entre requests
    
    # Deduplicar
    seen = set()
    unique_br = []
    for br in all_br:
        br_id = br['br_number'].upper().replace('-', '').replace(' ', '')
        if br_id not in seen:
            seen.add(br_id)
            unique_br.append(br)
    
    print(f"  → Found {len(unique_br)} unique BR patents")
    
    return unique_br

# ========================================
# ENDPOINT PRINCIPAL
# ========================================

@app.get("/api/v13/search/{molecule}")
async def search_molecule(molecule: str, brand: Optional[str] = None):
    """
    V13 - ESTRATÉGIA DO USUÁRIO (simples e funciona!)
    
    1. PubChem → Dev codes
    2. Google Patents Search → WO numbers (como usuário fez!)
    3. Para cada WO → Buscar BR family (como usuário fez!)
    4. Skip INPI (não é confiável)
    """
    start_time = datetime.now()
    
    print(f"\n{'='*60}")
    print(f"V13 PATENT SEARCH: {molecule}")
    print(f"Estratégia: GOOGLE PATENTS DIRETO (como usuário mostrou!)")
    print(f"{'='*60}")
    
    # 1. PubChem
    print(f"\n[1/4] PubChem")
    pubchem = await get_pubchem_data(molecule)
    print(f"  → {len(pubchem['dev_codes'])} dev codes")
    
    # 2. Google Patents → WOs (estratégia do usuário!)
    wo_numbers = await search_google_patents_wo(molecule, pubchem['dev_codes'])
    
    # 3. Para cada WO → BRs (estratégia do usuário!)
    br_patents = await search_br_patents(wo_numbers)
    
    print(f"\n[4/4] Skip INPI (Google Patents é suficiente!)")
    
    # Cortellis comparison
    expected_wos = []
    if molecule.lower() == 'darolutamide':
        expected_wos = [
            'WO2016162604', 'WO2011051540', 'WO2018162793',
            'WO2021229145', 'WO2023194528', 'WO2023222557', 'WO2023161458'
        ]
    
    matched_wos = [wo for wo in wo_numbers if wo in expected_wos]
    missing_wos = [wo for wo in expected_wos if wo not in wo_numbers]
    
    match_rate = 0
    if expected_wos:
        match_rate = int((len(matched_wos) / len(expected_wos)) * 100)
    
    status = "✅ EXCELLENT" if match_rate >= 70 else "⚠️ ACCEPTABLE" if match_rate >= 40 else "❌ LOW"
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    print(f"\n{'='*60}")
    print(f"RESULTADO:")
    print(f"  WOs: {len(wo_numbers)} (expected: {len(expected_wos)})")
    print(f"  BRs: {len(br_patents)}")
    print(f"  Match: {match_rate}% - {status}")
    print(f"  Tempo: {elapsed:.1f}s")
    print(f"{'='*60}")
    
    return {
        "molecule_info": {
            "name": molecule,
            "brand": brand or "Unknown",
            "dev_codes": pubchem['dev_codes'],
            "cas": pubchem['cas']
        },
        "search_strategy": {
            "mode": "V13 - Google Patents Direto (estratégia do usuário!)",
            "sources": [
                "Google Patents (WO search) - COMO USUÁRIO FEZ!",
                "Google Patents (BR family) - COMO USUÁRIO FEZ!",
                "NO INPI (não confiável)"
            ],
            "why_this_works": "Usuário mostrou: busca direta funciona melhor que APIs complexas!",
            "user_query_example": "darolutamide wo site:patents.google.com"
        },
        "wo_discovery": {
            "total_wo": len(wo_numbers),
            "wo_numbers": wo_numbers,
            "source": "Google Patents Search (SerpAPI)"
        },
        "br_patents": {
            "total_br": len(br_patents),
            "patents": br_patents
        },
        "performance": {
            "execution_time_seconds": round(elapsed, 2)
        },
        "cortellis_comparison": {
            "expected_wos": len(expected_wos),
            "found_wos": len(wo_numbers),
            "matches": len(matched_wos),
            "match_rate": f"{match_rate}%",
            "matched_wos": matched_wos,
            "missing_wos": missing_wos,
            "expected_br": 8,
            "found_br": len(br_patents),
            "status": status
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "13.0.0"}

@app.get("/api/v13/test/darolutamide")
async def test_darolutamide():
    return await search_molecule("Darolutamide", "Nubeqa")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
