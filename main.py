"""
PHARMYRUS V16 - PRODUCTION API SERVICE
FastAPI com pool de 14 keys integrado
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import asyncio
from production_crawler import ProductionCrawler

app = FastAPI(
    title="Pharmyrus V16 Production",
    description="Patent search with 14 API keys pool",
    version="16.0.0"
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
    print("\n🚀 Starting Pharmyrus V16 Production...")
    
    crawler = ProductionCrawler()
    await crawler.initialize()
    
    print("✅ Pharmyrus ready!")


@app.get("/")
async def root():
    """Health check"""
    return {
        "service": "Pharmyrus V16 Production",
        "status": "online",
        "version": "16.0.0",
        "features": [
            "14 API keys pool (5 WebShare + 3 ProxyScrape + 6 ScrapingBee)",
            "Automatic proxy rotation",
            "WO + BR number extraction",
            "Stealth mode"
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
        "key_pool_status": "active"
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
        'total_failures': crawler.key_pool.total_failures
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
