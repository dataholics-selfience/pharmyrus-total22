"""
PHARMYRUS V16.1 - LIGHTWEIGHT API SERVICE
FastAPI sem Playwright - Apenas httpx + proxies
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import asyncio
from lightweight_crawler import LightweightCrawler

app = FastAPI(
    title="Pharmyrus V16.1 Lightweight",
    description="Patent search with 14 API keys - NO Playwright",
    version="16.1.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global crawler instance
crawler = None


class SearchRequest(BaseModel):
    nome_molecula: str
    nome_comercial: Optional[str] = None
    dev_codes: Optional[List[str]] = None


class SearchResponse(BaseModel):
    molecule: str
    wo_numbers: List[str]
    br_numbers: List[str]
    summary: dict


@app.on_event("startup")
async def startup():
    """Initialize crawler on startup"""
    global crawler
    print("\n🚀 Starting Pharmyrus V16.1 Lightweight...")
    
    crawler = LightweightCrawler()
    await crawler.initialize()
    
    print("✅ Pharmyrus ready!")


@app.get("/")
async def root():
    """Health check"""
    return {
        "service": "Pharmyrus V16.1 Lightweight",
        "status": "online",
        "version": "16.1.0",
        "features": [
            "14 API keys pool (5 WebShare + 3 ProxyScrape + 6 ScrapingBee)",
            "200+ proxies rotating",
            "httpx async requests (NO Playwright)",
            "WO + BR number extraction",
            "Lightweight deployment"
        ]
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    if not crawler:
        return {"status": "initializing"}
    
    return {
        "status": "healthy",
        "proxies_available": len(crawler.proxies),
        "key_pool_status": "active",
        "engine": "httpx (lightweight)"
    }


@app.get("/api/v16/test/{molecule}")
async def test_molecule(molecule: str):
    """Simple test endpoint - returns mock data immediately"""
    return {
        "status": "success",
        "molecule": molecule,
        "test": True,
        "message": "This is a test endpoint. Use POST /api/search for real searches.",
        "system_info": {
            "version": "16.1.0",
            "engine": "httpx lightweight",
            "proxies": len(crawler.proxies) if crawler else 0,
            "keys": 14
        }
    }


@app.post("/api/search", response_model=SearchResponse)
async def search_molecule(request: SearchRequest):
    """
    Search for molecule patents
    
    Returns WO numbers and BR numbers
    """
    if not crawler:
        raise HTTPException(status_code=503, detail="Crawler not initialized")
    
    try:
        result = await crawler.search_molecule(
            molecule=request.nome_molecula,
            dev_codes=request.dev_codes or []
        )
        
        return SearchResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status")
async def get_status():
    """Get key pool status"""
    if not crawler:
        raise HTTPException(status_code=503, detail="Crawler not initialized")
    
    # Get stats from key pool
    stats = {
        'total_keys': len(crawler.key_pool.keys),
        'total_proxies': len(crawler.proxies),
        'total_requests': crawler.key_pool.total_requests,
        'total_success': crawler.key_pool.total_success,
        'total_failures': crawler.key_pool.total_failures,
        'engine': 'httpx (lightweight - NO Playwright)'
    }
    
    # Group by service
    by_service = {}
    for key in crawler.key_pool.keys:
        if key.service not in by_service:
            by_service[key.service] = {
                'count': 0,
                'quota_total': 0,
                'quota_used': 0,
                'quota_remaining': 0
            }
        
        by_service[key.service]['count'] += 1
        by_service[key.service]['quota_total'] += key.quota_limit
        by_service[key.service]['quota_used'] += key.used_count
        by_service[key.service]['quota_remaining'] += key.quota_remaining
    
    return {
        'global': stats,
        'by_service': by_service
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
