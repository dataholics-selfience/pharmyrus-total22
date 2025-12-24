"""
Google Patents Crawler - Playwright
Scraping direto sem APIs externas
Usado como fallback quando INPI não retorna WOs suficientes
"""
import re
import asyncio
from typing import List, Dict, Any
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout


class GooglePatentsCrawler:
    """
    Crawler próprio para Google Patents
    SEM APIs externas, SEM SerpAPI
    Apenas Playwright + scraping direto
    """
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.base_url = "https://patents.google.com"
    
    async def search_wo_numbers(
        self, 
        molecule: str, 
        companies: List[str] = None,
        years: List[str] = None,
        max_results: int = 20
    ) -> List[str]:
        """
        Busca WO numbers via scraping direto Google Patents
        
        Args:
            molecule: Nome da molécula
            companies: Lista de empresas (ex: ['Bayer', 'Orion'])
            years: Anos para buscar (ex: ['2016', '2018', '2021'])
            max_results: Máximo de WO numbers
            
        Returns:
            Lista de WO numbers únicos
        """
        if companies is None:
            companies = ['Bayer', 'Orion']
        
        if years is None:
            years = ['2016', '2018', '2020', '2021', '2023']
        
        all_wo_numbers = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            page = await context.new_page()
            
            try:
                # Estratégia 1: Busca por molécula + empresa
                for company in companies:
                    query = f"{molecule} {company} patent"
                    wos = await self._search_and_extract(page, query)
                    all_wo_numbers.extend(wos)
                    await asyncio.sleep(1)  # Rate limiting
                
                # Estratégia 2: Busca por molécula + ano
                for year in years:
                    query = f"{molecule} WO{year}"
                    wos = await self._search_and_extract(page, query)
                    all_wo_numbers.extend(wos)
                    await asyncio.sleep(1)
                
            finally:
                await browser.close()
        
        # Deduplicar e limitar
        unique_wos = list(dict.fromkeys(all_wo_numbers))[:max_results]
        
        print(f"  ✓ Google Patents Crawler: {len(unique_wos)} WO numbers")
        return unique_wos
    
    async def _search_and_extract(self, page, query: str) -> List[str]:
        """Executa uma busca e extrai WO numbers"""
        try:
            url = f"{self.base_url}/?q={query}&num=20"
            
            await page.goto(url, timeout=30000, wait_until='domcontentloaded')
            await page.wait_for_timeout(2000)  # Esperar JS carregar
            
            # Extrair HTML
            html = await page.content()
            
            # Padrões de extração
            patterns = [
                r'WO[\s-]?(\d{4})[\s/-]?(\d{6})',  # WO2016162604
                r'/patent/WO(\d{4})(\d{6})',        # /patent/WO2016162604
            ]
            
            wo_numbers = []
            for pattern in patterns:
                matches = re.findall(pattern, html, re.I)
                for year, num in matches:
                    wo = f'WO{year}{num}'
                    if wo not in wo_numbers:
                        wo_numbers.append(wo)
            
            if wo_numbers:
                print(f"    → Found {len(wo_numbers)} WOs from: {query}")
            
            return wo_numbers
            
        except PlaywrightTimeout:
            print(f"    ✗ Timeout for: {query}")
            return []
        except Exception as e:
            print(f"    ✗ Error for '{query}': {e}")
            return []
    
    async def get_patent_details(self, patent_id: str) -> Dict[str, Any]:
        """
        Busca detalhes completos de uma patente
        
        Args:
            patent_id: WO number ou publication number
            
        Returns:
            Dict com title, abstract, assignee, inventors, etc
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page = await browser.new_page()
            
            try:
                url = f"{self.base_url}/patent/{patent_id}"
                await page.goto(url, timeout=30000)
                await page.wait_for_timeout(2000)
                
                # Extrair informações estruturadas
                details = {
                    'patent_id': patent_id,
                    'title': '',
                    'abstract': '',
                    'assignee': '',
                    'inventors': [],
                    'filing_date': '',
                    'publication_date': '',
                    'url': url
                }
                
                # Title
                try:
                    title_elem = await page.query_selector('meta[name="DC.title"]')
                    if title_elem:
                        details['title'] = await title_elem.get_attribute('content')
                except:
                    pass
                
                # Abstract
                try:
                    abstract_elem = await page.query_selector('meta[name="DC.description"]')
                    if abstract_elem:
                        details['abstract'] = await abstract_elem.get_attribute('content')
                except:
                    pass
                
                # Assignee
                try:
                    assignee_elem = await page.query_selector('dd[itemprop="assigneeCurrent"]')
                    if assignee_elem:
                        details['assignee'] = await assignee_elem.inner_text()
                except:
                    pass
                
                # Filing date
                try:
                    filing_elem = await page.query_selector('time[itemprop="filingDate"]')
                    if filing_elem:
                        details['filing_date'] = await filing_elem.get_attribute('datetime')
                except:
                    pass
                
                return details
                
            except Exception as e:
                print(f"    ✗ Error getting details for {patent_id}: {e}")
                return {'patent_id': patent_id, 'error': str(e)}
            finally:
                await browser.close()
    
    async def search_worldwide_applications(self, wo_number: str) -> List[str]:
        """
        Busca aplicações worldwide de um WO
        Retorna BR numbers encontrados
        
        Args:
            wo_number: WO number (ex: WO2016162604)
            
        Returns:
            Lista de BR numbers
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page = await browser.new_page()
            
            try:
                url = f"{self.base_url}/patent/{wo_number}"
                await page.goto(url, timeout=30000)
                await page.wait_for_timeout(3000)
                
                # Clicar em "Worldwide applications"
                try:
                    worldwide_btn = await page.query_selector('a[href*="worldwide"]')
                    if worldwide_btn:
                        await worldwide_btn.click()
                        await page.wait_for_timeout(2000)
                except:
                    pass
                
                # Extrair HTML
                html = await page.content()
                
                # Procurar por BR patents
                br_matches = re.findall(r'BR[\s-]?(\d{10,})', html, re.I)
                br_numbers = [f'BR{num}' for num in br_matches]
                br_numbers = list(dict.fromkeys(br_numbers))[:20]
                
                if br_numbers:
                    print(f"    → WO{wo_number}: Found {len(br_numbers)} BR applications")
                
                return br_numbers
                
            except Exception as e:
                print(f"    ✗ Error getting worldwide for {wo_number}: {e}")
                return []
            finally:
                await browser.close()


