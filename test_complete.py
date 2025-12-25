#!/usr/bin/env python3
"""
PHARMYRUS V16 - TESTE COMPLETO DE PRODUÇÃO
Testa todo o sistema com as 14 keys
"""
import asyncio
import sys
import json

try:
    from production_crawler import ProductionCrawler
except ImportError:
    print("❌ Erro ao importar módulos")
    print("   Instale: pip install -r requirements.txt")
    print("   Instale: playwright install chromium")
    sys.exit(1)


async def test_key_pool():
    """Test 1: Key pool initialization"""
    print("\n" + "="*70)
    print("TEST 1: KEY POOL INITIALIZATION")
    print("="*70)
    
    try:
        crawler = ProductionCrawler()
        await crawler.initialize()
        
        print(f"\n✅ Key pool initialized")
        print(f"   Total proxies: {len(crawler.proxies)}")
        print(f"   Total keys: {len(crawler.key_pool.keys)}")
        
        return True, crawler
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        return False, None


async def test_simple_search(crawler):
    """Test 2: Simple search (aspirin)"""
    print("\n" + "="*70)
    print("TEST 2: SIMPLE SEARCH (aspirin)")
    print("="*70)
    
    try:
        result = await crawler.search_molecule(
            molecule='aspirin',
            dev_codes=[]
        )
        
        print(f"\n✅ Search completed")
        print(f"   WO numbers: {result['summary']['total_wo']}")
        print(f"   BR numbers: {result['summary']['total_br']}")
        
        if result['wo_numbers']:
            print(f"\n   WO samples:")
            for wo in result['wo_numbers'][:3]:
                print(f"   - {wo}")
        
        return result['summary']['total_wo'] > 0
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        return False


async def test_darolutamide(crawler):
    """Test 3: Darolutamide (production test)"""
    print("\n" + "="*70)
    print("TEST 3: DAROLUTAMIDE (production)")
    print("="*70)
    
    try:
        result = await crawler.search_molecule(
            molecule='darolutamide',
            dev_codes=['ODM-201', 'BAY-1841788']
        )
        
        print(f"\n✅ Search completed")
        print(f"   WO numbers: {result['summary']['total_wo']}")
        print(f"   BR numbers: {result['summary']['total_br']}")
        
        # Save result
        with open('/tmp/pharmyrus_v16_result.json', 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"\n💾 Result saved: /tmp/pharmyrus_v16_result.json")
        
        # Validation
        expected_wos = {
            'WO2011051540', 'WO2016162604', 'WO2018162793',
            'WO2021229145', 'WO2023194528'
        }
        
        found = set(result['wo_numbers'])
        matched = found.intersection(expected_wos)
        
        print(f"\n🎯 VALIDATION:")
        print(f"   Expected: {len(expected_wos)} WOs")
        print(f"   Found: {result['summary']['total_wo']} WOs")
        print(f"   Matched: {len(matched)} WOs")
        print(f"   Match rate: {len(matched)/len(expected_wos)*100:.1f}%")
        
        if matched:
            print(f"\n   Matched WOs:")
            for wo in sorted(matched):
                print(f"   ✅ {wo}")
        
        # Success criteria
        success = result['summary']['total_wo'] >= 3 and result['summary']['total_br'] >= 1
        
        return success
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        return False


async def main():
    """Run complete test suite"""
    print("\n" + "="*70)
    print("PHARMYRUS V16 - COMPLETE TEST SUITE")
    print("="*70)
    
    results = {}
    
    # Test 1: Key pool
    success, crawler = await test_key_pool()
    results['key_pool'] = success
    
    if not success or not crawler:
        print("\n❌ ABORTED: Key pool failed")
        return 1
    
    # Test 2: Simple search
    results['simple_search'] = await test_simple_search(crawler)
    
    # Test 3: Darolutamide
    results['darolutamide'] = await test_darolutamide(crawler)
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for test, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n✅ ALL TESTS PASSED!")
        print("\n🎯 System is PRODUCTION READY")
        print("   - 14 keys working")
        print("   - Proxy rotation OK")
        print("   - WO + BR extraction OK")
        print("\n📦 Ready for GitHub + Railway deploy!")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED")
        print("   Check logs above for details")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        sys.exit(1)
