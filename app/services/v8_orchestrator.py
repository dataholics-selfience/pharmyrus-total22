"""
V8 TRIPLE-SOURCE ORCHESTRATOR
Layered architecture with comprehensive debug and Cortellis comparison
"""

import asyncio
import logging
from typing import Dict, List, Set
from datetime import datetime

from app.crawlers.epo_ops import EPOOPSClient
from app.crawlers.wipo_crawler import WIPOCrawler
from app.crawlers.inpi_crawler import INPICrawler
from app.services.pubchem import PubChemService

logger = logging.getLogger(__name__)


# Cortellis baseline for Darolutamide
CORTELLIS_BASELINE = {
    'molecule': 'Darolutamide',
    'wo_numbers': [
        'WO2016162604',
        'WO2011051540',
        'WO2018162793',
        'WO2021229145',
        'WO2023194528',
        'WO2023222557',
        'WO2023161458'
    ],
    'br_patents': {
        'BR112017021636': 'WO2016162604',
        'BR112012008823': 'WO2011051540',
        'BR112019018458': 'WO2018162793',
        'BR112022022978': 'WO2021229145',
        'BR122025003584': 'WO2018162793',
        'BR112024020202': 'WO2023194528',
        'BR112024021896': 'WO2023222557',
        'BR112024016586': 'WO2023161458'
    }
}


