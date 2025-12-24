"""
V8 Triple-Source Patent Intelligence API
FastAPI with comprehensive debug endpoints
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import logging
import sys

from app.services.v8_orchestrator import V8TripleSourceOrchestrator

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Pharmyrus V8 - Triple-Source Patent Intelligence",
    description="Multi-source patent discovery with EPO OPS + WIPO + INPI",
    version="8.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request model
class PatentSearchRequest(BaseModel):
    molecule_name: str
    brand_name: Optional[str] = None
    target_countries: List[str] = ['BR']


# Initialize orchestrator
logger.info("✅ V8 Triple-Source Orchestrator initialized")
orchestrator = V8TripleSourceOrchestrator()


@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "version": "8.0.0",
        "features": [
            "EPO OPS API (applicant filter)",
            "WIPO Patentscope",
            "INPI crawler integration",
            "Cortellis baseline comparison",
            "Comprehensive debug"
        ]
    }


@app.post("/api/v8/search")
async def search_patents(request: PatentSearchRequest):
    """
    V8 Triple-Source Patent Search
    
    Features:
    - EPO OPS API for WO discovery (by applicant)
    - WIPO Patentscope cross-validation
    - EPO INPADOC families for BR extraction
    - INPI crawler validation
    - Cortellis baseline comparison
    - Comprehensive debug and statistics
    """
    
    logger.info(f"\n🔍 New V8 search request: {request.molecule_name}")
    
    try:
        results = await orchestrator.search(
            molecule_name=request.molecule_name,
            brand_name=request.brand_name,
            target_countries=request.target_countries
        )
        
        return results
        
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v8/test/darolutamide")
async def test_darolutamide():
    """
    Quick test with Darolutamide
    
    Returns results with Cortellis baseline comparison
    """
    
    logger.info("\n🧪 Running Darolutamide test...")
    
    try:
        results = await orchestrator.search(
            molecule_name="Darolutamide",
            brand_name="Nubeqa",
            target_countries=["BR"]
        )
        
        return results
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
