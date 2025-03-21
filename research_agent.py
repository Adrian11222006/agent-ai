import requests
from bs4 import BeautifulSoup
import nltk
from nltk.tokenize import sent_tokenize
from langdetect import detect, DetectorFactory
import json
import time
from typing import List, Dict, Optional, Tuple
import hashlib
import os
from datetime import datetime, timedelta
import urllib.parse
import concurrent.futures
from urllib.parse import urlparse, urljoin

class ResearchAgent:
    def __init__(self, cache_dir: str = ".cache"):
        """
        Inicjalizacja agenta badawczego.
        
        Args:
            cache_dir: Ścieżka do katalogu cache
        """
        # Ustaw seed dla langdetect dla spójnych wyników
        DetectorFactory.seed = 0
        
        # Inicjalizacja NLTK
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt', quiet=True)
            
        # Konfiguracja cache
        self.cache_dir = cache_dir
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
            
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 2  # sekundy
        
        # Limity
        self.max_text_length = 100000  # maksymalna długość tekstu do analizy
        self.max_retries = 3  # maksymalna liczba prób pobrania strony

    def _rate_limit(self):
        """Implementacja rate limiting dla zapytań."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last_request)
            
        self.last_request_time = time.time()

    def search_web(self, query: str) -> List[Dict]:
        """
        Wyszukuje informacje w internecie używając DuckDuckGo.
        """
        try:
            # Wyszukiwanie przez DuckDuckGo
            results = self._search_duckduckgo(query)
            if not results:
                return []
                
            # Usuń duplikaty na podstawie URL
            seen_urls = set()
            unique_results = []
            for result in results:
                if result['url'] not in seen_urls:
                    seen_urls.add(result['url'])
                    unique_results.append(result)
            
            return unique_results[:5]  # Limit do 5 najlepszych wyników
            
        except Exception as e:
            print(f"Błąd podczas wyszukiwania: {e}")
            return []

    def _search_duckduckgo(self, query: str) -> List[Dict]:
        """
        Wyszukuje informacje przez DuckDuckGo.
        """
        try:
            self._rate_limit()
            
            # Przygotuj URL i parametry
            base_url = "https://html.duckduckgo.com/html/"
            params = {
                'q': query,
                'kl': 'pl-pl'  # Preferuj wyniki po polsku
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            response = requests.post(base_url, data=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            for result in soup.select('.result'):
                title_elem = result.select_one('.result__title')
                snippet_elem = result.select_one('.result__snippet')
                url_elem = result.select_one('.result__url')
                
                if not all([title_elem, snippet_elem, url_elem]):
                    continue
                    
                title = title_elem.get_text(strip=True)
                snippet = snippet_elem.get_text(strip=True)
                url = url_elem.get('href', '')
                
                if url and title and snippet:
                    results.append({
                        'title': title,
                        'url': url,
                        'summary': snippet,
                        'source': 'DuckDuckGo'
                    })
                    
            return results
            
        except Exception as e:
            print(f"Błąd podczas wyszukiwania DuckDuckGo: {e}")
            return []

    def get_page_content(self, url: str) -> Optional[str]:
        """
        Pobiera treść strony internetowej.
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Wykryj kodowanie
            if 'charset' in response.headers.get('content-type', '').lower():
                response.encoding = response.apparent_encoding
                
            return response.text
        except Exception as e:
            print(f"Błąd podczas pobierania strony {url}: {e}")
            return None

    def extract_main_content(self, html: str) -> str:
        """
        Wydobywa główną treść ze strony HTML.
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Usuń niepotrzebne elementy
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                element.decompose()
            
            # Znajdź główną treść
            main_content = ""
            
            # Szukaj w typowych kontenerach treści
            content_tags = soup.find_all(['article', 'main', 'div'], class_=['content', 'article', 'post'])
            if not content_tags:
                content_tags = soup.find_all(['p', 'article', 'section'])
            
            for tag in content_tags:
                text = tag.get_text(strip=True)
                if len(text) > 100:  # Ignoruj krótkie fragmenty
                    main_content += text + "\n\n"
                    if len(main_content) > self.max_text_length:
                        break
            
            return main_content.strip()
        except Exception as e:
            print(f"Błąd podczas ekstrakcji treści: {e}")
            return ""

    def process_query(self, query: str) -> Tuple[str, List[Dict]]:
        """
        Przetwarza zapytanie i zwraca wyniki wyszukiwania.
        """
        try:
            # Wyszukaj informacje tylko w DuckDuckGo
            results = self._search_duckduckgo(query)
            
            if not results:
                return "Nie znaleziono informacji na ten temat.", []
            
            # Usuń duplikaty na podstawie URL
            unique_results = []
            seen_urls = set()
            for result in results:
                if result['url'] not in seen_urls:
                    seen_urls.add(result['url'])
                    unique_results.append(result)
            
            # Ogranicz do 5 najlepszych wyników
            results = unique_results[:5]
            
            # Pobierz treść dla każdego wyniku
            sources = []
            content = []
            
            for result in results:
                try:
                    page_content = self.get_page_content(result['url'])
                    if page_content:
                        main_content = self.extract_main_content(page_content)
                        if main_content:
                            content.append(main_content[:1000])  # Skróć treść do 1000 znaków
                            sources.append({
                                'title': result['title'],
                                'url': result['url']
                            })
                except Exception as e:
                    print(f"Błąd podczas pobierania treści z {result['url']}: {str(e)}")
                    continue
            
            # Przygotuj podsumowanie
            if content:
                summary = "\n\n".join(content[:3])  # Użyj 3 pierwszych źródeł
                summary = summary[:1500]  # Ogranicz długość podsumowania
            else:
                summary = "Nie znaleziono informacji na ten temat."
            
            return summary, sources
            
        except Exception as e:
            print(f"Błąd podczas przetwarzania zapytania: {str(e)}")
            return "Wystąpił błąd podczas wyszukiwania.", []

def main():
    """Funkcja główna do testowania agenta."""
    agent = ResearchAgent()
    
    while True:
        try:
            query = input("\nO co chcesz się dowiedzieć? (wpisz 'exit' aby zakończyć): ").strip()
            
            if query.lower() == 'exit':
                break
            
            if not query:
                print("Zapytanie nie może być puste!")
                continue
            
            summary, sources = agent.process_query(query)
            
            print("\nPodsumowanie:")
            print("-" * 50)
            print(summary)
            
            if sources:
                print("\nŹródła:")
                for source in sources:
                    print(f"- {source['title']}")
                    print(f"  {source['url']}")
            
            print("-" * 50)
            
        except KeyboardInterrupt:
            print("\nPrzerwano działanie programu.")
            break
        except Exception as e:
            print(f"\nWystąpił nieoczekiwany błąd: {e}")

if __name__ == "__main__":
    main()
