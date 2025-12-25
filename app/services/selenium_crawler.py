"""
Selenium Stealth Crawler
Layer 2: Fallback when Playwright fails
"""
import time
from typing import List, Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from app.utils.user_agents import get_desktop_user_agent
from app.utils.delays import page_load_delay, search_delay, gaussian_delay


class SeleniumCrawler:
    """Selenium crawler with stealth configuration"""
    
    def __init__(self):
        self.driver: Optional[webdriver.Chrome] = None
        
    def __enter__(self):
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        
    def start(self):
        """Start browser with stealth configuration"""
        options = Options()
        
        # Headless mode
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-infobars')
        options.add_argument('--window-size=1920,1080')
        
        # Random user agent
        user_agent = get_desktop_user_agent()
        options.add_argument(f'user-agent={user_agent}')
        
        # Exclude automation flags
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Disable webdriver flag
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        # Create driver
        self.driver = webdriver.Chrome(options=options)
        
        # Inject stealth script
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.chrome = {
                    runtime: {}
                };
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
            '''
        })
        
        print(f"  🔧 Selenium started (UA: {user_agent[:50]}...)")
        
    def stop(self):
        """Stop browser"""
        if self.driver:
            self.driver.quit()
            
    def search_google(self, query: str) -> List[Dict[str, Any]]:
        """
        Search Google and extract results
        
        Args:
            query: Search query
            
        Returns:
            List of search results
        """
        results = []
        
        try:
            # Navigate to Google
            search_url = f"https://www.google.com/search?q={query}&num=20"
            self.driver.get(search_url)
            
            # Human-like delay
            time.sleep(gaussian_delay(2, 4))
            
            # Wait for results
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.g"))
            )
            
            # Extract results
            result_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.g")
            
            for elem in result_elements[:20]:
                try:
                    # Extract title
                    title_elem = elem.find_element(By.CSS_SELECTOR, "h3")
                    title = title_elem.text if title_elem else ""
                    
                    # Extract link
                    link_elem = elem.find_element(By.CSS_SELECTOR, "a")
                    link = link_elem.get_attribute('href') if link_elem else ""
                    
                    # Extract snippet
                    snippet = ""
                    try:
                        snippet_elem = elem.find_element(By.CSS_SELECTOR, "div[data-sncf], div.VwiC3b")
                        snippet = snippet_elem.text
                    except:
                        pass
                    
                    if title and link:
                        results.append({
                            'title': title,
                            'link': link,
                            'snippet': snippet
                        })
                except Exception as e:
                    continue
                    
            print(f"    ✓ Found {len(results)} results for '{query[:50]}...'")
            
        except Exception as e:
            print(f"    ✗ Selenium error: {str(e)[:100]}")
            
        return results
        
    def search_google_patents(self, query: str) -> List[Dict[str, Any]]:
        """
        Search Google Patents specifically
        
        Args:
            query: Patent search query
            
        Returns:
            List of patent results
        """
        results = []
        
        try:
            # Navigate to Google Patents
            search_url = f"https://patents.google.com/?q={query}&num=100"
            self.driver.get(search_url)
            
            # Wait for results
            time.sleep(gaussian_delay(3, 5))
            
            # Extract results
            result_elements = self.driver.find_elements(By.CSS_SELECTOR, "search-result-item")
            
            for elem in result_elements[:100]:
                try:
                    # Extract patent ID
                    id_elem = elem.find_element(By.CSS_SELECTOR, "span.patent-number")
                    patent_id = id_elem.text if id_elem else ""
                    
                    # Extract title
                    title_elem = elem.find_element(By.CSS_SELECTOR, "a.patent-title")
                    title = title_elem.text if title_elem else ""
                    
                    # Extract link
                    link = f"https://patents.google.com/patent/{patent_id}" if patent_id else ""
                    
                    if patent_id:
                        results.append({
                            'patent_id': patent_id,
                            'title': title,
                            'link': link
                        })
                except Exception as e:
                    continue
                    
            print(f"    ✓ Found {len(results)} patents for '{query[:50]}...'")
            
        except Exception as e:
            print(f"    ✗ Selenium Google Patents error: {str(e)[:100]}")
            
        return results


def test_crawler():
    """Test crawler"""
    with SeleniumCrawler() as crawler:
        results = crawler.search_google("Darolutamide patent WO")
        for r in results[:3]:
            print(f"  - {r['title']}")


if __name__ == "__main__":
    test_crawler()
