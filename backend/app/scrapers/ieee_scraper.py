import requests
from bs4 import BeautifulSoup
from typing import List, Dict
from datetime import datetime
import time
import re
import json

class IEEEScraper:
    """Scraper for IEEE Xplore journals"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.use_selenium = True  # Flag to enable/disable Selenium
    
    def scrape_journal(self, journal_url: str, journal_id: str) -> List[Dict]:
        """
        Scrape papers from an IEEE journal
        Returns list of paper dictionaries
        """
        papers = []
        
        try:
            print(f"Scraping journal: {journal_url}")
            
            # Try Selenium first (best for JavaScript-heavy sites)
            if self.use_selenium:
                try:
                    from app.scrapers.ieee_selenium_scraper import IEEESeleniumScraper
                    selenium_scraper = IEEESeleniumScraper()
                    papers = selenium_scraper.scrape_journal(journal_url, journal_id)
                    
                    if papers:
                        print(f"  Selenium scraping successful: {len(papers)} papers found")
                        return papers
                except Exception as e:
                    print(f"  Selenium scraping failed: {e}")
                    print(f"  Falling back to HTML scraping...")
            
            # Fallback to HTML scraping
            papers = self._scrape_via_html(journal_url, journal_id)
            
            if not papers:
                # Last resort: return informative mock data
                papers = self._get_mock_data(journal_url, journal_id)
            
        except Exception as e:
            print(f"Error scraping {journal_url}: {e}")
            papers = self._get_mock_data(journal_url, journal_id)
        
        return papers
    
    def _scrape_via_html(self, journal_url: str, journal_id: str) -> List[Dict]:
        """Scrape papers from HTML (limited due to JavaScript)"""
        papers = []
        
        try:
            response = self.session.get(journal_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try to find any document links in the initial HTML
            links = soup.find_all('a', href=re.compile(r'/document/\d+'))
            
            print(f"  Found {len(links)} document links in HTML")
            
            seen_urls = set()
            for link in links[:20]:
                href = link.get('href', '')
                if href and href not in seen_urls:
                    seen_urls.add(href)
                    
                    title = link.get_text(strip=True)
                    if title and len(title) > 10:
                        paper = {
                            'title': title,
                            'authors': ['Unknown'],
                            'abstract': 'Abstract not available. This paper was found but detailed information requires JavaScript rendering. Click the link to view on IEEE Xplore.',
                            'url': f"https://ieeexplore.ieee.org{href}" if href.startswith('/') else href,
                            'publishedDate': datetime.now().strftime('%Y-%m-%d'),
                            'journalId': journal_id,
                            'topics': []
                        }
                        papers.append(paper)
            
        except Exception as e:
            print(f"  HTML scrape failed: {e}")
        
        return papers
    
    def _get_mock_data(self, journal_url: str, journal_id: str) -> List[Dict]:
        """Return informative mock data explaining the limitation"""
        return [
            {
                'title': 'IEEE Xplore Scraping Limitation',
                'authors': ['System Message'],
                'abstract': 'IEEE Xplore uses JavaScript to load paper content dynamically. Selenium scraping was attempted but failed. To get real papers, you may need to: (1) Install Chrome browser, (2) Check if ChromeDriver is properly installed, or (3) Use IEEE\'s official API with an API key. The journal URL is: ' + journal_url,
                'url': journal_url,
                'publishedDate': datetime.now().strftime('%Y-%m-%d'),
                'journalId': journal_id,
                'topics': []
            }
        ]

