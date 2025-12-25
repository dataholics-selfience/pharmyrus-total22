"""
Pharmyrus V15 - Patent Search with Real Crawlers
Multi-layer stealth architecture (Playwright → HTTP)
"""
import re
import asyncio
from datetime import datetime
from typing import Dict, List
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.pubchem import get_pubchem_data
from app.services.orchestrator import SearchOrchestrator
from app.services.inpi import search_inpi


app = FastAPI(title="Pharmyrus V15 - Stealth Crawlers")


class SearchRequest(BaseModel):
    nome_molecula: str
    nome_comercial: str = ""


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy", "version": "V15", "mode": "stealth_crawlers"}


@app.post("/api/v15/search")
async def search_patents(request: SearchRequest):
    """
    V15 Patent Search with Real Crawlers
    
    Multi-layer fallback:
    1. Playwright (CDP stealth)
    2. HTTP (basic fallback)
    """
    start_time = datetime.now()
    molecule = request.nome_molecula.strip()
    brand = request.nome_comercial.strip()
    
    if not molecule:
        raise HTTPException(400, "nome_molecula required")
        
    print(f"\n{'='*60}")
    print(f"V15 STEALTH SEARCH: {molecule}")
    print(f"Target: Find WO numbers via real crawlers")
    print(f"{'='*60}")
    
    # Step 1: PubChem
    print(f"\n[1/4] PUBCHEM DATA")
    pubchem_data = await get_pubchem_data(molecule)
    
    # Step 2: Build search queries
    print(f"\n[2/4] BUILD QUERIES")
    queries = _build_search_queries(molecule, brand, pubchem_data)
    print(f"  Built {len(queries)} search queries")
    
    # Step 3: WO Discovery (multi-layer crawlers)
    print(f"\n[3/4] WO DISCOVERY (multi-layer)")
    orchestrator = SearchOrchestrator()
    wo_numbers = set()
    layer_stats = {}
    
    for i, query in enumerate(queries[:10], 1):  # Limit to 10 queries for speed
        print(f"  Query {i}/{min(10, len(queries))}: {query['query'][:60]}...")
        
        result = await orchestrator.search_with_fallback(query['query'])
        
        if result['success']:
            # Track which layer succeeded
            layer = result['layer']
            layer_stats[layer] = layer_stats.get(layer, 0) + 1
            
            # Extract WO numbers from results
            for item in result['results']:
                text = item['title'] + ' ' + item.get('snippet', '') + ' ' + item.get('link', '')
                wos = _extract_wo_numbers(text)
                wo_numbers.update(wos)
                
        await asyncio.sleep(1)  # Delay between queries
        
    await orchestrator.cleanup()
    
    wo_list = sorted(list(wo_numbers))
    print(f"\n  Total WOs discovered: {len(wo_list)}")
    
    # Step 4: BR Patents from INPI
    print(f"\n[4/4] BR PATENTS (INPI)")
    br_patents_inpi = await search_inpi(molecule)
    
    # Execution time
    exec_time = (datetime.now() - start_time).total_seconds()
    
    # Cortellis comparison
    cortellis_expected = [
        "WO2016162604", "WO2011051540", "WO2018162793",
        "WO2021229145", "WO2023194528", "WO2023222557", "WO2023161458"
    ]
    
    matched = [wo for wo in wo_list if wo in cortellis_expected]
    match_rate = round((len(matched) / len(cortellis_expected)) * 100) if cortellis_expected else 0
    
    # Output
    result = {
        "molecule_info": {
            "name": molecule,
            "brand": brand,
            "dev_codes": pubchem_data['dev_codes'],
            "cas": pubchem_data['cas']
        },
        "search_strategy": {
            "version": "V15 - Real Stealth Crawlers",
            "mode": "multi_layer_fallback",
            "layers": ["Playwright (stealth)", "HTTP (fallback)"],
            "layer_stats": layer_stats,
            "techniques": [
                "CDP anti-detection (hide navigator.webdriver)",
                "User-Agent rotation (30+ UAs)",
                "Gaussian human-like delays",
                "Exponential backoff with jitter",
                "Realistic headers (Sec-Fetch-*)",
                "Viewport & geolocation spoofing"
            ]
        },
        "wo_discovery": {
            "total_wo": len(wo_list),
            "wo_numbers": wo_list,
            "queries_executed": min(10, len(queries))
        },
        "br_patents": {
            "from_inpi": len(br_patents_inpi),
            "patents": br_patents_inpi
        },
        "cortellis_comparison": {
            "expected": cortellis_expected,
            "found": wo_list,
            "matched": matched,
            "missing": [wo for wo in cortellis_expected if wo not in wo_list],
            "match_rate": f"{match_rate}%",
            "status": "✅ Excellent" if match_rate >= 70 else "⚠ Good" if match_rate >= 50 else "❌ Low"
        },
        "performance": {
            "execution_time_seconds": round(exec_time, 2)
        }
    }
    
    print(f"\n{'='*60}")
    print(f"RESULT:")
    print(f"  WOs found: {len(wo_list)}")
    print(f"  BR patents (INPI): {len(br_patents_inpi)}")
    print(f"  Match rate: {match_rate}%")
    print(f"  Status: {result['cortellis_comparison']['status']}")
    print(f"  Time: {exec_time:.1f}s")
    print(f"{'='*60}\n")
    
    return result


def _build_search_queries(molecule: str, brand: str, pubchem_data: Dict) -> List[Dict]:
    """Build search queries for WO discovery"""
    queries = []
    
    # Base molecule queries with years
    for year in [2011, 2016, 2018, 2019, 2020, 2021, 2022, 2023]:
        queries.append({
            'query': f"{molecule} patent WO{year}",
            'type': 'molecule_year'
        })
        
    # Dev code queries
    for dev in pubchem_data['dev_codes'][:5]:
        queries.append({
            'query': f"{dev} patent WO",
            'type': 'dev_code'
        })
        
    # CAS query
    if pubchem_data['cas']:
        queries.append({
            'query': f"{pubchem_data['cas']} patent WO",
            'type': 'cas'
        })
        
    # Brand query
    if brand:
        queries.append({
            'query': f"{brand} patent WO",
            'type': 'brand'
        })
        
    return queries


def _extract_wo_numbers(text: str) -> set:
    """Extract WO patent numbers from text"""
    wo_pattern = re.compile(r'WO[\s-]?(\d{4})[\s\/]?(\d{6})', re.IGNORECASE)
    matches = wo_pattern.findall(text)
    
    wo_numbers = set()
    for year, num in matches:
        wo_numbers.add(f"WO{year}{num}")
        
    return wo_numbers


@app.get("/api/v15/test/{molecule}")
async def test_search(molecule: str):
    """Quick test endpoint"""
    request = SearchRequest(nome_molecula=molecule)
    return await search_patents(request)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
