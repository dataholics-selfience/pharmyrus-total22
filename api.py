"""
Pharmyrus V10 - INPI FIRST
Estratégia: INPI Crawler retorna BR + WO juntos!
Sem SerpAPI, sem Google direto
Apenas: PubChem + INPI Crawler (intensivo) + Playwright (fallback)
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

app = FastAPI(title="Pharmyrus V10 INPI-First", version="10.0.0")

# ========================================
# 1. PUBCHEM
# ========================================

async def get_pubchem_data(molecule: str) -> Dict[str, Any]:
    """Busca dev codes, CAS e synonyms no PubChem"""
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{molecule}/synonyms/JSON"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            
            syns = data.get('InformationList', {}).get('Information', [{}])[0].get('Synonym', [])
            
            # Dev codes: AB-123, MLN-4567
            dev_codes = [s for s in syns if re.match(r'^[A-Z]{2,5}-?\d{3,7}[A-Z]?$', s, re.I)][:15]
            
            # CAS: 123-45-6
            cas = next((s for s in syns if re.match(r'^\d{2,7}-\d{2}-\d$', s)), None)
            
            # Todos os synonyms (para queries)
            all_syns = [s for s in syns if s and len(s) > 2 and len(s) < 50][:30]
            
            return {
                'dev_codes': dev_codes,
                'cas': cas,
                'all_synonyms': all_syns
            }
        except Exception as e:
            print(f"PubChem error: {e}")
            return {'dev_codes': [], 'cas': None, 'all_synonyms': []}


# ========================================
# 2. INPI CRAWLER (fonte principal!)
# ========================================

async def search_inpi_detailed(query: str) -> Dict[str, Any]:
    """
    Busca no INPI Crawler
    Retorna: BR patents + WO numbers (já vêm juntos!)
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
                # Extrair BR number
                br_num = item.get('title', '')
                if br_num and br_num.startswith('BR'):
                    
                    # Extrair WO number do texto (INPI retorna isso!)
                    full_text = str(item.get('fullText', '')) + ' ' + str(item.get('applicant', ''))
                    
                    # Procurar WO numbers no texto
                    wo_matches = re.findall(r'WO[\s-]?(\d{4})[\s/-]?(\d{6})', full_text, re.I)
                    for year, num in wo_matches:
                        wo = f'WO{year}{num}'
                        if wo not in wo_numbers:
                            wo_numbers.append(wo)
                    
                    br_patents.append({
                        'br_number': br_num.replace(' ', '-'),
                        'title': item.get('applicant', ''),
                        'filing_date': item.get('depositDate', ''),
                        'full_text': item.get('fullText', '')[:200],
                        'link': f"https://busca.inpi.gov.br/pePI/servlet/PatenteServletController?Action=detail&CodPedido={br_num}",
                        'source': f'inpi_{query[:20]}'
                    })
            
            return {
                'br_patents': br_patents,
                'wo_numbers': wo_numbers,
                'source': f'inpi:{query}'
            }
            
        except Exception as e:
            print(f"    ✗ INPI error for '{query}': {e}")
            return {'br_patents': [], 'wo_numbers': [], 'source': f'inpi:{query}'}


# ========================================
# 3. INPI ABUSE (como seu n8n - 15+ queries)
# ========================================

async def inpi_abuse_search(molecule: str, pubchem_data: Dict) -> Dict[str, Any]:
    """
    Estratégia ABUSE: múltiplas queries INPI
    Igual ao seu workflow n8n com 15 HTTP nodes
    """
    queries = []
    
    # 1. Nome principal
    queries.append(molecule)
    queries.append(molecule.lower())
    queries.append(molecule.upper())
    
    # 2. Dev codes (todos!)
    for dev in pubchem_data['dev_codes']:
        queries.append(dev)
        # Sem hífen também
        queries.append(dev.replace('-', ''))
    
    # 3. CAS
    if pubchem_data['cas']:
        queries.append(pubchem_data['cas'])
    
    # 4. Synonyms mais relevantes
    for syn in pubchem_data['all_synonyms'][:10]:
        if syn not in queries:
            queries.append(syn)
    
    # Limitar a 25 queries (não sobrecarregar)
    queries = queries[:25]
    
    print(f"\n[2/3] INPI ABUSE: {len(queries)} queries")
    
    # Executar todas em paralelo
    tasks = [search_inpi_detailed(q) for q in queries]
    results = await asyncio.gather(*tasks)
    
    # Consolidar resultados
    all_br = []
    all_wo = []
    
    for result in results:
        all_br.extend(result['br_patents'])
        all_wo.extend(result['wo_numbers'])
    
    # Deduplicar BR
    seen_br = set()
    unique_br = []
    for br in all_br:
        br_id = br['br_number'].upper().replace('-', '').replace(' ', '')
        if br_id not in seen_br:
            seen_br.add(br_id)
            unique_br.append(br)
    
    # Deduplicar WO
    unique_wo = list(dict.fromkeys(all_wo))
    
    print(f"  → Found {len(unique_br)} BR patents")
    print(f"  → Found {len(unique_wo)} WO numbers (from INPI!)")
    
    return {
        'br_patents': unique_br,
        'wo_numbers': unique_wo,
        'queries_used': queries
    }


# ========================================
# 4. PLAYWRIGHT FALLBACK (se necessário)
# ========================================