# ========================================
# Funções auxiliares para uso fácil
# ========================================

async def quick_search_wo_numbers(
    molecule: str,
    companies: List[str] = None,
    years: List[str] = None
) -> List[str]:
    """
    Busca rápida de WO numbers
    
    Usage:
        wos = await quick_search_wo_numbers("Darolutamide")
    """
    crawler = GooglePatentsCrawler(headless=True)
    return await crawler.search_wo_numbers(molecule, companies, years)


async def quick_get_details(patent_id: str) -> Dict[str, Any]:
    """
    Busca rápida de detalhes de patente
    
    Usage:
        details = await quick_get_details("WO2016162604")
    """
    crawler = GooglePatentsCrawler(headless=True)
    return await crawler.get_patent_details(patent_id)


# ========================================
# EXEMPLO DE USO
# ========================================

if __name__ == "__main__":
    async def main():
        # Teste 1: Buscar WO numbers
        print("\n=== TESTE 1: Buscar WO Numbers ===")
        crawler = GooglePatentsCrawler()
        
        wos = await crawler.search_wo_numbers(
            molecule="Darolutamide",
            companies=["Bayer", "Orion"],
            years=["2016", "2018", "2021", "2023"]
        )
        
        print(f"\nEncontrados: {len(wos)} WO numbers")
        for wo in wos[:10]:
            print(f"  - {wo}")
        
        # Teste 2: Detalhes de uma patente
        if wos:
            print(f"\n=== TESTE 2: Detalhes de {wos[0]} ===")
            details = await crawler.get_patent_details(wos[0])
            print(f"Title: {details.get('title', 'N/A')}")
            print(f"Assignee: {details.get('assignee', 'N/A')}")
        
        # Teste 3: Worldwide applications
        if wos:
            print(f"\n=== TESTE 3: BR Applications de {wos[0]} ===")
            br_patents = await crawler.search_worldwide_applications(wos[0])
            print(f"BR patents: {len(br_patents)}")
            for br in br_patents[:5]:
                print(f"  - {br}")
    
    asyncio.run(main())
