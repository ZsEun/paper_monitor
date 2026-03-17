from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from typing import List, Dict
from datetime import datetime
import time

class IEEESeleniumScraper:
    """Selenium-based scraper for IEEE Xplore journals"""
    
    def __init__(self):
        self.driver = None
    
    def _init_driver(self):
        """Initialize Chrome driver with headless mode"""
        if self.driver:
            return
        
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')  # Use new headless mode
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-setuid-sandbox')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        # Add options to prevent crashes
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-infobars')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(30)
            print("Chrome driver initialized successfully")
        except Exception as e:
            print(f"Error initializing Chrome driver: {e}")
            raise
    
    def scrape_journal(self, journal_url: str, journal_id: str) -> List[Dict]:
        """
        Scrape papers from an IEEE journal using Selenium
        Handles pagination to get all papers from the issue
        Returns list of paper dictionaries
        """
        papers = []
        
        try:
            print(f"Scraping journal with Selenium: {journal_url}")
            
            self._init_driver()
            
            # Track seen titles across all pages
            seen_titles = set()
            page_number = 1
            
            # First pass: collect all paper metadata from listing pages
            while True:
                # Construct URL for current page
                if page_number == 1:
                    current_url = journal_url
                else:
                    # Add pagination parameters
                    if '?' in journal_url:
                        current_url = f"{journal_url}&pageNumber={page_number}"
                    else:
                        current_url = f"{journal_url}?pageNumber={page_number}"
                
                print(f"  Scraping page {page_number}: {current_url}")
                
                # Load the page
                self.driver.get(current_url)
                
                # Wait for content to load
                wait = WebDriverWait(self.driver, 15)
                
                # Try multiple selectors to find papers
                paper_selectors = [
                    (By.CSS_SELECTOR, 'xpl-results-item'),
                    (By.CSS_SELECTOR, '.List-results-items'),
                    (By.CSS_SELECTOR, '.result-item'),
                    (By.CSS_SELECTOR, 'div[class*="result"]'),
                ]
                
                paper_elements = []
                for selector_type, selector_value in paper_selectors:
                    try:
                        wait.until(EC.presence_of_element_located((selector_type, selector_value)))
                        paper_elements = self.driver.find_elements(selector_type, selector_value)
                        if paper_elements:
                            print(f"    Found {len(paper_elements)} items using selector: {selector_value}")
                            break
                    except:
                        continue
                
                # If still no papers, try finding document links
                if not paper_elements:
                    print("    No paper elements found, trying to find document links...")
                    time.sleep(3)  # Give more time for JavaScript to load
                    paper_elements = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="/document/"]')
                    print(f"    Found {len(paper_elements)} document links")
                
                # If no papers found on this page, we've reached the end
                if not paper_elements:
                    print(f"    No papers found on page {page_number}, stopping pagination")
                    break
                
                # Extract paper information from current page (without abstracts yet)
                papers_on_page = 0
                for element in paper_elements:
                    try:
                        paper = self._extract_paper_metadata(element, journal_url, journal_id)
                        if paper and paper['title'] not in seen_titles:
                            seen_titles.add(paper['title'])
                            papers.append(paper)
                            papers_on_page += 1
                    except Exception as e:
                        print(f"    Error extracting paper: {e}")
                        continue
                
                print(f"    Extracted {papers_on_page} new papers from page {page_number}")
                
                # Check if there's a next page button
                try:
                    # Look for next page button or pagination indicator
                    next_buttons = self.driver.find_elements(By.CSS_SELECTOR, 
                        'button[aria-label*="next"], a[aria-label*="next"], .next-page, [class*="next"]')
                    
                    # Also check if we can find pagination info
                    pagination_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                        '.pagination, [class*="pagination"]')
                    
                    has_next = False
                    if next_buttons:
                        for btn in next_buttons:
                            if btn.is_enabled() and btn.is_displayed():
                                has_next = True
                                break
                    
                    # If no clear next button, check if we got a full page of results
                    # IEEE typically shows 25-30 papers per page
                    if not has_next and papers_on_page < 20:
                        print(f"    Only {papers_on_page} papers on this page, likely the last page")
                        break
                    
                    if not has_next and not pagination_elements:
                        print(f"    No next page button found, stopping pagination")
                        break
                    
                except Exception as e:
                    print(f"    Error checking for next page: {e}")
                    # If we can't determine pagination, stop after first page
                    break
                
                page_number += 1
                
                # Safety limit to prevent infinite loops
                if page_number > 10:
                    print(f"    Reached safety limit of 10 pages, stopping")
                    break
                
                # Small delay between pages
                time.sleep(2)
            
            print(f"  Collected {len(papers)} papers metadata across {page_number} page(s)")
            
            # Second pass: fetch abstracts for all papers
            print(f"  Fetching abstracts for {len(papers)} papers...")
            for idx, paper in enumerate(papers):
                print(f"    [{idx+1}/{len(papers)}] Fetching abstract for: {paper['title'][:60]}...")
                paper['abstract'] = self._fetch_abstract_from_detail_page(paper['url'])
                time.sleep(1)  # Small delay between requests
            
            print(f"  Successfully extracted {len(papers)} unique papers with abstracts")
            
        except Exception as e:
            print(f"Error scraping with Selenium: {e}")
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None
        
        return papers
    
    def _extract_paper_metadata(self, element, journal_url: str, journal_id: str) -> Dict:
        """Extract paper metadata from a web element (without abstract)"""
        paper = {}
        
        try:
            # Try to find title
            title_selectors = ['h3', 'h2', '.article-title', 'a']
            title = None
            for selector in title_selectors:
                try:
                    title_elem = element.find_element(By.CSS_SELECTOR, selector)
                    title = title_elem.text.strip()
                    if title and len(title) > 10:
                        break
                except:
                    continue
            
            if not title:
                return None
            
            paper['title'] = title
            
            # Try to find URL
            url = journal_url
            try:
                link_elem = element.find_element(By.CSS_SELECTOR, 'a[href*="/document/"]')
                href = link_elem.get_attribute('href')
                if href:
                    url = href
            except:
                try:
                    # If element itself is a link
                    href = element.get_attribute('href')
                    if href and '/document/' in href:
                        url = href
                except:
                    pass
            
            paper['url'] = url
            
            # Try to find authors
            authors = []
            try:
                author_elements = element.find_elements(By.CSS_SELECTOR, '.author, [class*="author"]')
                for author_elem in author_elements:
                    author_name = author_elem.text.strip()
                    if author_name and author_name not in authors:
                        authors.append(author_name)
            except:
                pass
            
            paper['authors'] = authors if authors else ['Unknown']
            
            # Try to find publication date
            pub_date = datetime.now().strftime('%Y-%m-%d')
            try:
                date_elem = element.find_element(By.CSS_SELECTOR, '.date, [class*="date"], [class*="publish"]')
                date_text = date_elem.text.strip()
                if date_text:
                    pub_date = self._parse_date(date_text)
            except:
                pass
            
            paper['publishedDate'] = pub_date
            paper['journalId'] = journal_id
            paper['topics'] = []
            paper['abstract'] = ''  # Will be filled in second pass
            
            return paper
            
        except Exception as e:
            print(f"    Error in _extract_paper_metadata: {e}")
            return None
    
    def _fetch_abstract_from_detail_page(self, paper_url: str) -> str:
        """
        Navigate to paper detail page and extract the full abstract
        """
        try:
            print(f"      Fetching abstract from: {paper_url[:80]}...")
            
            # Navigate to the paper detail page
            self.driver.get(paper_url)
            
            # Wait for abstract to load
            wait = WebDriverWait(self.driver, 10)
            
            # Try multiple selectors for abstract
            abstract_selectors = [
                '.abstract-text',
                '.abstract',
                '[class*="abstract"]',
                'div.u-mb-1',
                '.article-content'
            ]
            
            for selector in abstract_selectors:
                try:
                    abstract_elem = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    abstract_text = abstract_elem.text.strip()
                    
                    # Clean up the abstract text
                    if abstract_text and len(abstract_text) > 50:
                        # Remove "Abstract:" prefix if present
                        if abstract_text.lower().startswith('abstract:'):
                            abstract_text = abstract_text[9:].strip()
                        
                        print(f"      ✓ Abstract found ({len(abstract_text)} chars)")
                        return abstract_text
                except:
                    continue
            
            print(f"      ⚠ No abstract found on detail page")
            return 'Abstract not available'
            
        except Exception as e:
            print(f"      Error fetching abstract: {e}")
            return 'Abstract not available'
    
    def _parse_date(self, date_text: str) -> str:
        """Parse date from various formats"""
        try:
            for fmt in ['%d %B %Y', '%B %Y', '%Y', '%d %b %Y', '%b %Y']:
                try:
                    date_obj = datetime.strptime(date_text, fmt)
                    return date_obj.strftime('%Y-%m-%d')
                except:
                    continue
        except:
            pass
        
        return datetime.now().strftime('%Y-%m-%d')
    
    def __del__(self):
        """Cleanup driver on deletion"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
