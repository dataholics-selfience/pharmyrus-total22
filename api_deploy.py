"""
V7 Enhanced API - FastAPI
Production-ready API with V7 orchestrator
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import logging
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Pharmyrus V7 Enhanced API",
    description="World-class patent intelligence with multi-source crawling",
    version="7.0.0"
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
class SearchRequest(BaseModel):
    molecule_name: str = Field(..., description="Molecule name")
    brand_name: Optional[str] = Field(None, description="Brand name")
    target_countries: List[str] = Field(default=["BR"], description="Target countries")


# Global orchestrator (initialized on startup)
orchestrator = None


@app.on_event("startup")
async def startup():
    """Initialize orchestrator on startup"""
    global orchestrator
    from app.services.v7_orchestrator import V7EnhancedOrchestrator
    orchestrator = V7EnhancedOrchestrator()
    logger.info("✅ V7 Enhanced Orchestrator initialized")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Pharmyrus V7 Enhanced API",
        "version": "7.0.0",
        "description": "World-class patent intelligence",
        "endpoints": {
            "health": "/health",
            "search": "/api/v7/search"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "7.0.0",
        "orchestrator": "ready" if orchestrator else "not_initialized"
    }


@app.post("/api/v7/search")
async def search_patents(request: SearchRequest):
    """
    Search patents using V7 Enhanced orchestrator
    
    Features:
    - WIPO Patentscope search
    - Google Patents Enhanced search
    - Multi-strategy WO discovery
    - BR family extraction
    - Comprehensive consolidation
    
    Returns detailed patent intelligence report
    """
    if not orchestrator:
        raise HTTPException(
            status_code=503,
            detail="Orchestrator not initialized"
        )
    
    try:
        logger.info(f"\n🔍 New search request: {request.molecule_name}")
        
        results = await orchestrator.search(
            molecule_name=request.molecule_name,
            brand_name=request.brand_name,
            target_countries=request.target_countries
        )
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
