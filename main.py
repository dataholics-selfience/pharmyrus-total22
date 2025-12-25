"""
PHARMYRUS V17 - HIGH-VOLUME PRODUCTION API
- IP diferente garantido
- Quarentena automática
- Paralelização
- Coleta real de WOs e BRs
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import asyncio
from high_volume_crawler import HighVolumeCrawler

app = FastAPI(
    title="Pharmyrus V17 Production",
    description="High-volume patent search with guaranteed IP rotation",
    version="17.0.0"
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
    proxy_stats: Optional[dict] = None


@app.on_event("startup")
async def startup():
    """Initialize crawler on startup"""
    global crawler
    print("\n🚀 Starting Pharmyrus V17 Production...")
    
    crawler = HighVolumeCrawler()
    await crawler.initialize()
    
    print("✅ Pharmyrus V17 ready!")


@app.get("/")
async def root():
    """Health check"""
    return {
        "service": "Pharmyrus V17 Production",
        "status": "online",
        "version": "17.0.0",
        "features": [
            "14 API keys pool",
            "200+ proxies with rotation",
            "IP diferente garantido por consulta",
            "Quarentena automática (3 falhas = 5 min ban)",
            "Paralelização (até 5 queries simultâneas)",
            "Coleta real de WOs e BRs"
        ]
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    if not crawler:
        return {"status": "initializing"}
    
    proxy_status = crawler.proxy_manager.get_status()
    
    return {
        "status": "healthy",
        "total_proxies": proxy_status['total_proxies'],
        "healthy_proxies": proxy_status['healthy_proxies'],
        "quarantined_proxies": proxy_status['quarantined_proxies'],
        "global_success_rate": f"{proxy_status['global_success_rate']*100:.1f}%",
        "version": "17.0.0"
    }


@app.get("/api/v17/test/{molecule}")
async def test_molecule(molecule: str):
    """Quick test endpoint"""
    if not crawler:
        raise HTTPException(status_code=503, detail="Crawler not initialized")
    
    proxy_status = crawler.proxy_manager.get_status()
    
    return {
        "status": "success",
        "molecule": molecule,
        "test": True,
        "message": "System ready. Use POST /api/search for real searches.",
        "system_info": {
            "version": "17.0.0",
            "total_proxies": proxy_status['total_proxies'],
            "healthy_proxies": proxy_status['healthy_proxies'],
            "quarantined_proxies": proxy_status['quarantined_proxies'],
            "keys": 14
        }
    }


@app.post("/api/search", response_model=SearchResponse)
async def search_molecule(request: SearchRequest):
    """
    HIGH-VOLUME search for molecule patents
    
    Features:
    - Parallel execution (5 concurrent queries)
    - IP rotation guaranteed
    - Quarantine bad proxies automatically
    - Real WO + BR collection
    """
    if not crawler:
        raise HTTPException(status_code=503, detail="Crawler not initialized")
    
    try:
        result = await crawler.search_molecule_parallel(
            molecule=request.nome_molecula,
            dev_codes=request.dev_codes or []
        )
        
        return SearchResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/proxy/status")
async def get_proxy_status():
    """Get detailed proxy pool status"""
    if not crawler:
        raise HTTPException(status_code=503, detail="Crawler not initialized")
    
    return crawler.proxy_manager.get_status()


@app.get("/api/status")
async def get_status():
    """Get complete system status"""
    if not crawler:
        raise HTTPException(status_code=503, detail="Crawler not initialized")
    
    proxy_status = crawler.proxy_manager.get_status()
    
    # Key pool stats
    key_stats = {
        'total_keys': len(crawler.key_pool.keys),
        'total_requests': crawler.key_pool.total_requests,
        'total_success': crawler.key_pool.total_success,
        'total_failures': crawler.key_pool.total_failures
    }
    
    return {
        'system': {
            'version': '17.0.0',
            'engine': 'httpx + advanced proxy rotation'
        },
        'keys': key_stats,
        'proxies': proxy_status
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
