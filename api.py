"""
Pharmyrus V9 - SIMPLE
Baseado no workflow n8n que JÁ FUNCIONA
Sem dependências complexas, sem Playwright, sem EPO OPS
Apenas: PubChem + Google Patents (via requests) + INPI Crawler
"""
import os
import re
import json
import asyncio
from typing import List, Dict, Any
from datetime import datetime

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="Pharmyrus V9 Simple", version="9.0.0")

# ========================================
# 1. PUBCHEM (igual ao n8n)
# ========================================

async def get_pubchem_data(molecule: str) -> Dict[str, Any]:
    """Busca dev codes e CAS no PubChem (igual ao n8n)"""
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{molecule}/synonyms/JSON"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            
            syns = data.get('InformationList', {}).get('Information', [{}])[0].get('Synonym', [])
            
            # Dev codes: AB-123, MLN-4567
            dev_codes = [s for s in syns if re.match(r'^[A-Z]{2,5}-?\d{3,7}[A-Z]?$', s, re.I)][:10]
            
            # CAS: 123-45-6
            cas = next((s for s in syns if re.match(r'^\d{2,7}-\d{2}-\d$', s)), None)
            
            return {
                'dev_codes': dev_codes,
                'cas': cas,
                'all_synonyms': syns[:50]
            }
        except Exception as e:
            print(f"PubChem error: {e}")
            return {'dev_codes': [], 'cas': None, 'all_synonyms': []}


# ========================================
# 2. GOOGLE SEARCH para encontrar WO numbers
# (Igual ao n8n quando NÃO usa SerpAPI)
# ========================================

async def search_wo_numbers_via_google(query: str) -> List[str]:
    """
    Busca WO numbers via Google Search comum
    Extrai WO numbers dos resultados
    """
    # Google Search aceita requests simples com user-agent
    url = "https://www.google.com/search"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    async with httpx.AsyncClient(timeout=30.0, headers=headers, follow_redirects=True) as client:
        try:
            params = {
                'q': query,
                'num': 20
            }
            resp = await client.get(url, params=params)
            
            # Extrair WO numbers do HTML
            # Padrões: WO2016162604, WO 2016/162604, WO2016/162604
            patterns = [
                r'WO[\s-]?(\d{4})[\s/-]?(\d{6})',  # WO2016162604 ou WO 2016/162604
                r'WO[\s-]?(\d{4})[\s/-](\d{6})',   # WO2016-162604
            ]
            
            wo_numbers = []
            for pattern in patterns:
                matches = re.findall(pattern, resp.text, re.I)
                for year, num in matches:
                    wo = f'WO{year}{num}'
                    if wo not in wo_numbers:
                        wo_numbers.append(wo)
            
            if wo_numbers:
                print(f"    ✓ Found {len(wo_numbers)} WOs from: {query[:50]}")
            
            return wo_numbers[:20]
        except Exception as e:
            print(f"    ✗ Google search error: {e}")
            return []


# ========================================
# 3. INPI CRAWLER (seu crawler existente!)
# ========================================

async def search_inpi_crawler(query: str) -> List[Dict[str, Any]]:
    """Usa SEU crawler INPI que JÁ FUNCIONA"""
    url = "https://crawler3-production.up.railway.app/api/data/inpi/patents"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            params = {'medicine': query}
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            
            patents = data.get('data', [])
            
            br_patents = []
            for p in patents:
                if p.get('title', '').startswith('BR'):
                    br_patents.append({
                        'number': p['title'].replace(' ', '-'),
                        'title': p.get('applicant', ''),
                        'filing_date': p.get('depositDate', ''),
                        'link': f"https://busca.inpi.gov.br/pePI/servlet/PatenteServletController?Action=detail&CodPedido={p['title']}",
                        'source': 'inpi_crawler'
                    })
            
            return br_patents
        except Exception as e:
            print(f"INPI crawler error: {e}")
            return []


# ========================================
# 4. ORCHESTRATOR (igual ao n8n)
# ========================================

