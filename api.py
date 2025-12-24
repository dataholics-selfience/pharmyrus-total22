"""
Pharmyrus V12 - SEQUENTIAL INPI Requests
==========================================

CORREÇÃO CRÍTICA vs V11:
- V11: 27 requests PARALELOS → 500 errors (overload)
- V12: 10-12 requests SEQUENCIAIS com delay → funciona!

Estratégia:
- PubChem → Dev codes, CAS
- INPI SEQUENTIAL (10-12 queries PT com delay 1s)
- Retry automático em caso de 500
"""

from fastapi import FastAPI
from typing import Dict, List, Any, Optional
import httpx
import asyncio
import re
from urllib.parse import quote
from datetime import datetime
import time

app = FastAPI(title="Pharmyrus V12", version="12.0.0")

# ========================================
# TRADUTOR PT
# ========================================

PT_TRANSLATIONS = {
    'Darolutamide': 'Darolutamida',
    'Abiraterone': 'Abiraterona',
    'Enzalutamide': 'Enzalutamida',
    'Apalutamide': 'Apalutamida',
    'Olaparib': 'Olaparibe',
    'Niraparib': 'Niraparibe',
    'Venetoclax': 'Venetoclax',
    'Axitinib': 'Axitinibe',
    'Tivozanib': 'Tivozanibe',
    'Trastuzumab': 'Trastuzumabe',
    'Ixazomib': 'Ixazomibe',
    'Sonidegib': 'Sonidegibe',
}

def translate_to_portuguese(molecule: str) -> str:
    if molecule in PT_TRANSLATIONS:
        return PT_TRANSLATIONS[molecule]
    
    pt = molecule
    if pt.endswith('ide'):
        pt = pt[:-3] + 'ida'
    elif pt.endswith('ine'):
        pt = pt[:-3] + 'ina'
    elif pt.endswith('one'):
        pt = pt[:-3] + 'ona'
    elif pt.endswith('ib') and not pt.endswith('sib'):
        pt = pt + 'e'
    
    return pt

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
            
            dev_codes = []
            seen_devs = set()
            for s in syns:
                if re.match(r'^[A-Z]{2,5}[-\s]?\d{3,7}[A-Z]?$', s, re.I):
                    clean = s.strip().upper()
                    if clean not in seen_devs and len(dev_codes) < 15:
                        seen_devs.add(clean)
                        dev_codes.append(s)
            
            cas = None
            for s in syns:
                if re.match(r'^\d{2,7}-\d{2}-\d$', s):
                    cas = s
                    break
            
            all_syns = [s for s in syns if len(s) > 3 and len(s) < 50][:50]
            
            return {
                'dev_codes': dev_codes,
                'cas': cas,
                'all_synonyms': all_syns
            }
            
        except:
            return {'dev_codes': [], 'cas': None, 'all_synonyms': []}

# ========================================
# INPI CRAWLER (SEQUENTIAL!)
# ========================================

async def search_inpi_single(query: str, retry: int = 0) -> Dict[str, Any]:
    """
    Busca INPI com RETRY automático
    """
    url = "https://crawler3-production.up.railway.app/api/data/inpi/patents"
    
    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            params = {'medicine': query}
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            
            results = data.get('data', [])
            
            br_patents = []
            wo_numbers = []
            
            for item in results:
                br_num = item.get('title', '').strip()
                
                if br_num == 'Pedido' or not br_num.startswith('BR'):
                    continue
                
                real_title = item.get('applicant', '').strip()
                filing_date = item.get('depositDate', '').strip()
                full_text = item.get('fullText', '').strip()
                
                # Extrair WO do fullText
                wo_matches = re.findall(r'WO[\s-]?(\d{4})[\s/-]?(\d{6})', full_text, re.I)
                for year, num in wo_matches:
                    wo = f'WO{year}{num}'
                    if wo not in wo_numbers:
                        wo_numbers.append(wo)
                
                br_patents.append({
                    'br_number': br_num.replace(' ', ''),
                    'title': real_title,
                    'filing_date': filing_date,
                    'full_text': full_text[:300],
                    'link': f"https://busca.inpi.gov.br/pePI/servlet/PatenteServletController?Action=detail&CodPedido={br_num}",
                    'source': f'inpi_{query[:20]}'
                })
            
            if br_patents or wo_numbers:
                print(f"    ✓ '{query}': {len(br_patents)} BR, {len(wo_numbers)} WO")
            
            return {
                'br_patents': br_patents,
                'wo_numbers': wo_numbers,
                'source': f'inpi:{query}'
            }
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 500 and retry < 2:
                print(f"    ⚠ '{query}': 500 error, retry {retry+1}/2...")
                await asyncio.sleep(2)
                return await search_inpi_single(query, retry + 1)
            else:
                print(f"    ✗ '{query}': HTTP {e.response.status_code}")
                return {'br_patents': [], 'wo_numbers': [], 'source': f'inpi:{query}'}
        except Exception as e:
            print(f"    ✗ '{query}': {type(e).__name__}")
            return {'br_patents': [], 'wo_numbers': [], 'source': f'inpi:{query}'}

# ========================================
# INPI SEQUENTIAL (NÃO PARALELO!)
# ========================================