class V8TripleSourceOrchestrator:
    """
    V8 Orchestrator: Triple-source patent intelligence
    
    LAYER 1: WO Discovery (Multi-Source)
      - EPO OPS API (primary, by applicant)
      - WIPO Patentscope (secondary, cross-validation)
      
    LAYER 2: BR Extraction (Dual-Source)
      - EPO OPS INPADOC families
      - INPI crawler (validation)
      
    LAYER 3: Debug & Statistics
      - Source comparison
      - Cortellis baseline comparison
      - Performance metrics
    """
    
    def __init__(self):
        self.pubchem = PubChemService()
        
    async def search(
        self,
        molecule_name: str,
        brand_name: Optional[str] = None,
        target_countries: List[str] = ['BR']
    ) -> Dict:
        """
        Execute triple-source patent search with debug
        
        Args:
            molecule_name: Molecule name (e.g., "Darolutamide")
            brand_name: Brand name (optional)
            target_countries: Target countries for patents
            
        Returns:
            Comprehensive results with debug info
        """
        start_time = datetime.now()
        
        logger.info("=" * 80)
        logger.info(f"🚀 V8 TRIPLE-SOURCE ORCHESTRATOR - {molecule_name}")
        logger.info("=" * 80)
        
        # PHASE 1: PubChem Intelligence
        logger.info("\n📊 PHASE 1: PubChem Intelligence")
        pubchem_data = await self._phase1_pubchem(molecule_name)
        
        # PHASE 2: Multi-Source WO Discovery
        logger.info("\n🌍 PHASE 2: Multi-Source WO Discovery")
        wo_discovery = await self._phase2_wo_discovery(molecule_name, pubchem_data)
        
        # PHASE 3: Multi-Source BR Extraction
        logger.info("\n🔍 PHASE 3: Multi-Source BR Extraction")
        br_extraction = await self._phase3_br_extraction(wo_discovery)
        
        # PHASE 4: Consolidate & Debug
        logger.info("\n📊 PHASE 4: Consolidate & Debug")
        results = await self._phase4_consolidate(
            molecule_name,
            pubchem_data,
            wo_discovery,
            br_extraction,
            start_time
        )
        
        # PHASE 5: Cortellis Comparison (if Darolutamide)
        if molecule_name.lower() == 'darolutamide':
            logger.info("\n🎯 PHASE 5: Cortellis Baseline Comparison")
            results['cortellis_comparison'] = self._compare_with_cortellis(results)
        
        return results
    
    async def _phase1_pubchem(self, molecule: str) -> Dict:
        """Get PubChem intelligence"""
        
        data = await self.pubchem.get_molecule_data(molecule)
        
        logger.info(f"   ✅ PubChem Data:")
        logger.info(f"      CID: {data.get('cid')}")
        logger.info(f"      CAS: {data.get('cas')}")
        logger.info(f"      Dev Codes: {len(data.get('dev_codes', []))}")
        logger.info(f"      Synonyms: {len(data.get('synonyms', []))}")
        
        return data
    
    async def _phase2_wo_discovery(self, molecule: str, pubchem_data: Dict) -> Dict:
        """
        Multi-source WO discovery with applicant filtering
        """
        
        # Define major pharma applicants
        applicants = [
            'Bayer',
            'Orion',
            'Pfizer',
            'Novartis',
            'Roche'
        ]
        
        discovery = {
            'epo': {'wo_numbers': [], 'statistics': {}},
            'wipo': {'wo_numbers': [], 'statistics': {}},
            'consolidated': set(),
            'debug': {
                'epo_only': set(),
                'wipo_only': set(),
                'overlap': set()
            }
        }
        
        # SOURCE 1: EPO OPS (Primary)
        logger.info("   🎯 Source 1: EPO OPS API")
        try:
            async with EPOOPSClient() as epo:
                epo_results = await epo.search_by_applicant(
                    molecule=molecule,
                    applicants=applicants,
                    max_results=30
                )
                
                discovery['epo']['wo_numbers'] = epo_results['wo_numbers']
                discovery['epo']['statistics'] = epo_results['statistics']
                discovery['consolidated'].update(epo_results['wo_numbers'])
                
                logger.info(f"      ✅ EPO: {len(epo_results['wo_numbers'])} WO")
                
        except Exception as e:
            logger.warning(f"      ⚠️  EPO failed: {e}")
        
        # SOURCE 2: WIPO Patentscope (Secondary)
        logger.info("   🎯 Source 2: WIPO Patentscope")
        try:
            async with WIPOCrawler() as wipo:
                wipo_results = await wipo.search_by_applicant(
                    molecule=molecule,
                    applicants=applicants[:2],  # Bayer, Orion only
                    max_per_applicant=15
                )
                
                discovery['wipo']['wo_numbers'] = wipo_results['wo_numbers']
                discovery['wipo']['statistics'] = wipo_results['statistics']
                discovery['consolidated'].update(wipo_results['wo_numbers'])
                
                logger.info(f"      ✅ WIPO: {len(wipo_results['wo_numbers'])} WO")
                
        except Exception as e:
            logger.warning(f"      ⚠️  WIPO failed: {e}")
        
        # Debug: Source comparison
        epo_set = set(discovery['epo']['wo_numbers'])
        wipo_set = set(discovery['wipo']['wo_numbers'])
        
        discovery['debug']['epo_only'] = epo_set - wipo_set
        discovery['debug']['wipo_only'] = wipo_set - epo_set
        discovery['debug']['overlap'] = epo_set & wipo_set
        
        discovery['consolidated'] = sorted(list(discovery['consolidated']))
        
        logger.info(f"\n   📊 WO Discovery Summary:")
        logger.info(f"      EPO: {len(epo_set)} WO")
        logger.info(f"      WIPO: {len(wipo_set)} WO")
        logger.info(f"      Overlap: {len(discovery['debug']['overlap'])} WO")
        logger.info(f"      Consolidated: {len(discovery['consolidated'])} WO")
        
        return discovery
    
    async def _phase3_br_extraction(self, wo_discovery: Dict) -> Dict:
        """
        Multi-source BR extraction
        """
        
        wo_numbers = wo_discovery['consolidated']
        
        if not wo_numbers:
            logger.warning("   ⚠️  No WO numbers to process")
            return {
                'epo_families': {},
                'inpi_validation': {},
                'consolidated_br': [],
                'statistics': {}
            }
        
        extraction = {
            'epo_families': {},  # WO -> [BR]
            'inpi_validation': {},
            'consolidated_br': set(),
            'statistics': {
                'wo_processed': 0,
                'wo_with_br': 0,
                'total_br': 0,
                'br_validated': 0
            }
        }
        
        # SOURCE 1: EPO OPS Families
        logger.info(f"   🎯 Source 1: EPO OPS INPADOC Families")
        logger.info(f"      Processing {len(wo_numbers)} WO numbers...")
        
        try:
            async with EPOOPSClient() as epo:
                # Process in batches to show progress
                batch_size = 5
                
                for i in range(0, len(wo_numbers), batch_size):
                    batch = wo_numbers[i:i+batch_size]
                    families = await epo.batch_get_families(batch)
                    extraction['epo_families'].update(families)
                    
                    # Progress
                    processed = min(i + batch_size, len(wo_numbers))
                    logger.info(f"      Progress: {processed}/{len(wo_numbers)}")
                    
                # Consolidate BR
                for wo, br_list in extraction['epo_families'].items():
                    extraction['consolidated_br'].update(br_list)
                    extraction['statistics']['wo_with_br'] += 1
                    
                extraction['statistics']['wo_processed'] = len(wo_numbers)
                extraction['statistics']['total_br'] = len(extraction['consolidated_br'])
                
                logger.info(f"      ✅ EPO Families: {len(extraction['consolidated_br'])} BR from {len(extraction['epo_families'])} WO")
                
        except Exception as e:
            logger.warning(f"      ⚠️  EPO families failed: {e}")
        
        # SOURCE 2: INPI Validation
        if extraction['consolidated_br']:
            logger.info(f"   🎯 Source 2: INPI Validation")
            
            try:
                async with INPICrawler() as inpi:
                    br_list = list(extraction['consolidated_br'])
                    validation = await inpi.validate_br_numbers(br_list)
                    extraction['inpi_validation'] = validation
                    
                    validated = sum(validation.values())
                    extraction['statistics']['br_validated'] = validated
                    
                    logger.info(f"      ✅ INPI: {validated}/{len(br_list)} BR validated")
                    
            except Exception as e:
                logger.warning(f"      ⚠️  INPI validation failed: {e}")
        
        extraction['consolidated_br'] = sorted(list(extraction['consolidated_br']))
        
        return extraction
    
    async def _phase4_consolidate(
        self,
        molecule: str,
        pubchem_data: Dict,
        wo_discovery: Dict,
        br_extraction: Dict,
        start_time: datetime
    ) -> Dict:
        """Consolidate all results with debug info"""
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Build WO -> BR mapping
        wo_br_mapping = {}
        for wo, br_list in br_extraction.get('epo_families', {}).items():
            wo_br_mapping[wo] = br_list
        
        results = {
            'molecule_info': {
                'name': molecule,
                'cid': pubchem_data.get('cid'),
                'cas': pubchem_data.get('cas'),
                'dev_codes': pubchem_data.get('dev_codes', [])
            },
            'wo_discovery': {
                'total_wo': len(wo_discovery['consolidated']),
                'wo_numbers': wo_discovery['consolidated'],
                'by_source': {
                    'epo': len(wo_discovery['epo']['wo_numbers']),
                    'wipo': len(wo_discovery['wipo']['wo_numbers']),
                    'overlap': len(wo_discovery['debug']['overlap'])
                },
                'debug': {
                    'epo_only': sorted(list(wo_discovery['debug']['epo_only'])),
                    'wipo_only': sorted(list(wo_discovery['debug']['wipo_only'])),
                    'overlap': sorted(list(wo_discovery['debug']['overlap']))
                }
            },
            'br_extraction': {
                'total_br': len(br_extraction['consolidated_br']),
                'br_numbers': br_extraction['consolidated_br'],
                'wo_br_mapping': wo_br_mapping,
                'statistics': br_extraction['statistics'],
                'validation': br_extraction.get('inpi_validation', {})
            },
            'performance': {
                'execution_time_seconds': round(execution_time, 2),
                'wo_per_second': round(len(wo_discovery['consolidated']) / max(execution_time, 1), 2),
                'br_per_second': round(len(br_extraction['consolidated_br']) / max(execution_time, 1), 2)
            }
        }
        
        logger.info(f"\n   ✅ Consolidated Results:")
        logger.info(f"      Total WO: {results['wo_discovery']['total_wo']}")
        logger.info(f"      Total BR: {results['br_extraction']['total_br']}")
        logger.info(f"      Execution Time: {execution_time:.1f}s")
        
        return results
    
    def _compare_with_cortellis(self, results: Dict) -> Dict:
        """
        Compare results with Cortellis baseline (Darolutamide only)
        """
        
        baseline = CORTELLIS_BASELINE
        found_wo = set(results['wo_discovery']['wo_numbers'])
        found_br = set(results['br_extraction']['br_numbers'])
        
        expected_wo = set(baseline['wo_numbers'])
        expected_br = set(baseline['br_patents'].keys())
        
        comparison = {
            'wo_comparison': {
                'expected': len(expected_wo),
                'found': len(found_wo),
                'match': len(found_wo & expected_wo),
                'missing': sorted(list(expected_wo - found_wo)),
                'extra': sorted(list(found_wo - expected_wo)),
                'match_rate': round(len(found_wo & expected_wo) / max(len(expected_wo), 1) * 100, 1)
            },
            'br_comparison': {
                'expected': len(expected_br),
                'found': len(found_br),
                'match': len(found_br & expected_br),
                'missing': sorted(list(expected_br - found_br)),
                'extra': sorted(list(found_br - expected_br)),
                'match_rate': round(len(found_br & expected_br) / max(len(expected_br), 1) * 100, 1)
            },
            'overall_assessment': 'unknown'
        }
        
        # Assessment
        wo_rate = comparison['wo_comparison']['match_rate']
        br_rate = comparison['br_comparison']['match_rate']
        
        if wo_rate >= 70 and br_rate >= 70:
            comparison['overall_assessment'] = '✅ EXCELLENT - Matches Cortellis'
        elif wo_rate >= 50 or br_rate >= 50:
            comparison['overall_assessment'] = '⚠️  GOOD - Partial match'
        else:
            comparison['overall_assessment'] = '❌ NEEDS IMPROVEMENT'
        
        logger.info(f"\n   🎯 Cortellis Comparison:")
        logger.info(f"      WO Match: {comparison['wo_comparison']['match']}/{comparison['wo_comparison']['expected']} ({wo_rate}%)")
        logger.info(f"      BR Match: {comparison['br_comparison']['match']}/{comparison['br_comparison']['expected']} ({br_rate}%)")
        logger.info(f"      Assessment: {comparison['overall_assessment']}")
        
        if comparison['wo_comparison']['missing']:
            logger.info(f"\n      Missing WO (vs Cortellis):")
            for wo in comparison['wo_comparison']['missing'][:5]:
                logger.info(f"         ❌ {wo}")
                
        if comparison['br_comparison']['missing']:
            logger.info(f"\n      Missing BR (vs Cortellis):")
            for br in comparison['br_comparison']['missing'][:5]:
                expected_wo = baseline['br_patents'].get(br, 'unknown')
                logger.info(f"         ❌ {br} ← {expected_wo}")
        
        return comparison


# Test function
async def test_v8_darolutamide():
    """Test V8 with Darolutamide"""
    
    orchestrator = V8TripleSourceOrchestrator()
    
    results = await orchestrator.search(
        molecule_name="Darolutamide",
        brand_name="Nubeqa",
        target_countries=["BR"]
    )
    
    import json
    print("\n" + "=" * 80)
    print("FINAL RESULTS:")
    print("=" * 80)
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_v8_darolutamide())