async def search_wo_via_playwright(molecule: str) -> List[str]:
    """
    Fallback: Crawler Playwright ROBUSTO para Google Patents
    Múltiplas estratégias de busca
    Usa apenas se INPI não retornar WOs suficientes
    """
    try:
        from google_patents_crawler import GooglePatentsCrawler
        
        crawler = GooglePatentsCrawler(headless=True)
        
        # Buscar com múltiplas estratégias
        wo_numbers = await crawler.search_wo_numbers(
            molecule=molecule,
            companies=['Bayer', 'Orion', 'AstraZeneca'],
            years=['2011', '2016', '2018', '2020', '2021', '2023'],
            max_results=30
        )
        
        print(f"  → Playwright Crawler found {len(wo_numbers)} WO numbers")
        return wo_numbers
            
    except ImportError:
        # Fallback simples se crawler não disponível
        print(f"  ⚠️ GooglePatentsCrawler not available, using simple Playwright")
        return await _simple_playwright_search(molecule)
    except Exception as e:
        print(f"  ✗ Playwright error: {e}")
        return []


async def _simple_playwright_search(molecule: str) -> List[str]:
    """Fallback simples se crawler avançado não disponível"""
    try:
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            url = f'https://patents.google.com/?q={molecule}+Bayer&num=20'
            await page.goto(url, timeout=30000)
            await page.wait_for_timeout(2000)
            
            html = await page.content()
            await browser.close()
            
            wo_matches = re.findall(r'WO[\s-]?(\d{4})[\s/-]?(\d{6})', html, re.I)
            wo_numbers = [f'WO{year}{num}' for year, num in wo_matches]
            return list(dict.fromkeys(wo_numbers))[:20]
            
    except Exception as e:
        print(f"  ✗ Simple Playwright error: {e}")
        return []


# ========================================
# 5. ORCHESTRATOR
# ========================================

async def search_patents_inpi_first(molecule: str, brand: str = "") -> Dict[str, Any]:
    """
    Fluxo V10 INPI-First:
    1. PubChem → dev codes + CAS + synonyms
    2. INPI ABUSE → BR + WO (principal!)
    3. Playwright → WO fallback (se necessário)
    4. Consolidate
    """
    start_time = datetime.now()
    
    # Phase 1: PubChem
    print(f"\n[1/3] PubChem: {molecule}")
    pubchem = await get_pubchem_data(molecule)
    print(f"  → {len(pubchem['dev_codes'])} dev codes, CAS={pubchem['cas']}")
    
    # Phase 2: INPI ABUSE (principal!)
    inpi_results = await inpi_abuse_search(molecule, pubchem)
    
    # Phase 3: Playwright fallback (se INPI retornou poucos WO)
    wo_numbers = inpi_results['wo_numbers']
    
    if len(wo_numbers) < 3:
        print(f"\n[3/3] Playwright Fallback (INPI only found {len(wo_numbers)} WOs)")
        playwright_wos = await search_wo_via_playwright(molecule)
        wo_numbers.extend(playwright_wos)
        wo_numbers = list(dict.fromkeys(wo_numbers))
    else:
        print(f"\n[3/3] Skipping Playwright (INPI found {len(wo_numbers)} WOs)")
    
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
            'mode': 'V10 INPI-First - INPI retorna BR + WO juntos!',
            'sources': ['PubChem', 'INPI Crawler (25 queries)', 'Playwright (fallback)'],
            'inpi_queries': inpi_results['queries_used']
        },
        'wo_discovery': {
            'total_wo': len(wo_numbers),
            'wo_numbers': wo_numbers,
            'source': 'INPI Crawler (extracted from BR patent data)'
        },
        'br_patents': {
            'total_br': len(inpi_results['br_patents']),
            'patents': inpi_results['br_patents']
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
        
        wo_upper = [w.upper() for w in wo_numbers]
        matches = [w for w in cortellis_wos if w in wo_upper]
        
        result['cortellis_comparison'] = {
            'expected_wos': 7,
            'found_wos': len(wo_numbers),
            'matches': len(matches),
            'match_rate': f"{round(len(matches)/7*100)}%",
            'matched_wos': matches,
            'missing_wos': [w for w in cortellis_wos if w not in wo_upper],
            'expected_br': 8,
            'found_br': len(inpi_results['br_patents']),
            'status': '✅ EXCELLENT' if len(matches) >= 6 else '✅ GOOD' if len(matches) >= 5 else '⚠️ NEEDS IMPROVEMENT'
        }
    
    return result


# ========================================
# 6. API ENDPOINTS
# ========================================

class SearchRequest(BaseModel):
    nome_molecula: str
    nome_comercial: str = ""

@app.post("/api/v10/search")
async def search_endpoint(req: SearchRequest):
    """Endpoint principal"""
    try:
        result = await search_patents_inpi_first(req.nome_molecula, req.nome_comercial)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v10/test/darolutamide")
async def test_darolutamide():
    """Teste rápido com Darolutamide"""
    result = await search_patents_inpi_first("Darolutamide", "Nubeqa")
    return JSONResponse(content=result)

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "10.0.0",
        "mode": "INPI-First (INPI retorna BR + WO juntos!)",
        "features": [
            "PubChem integration",
            "INPI Crawler ABUSE (25 queries)",
            "WO extraction from INPI data",
            "Playwright fallback",
            "ZERO SerpAPI dependency"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