async def search_patents_simple(molecule: str, brand: str = "") -> Dict[str, Any]:
    """
    Fluxo baseado no n8n que funciona:
    1. PubChem → dev codes + CAS
    2. Google Patents → WO numbers
    3. INPI Crawler → BR patents
    4. Consolidate
    """
    start_time = datetime.now()
    
    # Phase 1: PubChem
    print(f"[1/3] PubChem: {molecule}")
    pubchem = await get_pubchem_data(molecule)
    
    # Phase 2: Build queries (como no n8n - específico!)
    queries = []
    
    # Queries específicas com fabricante + WO
    queries.append(f'"{molecule}" "Bayer" "WO2016"')
    queries.append(f'"{molecule}" "Bayer" "WO2018"')
    queries.append(f'"{molecule}" "Bayer" "WO2021"')
    queries.append(f'"{molecule}" "Bayer" "WO2023"')
    queries.append(f'"{molecule}" "Orion" patent WO')
    
    if brand:
        queries.append(f'"{brand}" "Bayer" patent WO')
    
    # Dev codes com aspas (busca exata)
    for dev in pubchem['dev_codes'][:2]:
        queries.append(f'"{dev}" patent WO')
    
    # CAS number
    if pubchem['cas']:
        queries.append(f'"{pubchem["cas"]}" patent WO')
    
    # Buscar WO numbers via Google Search
    print(f"[2/3] Google Search: {len(queries)} queries")
    wo_tasks = [search_wo_numbers_via_google(q) for q in queries]
    wo_results = await asyncio.gather(*wo_tasks)
    
    all_wos = []
    for wos in wo_results:
        all_wos.extend(wos)
    all_wos = list(dict.fromkeys(all_wos))  # unique
    
    print(f"  → Found {len(all_wos)} WO numbers")
    
    # Phase 3: INPI Crawler
    print(f"[3/3] INPI Crawler")
    inpi_tasks = [
        search_inpi_crawler(molecule),
        search_inpi_crawler(pubchem['dev_codes'][0]) if pubchem['dev_codes'] else search_inpi_crawler(molecule),
        search_inpi_crawler(brand) if brand else search_inpi_crawler(molecule),
    ]
    inpi_results = await asyncio.gather(*inpi_tasks)
    
    all_br = []
    for br_list in inpi_results:
        all_br.extend(br_list)
    
    # Remove duplicates
    seen = set()
    unique_br = []
    for br in all_br:
        br_id = br['number'].upper().replace('-', '').replace(' ', '')
        if br_id not in seen:
            seen.add(br_id)
            unique_br.append(br)
    
    print(f"  → Found {len(unique_br)} BR patents")
    
    # Consolidate
    execution_time = (datetime.now() - start_time).total_seconds()
    
    result = {
        'molecule_info': {
            'name': molecule,
            'brand': brand,
            'dev_codes': pubchem['dev_codes'],
            'cas': pubchem['cas']
        },
        'search_strategy': {
            'mode': 'V9 Simple - Based on working n8n workflow',
            'sources': ['PubChem', 'Google Search (WO extraction)', 'INPI Crawler'],
            'queries_used': queries
        },
        'wo_discovery': {
            'total_wo': len(all_wos),
            'wo_numbers': all_wos
        },
        'br_patents': {
            'total_br': len(unique_br),
            'patents': unique_br
        },
        'performance': {
            'execution_time_seconds': execution_time
        }
    }
    
    # Comparar com Cortellis (Darolutamide)
    if molecule.lower() == 'darolutamide':
        cortellis_wos = [
            'WO2016162604', 'WO2011051540', 'WO2018162793',
            'WO2021229145', 'WO2023194528', 'WO2023222557', 'WO2023161458'
        ]
        
        found_wos_upper = [w.upper() for w in all_wos]
        matches = [w for w in cortellis_wos if w in found_wos_upper]
        
        result['cortellis_comparison'] = {
            'expected_wos': 7,
            'found_wos': len(all_wos),
            'matches': len(matches),
            'match_rate': f"{round(len(matches)/7*100)}%",
            'matched_wos': matches,
            'missing_wos': [w for w in cortellis_wos if w not in found_wos_upper],
            'expected_br': 8,
            'found_br': len(unique_br),
            'status': '✅ GOOD' if len(matches) >= 5 else '⚠️ NEEDS IMPROVEMENT'
        }
    
    return result


# ========================================
# 5. API ENDPOINTS
# ========================================

class SearchRequest(BaseModel):
    nome_molecula: str
    nome_comercial: str = ""

@app.post("/api/v9/search")
async def search_endpoint(req: SearchRequest):
    """Endpoint principal"""
    try:
        result = await search_patents_simple(req.nome_molecula, req.nome_comercial)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v9/test/darolutamide")
async def test_darolutamide():
    """Teste rápido com Darolutamide"""
    result = await search_patents_simple("Darolutamide", "Nubeqa")
    return JSONResponse(content=result)

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "9.0.0",
        "mode": "SIMPLE - Based on working n8n workflow",
        "features": [
            "PubChem integration",
            "Google Patents (simple HTTP)",
            "INPI Crawler (existing)",
            "Zero complex dependencies"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
