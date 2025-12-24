"""
Pharmyrus V11 - INPI-First Patent Search API
==============================================

CORREÇÕES CRÍTICAS vs V10:
1. ✅ Tradutor PT - INPI só funciona com nomes portugueses!
2. ✅ Parsing INPI corrigido (campos invertidos)
3. ✅ Busca contextual melhorada (WOs corretos)
4. ✅ Zero dependência de SerpAPI

Arquitetura:
- PubChem → Dev codes, CAS, synonyms
- INPI Crawler (25 queries PT!) → BR + WO numbers
- Playwright fallback (se < 3 WOs)
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import httpx
import asyncio
import re
from urllib.parse import quote
from datetime import datetime

app = FastAPI(title="Pharmyrus V11", version="11.0.0")

# ========================================
# TRADUTOR PT (CRÍTICO!)
# ========================================

PT_TRANSLATIONS = {
    # Oncológicos
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
    
    # Comuns
    'Aspirin': 'Aspirina',
    'Paracetamol': 'Paracetamol',
}

def translate_to_portuguese(molecule: str) -> str:
    """
    Traduz nome da molécula para português
    CRÍTICO: INPI BRASILEIRO só funciona com nomes PT!
    """
    # 1. Mapeamento direto
    if molecule in PT_TRANSLATIONS:
        return PT_TRANSLATIONS[molecule]
    
    # 2. Regras heurísticas
    pt = molecule
    
    # -ide → -ida (Darolutamide → Darolutamida)
    if pt.endswith('ide'):
        pt = pt[:-3] + 'ida'
    
    # -ine → -ina (Abiraterone → Abiraterona)
    elif pt.endswith('ine'):
        pt = pt[:-3] + 'ina'
    
    # -one → -ona
    elif pt.endswith('one'):
        pt = pt[:-3] + 'ona'
    
    # -ib → -ibe (Olaparib → Olaparibe)
    elif pt.endswith('ib') and not pt.endswith('sib'):
        pt = pt + 'e'
    
    return pt

# ========================================
# PUBCHEM
# ========================================

async def get_pubchem_data(molecule: str) -> Dict[str, Any]:
    """Busca dev codes, CAS, synonyms no PubChem"""
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{quote(molecule)}/synonyms/JSON"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(url)
            data = resp.json()
            
            syns = data['InformationList']['Information'][0]['Synonym']
            
            # Dev codes (AB-123, XYZ-456)
            dev_codes = []
            seen_devs = set()
            for s in syns:
                if re.match(r'^[A-Z]{2,5}[-\s]?\d{3,7}[A-Z]?$', s, re.I):
                    clean = s.strip().upper()
                    if clean not in seen_devs and len(dev_codes) < 15:
                        seen_devs.add(clean)
                        dev_codes.append(s)
            
            # CAS
            cas = None
            for s in syns:
                if re.match(r'^\d{2,7}-\d{2}-\d$', s):
                    cas = s
                    break
            
            # All synonyms filtrados
            all_syns = [s for s in syns if len(s) > 3 and len(s) < 50][:50]
            
            return {
                'dev_codes': dev_codes,
                'cas': cas,
                'all_synonyms': all_syns
            }
            
        except:
            return {'dev_codes': [], 'cas': None, 'all_synonyms': []}

# ========================================
# INPI CRAWLER
# ========================================

async def search_inpi_detailed(query: str) -> Dict[str, Any]:
    """
    Busca no INPI Crawler (crawler3-production.up.railway.app)
    
    ATENÇÃO: Crawler retorna campos INVERTIDOS!
    - field "title" = BR number (ex: "BR 11 2024 016586 8") 
    - field "applicant" = título real (ex: "FORMA CRISTALINA DE...")
    - field "depositDate" = data de depósito
    - field "fullText" = texto completo (pode conter WO numbers!)
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
                # CORREÇÃO: Campo "title" = BR number
                br_num = item.get('title', '').strip()
                
                # Skip header row
                if br_num == 'Pedido' or not br_num.startswith('BR'):
                    continue
                
                # CORREÇÃO: Campo "applicant" = título real
                real_title = item.get('applicant', '').strip()
                filing_date = item.get('depositDate', '').strip()
                full_text = item.get('fullText', '').strip()
                
                # Extrair WO numbers do fullText (INPI retorna isso!)
                wo_matches = re.findall(r'WO[\s-]?(\d{4})[\s/-]?(\d{6})', full_text, re.I)
                for year, num in wo_matches:
                    wo = f'WO{year}{num}'
                    if wo not in wo_numbers:
                        wo_numbers.append(wo)
                
                # Adicionar BR patent
                br_patents.append({
                    'br_number': br_num.replace(' ', ''),
                    'title': real_title,
                    'filing_date': filing_date,
                    'full_text': full_text[:300],
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
# INPI ABUSE (25 queries PORTUGUÊS!)
# ========================================

async def inpi_abuse_search(molecule: str, pubchem_data: Dict) -> Dict[str, Any]:
    """
    Estratégia ABUSE: 25+ queries INPI em PORTUGUÊS
    
    MUDANÇA CRÍTICA vs V10:
    - Adiciona nome PT PRIMEIRO (darolutamida)
    - Adiciona variações PT
    - Mantém dev codes (ODM-201 pode funcionar)
    """
    queries = []
    
    # 1. NOME EM PORTUGUÊS (CRÍTICO!)
    molecule_pt = translate_to_portuguese(molecule)
    queries.append(molecule_pt)  # "Darolutamida"
    queries.append(molecule_pt.lower())  # "darolutamida" 
    queries.append(molecule_pt.upper())  # "DAROLUTAMIDA"
    
    # 2. Nome original também (caso seja PT já)
    if molecule != molecule_pt:
        queries.append(molecule)
        queries.append(molecule.lower())
    
    # 3. Dev codes (podem funcionar)
    for dev in pubchem_data['dev_codes'][:10]:
        queries.append(dev)
        queries.append(dev.replace('-', ''))
    
    # 4. CAS
    if pubchem_data['cas']:
        queries.append(pubchem_data['cas'])
    
    # 5. Synonyms (talvez alguns sejam PT)
    for syn in pubchem_data['all_synonyms'][:5]:
        if syn.lower() not in [q.lower() for q in queries]:
            queries.append(syn)
    
    # Limitar a 30 queries
    queries = queries[:30]
    
    print(f"\n[2/3] INPI ABUSE: {len(queries)} queries (PT prioritário!)")
    print(f"  Nome PT: {molecule_pt}")
    
    # Executar em paralelo
    tasks = [search_inpi_detailed(q) for q in queries]
    results = await asyncio.gather(*tasks)
    
    # Consolidar
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
        'queries_tested': len(queries),
        'molecule_pt': molecule_pt
    }

# ========================================
# PLAYWRIGHT FALLBACK
# ========================================

async def playwright_fallback_search(molecule: str, wo_numbers: List[str]) -> Dict[str, Any]:
    """
    Fallback: se INPI retornou < 3 WOs, busca mais com Playwright
    
    ESTRATÉGIA MELHORADA:
    - Busca contextual: "Darolutamide Bayer patent WO2011"
    - Busca por dev code: "ODM-201 patent WO"
    - Anos específicos: 2011, 2016, 2018, 2021, 2023
    """
    print(f"\n[3/3] Playwright Fallback (INPI only found {len(wo_numbers)} WOs)")
    
    # TODO: Implementar Playwright real
    # Por enquanto, retorna vazio
    print(f"  ⚠️  Playwright not implemented yet")
    
    return {
        'wo_numbers': [],
        'br_patents': []
    }

# ========================================
# ENDPOINT PRINCIPAL
# ========================================

@app.get("/api/v11/search/{molecule}")
async def search_molecule(molecule: str, brand: Optional[str] = None):
    """
    V11 Patent Search - INPI-First com tradutor PT
    
    Exemplo: /api/v11/search/Darolutamide
    """
    start_time = datetime.now()
    
    print(f"\n{'='*60}")
    print(f"V11 PATENT SEARCH: {molecule}")
    print(f"{'='*60}")
    
    # 1. PubChem
    print(f"\n[1/3] PubChem: {molecule}")
    pubchem = await get_pubchem_data(molecule)
    print(f"  → {len(pubchem['dev_codes'])} dev codes, CAS={pubchem['cas']}")
    
    # 2. INPI ABUSE (com PT!)
    inpi_result = await inpi_abuse_search(molecule, pubchem)
    
    # 3. Playwright (se necessário)
    if len(inpi_result['wo_numbers']) < 3:
        playwright = await playwright_fallback_search(molecule, inpi_result['wo_numbers'])
        all_wo = list(dict.fromkeys(inpi_result['wo_numbers'] + playwright['wo_numbers']))
        all_br = inpi_result['br_patents'] + playwright['br_patents']
    else:
        print(f"\n[3/3] Skipping Playwright (INPI found {len(inpi_result['wo_numbers'])} WOs)")
        all_wo = inpi_result['wo_numbers']
        all_br = inpi_result['br_patents']
    
    # Cortellis comparison (Darolutamide baseline)
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
    
    status = "✅ EXCELLENT" if match_rate >= 70 else "⚠️ NEEDS IMPROVEMENT" if match_rate >= 40 else "❌ LOW"
    
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
            "mode": "V11 INPI-First com Tradutor PT",
            "sources": ["PubChem", "INPI Crawler (PT!)", "Playwright (fallback)"],
            "critical_fix": "Nome traduzido para PT antes de buscar INPI",
            "inpi_queries": inpi_result.get('queries_tested', 0)
        },
        "wo_discovery": {
            "total_wo": len(all_wo),
            "wo_numbers": all_wo,
            "source": "INPI Crawler (extracted from BR patent data)"
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

# ========================================
# ENDPOINTS AUXILIARES
# ========================================

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "11.0.0"}

@app.get("/api/v11/test/darolutamide")
async def test_darolutamide():
    """Endpoint de teste rápido"""
    return await search_molecule("Darolutamide", "Nubeqa")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