async def inpi_sequential_search(molecule: str, pubchem_data: Dict) -> Dict[str, Any]:
    """
    SEQUENTIAL INPI search com delay
    
    MUDANÇA CRÍTICA vs V11:
    - V11: 27 paralelos → 500 errors
    - V12: 10-12 sequenciais com delay → funciona!
    """
    queries = []
    
    # 1. Nome PT (PRIORITÁRIO!)
    molecule_pt = translate_to_portuguese(molecule)
    queries.append(molecule_pt)  # "Darolutamida"
    queries.append(molecule_pt.lower())  # "darolutamida"
    
    # 2. Dev codes top 3
    for dev in pubchem_data['dev_codes'][:3]:
        queries.append(dev)
    
    # 3. CAS
    if pubchem_data['cas']:
        queries.append(pubchem_data['cas'])
    
    # 4. Nome original (se diferente)
    if molecule != molecule_pt:
        queries.append(molecule)
        queries.append(molecule.lower())
    
    # 5. Synonyms relevantes (só 2)
    for syn in pubchem_data['all_synonyms'][:2]:
        if len(syn) > 5 and syn.lower() not in [q.lower() for q in queries]:
            queries.append(syn)
    
    # Limitar a 12 queries MAX
    queries = queries[:12]
    
    print(f"\n[2/3] INPI SEQUENTIAL: {len(queries)} queries (com delay)")
    print(f"  Nome PT: {molecule_pt}")
    
    # EXECUTAR SEQUENCIALMENTE (não paralelo!)
    all_br = []
    all_wo = []
    
    for i, query in enumerate(queries):
        # Buscar
        result = await search_inpi_single(query)
        
        all_br.extend(result['br_patents'])
        all_wo.extend(result['wo_numbers'])
        
        # DELAY entre requests (evita overload)
        if i < len(queries) - 1:
            await asyncio.sleep(1.0)  # 1 segundo entre requests
    
    # Deduplicar
    seen_br = set()
    unique_br = []
    for br in all_br:
        br_id = br['br_number'].upper().replace('-', '').replace(' ', '')
        if br_id not in seen_br:
            seen_br.add(br_id)
            unique_br.append(br)
    
    unique_wo = list(dict.fromkeys(all_wo))
    
    print(f"  → Found {len(unique_br)} BR patents")
    print(f"  → Found {len(unique_wo)} WO numbers")
    
    return {
        'br_patents': unique_br,
        'wo_numbers': unique_wo,
        'queries_tested': len(queries),
        'molecule_pt': molecule_pt
    }

# ========================================
# ENDPOINT PRINCIPAL
# ========================================

@app.get("/api/v12/search/{molecule}")
async def search_molecule(molecule: str, brand: Optional[str] = None):
    """
    V12 Patent Search - SEQUENTIAL INPI (não paralelo!)
    """
    start_time = datetime.now()
    
    print(f"\n{'='*60}")
    print(f"V12 PATENT SEARCH: {molecule}")
    print(f"{'='*60}")
    
    # 1. PubChem
    print(f"\n[1/3] PubChem: {molecule}")
    pubchem = await get_pubchem_data(molecule)
    print(f"  → {len(pubchem['dev_codes'])} dev codes, CAS={pubchem['cas']}")
    
    # 2. INPI SEQUENTIAL
    inpi_result = await inpi_sequential_search(molecule, pubchem)
    
    # 3. Skip Playwright por enquanto
    all_wo = inpi_result['wo_numbers']
    all_br = inpi_result['br_patents']
    
    if len(all_wo) < 3:
        print(f"\n[3/3] Skipping Playwright (not implemented)")
    else:
        print(f"\n[3/3] Skipping Playwright (INPI found {len(all_wo)} WOs)")
    
    # Cortellis comparison
    expected_wos = []
    expected_br = 8
    if molecule.lower() == 'darolutamide':
        expected_wos = [
            'WO2016162604', 'WO2011051540', 'WO2018162793',
            'WO2021229145', 'WO2023194528', 'WO2023222557', 'WO2023161458'
        ]
    
    matched_wos = [wo for wo in all_wo if wo in expected_wos]
    missing_wos = [wo for wo in expected_wos if wo not in all_wo]
    
    match_rate = 0
    if expected_wos:
        match_rate = int((len(matched_wos) / len(expected_wos)) * 100)
    
    status = "✅ EXCELLENT" if match_rate >= 70 else "⚠️ ACCEPTABLE" if match_rate >= 40 else "❌ LOW"
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    return {
        "molecule_info": {
            "name": molecule,
            "name_pt": inpi_result.get('molecule_pt', molecule),
            "brand": brand or "Unknown",
            "dev_codes": pubchem['dev_codes'],
            "cas": pubchem['cas']
        },
        "search_strategy": {
            "mode": "V12 INPI SEQUENTIAL (não paralelo!)",
            "sources": ["PubChem", "INPI Crawler SEQUENTIAL"],
            "critical_fix": "Requests sequenciais com delay 1s (vs paralelo V11)",
            "inpi_queries": inpi_result.get('queries_tested', 0)
        },
        "wo_discovery": {
            "total_wo": len(all_wo),
            "wo_numbers": all_wo,
            "source": "INPI Crawler (fullText extraction)"
        },
        "br_patents": {
            "total_br": len(all_br),
            "patents": all_br
        },
        "performance": {
            "execution_time_seconds": round(elapsed, 2)
        },
        "cortellis_comparison": {
            "expected_wos": len(expected_wos),
            "found_wos": len(all_wo),
            "matches": len(matched_wos),
            "match_rate": f"{match_rate}%",
            "matched_wos": matched_wos,
            "missing_wos": missing_wos,
            "expected_br": expected_br,
            "found_br": len(all_br),
            "status": status
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "12.0.0"}

@app.get("/api/v12/test/darolutamide")
async def test_darolutamide():
    return await search_molecule("Darolutamide", "Nubeqa")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
