"""
V7 Enhanced Orchestrator - Multi-Source Patent Intelligence
Coordinates WIPO Patentscope + Google Patents Enhanced crawlers
"""
import asyncio
import time
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class V7EnhancedOrchestrator:
    """
    Production orchestrator with world-class crawling strategies
    
    Pipeline:
    1. PubChem: Get molecule intelligence
    2. WIPO Patentscope: Primary WO discovery + BR families
    3. Google Patents Enhanced: Secondary WO discovery + BR extraction
    4. Cross-reference & deduplicate
    5. Enrich BR patent data
    
    Features:
    - Multi-source crawling (WIPO + Google Patents)
    - Intelligent WO discovery (multiple strategies)
    - BR family extraction from WO
    - Deduplication & enrichment
    - Comprehensive statistics
    """
    
    def __init__(self):
        self.wipo_crawler = None
        self.google_crawler = None
        
    async def search(
        self,
        molecule_name: str,
        brand_name: Optional[str] = None,
        target_countries: List[str] = None
    ) -> Dict:
        """
        Main search orchestration
        
        Returns comprehensive patent intelligence report
        """
        start_time = time.time()
        
        if target_countries is None:
            target_countries = ["BR"]
        
        logger.info("\n" + "="*80)
        logger.info(f"🚀 V7 ENHANCED ORCHESTRATOR - {molecule_name}")
        logger.info("="*80)
        
        results = {
            'success': True,
            'molecule_name': molecule_name,
            'brand_name': brand_name,
            'target_countries': target_countries,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Phase 1: PubChem Intelligence
            logger.info("\n📊 PHASE 1: PubChem Intelligence")
            pubchem_data = await self._get_pubchem_data(molecule_name)
            results['molecule_info'] = pubchem_data
            
            # Phase 2: WIPO Patentscope Search
            logger.info("\n🌍 PHASE 2: WIPO Patentscope Search")
            wipo_results = await self._wipo_search(
                molecule_name,
                pubchem_data.get('dev_codes', []),
                pubchem_data.get('cas'),
                ['Bayer', 'Orion', 'Pfizer', 'Novartis', 'Roche']
            )
            results['wipo_discovery'] = wipo_results
            
            # Phase 3: Google Patents Enhanced Search
            logger.info("\n🔍 PHASE 3: Google Patents Enhanced Search")
            google_results = await self._google_search(
                molecule_name,
                pubchem_data.get('dev_codes', []),
                pubchem_data.get('cas')
            )
            results['google_discovery'] = google_results
            
            # Phase 4: Consolidate & Deduplicate
            logger.info("\n🔄 PHASE 4: Consolidate Results")
            consolidated = self._consolidate_results(wipo_results, google_results)
            results['consolidated'] = consolidated
            
            # Phase 5: BR Patents Summary
            logger.info("\n📋 PHASE 5: BR Patents Summary")
            br_summary = self._create_br_summary(consolidated)
            results['br_patents'] = br_summary['br_patents']
            results['summary'] = br_summary['summary']
            
            # Statistics
            execution_time = time.time() - start_time
            results['execution_time'] = execution_time
            
            # Final Summary
            self._print_final_summary(results)
            
        except Exception as e:
            logger.error(f"❌ Orchestration failed: {e}")
            results['success'] = False
            results['error'] = str(e)
        
        return results
    
    async def _get_pubchem_data(self, molecule_name: str) -> Dict:
        """Phase 1: Get molecule data from PubChem"""
        try:
            # Import PubChem service
            from app.services.pubchem import get_molecule_data
            
            data = await asyncio.to_thread(get_molecule_data, molecule_name)
            
            logger.info(f"   ✅ PubChem Data:")
            logger.info(f"      CID: {data.get('cid', 'N/A')}")
            logger.info(f"      CAS: {data.get('cas', 'N/A')}")
            logger.info(f"      Dev Codes: {len(data.get('dev_codes', []))}")
            logger.info(f"      Synonyms: {len(data.get('synonyms', []))}")
            
            return data
            
        except Exception as e:
            logger.warning(f"   ⚠️  PubChem failed: {e}")
            return {
                'cid': None,
                'cas': None,
                'dev_codes': [],
                'synonyms': []
            }
    
    async def _wipo_search(
        self,
        molecule_name: str,
        dev_codes: List[str],
        cas_number: Optional[str],
        applicants: List[str]
    ) -> Dict:
        """Phase 2: WIPO Patentscope comprehensive search"""
        try:
            from app.crawlers.wipo_crawler import WIPOPatentscopeCrawler
            
            async with WIPOPatentscopeCrawler() as crawler:
                results = await crawler.comprehensive_search(
                    molecule_name=molecule_name,
                    dev_codes=dev_codes,
                    cas_number=cas_number,
                    applicants=applicants
                )
                
                logger.info(f"   ✅ WIPO Results:")
                logger.info(f"      WO Numbers: {results['total_wo_found']}")
                logger.info(f"      BR Patents: {results['total_br_found']}")
                logger.info(f"      Strategies: {len(results['strategies_used'])}")
                
                return results
                
        except Exception as e:
            logger.warning(f"   ⚠️  WIPO search failed: {e}")
            return {
                'wo_numbers': [],
                'br_mapping': {},
                'total_wo_found': 0,
                'total_br_found': 0
            }
    
    async def _google_search(
        self,
        molecule_name: str,
        dev_codes: List[str],
        cas_number: Optional[str]
    ) -> Dict:
        """Phase 3: Google Patents Enhanced search"""
        try:
            from app.crawlers.google_patents_enhanced import GooglePatentsEnhancedCrawler
            
            async with GooglePatentsEnhancedCrawler() as crawler:
                results = await crawler.comprehensive_search_and_extract(
                    molecule_name=molecule_name,
                    dev_codes=dev_codes,
                    cas_number=cas_number
                )
                
                logger.info(f"   ✅ Google Patents Results:")
                logger.info(f"      WO Numbers: {results['total_wo_found']}")
                logger.info(f"      BR Patents: {results['total_br_found']}")
                logger.info(f"      Conversion Rate: {results['conversion_rate']*100:.1f}%")
                
                return results
                
        except Exception as e:
            logger.warning(f"   ⚠️  Google Patents search failed: {e}")
            return {
                'wo_numbers': [],
                'br_mapping': {},
                'all_br_patents': [],
                'total_wo_found': 0,
                'total_br_found': 0
            }
    
    def _consolidate_results(
        self,
        wipo_results: Dict,
        google_results: Dict
    ) -> Dict:
        """Phase 4: Consolidate and deduplicate results"""
        
        # Combine WO numbers
        all_wo = set(wipo_results.get('wo_numbers', []))
        all_wo.update(google_results.get('wo_numbers', []))
        
        # Combine BR mappings
        combined_br_mapping = {}
        
        # Add WIPO BR mappings
        for wo, br_list in wipo_results.get('br_mapping', {}).items():
            if wo not in combined_br_mapping:
                combined_br_mapping[wo] = set()
            combined_br_mapping[wo].update(br_list)
        
        # Add Google BR mappings
        for wo, br_list in google_results.get('br_mapping', {}).items():
            if wo not in combined_br_mapping:
                combined_br_mapping[wo] = set()
            combined_br_mapping[wo].update(br_list)
        
        # Convert sets to lists
        combined_br_mapping = {
            wo: list(br_set) 
            for wo, br_set in combined_br_mapping.items()
        }
        
        # Get all unique BR patents
        all_br = set()
        for br_list in combined_br_mapping.values():
            all_br.update(br_list)
        
        logger.info(f"   ✅ Consolidated:")
        logger.info(f"      Total WO: {len(all_wo)} (WIPO: {wipo_results.get('total_wo_found', 0)}, Google: {google_results.get('total_wo_found', 0)})")
        logger.info(f"      Total BR: {len(all_br)}")
        logger.info(f"      WO with BR: {len(combined_br_mapping)}")
        
        return {
            'wo_numbers': list(all_wo),
            'br_mapping': combined_br_mapping,
            'all_br_patents': list(all_br),
            'total_wo': len(all_wo),
            'total_br': len(all_br),
            'wo_with_br': len(combined_br_mapping)
        }
    
    def _create_br_summary(self, consolidated: Dict) -> Dict:
        """Phase 5: Create BR patents summary"""
        
        br_patents_list = []
        
        for br_num in consolidated['all_br_patents']:
            # Find which WO this BR came from
            source_wo = []
            for wo, br_list in consolidated['br_mapping'].items():
                if br_num in br_list:
                    source_wo.append(wo)
            
            br_patents_list.append({
                'number': br_num,
                'source_wo': source_wo,
                'source': 'wo_family'
            })
        
        # Sort by BR number
        br_patents_list.sort(key=lambda x: x['number'])
        
        summary = {
            'total_wo_found': consolidated['total_wo'],
            'total_br_found': consolidated['total_br'],
            'wo_with_br': consolidated['wo_with_br'],
            'conversion_rate': consolidated['wo_with_br'] / consolidated['total_wo'] if consolidated['total_wo'] > 0 else 0
        }
        
        logger.info(f"   ✅ BR Summary:")
        logger.info(f"      BR Patents: {summary['total_br_found']}")
        logger.info(f"      Conversion Rate: {summary['conversion_rate']*100:.1f}%")
        
        return {
            'br_patents': br_patents_list,
            'summary': summary
        }
    
    def _print_final_summary(self, results: Dict):
        """Print final execution summary"""
        logger.info("\n" + "="*80)
        logger.info("📊 FINAL SUMMARY")
        logger.info("="*80)
        
        summary = results.get('summary', {})
        
        logger.info(f"\n🎯 Results:")
        logger.info(f"   WO Numbers Found: {summary.get('total_wo_found', 0)}")
        logger.info(f"   BR Patents Found: {summary.get('total_br_found', 0)}")
        logger.info(f"   Conversion Rate: {summary.get('conversion_rate', 0)*100:.1f}%")
        
        logger.info(f"\n⏱️  Execution Time: {results.get('execution_time', 0):.1f}s")
        
        # List BR patents
        if results.get('br_patents'):
            logger.info(f"\n🇧🇷 BR Patents:")
            for i, patent in enumerate(results['br_patents'][:10], 1):
                wo_list = ', '.join(patent.get('source_wo', [])[:2])
                logger.info(f"   {i}. {patent['number']} (from: {wo_list})")
            
            if len(results['br_patents']) > 10:
                logger.info(f"   ... and {len(results['br_patents']) - 10} more")
        
        logger.info("\n" + "="*80)


# Test function
async def test_v7_orchestrator():
    """Test V7 orchestrator with Darolutamide"""
    orchestrator = V7EnhancedOrchestrator()
    
    results = await orchestrator.search(
        molecule_name="Darolutamide",
        brand_name="Nubeqa",
        target_countries=["BR"]
    )
    
    print("\n" + "="*80)
    print("V7 ORCHESTRATOR TEST COMPLETE")
    print("="*80)
    print(f"\nSuccess: {results['success']}")
    print(f"WO Found: {results.get('summary', {}).get('total_wo_found', 0)}")
    print(f"BR Found: {results.get('summary', {}).get('total_br_found', 0)}")
    print(f"Time: {results.get('execution_time', 0):.1f}s")


if __name__ == "__main__":
    asyncio.run(test_v7_orchestrator())
